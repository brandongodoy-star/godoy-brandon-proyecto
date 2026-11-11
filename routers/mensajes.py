from typing import Literal

from fastapi import APIRouter, Depends, status

from database import obtener_conexion
from modelos import MensajeEntrada, MensajeMecanico, MensajeRespuesta
from repositorios import RepositorioMensaje
from seguridad import solo_personal

# Mensajería con los mecánicos: recepción les escribe y lee lo que ellos le mandan
router = APIRouter(prefix="/mensajes", tags=["Mensajes con mecánicos"], dependencies=[Depends(solo_personal)])


@router.get("", response_model=list[MensajeMecanico])
def listar_mensajes(
    mecanico_id: int | None = None, direccion: Literal["a_mecanico", "a_recepcion"] | None = None
):
    """«a_recepcion» son los que mandaron los mecánicos; «a_mecanico», los que envió recepción."""
    with obtener_conexion() as con:
        return RepositorioMensaje(con).listar(mecanico_id, direccion)


@router.post("", response_model=list[MensajeMecanico], status_code=status.HTTP_201_CREATED)
def enviar_mensaje(datos: MensajeEntrada, usuario: dict = Depends(solo_personal)):
    """Manda el mismo mensaje a cada mecánico de la lista (por ejemplo, a todo un equipo)."""
    contenido = datos.model_dump(exclude={"mecanico_ids"})
    with obtener_conexion() as con:
        return RepositorioMensaje(con).enviar(datos.mecanico_ids, contenido, usuario["nombre"] or usuario["username"])


@router.post("/{mensaje_id}/leido", response_model=MensajeRespuesta)
def marcar_leido(mensaje_id: int):
    with obtener_conexion() as con:
        RepositorioMensaje(con).marcar_leido_por_recepcion(mensaje_id)
    return {"mensaje": "Mensaje leído"}
