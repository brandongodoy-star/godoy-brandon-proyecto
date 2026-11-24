from fastapi import APIRouter, Depends, status

from database import obtener_conexion
from modelos import MensajeRespuesta, TallerEntrada, TallerRespuesta
from repositorios import RepositorioTaller
from seguridad import solo_personal

# Talleres (sedes): recepción y administración los registran; cada mecánico trabaja en uno
router = APIRouter(prefix="/talleres", tags=["Talleres"], dependencies=[Depends(solo_personal)])


@router.get("", response_model=list[TallerRespuesta])
def listar_talleres():
    with obtener_conexion() as con:
        return RepositorioTaller(con).listar()


@router.get("/{taller_id}", response_model=TallerRespuesta)
def ver_taller(taller_id: int):
    with obtener_conexion() as con:
        return RepositorioTaller(con).obtener_completo(taller_id)


@router.post("", response_model=TallerRespuesta, status_code=status.HTTP_201_CREATED)
def crear_taller(datos: TallerEntrada):
    with obtener_conexion() as con:
        repositorio = RepositorioTaller(con)
        return repositorio.obtener_completo(repositorio.crear(datos.model_dump())["id"])


@router.put("/{taller_id}", response_model=TallerRespuesta)
def actualizar_taller(taller_id: int, datos: TallerEntrada):
    with obtener_conexion() as con:
        repositorio = RepositorioTaller(con)
        repositorio.actualizar(taller_id, datos.model_dump())
        return repositorio.obtener_completo(taller_id)


@router.delete("/{taller_id}", response_model=MensajeRespuesta)
def eliminar_taller(taller_id: int):
    with obtener_conexion() as con:
        RepositorioTaller(con).eliminar(taller_id)
    return {"mensaje": "Taller eliminado"}
