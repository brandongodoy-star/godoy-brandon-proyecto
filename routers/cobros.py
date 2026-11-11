from fastapi import APIRouter, Depends, status

from database import obtener_conexion
from modelos import CobroDetalle, CobroProyecto, EstadoPago, MensajeRespuesta, PagoEntrada
from repositorios import RepositorioPago
from seguridad import solo_administrador, solo_personal

# Cobros a los clientes por cada proyecto de trabajo
router = APIRouter(tags=["Cobros"])


@router.get("/cobros", response_model=list[CobroProyecto], dependencies=[Depends(solo_personal)])
def listar_cobros(estado_pago: EstadoPago | None = None):
    with obtener_conexion() as con:
        return RepositorioPago(con).cobros(estado_pago)


@router.get("/ordenes/{orden_id}/cobro", response_model=CobroDetalle, dependencies=[Depends(solo_personal)])
def ver_cobro(orden_id: int):
    with obtener_conexion() as con:
        return RepositorioPago(con).cobro(orden_id)


@router.post("/ordenes/{orden_id}/pagos", response_model=CobroDetalle, status_code=status.HTTP_201_CREATED)
def registrar_pago(orden_id: int, datos: PagoEntrada, usuario: dict = Depends(solo_personal)):
    with obtener_conexion() as con:
        return RepositorioPago(con).registrar(orden_id, datos.model_dump(), usuario["username"])


@router.delete("/pagos/{pago_id}", response_model=MensajeRespuesta, dependencies=[Depends(solo_administrador)])
def anular_pago(pago_id: int):
    """Solo la administración puede anular un pago registrado por error."""
    with obtener_conexion() as con:
        RepositorioPago(con).eliminar(pago_id)
    return {"mensaje": "Pago anulado"}
