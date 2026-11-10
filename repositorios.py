import sqlite3

from fastapi import HTTPException

from creditos import NOMBRE_CATEGORIA, nivel_de, puede_trabajar, puntos_de_miembro, puntos_por

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
        orden = super().crear(datos)
        self._guardar_equipo(orden["id"], miembros)
        return self.obtener_por_id(orden["id"])

    def actualizar(self, orden_id: int, datos: dict) -> dict:
        actual = self.verificar_editable(orden_id)
        self._validar_referencias(datos, actual)
        miembros = self._validar_equipo(datos)
        super().actualizar(orden_id, datos)
        self._guardar_equipo(orden_id, miembros)
        return self.obtener_por_id(orden_id)

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
        self._sumar_creditos(
            orden["mecanico_id"],
            orden["id"],
            puntos_por(calificacion, categoria),
            f"Orden #{orden['id']} calificada «{calificacion}» ({auto})",
        )
        miembros = self.con.execute(
            "SELECT mecanico_id, calificacion FROM equipo_orden WHERE orden_id = ?", (orden["id"],)
        ).fetchall()
        for miembro in miembros:
            del_lider = miembro["calificacion"] or "sin calificar"
            self._sumar_creditos(
                miembro["mecanico_id"],
                orden["id"],
                puntos_de_miembro(calificacion, miembro["calificacion"], categoria),
                f"Orden #{orden['id']} en equipo: recepción «{calificacion}», líder «{del_lider}» ({auto})",
            )

    def _sumar_creditos(self, mecanico_id: int, orden_id: int, puntos: int, motivo: str) -> None:
        mecanico = RepositorioMecanico(self.con).obtener_por_id(mecanico_id)
        # Los créditos nunca bajan de 0; en el historial queda lo que de verdad cambió
        nuevos = max(0, mecanico["creditos"] + puntos)
        self.con.execute("UPDATE mecanicos SET creditos = ? WHERE id = ?", (nuevos, mecanico_id))
        self.con.execute(
            "INSERT INTO movimientos_credito (mecanico_id, orden_id, puntos, motivo) VALUES (?, ?, ?, ?)",
            (mecanico_id, orden_id, nuevos - mecanico["creditos"], motivo),
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

    def resolver(self, reporte_id: int) -> dict:
        self.obtener_por_id(reporte_id)
        self.con.execute("UPDATE reportes SET estado = 'resuelto' WHERE id = ?", (reporte_id,))
        return self.obtener_completo(reporte_id)


class RepositorioTrabajos:
    """Las órdenes de un mecánico vistas desde su área: las que dirige como líder y las que
    acompaña como miembro del equipo. Solo ve y cambia esas."""

    # :m es el mecánico que consulta
    PARTICIPA = """(o.mecanico_id = :m OR EXISTS (
        SELECT 1 FROM equipo_orden e WHERE e.orden_id = o.id AND e.mecanico_id = :m))"""
    CONSULTA = f"""
        SELECT o.id, o.estado, o.fecha_ingreso, o.diagnostico, o.calificacion,
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
            "equipo": self._equipo(orden_id),
            "puedo_dirigir": self._puede_dirigir(trabajo),
            "reportes_equipo": reportes,
        }

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

    def _equipo(self, orden_id: int) -> list[dict]:
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
