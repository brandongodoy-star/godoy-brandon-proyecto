from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EstadoOrden = Literal["recibido", "en reparacion", "listo", "entregado"]


class Entrada(BaseModel):
    """Base de los datos que envía el usuario: quita los espacios al inicio y al final."""

    model_config = ConfigDict(str_strip_whitespace=True)


class MensajeRespuesta(BaseModel):
    mensaje: str


# ---------- Clientes ----------
class ClienteEntrada(Entrada):
    nombre: str = Field(min_length=3, max_length=100)
    telefono: str = Field(min_length=8, max_length=20)
    direccion: str | None = Field(default=None, max_length=200)


class ClienteRespuesta(ClienteEntrada):
    id: int


# ---------- Vehículos ----------
class VehiculoEntrada(Entrada):
    placa: str = Field(min_length=3, max_length=10)
    marca: str = Field(min_length=2, max_length=50)
    modelo: str = Field(min_length=1, max_length=50)
    anio: int = Field(ge=1950)
    cliente_id: int = Field(gt=0)

    @field_validator("placa")
    @classmethod
    def placa_en_mayusculas(cls, valor: str) -> str:
        return valor.upper()

    @field_validator("anio")
    @classmethod
    def anio_no_futuro(cls, valor: int) -> int:
        if valor > date.today().year + 1:
            raise ValueError("El año no puede ser mayor que el del próximo año")
        return valor


class VehiculoRespuesta(VehiculoEntrada):
    id: int


# ---------- Mecánicos ----------
class MecanicoEntrada(Entrada):
    nombre: str = Field(min_length=3, max_length=100)
    especialidad: str | None = Field(default=None, max_length=60)
    activo: bool = True


class MecanicoRespuesta(MecanicoEntrada):
    id: int


# ---------- Repuestos ----------
class RepuestoEntrada(Entrada):
    nombre: str = Field(min_length=2, max_length=100)
    precio: float = Field(gt=0)
    existencia: int = Field(default=0, ge=0)


class RepuestoRespuesta(RepuestoEntrada):
    id: int


# ---------- Órdenes de servicio ----------
class OrdenEntrada(Entrada):
    vehiculo_id: int = Field(gt=0)
    mecanico_id: int = Field(gt=0)
    fecha_ingreso: date = Field(default_factory=date.today)
    diagnostico: str | None = Field(default=None, max_length=300)
    mano_obra: float = Field(default=0, ge=0)

    @field_validator("fecha_ingreso")
    @classmethod
    def fecha_no_futura(cls, valor: date) -> date:
        if valor > date.today():
            raise ValueError("La fecha de ingreso no puede ser futura")
        return valor


class OrdenRespuesta(OrdenEntrada):
    id: int
    estado: EstadoOrden


class DetalleEntrada(Entrada):
    repuesto_id: int = Field(gt=0)
    cantidad: int = Field(gt=0)


class DetalleRespuesta(BaseModel):
    id: int
    orden_id: int
    repuesto_id: int
    repuesto: str
    cantidad: int
    precio: float
    subtotal: float


class TotalOrden(BaseModel):
    orden_id: int
    mano_obra: float
    repuestos: float
    total: float
