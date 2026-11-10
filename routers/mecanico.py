from fastapi import APIRouter, Depends, HTTPException, status

from database import obtener_conexion
from modelos import (
    AvisoEntrada,
    MensajeRespuesta,
    NotaEntrada,
    PerfilMecanico,
    ReporteEntrada,
    ReporteRespuesta,
    Trabajo,
    TrabajoDetalle,
)
from repositorios import RepositorioReporte, RepositorioTrabajos
from seguridad import solo_mecanico

# Área limitada del mecánico: solo ve sus trabajos, sus reportes y su perfil
router = APIRouter(prefix="/mecanico", tags=["Área del mecánico"])


def mecanico_actual(usuario: dict = Depends(solo_mecanico)) -> dict:
    """La cuenta debe estar vinculada a un mecánico activo."""
    with obtener_conexion() as con:
        mecanico = con.execute(
            "SELECT activo FROM mecanicos WHERE id = ?", (usuario["mecanico_id"],)
        ).fetchone()
    if mecanico is None or not mecanico["activo"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Su ficha de mecánico está inactiva")
    return usuario


@router.get("/perfil", response_model=PerfilMecanico)
def mi_perfil(usuario: dict = Depends(mecanico_actual)):
    with obtener_conexion() as con:
        return RepositorioTrabajos(con, usuario["mecanico_id"]).perfil(usuario["username"])


@router.get("/trabajos", response_model=list[Trabajo])
def mis_trabajos(usuario: dict = Depends(mecanico_actual)):
    with obtener_conexion() as con:
        return RepositorioTrabajos(con, usuario["mecanico_id"]).listar()


@router.get("/trabajos/{orden_id}", response_model=TrabajoDetalle)
def ver_trabajo(orden_id: int, usuario: dict = Depends(mecanico_actual)):
    with obtener_conexion() as con:
        return RepositorioTrabajos(con, usuario["mecanico_id"]).detalle(orden_id)


@router.post("/trabajos/{orden_id}/empezar", response_model=TrabajoDetalle)
def empezar_trabajo(orden_id: int, usuario: dict = Depends(mecanico_actual)):
    with obtener_conexion() as con:
        return RepositorioTrabajos(con, usuario["mecanico_id"]).iniciar(orden_id)


@router.post("/trabajos/{orden_id}/listo", response_model=TrabajoDetalle)
def marcar_listo(orden_id: int, datos: NotaEntrada | None = None, usuario: dict = Depends(mecanico_actual)):
    nota = datos.nota if datos else None
    with obtener_conexion() as con:
        return RepositorioTrabajos(con, usuario["mecanico_id"]).marcar_listo(orden_id, nota)


@router.post("/trabajos/{orden_id}/aviso", response_model=MensajeRespuesta)
def enviar_aviso(orden_id: int, datos: AvisoEntrada, usuario: dict = Depends(mecanico_actual)):
    with obtener_conexion() as con:
        RepositorioTrabajos(con, usuario["mecanico_id"]).enviar_aviso(orden_id, datos.mensaje)
    return {"mensaje": "Aviso enviado a recepción"}


@router.get("/reportes", response_model=list[ReporteRespuesta])
def mis_reportes(usuario: dict = Depends(mecanico_actual)):
    with obtener_conexion() as con:
        return RepositorioReporte(con).listar(mecanico_id=usuario["mecanico_id"])


@router.post("/reportes", response_model=ReporteRespuesta, status_code=status.HTTP_201_CREATED)
def crear_reporte(datos: ReporteEntrada, usuario: dict = Depends(mecanico_actual)):
    with obtener_conexion() as con:
        return RepositorioReporte(con).crear_de_mecanico(usuario["mecanico_id"], datos.model_dump())
