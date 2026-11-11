import sqlite3

from fastapi import HTTPException

from creditos import (
    NOMBRE_CALIFICACION,
    NOMBRE_CATEGORIA,
    nivel_de,
    puede_trabajar,
    puntos_de_miembro,
    puntos_por,
)

ESTADOS_ORDEN = ("recibido", "en reparacion", "listo", "entregado")
ESTADOS_EDITABLES = ("recibido", "en reparacion")

# Total (mano de obra + repuestos) y lo pagado de la orden «o», para usar dentro de un SELECT
TOTAL_ORDEN = """(o.mano_obra + COALESCE((
    SELECT SUM(d.cantidad * r.precio) FROM detalle_orden d JOIN repuestos r ON r.id = d.repuesto_id
    WHERE d.orden_id = o.id), 0))"""
PAGADO_ORDEN = "COALESCE((SELECT SUM(p.monto) FROM pagos p WHERE p.orden_id = o.id), 0)"

# Datos de quien paga y del método, iguales en pagos de proyectos y en ventas de repuestos
COLUMNAS_PAGADOR = (
    "metodo", "referencia", "pagador_nombres", "pagador_apellidos", "pagador_identidad", "pagador_correo",
    "tarjeta_marca", "tarjeta_ultimos4", "tarjeta_titular", "autorizacion", "banco",
)


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

    def historial(self, vehiculo_id: int) -> list[dict]:
        """Todos los proyectos que ha tenido el vehículo, con su costo y lo pagado."""
        self.obtener_por_id(vehiculo_id)
        filas = self.con.execute(
            f"""
            SELECT o.id, o.estado, o.fecha_ingreso, o.diagnostico, o.calificacion, l.nombre AS lider,
                   {TOTAL_ORDEN} AS total, {PAGADO_ORDEN} AS pagado
            FROM ordenes_servicio o JOIN mecanicos l ON l.id = o.mecanico_id
            WHERE o.vehiculo_id = ? ORDER BY o.fecha_ingreso DESC, o.id DESC
            """,
            (vehiculo_id,),
        ).fetchall()
        return [dict(fila) for fila in filas]


class RepositorioMecanico(RepositorioBase):
    tabla = "mecanicos"
    # Los créditos no se editan como un dato más: cambian con las calificaciones y los ajustes
    columnas = ("nombre", "especialidad", "activo", "telefono", "correo", "fecha_contratacion")
    no_encontrado = "Mecánico no encontrado"

    def sumar_creditos(self, mecanico_id: int, orden_id: int | None, puntos: int, motivo: str) -> int:
        """Suma (o resta) créditos y deja la línea en el historial. Devuelve los créditos nuevos."""
        mecanico = self.obtener_por_id(mecanico_id)
        # Los créditos nunca bajan de 0; en el historial queda lo que de verdad cambió
        nuevos = max(0, mecanico["creditos"] + puntos)
        self.con.execute("UPDATE mecanicos SET creditos = ? WHERE id = ?", (nuevos, mecanico_id))
        self.con.execute(
            "INSERT INTO movimientos_credito (mecanico_id, orden_id, puntos, motivo) VALUES (?, ?, ?, ?)",
            (mecanico_id, orden_id, nuevos - mecanico["creditos"], motivo),
        )
        return nuevos

    def ajustar_creditos(self, mecanico_id: int, puntos: int, motivo: str, orden_id: int | None) -> dict:
        """Ajuste a mano de recepción, por ejemplo por un trabajo extra o una falta."""
        if orden_id is not None:
            orden = RepositorioOrden(self.con).obtener_por_id(orden_id)
            if mecanico_id != orden["mecanico_id"] and mecanico_id not in orden["equipo"]:
                raise HTTPException(status_code=400, detail="Ese mecánico no trabajó en ese proyecto")
        referencia = f" (proyecto #{orden_id})" if orden_id else ""
        self.sumar_creditos(mecanico_id, orden_id, puntos, f"Ajuste de recepción{referencia}: {motivo}")
        return self.obtener_por_id(mecanico_id)

    def historial_creditos(self, mecanico_id: int) -> list[dict]:
        self.obtener_por_id(mecanico_id)
        filas = self.con.execute(
            """
            SELECT fecha, puntos, motivo, orden_id FROM movimientos_credito
            WHERE mecanico_id = ? ORDER BY fecha DESC, id DESC LIMIT 50
            """,
            (mecanico_id,),
        ).fetchall()
        return [dict(fila) for fila in filas]


class RepositorioRepuesto(RepositorioBase):
    tabla = "repuestos"
    columnas = ("nombre", "precio", "existencia")
    no_encontrado = "Repuesto no encontrado"

    def hay_existencia(self, repuesto_id: int, cantidad: int) -> bool:
        return self.obtener_por_id(repuesto_id)["existencia"] >= cantidad


class RepositorioOrden(RepositorioBase):
    tabla = "ordenes_servicio"
    columnas = ("vehiculo_id", "mecanico_id", "fecha_ingreso", "diagnostico", "mano_obra", "indicaciones")
    no_encontrado = "Orden no encontrada"

    # mecanico_id es el líder del trabajo; los demás miembros del equipo están en equipo_orden

    def obtener_por_id(self, orden_id: int) -> dict:
        orden = super().obtener_por_id(orden_id)
        orden["equipo"] = [
            fila["mecanico_id"]
            for fila in self.con.execute(
                "SELECT mecanico_id FROM equipo_orden WHERE orden_id = ? ORDER BY id", (orden_id,)
            )
        ]
        return orden

    def obtener_todos(self, **filtros) -> list[dict]:
        ordenes = super().obtener_todos(**filtros)
        equipos: dict[int, list[int]] = {}
        for fila in self.con.execute("SELECT orden_id, mecanico_id FROM equipo_orden ORDER BY id"):
            equipos.setdefault(fila["orden_id"], []).append(fila["mecanico_id"])
        for orden in ordenes:
            orden["equipo"] = equipos.get(orden["id"], [])
        return ordenes

    def crear(self, datos: dict) -> dict:
        self._validar_referencias(datos)
        miembros = self._validar_equipo(datos)
        self._validar_disponibles([datos["mecanico_id"], *miembros])
        orden = super().crear(datos)
        self._guardar_equipo(orden["id"], miembros)
        return self.obtener_por_id(orden["id"])

    def actualizar(self, orden_id: int, datos: dict) -> dict:
        actual = self.verificar_editable(orden_id)
        self._validar_referencias(datos, actual)
        miembros = self._validar_equipo(datos)
        # Solo se revisa a los que entran nuevos: los que ya estaban en este proyecto siguen
        ya_estaban = {actual["mecanico_id"], *actual["equipo"]}
        self._validar_disponibles([m for m in [datos["mecanico_id"], *miembros] if m not in ya_estaban])
        super().actualizar(orden_id, datos)
        self._guardar_equipo(orden_id, miembros)
        return self.obtener_por_id(orden_id)

    def ocupados(self) -> dict[int, int]:
        """Mecánicos que ya trabajan en un proyecto activo: {mecanico_id: orden_id}."""
        filas = self.con.execute(
            """
            SELECT o.mecanico_id, o.id AS orden_id FROM ordenes_servicio o
            WHERE o.estado IN ('recibido', 'en reparacion')
            UNION ALL
            SELECT e.mecanico_id, e.orden_id FROM equipo_orden e
            JOIN ordenes_servicio o ON o.id = e.orden_id WHERE o.estado IN ('recibido', 'en reparacion')
            ORDER BY orden_id
            """
        ).fetchall()
        ocupados: dict[int, int] = {}
        for fila in filas:
            ocupados.setdefault(fila["mecanico_id"], fila["orden_id"])
        return ocupados

    def _validar_disponibles(self, mecanicos: list[int]) -> None:
        """Un mecánico que ya trabaja en un proyecto activo no está disponible para otro."""
        ocupados = self.ocupados()
        for mecanico_id in mecanicos:
            if mecanico_id in ocupados:
                nombre = RepositorioMecanico(self.con).obtener_por_id(mecanico_id)["nombre"]
                raise HTTPException(
                    status_code=400,
                    detail=f"{nombre} no está disponible: trabaja en el proyecto #{ocupados[mecanico_id]}",
                )

    def equipo_detallado(self, orden_id: int) -> list[dict]:
        """El líder y los acompañantes, con la tarea y la calificación que el líder dio a cada uno."""
        self.obtener_por_id(orden_id)
        filas = self.con.execute(
            """
            SELECT m.id AS mecanico_id, m.nombre, m.especialidad, m.creditos,
                   1 AS es_lider, NULL AS tarea, NULL AS calificacion
            FROM ordenes_servicio o JOIN mecanicos m ON m.id = o.mecanico_id WHERE o.id = :orden
            UNION ALL
            SELECT m.id, m.nombre, m.especialidad, m.creditos, 0, e.tarea, e.calificacion
            FROM equipo_orden e JOIN mecanicos m ON m.id = e.mecanico_id WHERE e.orden_id = :orden
            ORDER BY es_lider DESC, nombre
            """,
            {"orden": orden_id},
        ).fetchall()
        return [
            {**dict(fila), "es_lider": bool(fila["es_lider"]), "nivel": nivel_de(fila["creditos"])["nombre"]}
            for fila in filas
        ]

    def _validar_equipo(self, datos: dict) -> list[int]:
        """Los miembros deben existir, estar activos y no repetir al líder."""
        miembros = list(dict.fromkeys(datos.get("equipo") or []))
        if datos["mecanico_id"] in miembros:
            raise HTTPException(status_code=400, detail="El líder ya dirige el trabajo: no lo agregue al equipo")
        for mecanico_id in miembros:
            mecanico = RepositorioMecanico(self.con).obtener_por_id(mecanico_id)
            if not mecanico["activo"]:
                raise HTTPException(status_code=400, detail=f"{mecanico['nombre']} no está activo")
        return miembros

    def _guardar_equipo(self, orden_id: int, miembros: list[int]) -> None:
        """Deja exactamente esos miembros. Los que siguen conservan su tarea y su calificación."""
        marcadores = ", ".join("?" for _ in miembros)
        self.con.execute(
            "DELETE FROM equipo_orden WHERE orden_id = ?"
            + (f" AND mecanico_id NOT IN ({marcadores})" if miembros else ""),
            (orden_id, *miembros),
        )
        for mecanico_id in miembros:
            self.con.execute(
                "INSERT OR IGNORE INTO equipo_orden (orden_id, mecanico_id) VALUES (?, ?)",
                (orden_id, mecanico_id),
            )

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
        """El líder recibe los créditos de la calificación de recepción; cada miembro, la mitad
        según recepción y la mitad según la calificación que le dio su líder."""
        categoria = RepositorioVehiculo(self.con).obtener_por_id(orden["vehiculo_id"])["categoria"]
        auto = f"auto {NOMBRE_CATEGORIA[categoria].lower()}"
        self.con.execute(
            "UPDATE ordenes_servicio SET calificacion = ? WHERE id = ?", (calificacion, orden["id"])
        )
        mecanicos = RepositorioMecanico(self.con)
        mecanicos.sumar_creditos(
            orden["mecanico_id"],
            orden["id"],
            puntos_por(calificacion, categoria),
            f"Proyecto #{orden['id']} como líder: recepción «{NOMBRE_CALIFICACION[calificacion]}» ({auto})",
        )
        miembros = self.con.execute(
            "SELECT mecanico_id, calificacion FROM equipo_orden WHERE orden_id = ?", (orden["id"],)
        ).fetchall()
        for miembro in miembros:
            del_lider = NOMBRE_CALIFICACION.get(miembro["calificacion"], "sin calificar")
            mecanicos.sumar_creditos(
                miembro["mecanico_id"],
                orden["id"],
                puntos_de_miembro(calificacion, miembro["calificacion"], categoria),
                f"Proyecto #{orden['id']} en equipo: recepción «{NOMBRE_CALIFICACION[calificacion]}», "
                f"líder «{del_lider}» ({auto})",
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

    def agregar(self, orden_id: int, repuesto_id: int, cantidad: int, usuario: str | None = None) -> dict:
        """Agrega el repuesto a la orden y lo descuenta del inventario."""
        RepositorioOrden(self.con).verificar_editable(orden_id)
        repuesto = RepositorioRepuesto(self.con).obtener_por_id(repuesto_id)
        if repuesto["existencia"] < cantidad:
            raise HTTPException(status_code=400, detail="No hay existencia suficiente")
        RepositorioMovimiento(self.con).registrar(
            "repuesto_usado",
            f"{repuesto['nombre']} × {cantidad} en el proyecto #{orden_id}",
            cantidad=cantidad, repuesto_id=repuesto_id, orden_id=orden_id, usuario=usuario,
        )
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

    def quitar(self, orden_id: int, detalle_id: int, usuario: str | None = None) -> None:
        """Quita la línea de la orden y devuelve los repuestos al inventario."""
        RepositorioOrden(self.con).verificar_editable(orden_id)
        detalle = self.obtener_por_id(detalle_id)
        if detalle["orden_id"] != orden_id:
            raise HTTPException(status_code=404, detail=self.no_encontrado)
        self.con.execute(
            "UPDATE repuestos SET existencia = existencia + ? WHERE id = ?",
            (detalle["cantidad"], detalle["repuesto_id"]),
        )
        nombre = RepositorioRepuesto(self.con).obtener_por_id(detalle["repuesto_id"])["nombre"]
        RepositorioMovimiento(self.con).registrar(
            "repuesto_devuelto",
            f"{nombre} × {detalle['cantidad']} devuelto al almacén desde el proyecto #{orden_id}",
            cantidad=detalle["cantidad"], repuesto_id=detalle["repuesto_id"], orden_id=orden_id, usuario=usuario,
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

    def de_orden(self, orden_id: int) -> list[dict]:
        """Avisos de un proyecto en orden de llegada: los problemas que surgieron y la nota final."""
        filas = self.con.execute(
            """
            SELECT n.tipo, n.mensaje, n.fecha, m.nombre AS mecanico FROM notificaciones n
            LEFT JOIN mecanicos m ON m.id = n.mecanico_id
            WHERE n.orden_id = ? AND n.tipo IN ('avance', 'listo') ORDER BY n.id
            """,
            (orden_id,),
        ).fetchall()
        return [dict(fila) for fila in filas]


class RepositorioReporte(RepositorioBase):
    """Informes de los mecánicos sobre el equipo, los repuestos o la seguridad del taller."""

    tabla = "reportes"
    columnas = ("mecanico_id", "orden_id", "tipo", "titulo", "descripcion", "sobre_mecanico_id")
    no_encontrado = "Reporte no encontrado"

    CONSULTA_COMPLETA = (
        "SELECT r.*, m.nombre AS mecanico, s.nombre AS sobre_mecanico FROM reportes r "
        "JOIN mecanicos m ON m.id = r.mecanico_id LEFT JOIN mecanicos s ON s.id = r.sobre_mecanico_id"
    )

    def listar(
        self,
        mecanico_id: int | None = None,
        estado: str | None = None,
        orden_id: int | None = None,
        tipo: str | None = None,
    ) -> list[dict]:
        filtros = {"r.mecanico_id": mecanico_id, "r.estado": estado, "r.orden_id": orden_id, "r.tipo": tipo}
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

    def resolver(self, reporte_id: int, penalizacion: int = 0, comentario: str | None = None) -> dict:
        """Cierra el reporte. Si es de un líder sobre su equipo, recepción puede bajarle créditos
        al reportado, y el reportado recibe el reporte en su bandeja."""
        reporte = self.obtener_completo(reporte_id)
        if reporte["estado"] == "resuelto":
            raise HTTPException(status_code=400, detail="Este reporte ya fue resuelto")
        sobre = reporte["sobre_mecanico_id"]
        if penalizacion and sobre is None:
            raise HTTPException(status_code=400, detail="Este reporte no es sobre un mecánico: no se puede penalizar")
        if sobre is not None:
            if penalizacion:
                RepositorioMecanico(self.con).sumar_creditos(
                    sobre, reporte["orden_id"], -penalizacion, f"Reporte de su líder: «{reporte['titulo']}»"
                )
            texto = f"{reporte['mecanico']} lo reportó: {reporte['descripcion']}"
            texto += f"\n\nRecepción le bajó {penalizacion} créditos." if penalizacion else "\n\nRecepción no le bajó créditos."
            if comentario:
                texto += f"\nComentario de recepción: {comentario}"
            RepositorioMensaje(self.con).crear(
                {
                    "mecanico_id": sobre,
                    "remitente": "Recepción",
                    "asunto": f"Reporte de su líder: {reporte['titulo']}",
                    "texto": texto,
                    "orden_id": reporte["orden_id"],
                }
            )
        self.con.execute(
            "UPDATE reportes SET estado = 'resuelto', penalizacion = ?, comentario = ? WHERE id = ?",
            (penalizacion if sobre is not None else None, comentario, reporte_id),
        )
        return self.obtener_completo(reporte_id)


class RepositorioTrabajos:
    """Las órdenes de un mecánico vistas desde su área: las que dirige como líder y las que
    acompaña como miembro del equipo. Solo ve y cambia esas."""

    # :m es el mecánico que consulta
    PARTICIPA = """(o.mecanico_id = :m OR EXISTS (
        SELECT 1 FROM equipo_orden e WHERE e.orden_id = o.id AND e.mecanico_id = :m))"""
    CONSULTA = f"""
        SELECT o.id, o.estado, o.fecha_ingreso, o.diagnostico, o.calificacion, o.indicaciones,
               v.placa, v.marca, v.modelo, v.anio, v.categoria, c.nombre AS cliente,
               l.nombre AS lider, o.mecanico_id = :m AS soy_lider
        FROM ordenes_servicio o
        JOIN vehiculos v ON v.id = o.vehiculo_id
        JOIN clientes c ON c.id = v.cliente_id
        JOIN mecanicos l ON l.id = o.mecanico_id
        WHERE {PARTICIPA}
    """
    NOMBRE_ESTADO = {"recibido": "por empezar", "en reparacion": "en reparación"}

    def __init__(self, con: sqlite3.Connection, mecanico_id: int):
        self.con = con
        self.mecanico_id = mecanico_id

    def listar(self) -> list[dict]:
        filas = self.con.execute(
            self.CONSULTA + " ORDER BY o.fecha_ingreso DESC, o.id DESC", {"m": self.mecanico_id}
        ).fetchall()
        return [self._con_booleanos(fila) for fila in filas]

    def obtener(self, orden_id: int) -> dict:
        # Una orden en la que no participa responde igual que una que no existe
        fila = self.con.execute(
            self.CONSULTA + " AND o.id = :orden", {"m": self.mecanico_id, "orden": orden_id}
        ).fetchone()
        if fila is None:
            raise HTTPException(status_code=404, detail="Orden no encontrada")
        return self._con_booleanos(fila)

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
        # Los reportes del líder sobre su equipo solo los ve el líder (y recepción)
        reportes = (
            RepositorioReporte(self.con).listar(orden_id=orden_id, tipo="desempeno")
            if trabajo["soy_lider"]
            else []
        )
        return {
            **trabajo,
            "repuestos": [dict(fila) for fila in repuestos],
            "creditos": creditos,
            "equipo": RepositorioOrden(self.con).equipo_detallado(orden_id),
            "novedades": RepositorioNotificacion(self.con).de_orden(orden_id),
            "puedo_dirigir": self._puede_dirigir(trabajo),
            "reportes_equipo": reportes,
            "peticiones": RepositorioPeticion(self.con).listar(orden_id=orden_id),
        }

    def pedir_material(self, orden_id: int, datos: dict) -> dict:
        """Cualquiera del equipo puede pedir material al almacén mientras dura el trabajo."""
        trabajo = self.obtener(orden_id)
        if trabajo["estado"] not in ESTADOS_EDITABLES:
            raise HTTPException(status_code=400, detail="Este trabajo ya terminó")
        RepositorioRepuesto(self.con).obtener_por_id(datos["repuesto_id"])
        peticiones = RepositorioPeticion(self.con)
        peticion = peticiones.crear({**datos, "orden_id": orden_id, "mecanico_id": self.mecanico_id})
        return peticiones.obtener_completa(peticion["id"])

    def iniciar(self, orden_id: int) -> dict:
        trabajo = self._exigir_lider(orden_id)
        if trabajo["estado"] != "recibido":
            raise HTTPException(status_code=400, detail="Este trabajo ya fue empezado")
        self._cambiar_estado(orden_id, "en reparacion")
        return self.detalle(orden_id)

    def marcar_listo(self, orden_id: int, nota: str | None) -> dict:
        """Termina la reparación y avisa a recepción. Con esto el líder pierde sus permisos."""
        trabajo = self._exigir_lider(orden_id)
        if trabajo["estado"] == "recibido":
            raise HTTPException(status_code=400, detail="Primero empiece la reparación")
        if trabajo["estado"] != "en reparacion":
            raise HTTPException(status_code=400, detail="Este trabajo ya fue marcado como listo")
        sin_calificar = self.con.execute(
            "SELECT COUNT(*) FROM equipo_orden WHERE orden_id = ? AND calificacion IS NULL", (orden_id,)
        ).fetchone()[0]
        if sin_calificar:
            raise HTTPException(
                status_code=400,
                detail="Califique el trabajo de cada miembro del equipo antes de marcarlo como listo",
            )
        self._cambiar_estado(orden_id, "listo")
        mensaje = (
            f"El proyecto #{orden_id} ({trabajo['placa']}, {trabajo['marca']} {trabajo['modelo']}) "
            "está listo para entregar."
        )
        self._avisar("listo", mensaje + (f" Nota: {nota}" if nota else ""), orden_id)
        return self.detalle(orden_id)

    def enviar_aviso(self, orden_id: int, mensaje: str) -> None:
        """Cuenta a recepción cómo va un trabajo que todavía no está listo."""
        trabajo = self.obtener(orden_id)
        if trabajo["estado"] not in ESTADOS_EDITABLES:
            raise HTTPException(status_code=400, detail="Este trabajo ya terminó")
        estado = self.NOMBRE_ESTADO[trabajo["estado"]]
        self._avisar("avance", f"Proyecto #{orden_id} ({trabajo['placa']}) sigue {estado}: {mensaje}", orden_id)

    # ---------- Lo que solo puede hacer el líder, y solo mientras dura el trabajo ----------
    def dirigir_miembro(self, orden_id: int, miembro_id: int, cambios: dict) -> dict:
        """Asigna la tarea de un miembro y/o califica su trabajo."""
        self._exigir_direccion(orden_id)
        self._exigir_miembro(orden_id, miembro_id)
        campos = [campo for campo in ("tarea", "calificacion") if campo in cambios]
        if campos:
            self.con.execute(
                f"UPDATE equipo_orden SET {', '.join(f'{c} = ?' for c in campos)} "
                "WHERE orden_id = ? AND mecanico_id = ?",
                (*(cambios[c] for c in campos), orden_id, miembro_id),
            )
        return self.detalle(orden_id)

    def reportar_miembro(self, orden_id: int, datos: dict) -> dict:
        """Reporte del líder sobre un miembro de su equipo; también avisa a recepción."""
        self._exigir_direccion(orden_id)
        miembro = self._exigir_miembro(orden_id, datos["sobre_mecanico_id"])
        reportes = RepositorioReporte(self.con)
        reporte = reportes.crear(
            {**datos, "mecanico_id": self.mecanico_id, "orden_id": orden_id, "tipo": "desempeno"}
        )
        lider = RepositorioMecanico(self.con).obtener_por_id(self.mecanico_id)
        self._avisar(
            "reporte",
            f"Reporte del líder {lider['nombre']} sobre {miembro['nombre']} (orden #{orden_id}): {datos['titulo']}",
            orden_id,
        )
        return reportes.obtener_completo(reporte["id"])

    def perfil(self, usuario: str) -> dict:
        mecanico = RepositorioMecanico(self.con).obtener_por_id(self.mecanico_id)
        por_estado = dict(
            self.con.execute(
                f"SELECT estado, COUNT(*) FROM ordenes_servicio o WHERE {self.PARTICIPA} GROUP BY estado",
                {"m": self.mecanico_id},
            ).fetchall()
        )
        calificaciones = dict(
            self.con.execute(
                f"""
                SELECT calificacion, COUNT(*) FROM ordenes_servicio o
                WHERE {self.PARTICIPA} AND calificacion IS NOT NULL GROUP BY calificacion
                """,
                {"m": self.mecanico_id},
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

    @staticmethod
    def _con_booleanos(fila: sqlite3.Row) -> dict:
        return {**dict(fila), "soy_lider": bool(fila["soy_lider"])}

    @staticmethod
    def _puede_dirigir(trabajo: dict) -> bool:
        return trabajo["soy_lider"] and trabajo["estado"] in ESTADOS_EDITABLES

    def _exigir_lider(self, orden_id: int) -> dict:
        trabajo = self.obtener(orden_id)
        if not trabajo["soy_lider"]:
            raise HTTPException(status_code=403, detail="Solo el líder del trabajo puede hacer esto")
        return trabajo

    def _exigir_direccion(self, orden_id: int) -> dict:
        trabajo = self._exigir_lider(orden_id)
        if not self._puede_dirigir(trabajo):
            raise HTTPException(
                status_code=400, detail="El trabajo ya terminó: sus permisos de líder ya no aplican"
            )
        return trabajo

    def _exigir_miembro(self, orden_id: int, mecanico_id: int) -> dict:
        fila = self.con.execute(
            """
            SELECT m.id, m.nombre FROM equipo_orden e JOIN mecanicos m ON m.id = e.mecanico_id
            WHERE e.orden_id = ? AND e.mecanico_id = ?
            """,
            (orden_id, mecanico_id),
        ).fetchone()
        if fila is None:
            raise HTTPException(status_code=404, detail="Ese mecánico no es parte del equipo")
        return dict(fila)

    def _cambiar_estado(self, orden_id: int, estado: str) -> None:
        self.con.execute("UPDATE ordenes_servicio SET estado = ? WHERE id = ?", (estado, orden_id))

    def _avisar(self, tipo: str, mensaje: str, orden_id: int) -> None:
        RepositorioNotificacion(self.con).crear(
            {"tipo": tipo, "mensaje": mensaje, "orden_id": orden_id, "mecanico_id": self.mecanico_id}
        )


class RepositorioPeticion(RepositorioBase):
    """Material que piden los mecánicos; recepción lo envía desde el almacén o lo rechaza."""

    tabla = "peticiones"
    columnas = ("orden_id", "mecanico_id", "repuesto_id", "cantidad", "motivo")
    no_encontrado = "Petición no encontrada"

    CONSULTA_COMPLETA = """
        SELECT p.*, v.placa, m.nombre AS mecanico, r.nombre AS repuesto, r.existencia
        FROM peticiones p
        JOIN ordenes_servicio o ON o.id = p.orden_id
        JOIN vehiculos v ON v.id = o.vehiculo_id
        JOIN mecanicos m ON m.id = p.mecanico_id
        JOIN repuestos r ON r.id = p.repuesto_id
    """

    def listar(self, estado: str | None = None, orden_id: int | None = None) -> list[dict]:
        filtros = {"p.estado": estado, "p.orden_id": orden_id}
        filtros = {campo: valor for campo, valor in filtros.items() if valor is not None}
        where = " AND ".join(f"{campo} = ?" for campo in filtros)
        filas = self.con.execute(
            self.CONSULTA_COMPLETA + (f" WHERE {where}" if where else "") + " ORDER BY p.id DESC",
            list(filtros.values()),
        ).fetchall()
        return [dict(fila) for fila in filas]

    def obtener_completa(self, peticion_id: int) -> dict:
        self.obtener_por_id(peticion_id)
        return dict(self.con.execute(self.CONSULTA_COMPLETA + " WHERE p.id = ?", (peticion_id,)).fetchone())

    def enviar(self, peticion_id: int, usuario: str | None = None) -> dict:
        """Acepta la solicitud y manda el material: se agrega al proyecto, se descuenta del almacén
        y el mecánico que lo pidió recibe un aviso en su bandeja."""
        self._exigir_pendiente(peticion_id)
        peticion = self.obtener_completa(peticion_id)
        RepositorioDetalle(self.con).agregar(
            peticion["orden_id"], peticion["repuesto_id"], peticion["cantidad"], usuario
        )
        self._responder(peticion_id, "enviada", None)
        material = f"{peticion['repuesto']} × {peticion['cantidad']}"
        RepositorioMovimiento(self.con).registrar(
            "solicitud_aceptada",
            f"Solicitud de {peticion['mecanico']}: {material} al proyecto #{peticion['orden_id']}",
            cantidad=peticion["cantidad"], repuesto_id=peticion["repuesto_id"],
            orden_id=peticion["orden_id"], usuario=usuario,
        )
        RepositorioMensaje(self.con).crear(
            {
                "mecanico_id": peticion["mecanico_id"],
                "remitente": "Recepción",
                "asunto": f"Material enviado: {material}",
                "texto": f"Recepción aceptó su solicitud y envió {material} al proyecto #{peticion['orden_id']}.",
                "orden_id": peticion["orden_id"],
            }
        )
        return self.obtener_completa(peticion_id)

    def rechazar(self, peticion_id: int, respuesta: str) -> dict:
        self._exigir_pendiente(peticion_id)
        self._responder(peticion_id, "rechazada", respuesta)
        return self.obtener_completa(peticion_id)

    def _exigir_pendiente(self, peticion_id: int) -> dict:
        peticion = self.obtener_por_id(peticion_id)
        if peticion["estado"] != "pendiente":
            raise HTTPException(status_code=400, detail=f"Esta petición ya fue {peticion['estado']}")
        return peticion

    def _responder(self, peticion_id: int, estado: str, respuesta: str | None) -> None:
        self.con.execute(
            """
            UPDATE peticiones SET estado = ?, respuesta = ?, fecha_respuesta = datetime('now', 'localtime')
            WHERE id = ?
            """,
            (estado, respuesta, peticion_id),
        )


class RepositorioPago(RepositorioBase):
    """Cobros a los clientes. Un proyecto se puede pagar en partes, sin pasarse del total."""

    tabla = "pagos"
    columnas = ("orden_id", "monto", "tipo", *COLUMNAS_PAGADOR, "registrado_por")
    no_encontrado = "Pago no encontrado"

    CONSULTA_COBROS = f"""
        SELECT o.id, o.estado, o.fecha_ingreso, v.placa, v.marca, v.modelo,
               c.nombre AS cliente, c.telefono, {TOTAL_ORDEN} AS total, {PAGADO_ORDEN} AS pagado
        FROM ordenes_servicio o
        JOIN vehiculos v ON v.id = o.vehiculo_id
        JOIN clientes c ON c.id = v.cliente_id
    """

    def cobros(self, estado_pago: str | None = None) -> list[dict]:
        filas = self.con.execute(self.CONSULTA_COBROS + " ORDER BY o.id DESC").fetchall()
        cobros = [self._con_saldo(fila) for fila in filas]
        return [c for c in cobros if estado_pago is None or c["estado_pago"] == estado_pago]

    def cobro(self, orden_id: int) -> dict:
        RepositorioOrden(self.con).obtener_por_id(orden_id)
        fila = self.con.execute(self.CONSULTA_COBROS + " WHERE o.id = ?", (orden_id,)).fetchone()
        pagos = self.con.execute(
            "SELECT * FROM pagos WHERE orden_id = ? ORDER BY fecha, id", (orden_id,)
        ).fetchall()
        return {**self._con_saldo(fila), "pagos": [dict(pago) for pago in pagos]}

    def registrar(self, orden_id: int, datos: dict, usuario: str) -> dict:
        """Registra un pago o un anticipo. Los anticipos solo antes de que el trabajo esté listo."""
        cobro = self.cobro(orden_id)
        if cobro["saldo"] <= 0:
            raise HTTPException(status_code=400, detail="Este proyecto ya está pagado")
        if round(datos["monto"], 2) > cobro["saldo"]:
            raise HTTPException(status_code=400, detail=f"El pago es mayor que el saldo (L {cobro['saldo']:,.2f})")
        if datos["tipo"] == "anticipo" and cobro["estado"] not in ESTADOS_EDITABLES:
            raise HTTPException(
                status_code=400,
                detail="Los anticipos se registran antes de que el trabajo esté listo; registre un pago",
            )
        monto = round(datos["monto"], 2)
        self.crear({**datos, "monto": monto, "orden_id": orden_id, "registrado_por": usuario})
        nombre = "Anticipo" if datos["tipo"] == "anticipo" else "Pago"
        RepositorioMovimiento(self.con).registrar(
            datos["tipo"],
            f"{nombre} del proyecto #{orden_id} · {datos['pagador_nombres']} {datos['pagador_apellidos']} "
            f"· {datos['metodo']}",
            monto=monto, orden_id=orden_id, usuario=usuario,
        )
        return self.cobro(orden_id)

    def anular(self, pago_id: int, usuario: str) -> None:
        pago = self.obtener_por_id(pago_id)
        self.eliminar(pago_id)
        RepositorioMovimiento(self.con).registrar(
            "pago_anulado",
            f"Se anuló un {pago['tipo']} de L {pago['monto']:,.2f} del proyecto #{pago['orden_id']}",
            monto=-pago["monto"], orden_id=pago["orden_id"], usuario=usuario,
        )

    @staticmethod
    def _con_saldo(fila: sqlite3.Row) -> dict:
        cobro = dict(fila)
        cobro["total"] = round(cobro["total"], 2)
        cobro["pagado"] = round(cobro["pagado"], 2)
        cobro["saldo"] = round(cobro["total"] - cobro["pagado"], 2)
        if cobro["saldo"] <= 0 and cobro["pagado"] > 0:
            cobro["estado_pago"] = "pagado"
        elif cobro["pagado"] > 0:
            cobro["estado_pago"] = "parcial"
        else:
            cobro["estado_pago"] = "pendiente"
        return cobro


class RepositorioMensaje(RepositorioBase):
    """Mensajería entre recepción y los mecánicos. Cada mensaje pertenece a la conversación de un
    mecánico; «direccion» dice si lo envió recepción (a_mecanico) o el mecánico (a_recepcion)."""

    tabla = "mensajes"
    columnas = ("mecanico_id", "remitente", "asunto", "texto", "orden_id", "direccion")
    no_encontrado = "Mensaje no encontrado"

    CONSULTA_COMPLETA = "SELECT x.*, m.nombre AS mecanico FROM mensajes x JOIN mecanicos m ON m.id = x.mecanico_id"

    def enviar(self, mecanico_ids: list[int], datos: dict, remitente: str) -> list[dict]:
        """Recepción manda el mismo mensaje a cada mecánico de la lista."""
        if datos.get("orden_id") is not None:
            RepositorioOrden(self.con).obtener_por_id(datos["orden_id"])
        enviados = []
        for mecanico_id in dict.fromkeys(mecanico_ids):
            RepositorioMecanico(self.con).obtener_por_id(mecanico_id)
            mensaje = self.crear({**datos, "mecanico_id": mecanico_id, "remitente": remitente})
            enviados.append(self.obtener_completo(mensaje["id"]))
        return enviados

    def escribir_a_recepcion(self, mecanico_id: int, datos: dict) -> dict:
        """Un mecánico le escribe a recepción; solo puede hacerlo mientras tenga un proyecto activo."""
        if mecanico_id not in RepositorioOrden(self.con).ocupados():
            raise HTTPException(
                status_code=403, detail="Solo puede escribir a recepción mientras tenga un proyecto activo"
            )
        if datos.get("orden_id") is not None:
            RepositorioTrabajos(self.con, mecanico_id).obtener(datos["orden_id"])
        nombre = RepositorioMecanico(self.con).obtener_por_id(mecanico_id)["nombre"]
        mensaje = self.crear({**datos, "mecanico_id": mecanico_id, "remitente": nombre, "direccion": "a_recepcion"})
        return self.obtener_completo(mensaje["id"])

    def listar(self, mecanico_id: int | None = None, direccion: str | None = None) -> list[dict]:
        filtros = {"x.mecanico_id": mecanico_id, "x.direccion": direccion}
        filtros = {campo: valor for campo, valor in filtros.items() if valor is not None}
        where = " AND ".join(f"{campo} = ?" for campo in filtros)
        filas = self.con.execute(
            self.CONSULTA_COMPLETA + (f" WHERE {where}" if where else "") + " ORDER BY x.id DESC",
            list(filtros.values()),
        ).fetchall()
        return [dict(fila) for fila in filas]

    def obtener_completo(self, mensaje_id: int) -> dict:
        self.obtener_por_id(mensaje_id)
        return dict(self.con.execute(self.CONSULTA_COMPLETA + " WHERE x.id = ?", (mensaje_id,)).fetchone())

    def marcar_leido(self, mensaje_id: int, mecanico_id: int) -> None:
        """El mecánico marca como leído un mensaje que le mandó recepción."""
        mensaje = self.obtener_por_id(mensaje_id)
        # Un mensaje de otro mecánico, o uno que él mismo envió, responde como si no existiera
        if mensaje["mecanico_id"] != mecanico_id or mensaje["direccion"] != "a_mecanico":
            raise HTTPException(status_code=404, detail=self.no_encontrado)
        self.con.execute("UPDATE mensajes SET leido = 1 WHERE id = ?", (mensaje_id,))

    def marcar_todos(self, mecanico_id: int) -> int:
        return self.con.execute(
            "UPDATE mensajes SET leido = 1 WHERE mecanico_id = ? AND direccion = 'a_mecanico' AND leido = 0",
            (mecanico_id,),
        ).rowcount

    def marcar_leido_por_recepcion(self, mensaje_id: int) -> None:
        if self.obtener_por_id(mensaje_id)["direccion"] != "a_recepcion":
            raise HTTPException(status_code=400, detail="Ese mensaje lo envió recepción")
        self.con.execute("UPDATE mensajes SET leido = 1 WHERE id = ?", (mensaje_id,))


class RepositorioVenta(RepositorioBase):
    """Venta de un repuesto suelto (producto individual), sin proyecto de taller."""

    tabla = "ventas"
    columnas = ("repuesto_id", "cantidad", "precio_unitario", "total", *COLUMNAS_PAGADOR, "registrado_por")
    no_encontrado = "Venta no encontrada"

    CONSULTA_COMPLETA = "SELECT x.*, r.nombre AS repuesto FROM ventas x JOIN repuestos r ON r.id = x.repuesto_id"

    def vender(self, datos: dict, usuario: str) -> dict:
        repuesto = RepositorioRepuesto(self.con).obtener_por_id(datos["repuesto_id"])
        if repuesto["existencia"] < datos["cantidad"]:
            raise HTTPException(
                status_code=400, detail=f"No hay existencia suficiente: quedan {repuesto['existencia']}"
            )
        total = round(repuesto["precio"] * datos["cantidad"], 2)
        self.con.execute(
            "UPDATE repuestos SET existencia = existencia - ? WHERE id = ?", (datos["cantidad"], repuesto["id"])
        )
        venta = self.crear(
            {**datos, "precio_unitario": repuesto["precio"], "total": total, "registrado_por": usuario}
        )
        RepositorioMovimiento(self.con).registrar(
            "venta",
            f"Venta de {repuesto['nombre']} × {datos['cantidad']} · "
            f"{datos['pagador_nombres']} {datos['pagador_apellidos']} · {datos['metodo']}",
            monto=total, cantidad=datos["cantidad"], repuesto_id=repuesto["id"], usuario=usuario,
        )
        return self.obtener_completa(venta["id"])

    def listar(self) -> list[dict]:
        return [dict(fila) for fila in self.con.execute(self.CONSULTA_COMPLETA + " ORDER BY x.id DESC")]

    def obtener_completa(self, venta_id: int) -> dict:
        self.obtener_por_id(venta_id)
        return dict(self.con.execute(self.CONSULTA_COMPLETA + " WHERE x.id = ?", (venta_id,)).fetchone())


class RepositorioMovimiento(RepositorioBase):
    """Historial de movimientos: pagos, ventas, solicitudes aceptadas y repuestos usados o devueltos."""

    tabla = "movimientos"
    columnas = ("tipo", "descripcion", "monto", "cantidad", "repuesto_id", "orden_id", "usuario")
    no_encontrado = "Movimiento no encontrado"

    def registrar(self, tipo: str, descripcion: str, **campos) -> None:
        self.crear({"tipo": tipo, "descripcion": descripcion, **campos})

    def listar(self, tipos: list[str] | None = None, limite: int = 500) -> list[dict]:
        where = f" WHERE x.tipo IN ({', '.join('?' for _ in tipos)})" if tipos else ""
        filas = self.con.execute(
            "SELECT x.*, r.nombre AS repuesto FROM movimientos x LEFT JOIN repuestos r ON r.id = x.repuesto_id"
            + where + " ORDER BY x.fecha DESC, x.id DESC LIMIT ?",
            [*(tipos or []), limite],
        ).fetchall()
        return [dict(fila) for fila in filas]
