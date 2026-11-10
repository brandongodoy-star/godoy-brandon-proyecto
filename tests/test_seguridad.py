import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from conftest import PASSWORDS
from main import app
from seguridad import (
    ALGORITMO,
    CLAVE_SECRETA,
    buscar_usuario,
    encriptar_password,
    verificar_password,
)


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def admin(cliente, entrar):
    return entrar(cliente, "admin")


def nueva_cuenta(cliente, admin, username, rol="recepcion", **extra):
    datos = {"username": username, "password": "secreto123", "rol": rol, **extra}
    return cliente.post("/usuarios", json=datos, headers=admin)


# ---------- Cuentas de la empresa ----------
def test_no_hay_registro_publico(cliente):
    r = cliente.post("/auth/registro", json={"username": "intruso", "password": "secreto123"})
    assert r.status_code in (404, 405)
    assert buscar_usuario("intruso") is None


@pytest.mark.parametrize(
    "usuario, rol", [("admin", "administrador"), ("recepcion", "recepcion"), ("mecanico", "mecanico")]
)
def test_cuentas_que_trae_el_sistema(cliente, entrar, usuario, rol):
    yo = cliente.get("/auth/yo", headers=entrar(cliente, usuario)).json()
    assert yo["rol"] == rol
    assert "password_hash" not in yo
    assert (yo["mecanico_id"] is not None) == (rol == "mecanico")


def test_admin_crea_cuentas(cliente, admin):
    r = nueva_cuenta(cliente, admin, "cajera1", nombre="Ana Cajera")
    assert r.status_code == 201
    assert r.json()["rol"] == "recepcion"
    assert nueva_cuenta(cliente, admin, "cajera1").status_code == 400
    assert nueva_cuenta(cliente, admin, "pepe", password="123").status_code == 400
    assert any(u["username"] == "cajera1" for u in cliente.get("/usuarios", headers=admin).json())


@pytest.mark.parametrize("usuario", ["recepcion", "mecanico"])
def test_solo_el_admin_maneja_cuentas(cliente, entrar, usuario):
    encabezado = entrar(cliente, usuario)
    assert cliente.get("/usuarios", headers=encabezado).status_code == 403
    datos = {"username": "colado", "password": "secreto123", "rol": "administrador"}
    assert cliente.post("/usuarios", json=datos, headers=encabezado).status_code == 403


def test_cuenta_de_mecanico_necesita_su_ficha(cliente, admin):
    assert nueva_cuenta(cliente, admin, "sinficha", rol="mecanico").status_code == 400
    assert nueva_cuenta(cliente, admin, "fantasma", rol="mecanico", mecanico_id=9999).status_code == 404
    ocupado = buscar_usuario("mecanico")["mecanico_id"]
    r = nueva_cuenta(cliente, admin, "repetido", rol="mecanico", mecanico_id=ocupado)
    assert r.status_code == 400


def test_admin_no_borra_su_propia_cuenta(cliente, admin):
    propio = buscar_usuario("admin")["id"]
    assert cliente.delete(f"/usuarios/{propio}", headers=admin).status_code == 400
    otro = nueva_cuenta(cliente, admin, "temporal").json()["id"]
    assert cliente.delete(f"/usuarios/{otro}", headers=admin).status_code == 200
    assert buscar_usuario("temporal") is None


@pytest.mark.parametrize(
    "usuario, ruta, esperado",
    [
        ("mecanico", "/clientes", 403),
        ("mecanico", "/ordenes", 403),
        ("mecanico", "/notificaciones", 403),
        ("recepcion", "/clientes", 200),
        ("recepcion", "/mecanico/trabajos", 403),
        ("admin", "/ordenes", 200),
    ],
)
def test_cada_rol_entra_solo_a_lo_suyo(cliente, entrar, usuario, ruta, esperado):
    assert cliente.get(ruta, headers=entrar(cliente, usuario)).status_code == esperado


def test_cambiar_password(cliente, admin, entrar):
    nueva_cuenta(cliente, admin, "cambiante")
    encabezado = entrar(cliente, "cambiante", "secreto123")
    datos = {"password_actual": "equivocada", "password_nueva": "nueva12345"}
    assert cliente.post("/auth/cambiar-password", json=datos, headers=encabezado).status_code == 400
    datos["password_actual"] = "secreto123"
    assert cliente.post("/auth/cambiar-password", json=datos, headers=encabezado).status_code == 200
    viejo = cliente.post("/auth/login", data={"username": "cambiante", "password": "secreto123"})
    assert viejo.status_code == 401
    entrar(cliente, "cambiante", "nueva12345")


def test_password_se_guarda_encriptada(cliente, admin):
    nueva_cuenta(cliente, admin, "secreta")
    usuario = buscar_usuario("secreta")
    assert usuario["password_hash"] != "secreto123"
    assert usuario["password_hash"].startswith("pbkdf2_sha256$")


def test_mismo_password_distinto_hash():
    assert encriptar_password("abc123") != encriptar_password("abc123")
    assert verificar_password("abc123", encriptar_password("abc123"))


@pytest.mark.parametrize("hash_danado", ["texto", "a$b$c", "a$no_numero$00$c", "a$1$zz$c"])
def test_hash_danado_no_rompe_la_verificacion(hash_danado):
    assert verificar_password("abc123", hash_danado) is False


def test_login_correcto_y_ruta_protegida(cliente):
    r = cliente.post("/auth/login", data={"username": "admin", "password": PASSWORDS["admin"]})
    assert r.status_code == 200
    assert r.json()["rol"] == "administrador"
    token = r.json()["access_token"]
    r = cliente.get("/auth/yo", headers={"Authorization": f"Bearer {token}"})
    assert r.json()["username"] == "admin"


def test_login_password_incorrecta(cliente):
    r = cliente.post("/auth/login", data={"username": "admin", "password": "mala"})
    assert r.status_code == 401


def test_sin_token_o_token_falso(cliente):
    assert cliente.get("/auth/yo").status_code == 401
    r = cliente.get("/auth/yo", headers={"Authorization": "Bearer token.falso.123"})
    assert r.status_code == 401


def test_token_sin_expiracion_se_rechaza(cliente):
    token = jwt.encode({"sub": "admin"}, CLAVE_SECRETA, algorithm=ALGORITMO)
    r = cliente.get("/auth/yo", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_token_expirado_se_rechaza(cliente):
    expira = datetime.now(timezone.utc) - timedelta(minutes=1)
    token = jwt.encode({"sub": "admin", "exp": expira}, CLAVE_SECRETA, algorithm=ALGORITMO)
    r = cliente.get("/auth/yo", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_sin_variable_se_crea_y_reutiliza_una_clave(tmp_path):
    archivo = tmp_path / ".clave_secreta"
    entorno = {k: v for k, v in os.environ.items() if k != "TALLER_CLAVE_SECRETA"}
    entorno["TALLER_ARCHIVO_CLAVE"] = str(archivo)
    carpeta = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def clave_al_arrancar():
        r = subprocess.run(
            [sys.executable, "-c", "import seguridad; print(seguridad.CLAVE_SECRETA)"],
            cwd=carpeta,
            env=entorno,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr
        return r.stdout.strip()

    primera = clave_al_arrancar()
    assert len(primera) == 64
    assert archivo.read_text(encoding="utf-8") == primera
    assert clave_al_arrancar() == primera
