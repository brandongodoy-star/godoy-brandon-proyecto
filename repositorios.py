import sqlite3

from fastapi import HTTPException

ESTADOS_ORDEN = ("recibido", "en reparacion", "listo", "entregado")
ESTADOS_EDITABLES = ("recibido", "en reparacion")


class RepositorioBase:
    """Operaciones comunes sobre una tabla. Cada repositorio hijo indica su tabla y columnas.

    Recibe la conexión abierta, así todo lo que se haga con ella queda en una sola transacción.
    """

    tabla = ""
    columnas: tuple[str, ...] = ()
    no_encontrado = "Registro no encontrado"

    def __init__(self, con: sqlite3.Connection):
        self.con = con

    def obtener_todos(self, **filtros) -> list[dict]:
        """Lista la tabla; los filtros con valor None se ignoran. Sus nombres vienen del código."""
        filtros = {campo: valor for campo, valor in filtros.items() if valor is not None}
        where = " AND ".join(f"{campo} = ?" for campo in filtros)
        consulta = f"SELECT * FROM {self.tabla}" + (f" WHERE {where}" if where else "")
        filas = self.con.execute(consulta + " ORDER BY id", list(filtros.values())).fetchall()
        return [dict(fila) for fila in filas]

    def obtener_por_id(self, registro_id: int) -> dict:
        fila = self.con.execute(
            f"SELECT * FROM {self.tabla} WHERE id = ?", (registro_id,)
        ).fetchone()
        if fila is None:
            raise HTTPException(status_code=404, detail=self.no_encontrado)
        return dict(fila)

    def crear(self, datos: dict) -> dict:
        campos = [campo for campo in self.columnas if campo in datos]
        cursor = self.con.execute(
            f"INSERT INTO {self.tabla} ({', '.join(campos)}) "
            f"VALUES ({', '.join('?' for _ in campos)})",
            [datos[campo] for campo in campos],
        )
        return self.obtener_por_id(cursor.lastrowid)

    def actualizar(self, registro_id: int, datos: dict) -> dict:
        self.obtener_por_id(registro_id)
        campos = [campo for campo in self.columnas if campo in datos]
        self.con.execute(
            f"UPDATE {self.tabla} SET {', '.join(f'{campo} = ?' for campo in campos)} WHERE id = ?",
            [*(datos[campo] for campo in campos), registro_id],
        )
        return self.obtener_por_id(registro_id)

    def eliminar(self, registro_id: int) -> None:
        self.obtener_por_id(registro_id)
        self.con.execute(f"DELETE FROM {self.tabla} WHERE id = ?", (registro_id,))


class RepositorioCliente(RepositorioBase):
    tabla = "clientes"
    columnas = ("nombre", "telefono", "direccion")
    no_encontrado = "Cliente no encontrado"


class RepositorioVehiculo(RepositorioBase):
    tabla = "vehiculos"
    columnas = ("placa", "marca", "modelo", "anio", "cliente_id")
    no_encontrado = "Vehículo no encontrado"

    def crear(self, datos: dict) -> dict:
        RepositorioCliente(self.con).obtener_por_id(datos["cliente_id"])
        return super().crear(datos)

    def actualizar(self, vehiculo_id: int, datos: dict) -> dict:
        RepositorioCliente(self.con).obtener_por_id(datos["cliente_id"])
        return super().actualizar(vehiculo_id, datos)


class RepositorioMecanico(RepositorioBase):
    tabla = "mecanicos"
    columnas = ("nombre", "especialidad", "activo")
    no_encontrado = "Mecánico no encontrado"


class RepositorioRepuesto(RepositorioBase):
    tabla = "repuestos"
    columnas = ("nombre", "precio", "existencia")
    no_encontrado = "Repuesto no encontrado"

    def hay_existencia(self, repuesto_id: int, cantidad: int) -> bool:
        return self.obtener_por_id(repuesto_id)["existencia"] >= cantidad


class RepositorioOrden(RepositorioBase):
    tabla = "ordenes_servicio"
    columnas = ("vehiculo_id", "mecanico_id", "fecha_ingreso", "diagnostico", "mano_obra")
    no_encontrado = "Orden no encontrada"

    def crear(self, datos: dict) -> dict:
        self._validar_referencias(datos)
        return super().crear(datos)

    def actualizar(self, orden_id: int, datos: dict) -> dict:
        self.verificar_editable(orden_id)
        self._validar_referencias(datos)
        return super().actualizar(orden_id, datos)

    def eliminar(self, orden_id: int) -> None:
        """Borra la orden y devuelve sus repuestos al inventario."""
        self.verificar_editable(orden_id)
        detalle = RepositorioDetalle(self.con)
        for linea in detalle.obtener_de_orden(orden_id):
            detalle.quitar(orden_id, linea["id"])
        super().eliminar(orden_id)

    def verificar_editable(self, orden_id: int) -> dict:
        """Solo se pueden cambiar las órdenes que todavía están en el taller."""
        orden = self.obtener_por_id(orden_id)
        if orden["estado"] not in ESTADOS_EDITABLES:
            raise HTTPException(
                status_code=400,
                detail=f"La orden está '{orden['estado']}' y ya no se puede modificar",
            )
        return orden

    def calcular_total(self, orden_id: int) -> dict:
        orden = self.obtener_por_id(orden_id)
        repuestos = self.con.execute(
            """
            SELECT COALESCE(SUM(d.cantidad * r.precio), 0)
            FROM detalle_orden d JOIN repuestos r ON r.id = d.repuesto_id
            WHERE d.orden_id = ?
            """,
            (orden_id,),
        ).fetchone()[0]
        return {
            "orden_id": orden_id,
            "mano_obra": orden["mano_obra"],
            "repuestos": round(repuestos, 2),
            "total": round(orden["mano_obra"] + repuestos, 2),
        }

    def avanzar_estado(self, orden_id: int) -> dict:
        """Pasa la orden al siguiente estado: recibido → en reparacion → listo → entregado."""
        orden = self.obtener_por_id(orden_id)
        posicion = ESTADOS_ORDEN.index(orden["estado"])
        if posicion == len(ESTADOS_ORDEN) - 1:
            raise HTTPException(status_code=400, detail="La orden ya fue entregada")
        self.con.execute(
            "UPDATE ordenes_servicio SET estado = ? WHERE id = ?",
            (ESTADOS_ORDEN[posicion + 1], orden_id),
        )
        return self.obtener_por_id(orden_id)

    def _validar_referencias(self, datos: dict) -> None:
        RepositorioVehiculo(self.con).obtener_por_id(datos["vehiculo_id"])
        mecanico = RepositorioMecanico(self.con).obtener_por_id(datos["mecanico_id"])
        if not mecanico["activo"]:
            raise HTTPException(status_code=400, detail="El mecánico no está activo")


class RepositorioDetalle(RepositorioBase):
    tabla = "detalle_orden"
    columnas = ("orden_id", "repuesto_id", "cantidad")
    no_encontrado = "Ese repuesto no está en la orden"

    CONSULTA_COMPLETA = """
        SELECT d.id, d.orden_id, d.repuesto_id, r.nombre AS repuesto, d.cantidad, r.precio,
               ROUND(d.cantidad * r.precio, 2) AS subtotal
        FROM detalle_orden d JOIN repuestos r ON r.id = d.repuesto_id
    """

    def obtener_de_orden(self, orden_id: int) -> list[dict]:
        RepositorioOrden(self.con).obtener_por_id(orden_id)
        filas = self.con.execute(
            self.CONSULTA_COMPLETA + " WHERE d.orden_id = ? ORDER BY d.id", (orden_id,)
        ).fetchall()
        return [dict(fila) for fila in filas]

    def agregar(self, orden_id: int, repuesto_id: int, cantidad: int) -> dict:
        """Agrega el repuesto a la orden y lo descuenta del inventario."""
        RepositorioOrden(self.con).verificar_editable(orden_id)
        if not RepositorioRepuesto(self.con).hay_existencia(repuesto_id, cantidad):
            raise HTTPException(status_code=400, detail="No hay existencia suficiente")
        self.con.execute(
            "UPDATE repuestos SET existencia = existencia - ? WHERE id = ?",
            (cantidad, repuesto_id),
        )
        # Si el repuesto ya estaba en la orden se suma la cantidad en vez de repetir la línea
        existente = self.con.execute(
            "SELECT id FROM detalle_orden WHERE orden_id = ? AND repuesto_id = ?",
            (orden_id, repuesto_id),
        ).fetchone()
        if existente:
            detalle_id = existente["id"]
            self.con.execute(
                "UPDATE detalle_orden SET cantidad = cantidad + ? WHERE id = ?",
                (cantidad, detalle_id),
            )
        else:
            detalle_id = super().crear(
                {"orden_id": orden_id, "repuesto_id": repuesto_id, "cantidad": cantidad}
            )["id"]
        return dict(
            self.con.execute(self.CONSULTA_COMPLETA + " WHERE d.id = ?", (detalle_id,)).fetchone()
        )

    def quitar(self, orden_id: int, detalle_id: int) -> None:
        """Quita la línea de la orden y devuelve los repuestos al inventario."""
        RepositorioOrden(self.con).verificar_editable(orden_id)
        detalle = self.obtener_por_id(detalle_id)
        if detalle["orden_id"] != orden_id:
            raise HTTPException(status_code=404, detail=self.no_encontrado)
        self.con.execute(
            "UPDATE repuestos SET existencia = existencia + ? WHERE id = ?",
            (detalle["cantidad"], detalle["repuesto_id"]),
        )
        super().eliminar(detalle_id)
