import sqlite3

from fastapi import HTTPException

from creditos import NOMBRE_CATEGORIA, nivel_de, puede_trabajar, puntos_por

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
    columnas = ("placa", "marca", "modelo", "anio", "cliente_id", "categoria")
    no_encontrado = "Vehículo no encontrado"

    def crear(self, datos: dict) -> dict:
        RepositorioCliente(self.con).obtener_por_id(datos["cliente_id"])
        return super().crear(datos)

    def actualizar(self, vehiculo_id: int, datos: dict) -> dict:
        RepositorioCliente(self.con).obtener_por_id(datos["cliente_id"])
        return super().actualizar(vehiculo_id, datos)


class RepositorioMecanico(RepositorioBase):
    tabla = "mecanicos"
    # Los créditos no se editan a mano: solo cambian con las calificaciones de los trabajos
    columnas = ("nombre", "especialidad", "activo", "telefono", "correo", "fecha_contratacion")
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
        actual = self.verificar_editable(orden_id)
        self._validar_referencias(datos, actual)
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

    def avanzar_estado(self, orden_id: int, calificacion: str | None = None) -> dict:
        """Pasa la orden al siguiente estado: recibido → en reparacion → listo → entregado.

        Para entregarla hay que calificar el trabajo, y eso suma o resta créditos al mecánico.
        """
        orden = self.obtener_por_id(orden_id)
        posicion = ESTADOS_ORDEN.index(orden["estado"])
        if posicion == len(ESTADOS_ORDEN) - 1:
            raise HTTPException(status_code=400, detail="La orden ya fue entregada")
        siguiente = ESTADOS_ORDEN[posicion + 1]
        if siguiente == "entregado":
            if calificacion is None:
                raise HTTPException(status_code=400, detail="Califique el trabajo para entregar la orden")
            self._calificar(orden, calificacion)
        self.con.execute("UPDATE ordenes_servicio SET estado = ? WHERE id = ?", (siguiente, orden_id))
        return self.obtener_por_id(orden_id)

    def _calificar(self, orden: dict, calificacion: str) -> None:
        categoria = RepositorioVehiculo(self.con).obtener_por_id(orden["vehiculo_id"])["categoria"]
        mecanico = RepositorioMecanico(self.con).obtener_por_id(orden["mecanico_id"])
        # Los créditos nunca bajan de 0; en el historial queda lo que de verdad cambió
        nuevos = max(0, mecanico["creditos"] + puntos_por(calificacion, categoria))
        self.con.execute(
            "UPDATE ordenes_servicio SET calificacion = ? WHERE id = ?", (calificacion, orden["id"])
        )
        self.con.execute("UPDATE mecanicos SET creditos = ? WHERE id = ?", (nuevos, mecanico["id"]))
        self.con.execute(
            "INSERT INTO movimientos_credito (mecanico_id, orden_id, puntos, motivo) VALUES (?, ?, ?, ?)",
            (
                mecanico["id"],
                orden["id"],
                nuevos - mecanico["creditos"],
                f"Orden #{orden['id']} calificada «{calificacion}» "
                f"(auto {NOMBRE_CATEGORIA[categoria].lower()})",
            ),
        )

    def _validar_referencias(self, datos: dict, actual: dict | None = None) -> None:
        vehiculo = RepositorioVehiculo(self.con).obtener_por_id(datos["vehiculo_id"])
        mecanico = RepositorioMecanico(self.con).obtener_por_id(datos["mecanico_id"])
        if not mecanico["activo"]:
            raise HTTPException(status_code=400, detail="El mecánico no está activo")
        # El nivel solo se revisa al asignar: si luego baja de nivel, conserva lo que ya tenía
        sin_cambios = actual is not None and (actual["vehiculo_id"], actual["mecanico_id"]) == (
            datos["vehiculo_id"],
            datos["mecanico_id"],
        )
        if not sin_cambios and not puede_trabajar(mecanico["creditos"], vehiculo["categoria"]):
            nivel = nivel_de(mecanico["creditos"])["nombre"]
            raise HTTPException(
                status_code=400,
                detail=f"{mecanico['nombre']} es {nivel} y todavía no puede trabajar autos "
                f"{NOMBRE_CATEGORIA[vehiculo['categoria']]}",
            )


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


class RepositorioUsuario(RepositorioBase):
    """Cuentas de acceso. Se crean con seguridad.registrar_usuario para encriptar la contraseña."""

    tabla = "usuarios"
    no_encontrado = "Cuenta no encontrada"

    def listar(self) -> list[dict]:
        filas = self.con.execute(
            """
            SELECT u.id, u.username, u.rol, u.nombre, u.mecanico_id, m.nombre AS mecanico
            FROM usuarios u LEFT JOIN mecanicos m ON m.id = u.mecanico_id
            ORDER BY u.rol, u.username
            """
        ).fetchall()
        return [dict(fila) for fila in filas]


class RepositorioNotificacion(RepositorioBase):
    """Avisos de los mecánicos para recepción."""

    tabla = "notificaciones"
    columnas = ("tipo", "mensaje", "orden_id", "mecanico_id")
    no_encontrado = "Notificación no encontrada"

    def listar(self, solo_no_leidas: bool = False) -> list[dict]:
        where = " WHERE n.leida = 0" if solo_no_leidas else ""
        filas = self.con.execute(
            "SELECT n.*, m.nombre AS mecanico FROM notificaciones n "
            "LEFT JOIN mecanicos m ON m.id = n.mecanico_id" + where + " ORDER BY n.id DESC"
        ).fetchall()
        return [dict(fila) for fila in filas]

    def marcar_leida(self, notificacion_id: int) -> None:
        self.obtener_por_id(notificacion_id)
        self.con.execute("UPDATE notificaciones SET leida = 1 WHERE id = ?", (notificacion_id,))

    def marcar_todas(self) -> int:
        return self.con.execute("UPDATE notificaciones SET leida = 1 WHERE leida = 0").rowcount


class RepositorioReporte(RepositorioBase):
    """Informes de los mecánicos sobre el equipo, los repuestos o la seguridad del taller."""

    tabla = "reportes"
    columnas = ("mecanico_id", "orden_id", "tipo", "titulo", "descripcion")
    no_encontrado = "Reporte no encontrado"

    CONSULTA_COMPLETA = (
        "SELECT r.*, m.nombre AS mecanico FROM reportes r JOIN mecanicos m ON m.id = r.mecanico_id"
    )

    def listar(self, mecanico_id: int | None = None, estado: str | None = None) -> list[dict]:
        filtros = {"r.mecanico_id": mecanico_id, "r.estado": estado}
        filtros = {campo: valor for campo, valor in filtros.items() if valor is not None}
        where = " AND ".join(f"{campo} = ?" for campo in filtros)
        filas = self.con.execute(
            self.CONSULTA_COMPLETA + (f" WHERE {where}" if where else "") + " ORDER BY r.id DESC",
            list(filtros.values()),
        ).fetchall()
        return [dict(fila) for fila in filas]

    def obtener_completo(self, reporte_id: int) -> dict:
        self.obtener_por_id(reporte_id)
        return dict(
            self.con.execute(self.CONSULTA_COMPLETA + " WHERE r.id = ?", (reporte_id,)).fetchone()
        )

    def crear_de_mecanico(self, mecanico_id: int, datos: dict) -> dict:
        """Guarda el reporte y avisa a recepción. Solo puede mencionar órdenes del mismo mecánico."""
        if datos.get("orden_id") is not None:
            RepositorioTrabajos(self.con, mecanico_id).obtener(datos["orden_id"])
        reporte = self.crear({**datos, "mecanico_id": mecanico_id})
        mecanico = RepositorioMecanico(self.con).obtener_por_id(mecanico_id)
        RepositorioNotificacion(self.con).crear(
            {
                "tipo": "reporte",
                "mensaje": f"Nuevo reporte de {mecanico['nombre']}: {datos['titulo']}",
                "orden_id": datos.get("orden_id"),
                "mecanico_id": mecanico_id,
            }
        )
        return self.obtener_completo(reporte["id"])

    def resolver(self, reporte_id: int) -> dict:
        self.obtener_por_id(reporte_id)
        self.con.execute("UPDATE reportes SET estado = 'resuelto' WHERE id = ?", (reporte_id,))
        return self.obtener_completo(reporte_id)


class RepositorioTrabajos:
    """Las órdenes de un mecánico vistas desde su área: solo ve y cambia las suyas."""

    CONSULTA = """
        SELECT o.id, o.estado, o.fecha_ingreso, o.diagnostico, o.calificacion,
               v.placa, v.marca, v.modelo, v.anio, v.categoria, c.nombre AS cliente
        FROM ordenes_servicio o
        JOIN vehiculos v ON v.id = o.vehiculo_id
        JOIN clientes c ON c.id = v.cliente_id
        WHERE o.mecanico_id = ?
    """
    NOMBRE_ESTADO = {"recibido": "por empezar", "en reparacion": "en reparación"}

    def __init__(self, con: sqlite3.Connection, mecanico_id: int):
        self.con = con
        self.mecanico_id = mecanico_id

    def listar(self) -> list[dict]:
        filas = self.con.execute(
            self.CONSULTA + " ORDER BY o.fecha_ingreso DESC, o.id DESC", (self.mecanico_id,)
        ).fetchall()
        return [dict(fila) for fila in filas]

    def obtener(self, orden_id: int) -> dict:
        # Una orden de otro mecánico responde igual que una que no existe
        fila = self.con.execute(self.CONSULTA + " AND o.id = ?", (self.mecanico_id, orden_id)).fetchone()
        if fila is None:
            raise HTTPException(status_code=404, detail="Orden no encontrada")
        return dict(fila)

    def detalle(self, orden_id: int) -> dict:
        trabajo = self.obtener(orden_id)
        repuestos = self.con.execute(
            """
            SELECT r.nombre AS repuesto, d.cantidad
            FROM detalle_orden d JOIN repuestos r ON r.id = d.repuesto_id
            WHERE d.orden_id = ? ORDER BY d.id
            """,
            (orden_id,),
        ).fetchall()
        creditos = self.con.execute(
            "SELECT SUM(puntos) FROM movimientos_credito WHERE orden_id = ? AND mecanico_id = ?",
            (orden_id, self.mecanico_id),
        ).fetchone()[0]
        return {**trabajo, "repuestos": [dict(fila) for fila in repuestos], "creditos": creditos}

    def iniciar(self, orden_id: int) -> dict:
        if self.obtener(orden_id)["estado"] != "recibido":
            raise HTTPException(status_code=400, detail="Este trabajo ya fue empezado")
        self._cambiar_estado(orden_id, "en reparacion")
        return self.detalle(orden_id)

    def marcar_listo(self, orden_id: int, nota: str | None) -> dict:
        """Termina la reparación y avisa a recepción que puede entregar el vehículo."""
        trabajo = self.obtener(orden_id)
        if trabajo["estado"] == "recibido":
            raise HTTPException(status_code=400, detail="Primero empiece la reparación")
        if trabajo["estado"] != "en reparacion":
            raise HTTPException(status_code=400, detail="Este trabajo ya fue marcado como listo")
        self._cambiar_estado(orden_id, "listo")
        mensaje = (
            f"La orden #{orden_id} ({trabajo['placa']}, {trabajo['marca']} {trabajo['modelo']}) "
            "está lista para entregar."
        )
        self._avisar("listo", mensaje + (f" Nota: {nota}" if nota else ""), orden_id)
        return self.detalle(orden_id)

    def enviar_aviso(self, orden_id: int, mensaje: str) -> None:
        """Cuenta a recepción cómo va un trabajo que todavía no está listo."""
        trabajo = self.obtener(orden_id)
        if trabajo["estado"] not in ESTADOS_EDITABLES:
            raise HTTPException(status_code=400, detail="Este trabajo ya terminó")
        estado = self.NOMBRE_ESTADO[trabajo["estado"]]
        self._avisar("avance", f"Orden #{orden_id} ({trabajo['placa']}) sigue {estado}: {mensaje}", orden_id)

    def perfil(self, usuario: str) -> dict:
        mecanico = RepositorioMecanico(self.con).obtener_por_id(self.mecanico_id)
        por_estado = dict(
            self.con.execute(
                "SELECT estado, COUNT(*) FROM ordenes_servicio WHERE mecanico_id = ? GROUP BY estado",
                (self.mecanico_id,),
            ).fetchall()
        )
        calificaciones = dict(
            self.con.execute(
                """
                SELECT calificacion, COUNT(*) FROM ordenes_servicio
                WHERE mecanico_id = ? AND calificacion IS NOT NULL GROUP BY calificacion
                """,
                (self.mecanico_id,),
            ).fetchall()
        )
        historial = self.con.execute(
            """
            SELECT fecha, puntos, motivo, orden_id FROM movimientos_credito
            WHERE mecanico_id = ? ORDER BY fecha DESC, id DESC LIMIT 20
            """,
            (self.mecanico_id,),
        ).fetchall()
        return {
            "usuario": usuario,
            **{campo: mecanico[campo] for campo in ("nombre", "especialidad", "telefono", "correo", "fecha_contratacion", "creditos")},
            "nivel": nivel_de(mecanico["creditos"]),
            "estadisticas": {
                "por_empezar": por_estado.get("recibido", 0),
                "en_reparacion": por_estado.get("en reparacion", 0),
                "listos": por_estado.get("listo", 0),
                "entregados": por_estado.get("entregado", 0),
                "calificaciones": {c: calificaciones.get(c, 0) for c in ("excelente", "bien", "con problemas", "rehacer")},
            },
            "historial": [dict(fila) for fila in historial],
        }

    def _cambiar_estado(self, orden_id: int, estado: str) -> None:
        self.con.execute("UPDATE ordenes_servicio SET estado = ? WHERE id = ?", (estado, orden_id))

    def _avisar(self, tipo: str, mensaje: str, orden_id: int) -> None:
        RepositorioNotificacion(self.con).crear(
            {"tipo": tipo, "mensaje": mensaje, "orden_id": orden_id, "mecanico_id": self.mecanico_id}
        )
