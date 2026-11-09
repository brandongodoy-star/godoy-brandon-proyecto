import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from database import CARPETA, obtener_conexion

RUTA_CLAVE = os.getenv("TALLER_ARCHIVO_CLAVE", os.path.join(CARPETA, ".clave_secreta"))


def cargar_clave_secreta() -> str:
    """Usa TALLER_CLAVE_SECRETA si existe. Si no, una clave al azar guardada en .clave_secreta.

    El archivo se crea la primera vez y Git lo ignora, así la clave nunca queda en el repositorio.
    """
    clave = os.getenv("TALLER_CLAVE_SECRETA")
    if clave:
        return clave
    if os.path.exists(RUTA_CLAVE):
        with open(RUTA_CLAVE, encoding="utf-8") as archivo:
            clave = archivo.read().strip()
        if clave:
            return clave
    clave = secrets.token_hex(32)
    with open(RUTA_CLAVE, "w", encoding="utf-8") as archivo:
        archivo.write(clave)
    return clave


CLAVE_SECRETA = cargar_clave_secreta()

ALGORITMO = "HS256"
MINUTOS_EXPIRACION = 60
ITERACIONES = 200_000

oauth2_esquema = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ---------- Contraseñas ----------
def encriptar_password(password: str) -> str:
    """Devuelve 'pbkdf2_sha256$iteraciones$sal$hash' para guardar en la tabla usuarios."""
    sal = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(sal), ITERACIONES)
    return f"pbkdf2_sha256${ITERACIONES}${sal}${digest.hex()}"


def verificar_password(password: str, password_hash: str) -> bool:
    try:
        _, iteraciones, sal, esperado = password_hash.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(sal), int(iteraciones)
        )
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), esperado)


# ---------- Usuarios en la base ----------
def buscar_usuario(username: str):
    """Devuelve el usuario como diccionario o None si no existe."""
    with obtener_conexion() as con:
        fila = con.execute(
            "SELECT id, username, password_hash FROM usuarios WHERE username = ?", (username,)
        ).fetchone()
    return dict(fila) if fila else None


def registrar_usuario(username: str, password: str) -> dict:
    if buscar_usuario(username):
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está registrado")
    with obtener_conexion() as con:
        cursor = con.execute(
            "INSERT INTO usuarios (username, password_hash) VALUES (?, ?)",
            (username, encriptar_password(password)),
        )
        nuevo_id = cursor.lastrowid
    return {"id": nuevo_id, "username": username}


def autenticar(username: str, password: str):
    """Devuelve el usuario si la contraseña coincide; si no, None."""
    usuario = buscar_usuario(username)
    if usuario is None or not verificar_password(password, usuario["password_hash"]):
        return None
    return usuario


# ---------- Token JWT ----------
def crear_token(username: str) -> str:
    expira = datetime.now(timezone.utc) + timedelta(minutes=MINUTOS_EXPIRACION)
    return jwt.encode({"sub": username, "exp": expira}, CLAVE_SECRETA, algorithm=ALGORITMO)


def obtener_usuario_actual(token: str = Depends(oauth2_esquema)) -> dict:
    """Dependencia que protege los endpoints: exige un token válido y vigente."""
    no_autorizado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        datos = jwt.decode(
            token, CLAVE_SECRETA, algorithms=[ALGORITMO], options={"require": ["exp", "sub"]}
        )
    except jwt.PyJWTError:
        raise no_autorizado
    usuario = buscar_usuario(datos["sub"])
    if usuario is None:
        raise no_autorizado
    return {"id": usuario["id"], "username": usuario["username"]}
