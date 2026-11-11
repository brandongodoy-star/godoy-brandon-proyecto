from fastapi import APIRouter, Depends, status

from database import obtener_conexion
from modelos import AjusteCreditos, MecanicoEntrada, MecanicoRespuesta, MensajeRespuesta, MovimientoCredito
from repositorios import RepositorioMecanico
from seguridad import solo_personal

router = APIRouter(
    prefix="/mecanicos", tags=["Mecánicos"], dependencies=[Depends(solo_personal)]
)


@router.get("", response_model=list[MecanicoRespuesta])
def listar_mecanicos(solo_activos: bool = False):
    with obtener_conexion() as con:
        return RepositorioMecanico(con).obtener_todos(activo=1 if solo_activos else None)


@router.get("/{mecanico_id}", response_model=MecanicoRespuesta)
def obtener_mecanico(mecanico_id: int):
    with obtener_conexion() as con:
        return RepositorioMecanico(con).obtener_por_id(mecanico_id)


@router.post("", response_model=MecanicoRespuesta, status_code=status.HTTP_201_CREATED)
def crear_mecanico(datos: MecanicoEntrada):
    with obtener_conexion() as con:
        return RepositorioMecanico(con).crear(datos.model_dump(mode="json"))


@router.put("/{mecanico_id}", response_model=MecanicoRespuesta)
def actualizar_mecanico(mecanico_id: int, datos: MecanicoEntrada):
    with obtener_conexion() as con:
        return RepositorioMecanico(con).actualizar(mecanico_id, datos.model_dump(mode="json"))


@router.get("/{mecanico_id}/creditos", response_model=list[MovimientoCredito])
def historial_de_creditos(mecanico_id: int):
    with obtener_conexion() as con:
        return RepositorioMecanico(con).historial_creditos(mecanico_id)


@router.post("/{mecanico_id}/creditos", response_model=MecanicoRespuesta)
def ajustar_creditos(mecanico_id: int, datos: AjusteCreditos):
    """Recepción sube o baja créditos a mano, con un motivo (y el proyecto, si aplica)."""
    with obtener_conexion() as con:
        return RepositorioMecanico(con).ajustar_creditos(mecanico_id, datos.puntos, datos.motivo, datos.orden_id)


@router.delete("/{mecanico_id}", response_model=MensajeRespuesta)
def eliminar_mecanico(mecanico_id: int):
    # Si el mecánico ya tiene órdenes no se puede borrar; en ese caso se marca como inactivo
    with obtener_conexion() as con:
        RepositorioMecanico(con).eliminar(mecanico_id)
    return {"mensaje": "Mecánico eliminado"}
