from fastapi import APIRouter, Depends, Response, status

from database import obtener_conexion
from modelos import (
    AnticipoRespuesta,
    CobroDetalle,
    ComprobanteRespuesta,
    CobroProyecto,
    EstadoPago,
    MensajeRespuesta,
    PagoEntrada,
    VentaEntrada,
    VentaRespuesta,
)
from repositorios import RepositorioPago, RepositorioVenta
from routers.reportes import respuesta_pdf
from seguridad import solo_administrador, solo_personal

# Cobros: pagos y anticipos de los proyectos de taller, y venta de repuestos sueltos
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
    """Pago o anticipo de un trabajo de taller, con los datos de quien paga."""
    with obtener_conexion() as con:
        return RepositorioPago(con).registrar(orden_id, datos.model_dump(), usuario["username"])


@router.get("/anticipos", response_model=list[AnticipoRespuesta], dependencies=[Depends(solo_personal)])
def listar_anticipos():
    """Apartado de pagos anticipados: los abonos hechos antes de que el trabajo esté listo."""
    with obtener_conexion() as con:
        return RepositorioPago(con).anticipos()


@router.get("/pagos/{pago_id}/pdf", response_class=Response, dependencies=[Depends(solo_personal)])
def comprobante_de_pago(pago_id: int):
    """Comprobante en PDF que se guardó al registrar el pago o el anticipo."""
    with obtener_conexion() as con:
        return respuesta_pdf(RepositorioPago(con).pdf(pago_id), f"comprobante-P-{pago_id:06d}.pdf")


@router.get("/ventas/{venta_id}/pdf", response_class=Response, dependencies=[Depends(solo_personal)])
def comprobante_de_venta(venta_id: int):
    with obtener_conexion() as con:
        return respuesta_pdf(RepositorioVenta(con).pdf(venta_id), f"comprobante-V-{venta_id:06d}.pdf")


@router.get("/comprobantes", response_model=list[ComprobanteRespuesta], dependencies=[Depends(solo_administrador)])
def archivo_de_comprobantes():
    """Archivo de la administración: cada cobro con su comprobante en PDF y la nota del sistema."""
    with obtener_conexion() as con:
        return RepositorioPago(con).comprobantes()


@router.delete("/pagos/{pago_id}", response_model=MensajeRespuesta)
def anular_pago(pago_id: int, usuario: dict = Depends(solo_administrador)):
    """Solo la administración puede anular un pago registrado por error."""
    with obtener_conexion() as con:
        RepositorioPago(con).anular(pago_id, usuario["username"])
    return {"mensaje": "Pago anulado"}


@router.get("/ventas", response_model=list[VentaRespuesta], dependencies=[Depends(solo_personal)])
def listar_ventas():
    with obtener_conexion() as con:
        return RepositorioVenta(con).listar()


@router.post("/ventas", response_model=VentaRespuesta, status_code=status.HTTP_201_CREATED)
def vender_repuesto(datos: VentaEntrada, usuario: dict = Depends(solo_personal)):
    """Venta de un producto individual: se cobra y se descuenta del almacén."""
    with obtener_conexion() as con:
        return RepositorioVenta(con).vender(datos.model_dump(), usuario["username"])
