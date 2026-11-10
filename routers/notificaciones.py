from fastapi import APIRouter, Depends

from database import obtener_conexion
from modelos import MensajeRespuesta, NotificacionRespuesta
from repositorios import RepositorioNotificacion
from seguridad import solo_personal

# Avisos que los mecánicos envían a recepción (la pantalla de recepción se hará después)
router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"], dependencies=[Depends(solo_personal)])


@router.get("", response_model=list[NotificacionRespuesta])
def listar_notificaciones(solo_no_leidas: bool = False):
    with obtener_conexion() as con:
        return RepositorioNotificacion(con).listar(solo_no_leidas)


@router.post("/{notificacion_id}/leida", response_model=MensajeRespuesta)
def marcar_leida(notificacion_id: int):
    with obtener_conexion() as con:
        RepositorioNotificacion(con).marcar_leida(notificacion_id)
    return {"mensaje": "Notificación leída"}


@router.post("/leer-todas", response_model=MensajeRespuesta)
def marcar_todas():
    with obtener_conexion() as con:
        cantidad = RepositorioNotificacion(con).marcar_todas()
    return {"mensaje": f"{cantidad} notificaciones marcadas como leídas"}
