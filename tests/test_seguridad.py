import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

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


def test_registro_crea_usuario(cliente):
    r = cliente.post("/auth/registro", json={"username": "admin", "password": "secreto123"})
    assert r.status_code == 201
    assert r.json()["username"] == "admin"


def test_registro_repetido(cliente):
    r = cliente.post("/auth/registro", json={"username": "admin", "password": "otra123"})
    assert r.status_code == 400


def test_registro_password_corta(cliente):
    r = cliente.post("/auth/registro", json={"username": "pepe", "password": "123"})
    assert r.status_code == 400


def test_password_se_guarda_encriptada(cliente):
    usuario = buscar_usuario("admin")
    assert usuario["password_hash"] != "secreto123"
    assert usuario["password_hash"].startswith("pbkdf2_sha256$")


def test_mismo_password_distinto_hash():
    assert encriptar_password("abc123") != encriptar_password("abc123")
    assert verificar_password("abc123", encriptar_password("abc123"))


def test_login_correcto_y_ruta_protegida(cliente):
    r = cliente.post("/auth/login", data={"username": "admin", "password": "secreto123"})
    assert r.status_code == 200
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


def test_sin_clave_secreta_la_app_no_arranca():
    entorno = {k: v for k, v in os.environ.items() if k != "TALLER_CLAVE_SECRETA"}
    carpeta = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = subprocess.run(
        [sys.executable, "-c", "import seguridad"],
        cwd=carpeta,
        env=entorno,
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0
    assert "TALLER_CLAVE_SECRETA" in r.stderr
