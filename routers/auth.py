from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from seguridad import autenticar, crear_token, obtener_usuario_actual, registrar_usuario

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/registro", status_code=status.HTTP_201_CREATED)
def registro(
    username: str = Body(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$"),
    password: str = Body(min_length=6, max_length=72),
):
    return registrar_usuario(username, password)


@router.post("/login")
def login(formulario: OAuth2PasswordRequestForm = Depends()):
    usuario = autenticar(formulario.username, formulario.password)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": crear_token(usuario["username"]), "token_type": "bearer"}


@router.get("/yo")
def usuario_actual(usuario: dict = Depends(obtener_usuario_actual)):
    return usuario
