from fastapi import APIRouter, Depends, status

from database import obtener_conexion
from modelos import MensajeRespuesta, VehiculoEntrada, VehiculoRespuesta
from repositorios import RepositorioVehiculo
from seguridad import solo_personal

router = APIRouter(
    prefix="/vehiculos", tags=["Vehículos"], dependencies=[Depends(solo_personal)]
)


@router.get("", response_model=list[VehiculoRespuesta])
def listar_vehiculos(cliente_id: int | None = None):
    with obtener_conexion() as con:
        return RepositorioVehiculo(con).obtener_todos(cliente_id=cliente_id)


@router.get("/{vehiculo_id}", response_model=VehiculoRespuesta)
def obtener_vehiculo(vehiculo_id: int):
    with obtener_conexion() as con:
        return RepositorioVehiculo(con).obtener_por_id(vehiculo_id)


@router.post("", response_model=VehiculoRespuesta, status_code=status.HTTP_201_CREATED)
def crear_vehiculo(datos: VehiculoEntrada):
    with obtener_conexion() as con:
        return RepositorioVehiculo(con).crear(datos.model_dump(mode="json"))


@router.put("/{vehiculo_id}", response_model=VehiculoRespuesta)
def actualizar_vehiculo(vehiculo_id: int, datos: VehiculoEntrada):
    with obtener_conexion() as con:
        return RepositorioVehiculo(con).actualizar(vehiculo_id, datos.model_dump(mode="json"))


@router.delete("/{vehiculo_id}", response_model=MensajeRespuesta)
def eliminar_vehiculo(vehiculo_id: int):
    with obtener_conexion() as con:
        RepositorioVehiculo(con).eliminar(vehiculo_id)
    return {"mensaje": "Vehículo eliminado"}
