from fastapi import APIRouter, Depends, status

from database import obtener_conexion
from modelos import (
    DetalleEntrada,
    DetalleRespuesta,
    EstadoOrden,
    MensajeRespuesta,
    OrdenEntrada,
    OrdenRespuesta,
    TotalOrden,
)
from repositorios import RepositorioDetalle, RepositorioOrden
from seguridad import obtener_usuario_actual

router = APIRouter(
    prefix="/ordenes", tags=["Órdenes de servicio"], dependencies=[Depends(obtener_usuario_actual)]
)


# ---------- La orden ----------
@router.get("", response_model=list[OrdenRespuesta])
def listar_ordenes(estado: EstadoOrden | None = None, vehiculo_id: int | None = None):
    with obtener_conexion() as con:
        return RepositorioOrden(con).obtener_todos(estado=estado, vehiculo_id=vehiculo_id)


@router.get("/{orden_id}", response_model=OrdenRespuesta)
def obtener_orden(orden_id: int):
    with obtener_conexion() as con:
        return RepositorioOrden(con).obtener_por_id(orden_id)


@router.post("", response_model=OrdenRespuesta, status_code=status.HTTP_201_CREATED)
def crear_orden(datos: OrdenEntrada):
    with obtener_conexion() as con:
        return RepositorioOrden(con).crear(datos.model_dump(mode="json"))


@router.put("/{orden_id}", response_model=OrdenRespuesta)
def actualizar_orden(orden_id: int, datos: OrdenEntrada):
    with obtener_conexion() as con:
        return RepositorioOrden(con).actualizar(orden_id, datos.model_dump(mode="json"))


@router.delete("/{orden_id}", response_model=MensajeRespuesta)
def eliminar_orden(orden_id: int):
    with obtener_conexion() as con:
        RepositorioOrden(con).eliminar(orden_id)
    return {"mensaje": "Orden eliminada y repuestos devueltos al inventario"}


@router.post("/{orden_id}/avanzar", response_model=OrdenRespuesta)
def avanzar_estado(orden_id: int):
    with obtener_conexion() as con:
        return RepositorioOrden(con).avanzar_estado(orden_id)


@router.get("/{orden_id}/total", response_model=TotalOrden)
def calcular_total(orden_id: int):
    with obtener_conexion() as con:
        return RepositorioOrden(con).calcular_total(orden_id)


# ---------- Repuestos usados en la orden ----------
@router.get("/{orden_id}/repuestos", response_model=list[DetalleRespuesta])
def listar_repuestos_de_orden(orden_id: int):
    with obtener_conexion() as con:
        return RepositorioDetalle(con).obtener_de_orden(orden_id)


@router.post(
    "/{orden_id}/repuestos", response_model=DetalleRespuesta, status_code=status.HTTP_201_CREATED
)
def agregar_repuesto(orden_id: int, datos: DetalleEntrada):
    with obtener_conexion() as con:
        return RepositorioDetalle(con).agregar(orden_id, datos.repuesto_id, datos.cantidad)


@router.delete("/{orden_id}/repuestos/{detalle_id}", response_model=MensajeRespuesta)
def quitar_repuesto(orden_id: int, detalle_id: int):
    with obtener_conexion() as con:
        RepositorioDetalle(con).quitar(orden_id, detalle_id)
    return {"mensaje": "Repuesto quitado y devuelto al inventario"}
