from datetime import date, timedelta
from itertools import count

import pytest
from fastapi.testclient import TestClient

from main import app

numeros = count(1)

PAGADOR = {
    "pagador_nombres": "Ana",
    "pagador_apellidos": "Reyes",
    "pagador_identidad": "0801-1990-00001",
    "metodo": "efectivo",
}


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def recepcion(cliente, entrar):
    return entrar(cliente, "recepcion")


def crear(cliente, encabezado, ruta, datos):
    r = cliente.post(ruta, json=datos, headers=encabezado)
    assert r.status_code == 201, r.text
    return r.json()


def datos_proyecto(cliente, recepcion, **extra):
    n = next(numeros)
    dueno = crear(cliente, recepcion, "/clientes", {"nombre": "Cliente con prisa", "telefono": "9999-4444"})
    vehiculo = crear(
        cliente, recepcion, "/vehiculos",
        {"placa": f"LIM-{n:04d}", "marca": "Honda", "modelo": "Civic", "anio": 2022, "cliente_id": dueno["id"]},
    )
    mecanico = crear(cliente, recepcion, "/mecanicos", {"nombre": f"Mecánico de fechas {n}"})
    return {"vehiculo_id": vehiculo["id"], "mecanico_id": mecanico["id"], "mano_obra": 800, **extra}


# ---------- Fecha límite de entrega ----------
def test_proyecto_con_fecha_limite(cliente, recepcion):
    limite = (date.today() + timedelta(days=5)).isoformat()
    orden = crear(cliente, recepcion, "/ordenes", datos_proyecto(cliente, recepcion, fecha_limite=limite))
    assert orden["fecha_limite"] == limite
    assert cliente.get(f"/ordenes/{orden['id']}", headers=recepcion).json()["fecha_limite"] == limite


def test_el_cliente_no_especifico_la_fecha(cliente, recepcion):
    orden = crear(cliente, recepcion, "/ordenes", datos_proyecto(cliente, recepcion))
    assert orden["fecha_limite"] is None

    # Después se le puede poner, y volver a quitar
    cambio = {k: orden[k] for k in ("vehiculo_id", "mecanico_id", "fecha_ingreso", "mano_obra")}
    limite = (date.today() + timedelta(days=2)).isoformat()
    r = cliente.put(f"/ordenes/{orden['id']}", json={**cambio, "fecha_limite": limite}, headers=recepcion)
    assert r.json()["fecha_limite"] == limite
    r = cliente.put(f"/ordenes/{orden['id']}", json={**cambio, "fecha_limite": None}, headers=recepcion)
    assert r.json()["fecha_limite"] is None


def test_fecha_limite_antes_del_ingreso(cliente, recepcion):
    ayer = (date.today() - timedelta(days=1)).isoformat()
    r = cliente.post("/ordenes", json=datos_proyecto(cliente, recepcion, fecha_limite=ayer), headers=recepcion)
    assert r.status_code == 400
    assert "fecha límite" in str(r.json()["detail"])


def test_el_mecanico_ve_la_fecha_limite(cliente, entrar):
    mecanico = entrar(cliente, "mecanico")
    trabajos = cliente.get("/mecanico/trabajos", headers=mecanico).json()
    assert all("fecha_limite" in t for t in trabajos)
    assert any(t["fecha_limite"] for t in trabajos)


# ---------- Apartado de anticipos ----------
def test_apartado_de_anticipos(cliente, recepcion, entrar):
    limite = (date.today() + timedelta(days=3)).isoformat()
    orden = crear(cliente, recepcion, "/ordenes", datos_proyecto(cliente, recepcion, fecha_limite=limite))
    ruta = f"/ordenes/{orden['id']}/pagos"
    crear(cliente, recepcion, ruta, {"monto": 300, "tipo": "anticipo", **PAGADOR})
    crear(cliente, recepcion, ruta, {"monto": 100, "tipo": "pago", **PAGADOR})

    anticipos = cliente.get("/anticipos", headers=recepcion).json()
    propios = [a for a in anticipos if a["orden_id"] == orden["id"]]
    assert len(propios) == 1  # el pago normal no aparece
    assert (propios[0]["monto"], propios[0]["cliente"], propios[0]["fecha_limite"]) == (300, "Cliente con prisa", limite)
    assert all(a["tipo"] == "anticipo" for a in anticipos)
    assert cliente.get("/anticipos", headers=entrar(cliente, "mecanico")).status_code == 403
