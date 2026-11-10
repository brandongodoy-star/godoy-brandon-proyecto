from fastapi import APIRouter, Depends, HTTPException, status

from database import obtener_conexion
from modelos import MensajeRespuesta, UsuarioEntrada, UsuarioRespuesta
from repositorios import RepositorioUsuario
from seguridad import registrar_usuario, solo_administrador

router = APIRouter(prefix="/usuarios", tags=["Cuentas"])


@router.get("", response_model=list[UsuarioRespuesta])
def listar_usuarios(_: dict = Depends(solo_administrador)):
    with obtener_conexion() as con:
        return RepositorioUsuario(con).listar()


@router.post("", response_model=UsuarioRespuesta, status_code=status.HTTP_201_CREATED)
def crear_usuario(datos: UsuarioEntrada, _: dict = Depends(solo_administrador)):
    return registrar_usuario(**datos.model_dump())


@router.delete("/{usuario_id}", response_model=MensajeRespuesta)
def eliminar_usuario(usuario_id: int, administrador: dict = Depends(solo_administrador)):
    if usuario_id == administrador["id"]:
        raise HTTPException(status_code=400, detail="No puede eliminar su propia cuenta")
    with obtener_conexion() as con:
        RepositorioUsuario(con).eliminar(usuario_id)
    return {"mensaje": "Cuenta eliminada"}
