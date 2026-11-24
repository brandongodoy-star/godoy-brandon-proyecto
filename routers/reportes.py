from typing import Literal

from fastapi import APIRouter, Depends, Response

from database import obtener_conexion
from modelos import ReporteRespuesta, ResolverEntrada
from repositorios import RepositorioReporte
from seguridad import solo_personal

# Reportes de todos los mecánicos, para administración y recepción
router = APIRouter(prefix="/reportes", tags=["Reportes"], dependencies=[Depends(solo_personal)])


@router.get("", response_model=list[ReporteRespuesta])
def listar_reportes(estado: Literal["abierto", "resuelto"] | None = None):
    with obtener_conexion() as con:
        return RepositorioReporte(con).listar(estado=estado)


def respuesta_pdf(contenido: bytes, nombre: str) -> Response:
    """El PDF se abre en el navegador; al guardarlo se llama como `nombre` (por ejemplo «reporte-3.pdf»)."""
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{nombre}"'},
    )


@router.get("/{reporte_id}/pdf", response_class=Response)
def pdf_del_reporte(reporte_id: int):
    """Copia en PDF que se guardó al enviar el reporte."""
    with obtener_conexion() as con:
        return respuesta_pdf(RepositorioReporte(con).pdf(reporte_id), f"reporte-{reporte_id}.pdf")


@router.post("/{reporte_id}/resolver", response_model=ReporteRespuesta)
def resolver_reporte(reporte_id: int, datos: ResolverEntrada | None = None):
    """Si es el reporte de un líder, se puede bajar la fama del reportado (créditos enteros)."""
    datos = datos or ResolverEntrada()
    with obtener_conexion() as con:
        return RepositorioReporte(con).resolver(reporte_id, datos.penalizacion, datos.comentario)
