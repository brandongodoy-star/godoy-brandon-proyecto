from typing import Literal

from fastapi import APIRouter, Depends

from database import obtener_conexion
from modelos import ReporteRespuesta
from repositorios import RepositorioReporte
from seguridad import solo_personal

# Reportes de todos los mecánicos, para administración y recepción
router = APIRouter(prefix="/reportes", tags=["Reportes"], dependencies=[Depends(solo_personal)])


@router.get("", response_model=list[ReporteRespuesta])
def listar_reportes(estado: Literal["abierto", "resuelto"] | None = None):
    with obtener_conexion() as con:
        return RepositorioReporte(con).listar(estado=estado)


@router.post("/{reporte_id}/resolver", response_model=ReporteRespuesta)
def resolver_reporte(reporte_id: int):
    with obtener_conexion() as con:
        return RepositorioReporte(con).resolver(reporte_id)
