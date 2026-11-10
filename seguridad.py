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

ROLES = ("administrador", "recepcion", "mecanico")

# Cuentas que entrega la empresa. Se crean al arrancar si todavía no hay ninguna cuenta
# de ese rol. Cambie las contraseñas después de entrar por primera vez.
CUENTAS_INICIALES = (
    {"username": "admin", "password": "Admin2026!", "rol": "administrador", "nombre": "Administración"},
    {"username": "recepcion", "password": "Recepcion2026!", "rol": "recepcion", "nombre": "Recepción"},
    {"username": "mecanico", "password": "Mecanico2026!", "rol": "mecanico"},
)


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
            "SELECT id, username, password_hash, rol, nombre, mecanico_id FROM usuarios WHERE username = ?",
            (username,),
        ).fetchone()
    return dict(fila) if fila else None


def registrar_usuario(
    username: str, password: str, rol: str, nombre: str | None = None, mecanico_id: int | None = None
) -> dict:
    """Crea una cuenta. Las de mecánico deben quedar vinculadas a una ficha de mecánico libre."""
    if buscar_usuario(username):
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está registrado")
    if rol == "mecanico":
        if mecanico_id is None:
            raise HTTPException(status_code=400, detail="Una cuenta de mecánico necesita su ficha de mecánico")
    else:
        mecanico_id = None
    with obtener_conexion() as con:
        if mecanico_id is not None:
            if not con.execute("SELECT 1 FROM mecanicos WHERE id = ?", (mecanico_id,)).fetchone():
                raise HTTPException(status_code=404, detail="Mecánico no encontrado")
            if con.execute("SELECT 1 FROM usuarios WHERE mecanico_id = ?", (mecanico_id,)).fetchone():
                raise HTTPException(status_code=400, detail="Ese mecánico ya tiene una cuenta")
        cursor = con.execute(
            "INSERT INTO usuarios (username, password_hash, rol, nombre, mecanico_id) VALUES (?, ?, ?, ?, ?)",
            (username, encriptar_password(password), rol, nombre, mecanico_id),
        )
        nuevo_id = cursor.lastrowid
    return {"id": nuevo_id, "username": username, "rol": rol, "nombre": nombre, "mecanico_id": mecanico_id}


def crear_cuentas_iniciales() -> None:
    """Crea las cuentas de CUENTAS_INICIALES para los roles que todavía no tienen ninguna."""
    with obtener_conexion() as con:
        roles_con_cuenta = {fila["rol"] for fila in con.execute("SELECT DISTINCT rol FROM usuarios")}
        # La cuenta de mecánico de prueba se vincula al primer mecánico activo sin cuenta
        libre = con.execute(
            """
            SELECT id FROM mecanicos m
            WHERE activo = 1 AND NOT EXISTS (SELECT 1 FROM usuarios u WHERE u.mecanico_id = m.id)
            ORDER BY id LIMIT 1
            """
        ).fetchone()
    for cuenta in CUENTAS_INICIALES:
        if cuenta["rol"] in roles_con_cuenta or buscar_usuario(cuenta["username"]):
            continue
        if cuenta["rol"] == "mecanico":
            if libre is None:
                continue
            registrar_usuario(**cuenta, mecanico_id=libre["id"])
        else:
            registrar_usuario(**cuenta)


def cambiar_password(usuario_id: int, actual: str, nueva: str) -> None:
    with obtener_conexion() as con:
        fila = con.execute("SELECT password_hash FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        if fila is None or not verificar_password(actual, fila["password_hash"]):
            raise HTTPException(status_code=400, detail="La contraseña actual no es correcta")
        con.execute(
            "UPDATE usuarios SET password_hash = ? WHERE id = ?", (encriptar_password(nueva), usuario_id)
        )


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
    usuario.pop("password_hash")
    return usuario


def requiere_rol(*roles: str):
    """Dependencia que solo deja pasar a las cuentas con alguno de esos roles."""

    def verificar(usuario: dict = Depends(obtener_usuario_actual)) -> dict:
        if usuario["rol"] not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Su cuenta no tiene permiso para esta sección",
            )
        return usuario

    return verificar


# Administración y recepción manejan el taller; el mecánico solo entra a su área
solo_personal = requiere_rol("administrador", "recepcion")
solo_administrador = requiere_rol("administrador")
solo_mecanico = requiere_rol("mecanico")
