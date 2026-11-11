from fastapi import APIRouter, Depends, HTTPException, status

from database import obtener_conexion
from modelos import (
    AvisoEntrada,
    MensajeARecepcion,
    MensajeMecanico,
    MensajeRespuesta,
    MiembroEntrada,
    NotaEntrada,
    PerfilMecanico,
    PeticionEntrada,
    PeticionRespuesta,
    ReporteEntrada,
    ReporteMiembroEntrada,
    ReporteRespuesta,
    RepuestoDisponible,
    Trabajo,
    TrabajoDetalle,
)
from repositorios import RepositorioMensaje, RepositorioReporte, RepositorioRepuesto, RepositorioTrabajos
from seguridad import solo_mecanico

# Área limitada del mecánico: solo ve sus trabajos, sus reportes y su perfil
router = APIRouter(prefix="/mecanico", tags=["Área del mecánico"])


def mecanico_actual(usuario: dict = Depends(solo_mecanico)) -> dict:
    """La cuenta debe estar vinculada a un mecánico activo."""
    with obtener_conexion() as con:
        mecanico = con.execute(
            "SELECT activo FROM mecanicos WHERE id = ?", (usuario["mecanico_id"],)
        ).fetchone()
    if mecanico is None or not mecanico["activo"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Su ficha de mecánico está inactiva")
    return usuario


@router.get("/perfil", response_model=PerfilMecanico)
def mi_perfil(usuario: dict = Depends(mecanico_actual)):
    with obtener_conexion() as con:
        return RepositorioTrabajos(con, usuario["mecanico_id"]).perfil(usuario["username"])


@router.get("/trabajos", response_model=list[Trabajo])
def mis_trabajos(usuario: dict = Depends(mecanico_actual)):
    with obtener_conexion() as con:
        return RepositorioTrabajos(con, usuario["mecanico_id"]).listar()


@router.get("/trabajos/{orden_id}", response_model=TrabajoDetalle)
def ver_trabajo(orden_id: int, usuario: dict = Depends(mecanico_actual)):
    with obtener_conexion() as con:
        return RepositorioTrabajos(con, usuario["mecanico_id"]).detalle(orden_id)


@router.post("/trabajos/{orden_id}/empezar", response_model=TrabajoDetalle)
def empezar_trabajo(orden_id: int, usuario: dict = Depends(mecanico_actual)):
    with obtener_conexion() as con:
        return RepositorioTrabajos(con, usuario["mecanico_id"]).iniciar(orden_id)


@router.post("/trabajos/{orden_id}/listo", response_model=TrabajoDetalle)
def marcar_listo(orden_id: int, datos: NotaEntrada | None = None, usuario: dict = Depends(mecanico_actual)):
    nota = datos.nota if datos else None
    with obtener_conexion() as con:
        return RepositorioTrabajos(con, usuario["mecanico_id"]).marcar_listo(orden_id, nota)


@router.post("/trabajos/{orden_id}/aviso", response_model=MensajeRespuesta)
def enviar_aviso(orden_id: int, datos: AvisoEntrada, usuario: dict = Depends(mecanico_actual)):
    with obtener_conexion() as con:
        RepositorioTrabajos(con, usuario["mecanico_id"]).enviar_aviso(orden_id, datos.mensaje)
    return {"mensaje": "Aviso enviado a recepción"}


# ---------- Material del almacén ----------
@router.get("/repuestos", response_model=list[RepuestoDisponible])
def repuestos_del_almacen(_: dict = Depends(mecanico_actual)):
    with obtener_conexion() as con:
        return RepositorioRepuesto(con).obtener_todos()


@router.post(
    "/trabajos/{orden_id}/peticiones", response_model=PeticionRespuesta, status_code=status.HTTP_201_CREATED
)
def pedir_material(orden_id: int, datos: PeticionEntrada, usuario: dict = Depends(mecanico_actual)):
    """Cualquiera del equipo pide material; recepción lo envía o lo rechaza desde su bandeja."""
    with obtener_conexion() as con:
        return RepositorioTrabajos(con, usuario["mecanico_id"]).pedir_material(orden_id, datos.model_dump())


# ---------- Solo el líder del trabajo, mientras el trabajo no termine ----------
@router.put("/trabajos/{orden_id}/equipo/{miembro_id}", response_model=TrabajoDetalle)
def dirigir_miembro(
    orden_id: int, miembro_id: int, datos: MiembroEntrada, usuario: dict = Depends(mecanico_actual)
):
    """Asigna la tarea de un miembro y/o califica su trabajo (solo cambia lo que se envía)."""
    with obtener_conexion() as con:
        return RepositorioTrabajos(con, usuario["mecanico_id"]).dirigir_miembro(
            orden_id, miembro_id, datos.model_dump(include=datos.model_fields_set)
        )


@router.post(
    "/trabajos/{orden_id}/reportes-equipo",
    response_model=ReporteRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def reportar_miembro(orden_id: int, datos: ReporteMiembroEntrada, usuario: dict = Depends(mecanico_actual)):
    with obtener_conexion() as con:
        return RepositorioTrabajos(con, usuario["mecanico_id"]).reportar_miembro(orden_id, datos.model_dump())


@router.get("/reportes", response_model=list[ReporteRespuesta])
def mis_reportes(usuario: dict = Depends(mecanico_actual)):
    with obtener_conexion() as con:
        return RepositorioReporte(con).listar(mecanico_id=usuario["mecanico_id"])


@router.post("/reportes", response_model=ReporteRespuesta, status_code=status.HTTP_201_CREATED)
def crear_reporte(datos: ReporteEntrada, usuario: dict = Depends(mecanico_actual)):
    with obtener_conexion() as con:
        return RepositorioReporte(con).crear_de_mecanico(usuario["mecanico_id"], datos.model_dump())


# ---------- Bandeja: mensajes de recepción ----------
@router.get("/mensajes", response_model=list[MensajeMecanico])
def mis_mensajes(usuario: dict = Depends(mecanico_actual)):
    with obtener_conexion() as con:
        return RepositorioMensaje(con).listar(usuario["mecanico_id"])


@router.post("/mensajes/leer-todos", response_model=MensajeRespuesta)
def leer_todos(usuario: dict = Depends(mecanico_actual)):
    with obtener_conexion() as con:
        cantidad = RepositorioMensaje(con).marcar_todos(usuario["mecanico_id"])
    return {"mensaje": f"{cantidad} mensajes marcados como leídos"}


@router.post("/mensajes/{mensaje_id}/leido", response_model=MensajeRespuesta)
def marcar_leido(mensaje_id: int, usuario: dict = Depends(mecanico_actual)):
    with obtener_conexion() as con:
        RepositorioMensaje(con).marcar_leido(mensaje_id, usuario["mecanico_id"])
    return {"mensaje": "Mensaje leído"}


@router.post("/mensajes", response_model=MensajeMecanico, status_code=status.HTTP_201_CREATED)
def escribir_a_recepcion(datos: MensajeARecepcion, usuario: dict = Depends(mecanico_actual)):
    """Mientras tenga un proyecto activo, el mecánico puede escribirle a recepción (por ejemplo, para pedir algo)."""
    with obtener_conexion() as con:
        return RepositorioMensaje(con).escribir_a_recepcion(usuario["mecanico_id"], datos.model_dump())
