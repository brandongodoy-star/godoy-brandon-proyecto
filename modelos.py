from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from creditos import nivel_de

EstadoOrden = Literal["recibido", "en reparacion", "listo", "entregado"]
Categoria = Literal["estandar", "premium", "lujo"]
Calificacion = Literal["excelente", "bien", "con problemas", "rehacer"]
Rol = Literal["administrador", "recepcion", "mecanico"]
TipoReporte = Literal["equipo", "repuestos", "seguridad", "otro"]


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
    categoria: Categoria = "estandar"

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
    telefono: str | None = Field(default=None, max_length=20)
    correo: str | None = Field(default=None, max_length=100, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    fecha_contratacion: date | None = None

    @field_validator("fecha_contratacion")
    @classmethod
    def contratacion_no_futura(cls, valor: date | None) -> date | None:
        if valor and valor > date.today():
            raise ValueError("La fecha de contratación no puede ser futura")
        return valor


class MecanicoRespuesta(MecanicoEntrada):
    id: int
    creditos: int

    @computed_field
    @property
    def nivel(self) -> str:
        return nivel_de(self.creditos)["nombre"]


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
    # mecanico_id es el líder del trabajo; equipo son los demás mecánicos que lo acompañan
    equipo: list[Annotated[int, Field(gt=0)]] = Field(default_factory=list, max_length=6)

    @field_validator("fecha_ingreso")
    @classmethod
    def fecha_no_futura(cls, valor: date) -> date:
        if valor > date.today():
            raise ValueError("La fecha de ingreso no puede ser futura")
        return valor


class OrdenRespuesta(OrdenEntrada):
    id: int
    estado: EstadoOrden
    calificacion: Calificacion | None = None


class AvanceEntrada(Entrada):
    """Al pasar una orden a «entregado», recepción califica el trabajo del mecánico."""

    calificacion: Calificacion | None = None


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


# ---------- Cuentas ----------
class UsuarioEntrada(Entrada):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=6, max_length=72)
    rol: Rol
    nombre: str | None = Field(default=None, max_length=100)
    mecanico_id: int | None = Field(default=None, gt=0)


class UsuarioRespuesta(BaseModel):
    id: int
    username: str
    rol: Rol
    nombre: str | None = None
    mecanico_id: int | None = None
    mecanico: str | None = None


class CambioPassword(Entrada):
    password_actual: str = Field(min_length=1, max_length=72)
    password_nueva: str = Field(min_length=6, max_length=72)


# ---------- Área del mecánico ----------
class NotaEntrada(Entrada):
    nota: str | None = Field(default=None, max_length=300)


class AvisoEntrada(Entrada):
    mensaje: str = Field(min_length=3, max_length=300)


class Trabajo(BaseModel):
    """Una orden vista por el mecánico: sin precios ni datos de contacto del cliente."""

    id: int
    estado: EstadoOrden
    fecha_ingreso: date
    diagnostico: str | None = None
    calificacion: Calificacion | None = None
    placa: str
    marca: str
    modelo: str
    anio: int
    categoria: Categoria
    cliente: str
    lider: str
    soy_lider: bool


class RepuestoDeTrabajo(BaseModel):
    repuesto: str
    cantidad: int


class MiembroEquipo(BaseModel):
    mecanico_id: int
    nombre: str
    especialidad: str | None = None
    nivel: str
    es_lider: bool
    tarea: str | None = None
    calificacion: Calificacion | None = None


class MiembroEntrada(Entrada):
    """Lo que el líder cambia de un miembro: solo se actualizan los campos que envía."""

    tarea: str | None = Field(default=None, max_length=200)
    calificacion: Calificacion | None = None


class ReporteMiembroEntrada(Entrada):
    sobre_mecanico_id: int = Field(gt=0)
    titulo: str = Field(min_length=3, max_length=100)
    descripcion: str = Field(min_length=5, max_length=1000)


class NivelSiguiente(BaseModel):
    nombre: str
    minimo: int


class Nivel(BaseModel):
    nombre: str
    minimo: int
    categorias: list[Categoria]
    siguiente: NivelSiguiente | None = None


class MovimientoCredito(BaseModel):
    fecha: str
    puntos: int
    motivo: str
    orden_id: int | None = None


class EstadisticasMecanico(BaseModel):
    por_empezar: int
    en_reparacion: int
    listos: int
    entregados: int
    calificaciones: dict[str, int]


class PerfilMecanico(BaseModel):
    usuario: str
    nombre: str
    especialidad: str | None = None
    telefono: str | None = None
    correo: str | None = None
    fecha_contratacion: date | None = None
    creditos: int
    nivel: Nivel
    estadisticas: EstadisticasMecanico
    historial: list[MovimientoCredito]


# ---------- Reportes y notificaciones ----------
class ReporteEntrada(Entrada):
    tipo: TipoReporte
    titulo: str = Field(min_length=3, max_length=100)
    descripcion: str = Field(min_length=5, max_length=1000)
    orden_id: int | None = Field(default=None, gt=0)


class ReporteRespuesta(BaseModel):
    id: int
    mecanico_id: int
    mecanico: str
    orden_id: int | None = None
    tipo: TipoReporte | Literal["desempeno"]
    titulo: str
    descripcion: str
    estado: Literal["abierto", "resuelto"]
    fecha: str
    sobre_mecanico_id: int | None = None
    sobre_mecanico: str | None = None


class TrabajoDetalle(Trabajo):
    repuestos: list[RepuestoDeTrabajo]
    creditos: int | None = None
    equipo: list[MiembroEquipo]
    # El líder solo dirige mientras el trabajo está «recibido» o «en reparacion»
    puedo_dirigir: bool
    reportes_equipo: list[ReporteRespuesta]


class NotificacionRespuesta(BaseModel):
    id: int
    tipo: Literal["listo", "avance", "reporte"]
    mensaje: str
    orden_id: int | None = None
    mecanico_id: int | None = None
    mecanico: str | None = None
    leida: bool
    fecha: str
