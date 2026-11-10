import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:
        yield c


def test_la_raiz_muestra_la_interfaz(cliente):
    r = cliente.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Taller Mecánico" in r.text


@pytest.mark.parametrize("archivo", ["/", "/app.js", "/estilos.css"])
def test_archivos_de_la_interfaz_sin_copias_viejas(cliente, archivo):
    r = cliente.get(archivo)
    assert r.status_code == 200
    # El navegador debe revisar si hay una versión nueva en vez de usar la que guardó
    assert r.headers["cache-control"] == "no-cache"


def test_la_pagina_pide_los_archivos_con_version(cliente):
    html = cliente.get("/").text
    assert "/app.js?v=" in html and "/estilos.css?v=" in html
    assert cliente.get("/app.js?v=3").status_code == 200


def test_la_interfaz_no_tapa_la_api(cliente):
    assert cliente.get("/docs").status_code == 200
    r = cliente.get("/clientes")
    assert r.status_code == 401
    assert r.headers["content-type"] == "application/json"
