import os
import tempfile

import pytest

# Se configuran antes de importar la app para no tocar taller.db ni pedir una clave real
os.environ["TALLER_BD"] = os.path.join(tempfile.mkdtemp(), "prueba.db")
os.environ["TALLER_CLAVE_SECRETA"] = "clave-solo-para-las-pruebas-automaticas-del-taller"

from seguridad import CUENTAS_INICIALES  # noqa: E402

# Contraseña de cada cuenta que trae el sistema: {"admin": "...", "recepcion": "...", ...}
PASSWORDS = {cuenta["username"]: cuenta["password"] for cuenta in CUENTAS_INICIALES}


@pytest.fixture(scope="session")
def entrar():
    """Devuelve una función que inicia sesión y regresa el encabezado con el token."""

    def _entrar(cliente, usuario, password=None):
        r = cliente.post(
            "/auth/login", data={"username": usuario, "password": password or PASSWORDS[usuario]}
        )
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _entrar
