from fastapi import APIRouter, Depends, status

from database import obtener_conexion
from modelos import (
    AuxiliarRespuesta,
    EstadoTarea,
    MensajeRespuesta,
    RealizadaEntrada,
    TareaEntrada,
    TareaRespuesta,
)
from repositorios import RepositorioTarea
from seguridad import solo_auxiliar, solo_personal

# Recepción y administración asignan las tareas de traslado y ven cómo van
router = APIRouter(prefix="/tareas", tags=["Tareas de traslado"], dependencies=[Depends(solo_personal)])


@router.get("", response_model=list[TareaRespuesta])
def listar_tareas(estado: EstadoTarea | None = None):
    with obtener_conexion() as con:
        return RepositorioTarea(con).listar(estado)


@router.get("/auxiliares", response_model=list[AuxiliarRespuesta])
def listar_auxiliares():
    """Cuentas de auxiliar a las que se les puede asignar una tarea."""
    with obtener_conexion() as con:
        return RepositorioTarea(con).auxiliares()


@router.post("", response_model=TareaRespuesta, status_code=status.HTTP_201_CREATED)
def crear_tarea(datos: TareaEntrada, usuario: dict = Depends(solo_personal)):
    with obtener_conexion() as con:
        return RepositorioTarea(con).crear_de_recepcion(datos.model_dump(), usuario["username"])


@router.delete("/{tarea_id}", response_model=MensajeRespuesta)
def cancelar_tarea(tarea_id: int):
    with obtener_conexion() as con:
        RepositorioTarea(con).cancelar(tarea_id)
    return {"mensaje": "Tarea cancelada"}


# Área del auxiliar de operaciones y traslado: su bandeja y sus trabajos
router_auxiliar = APIRouter(prefix="/auxiliar", tags=["Área del auxiliar"])


@router_auxiliar.get("/tareas", response_model=list[TareaRespuesta])
def mis_tareas(usuario: dict = Depends(solo_auxiliar)):
    """Las tareas que tiene y las pendientes que todavía no tienen auxiliar."""
    with obtener_conexion() as con:
        return RepositorioTarea(con).de_auxiliar(usuario["id"])


@router_auxiliar.post("/tareas/{tarea_id}/aceptar", response_model=TareaRespuesta)
def aceptar_tarea(tarea_id: int, usuario: dict = Depends(solo_auxiliar)):
    with obtener_conexion() as con:
        return RepositorioTarea(con).aceptar(tarea_id, usuario["id"])


@router_auxiliar.post("/tareas/{tarea_id}/realizada", response_model=TareaRespuesta)
def marcar_realizada(tarea_id: int, datos: RealizadaEntrada | None = None, usuario: dict = Depends(solo_auxiliar)):
    """Queda registrado que el trabajo se hizo. Si era recibir producto, entra al almacén."""
    nota = datos.nota if datos else None
    with obtener_conexion() as con:
        return RepositorioTarea(con).realizar(tarea_id, usuario["id"], nota)
