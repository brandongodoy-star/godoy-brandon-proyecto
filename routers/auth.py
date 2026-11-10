from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from modelos import CambioPassword, MensajeRespuesta
from seguridad import autenticar, cambiar_password, crear_token, obtener_usuario_actual

# No hay registro público: las cuentas las crea la administración en /usuarios
router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login")
def login(formulario: OAuth2PasswordRequestForm = Depends()):
    usuario = autenticar(formulario.username, formulario.password)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "access_token": crear_token(usuario["username"]),
        "token_type": "bearer",
        "rol": usuario["rol"],
    }


@router.get("/yo")
def usuario_actual(usuario: dict = Depends(obtener_usuario_actual)):
    return usuario


@router.post("/cambiar-password", response_model=MensajeRespuesta)
def cambiar_mi_password(datos: CambioPassword, usuario: dict = Depends(obtener_usuario_actual)):
    cambiar_password(usuario["id"], datos.password_actual, datos.password_nueva)
    return {"mensaje": "Contraseña actualizada"}
