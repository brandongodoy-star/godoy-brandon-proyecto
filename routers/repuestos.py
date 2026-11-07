from fastapi import APIRouter, Depends, status

from database import obtener_conexion
from modelos import MensajeRespuesta, RepuestoEntrada, RepuestoRespuesta
from repositorios import RepositorioRepuesto
from seguridad import obtener_usuario_actual

router = APIRouter(
    prefix="/repuestos", tags=["Repuestos"], dependencies=[Depends(obtener_usuario_actual)]
)


@router.get("", response_model=list[RepuestoRespuesta])
def listar_repuestos():
    with obtener_conexion() as con:
        return RepositorioRepuesto(con).obtener_todos()


@router.get("/{repuesto_id}", response_model=RepuestoRespuesta)
def obtener_repuesto(repuesto_id: int):
    with obtener_conexion() as con:
        return RepositorioRepuesto(con).obtener_por_id(repuesto_id)


@router.post("", response_model=RepuestoRespuesta, status_code=status.HTTP_201_CREATED)
def crear_repuesto(datos: RepuestoEntrada):
    with obtener_conexion() as con:
        return RepositorioRepuesto(con).crear(datos.model_dump(mode="json"))


@router.put("/{repuesto_id}", response_model=RepuestoRespuesta)
def actualizar_repuesto(repuesto_id: int, datos: RepuestoEntrada):
    with obtener_conexion() as con:
        return RepositorioRepuesto(con).actualizar(repuesto_id, datos.model_dump(mode="json"))


@router.delete("/{repuesto_id}", response_model=MensajeRespuesta)
def eliminar_repuesto(repuesto_id: int):
    with obtener_conexion() as con:
        RepositorioRepuesto(con).eliminar(repuesto_id)
    return {"mensaje": "Repuesto eliminado"}
