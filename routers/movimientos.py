from fastapi import APIRouter, Depends, Query

from database import obtener_conexion
from modelos import MovimientoRespuesta, TipoMovimiento
from repositorios import RepositorioMovimiento
from seguridad import solo_personal

# Historial de movimientos: pagos, ventas, solicitudes aceptadas y repuestos usados o devueltos
router = APIRouter(prefix="/movimientos", tags=["Historial de movimientos"], dependencies=[Depends(solo_personal)])


@router.get("", response_model=list[MovimientoRespuesta])
def listar_movimientos(tipo: list[TipoMovimiento] | None = Query(default=None)):
    """Filtra por uno o varios tipos: ?tipo=pago&tipo=anticipo"""
    with obtener_conexion() as con:
        return RepositorioMovimiento(con).listar(tipo)
