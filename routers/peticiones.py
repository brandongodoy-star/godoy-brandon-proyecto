from typing import Literal

from fastapi import APIRouter, Depends

from database import obtener_conexion
from modelos import PeticionRespuesta, RechazoEntrada
from repositorios import RepositorioPeticion
from seguridad import solo_personal

# Material que piden los mecánicos; recepción lo envía desde el almacén o lo rechaza
router = APIRouter(prefix="/peticiones", tags=["Peticiones de material"], dependencies=[Depends(solo_personal)])


@router.get("", response_model=list[PeticionRespuesta])
def listar_peticiones(estado: Literal["pendiente", "enviada", "rechazada"] | None = None):
    with obtener_conexion() as con:
        return RepositorioPeticion(con).listar(estado=estado)


@router.post("/{peticion_id}/enviar", response_model=PeticionRespuesta)
def enviar_material(peticion_id: int, usuario: dict = Depends(solo_personal)):
    with obtener_conexion() as con:
        return RepositorioPeticion(con).enviar(peticion_id, usuario["username"])


@router.post("/{peticion_id}/rechazar", response_model=PeticionRespuesta)
def rechazar_peticion(peticion_id: int, datos: RechazoEntrada):
    with obtener_conexion() as con:
        return RepositorioPeticion(con).rechazar(peticion_id, datos.respuesta)
