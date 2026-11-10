from datetime import date
from itertools import count

import pytest
from fastapi.testclient import TestClient

from main import app

numeros = count(1)


@pytest.fixture(scope="module")
def api(entrar):
    """Cliente HTTP que ya inició sesión con la cuenta de recepción."""
    with TestClient(app) as c:
        c.headers.update(entrar(c, "recepcion"))
        yield c


# ---------- Ayudantes para crear datos ----------
def crear(api, ruta, datos):
    r = api.post(ruta, json=datos)
    assert r.status_code == 201, r.text
    return r.json()


def nuevo_cliente(api):
    return crear(api, "/clientes", {"nombre": "Cliente de prueba", "telefono": "9999-0000"})


def nuevo_vehiculo(api, cliente_id=None):
    cliente_id = cliente_id or nuevo_cliente(api)["id"]
    datos = {
        "placa": f"PRB-{next(numeros):04d}",
        "marca": "Toyota",
        "modelo": "Yaris",
        "anio": 2020,
        "cliente_id": cliente_id,
    }
    return crear(api, "/vehiculos", datos)


def nuevo_mecanico(api, activo=True):
    return crear(api, "/mecanicos", {"nombre": "Mecánico de prueba", "activo": activo})


def nuevo_repuesto(api, precio=100, existencia=5):
    datos = {"nombre": "Repuesto de prueba", "precio": precio, "existencia": existencia}
    return crear(api, "/repuestos", datos)


def nueva_orden(api, mano_obra=0):
    datos = {
        "vehiculo_id": nuevo_vehiculo(api)["id"],
        "mecanico_id": nuevo_mecanico(api)["id"],
        "mano_obra": mano_obra,
    }
    return crear(api, "/ordenes", datos)


def existencia(api, repuesto_id):
    return api.get(f"/repuestos/{repuesto_id}").json()["existencia"]


# ---------- Acceso ----------
@pytest.mark.parametrize("ruta", ["/clientes", "/vehiculos", "/mecanicos", "/repuestos", "/ordenes"])
def test_sin_token_no_hay_acceso(api, ruta):
    assert api.get(ruta, headers={"Authorization": ""}).status_code == 401


# ---------- Clientes ----------
def test_crud_cliente(api):
    cliente = crear(api, "/clientes", {"nombre": "  Laura Paz ", "telefono": "9876-5432"})
    assert cliente["nombre"] == "Laura Paz"
    assert api.get(f"/clientes/{cliente['id']}").json() == cliente

    datos = {"nombre": "Laura Paz", "telefono": "3333-4444", "direccion": "Col. Kennedy"}
    r = api.put(f"/clientes/{cliente['id']}", json=datos)
    assert r.status_code == 200
    assert r.json()["direccion"] == "Col. Kennedy"
    assert any(c["id"] == cliente["id"] for c in api.get("/clientes").json())

    assert api.delete(f"/clientes/{cliente['id']}").status_code == 200
    assert api.get(f"/clientes/{cliente['id']}").status_code == 404


def test_cliente_con_datos_invalidos(api):
    r = api.post("/clientes", json={"nombre": "Ana", "telefono": "12"})
    assert r.status_code == 400


def test_cliente_inexistente(api):
    assert api.get("/clientes/99999").status_code == 404
    assert api.put("/clientes/99999", json={"nombre": "Nadie", "telefono": "9999-9999"}).status_code == 404
    assert api.delete("/clientes/99999").status_code == 404


def test_no_se_borra_cliente_con_vehiculos(api):
    vehiculo = nuevo_vehiculo(api)
    assert api.delete(f"/clientes/{vehiculo['cliente_id']}").status_code == 400


# ---------- Vehículos ----------
def test_placa_en_mayusculas_y_sin_repetir(api):
    cliente_id = nuevo_cliente(api)["id"]
    datos = {"placa": " hzz-9999 ", "marca": "Kia", "modelo": "Rio", "anio": 2019, "cliente_id": cliente_id}
    assert crear(api, "/vehiculos", datos)["placa"] == "HZZ-9999"
    assert api.post("/vehiculos", json=datos).status_code == 409


def test_vehiculo_de_cliente_inexistente(api):
    datos = {"placa": "NOX-0001", "marca": "Kia", "modelo": "Rio", "anio": 2019, "cliente_id": 99999}
    assert api.post("/vehiculos", json=datos).status_code == 404


def test_vehiculo_con_anio_futuro(api):
    datos = {
        "placa": "FUT-0001",
        "marca": "Kia",
        "modelo": "Rio",
        "anio": date.today().year + 5,
        "cliente_id": nuevo_cliente(api)["id"],
    }
    assert api.post("/vehiculos", json=datos).status_code == 400


def test_filtrar_vehiculos_por_cliente(api):
    cliente_id = nuevo_cliente(api)["id"]
    nuevo_vehiculo(api, cliente_id)
    nuevo_vehiculo(api, cliente_id)
    vehiculos = api.get("/vehiculos", params={"cliente_id": cliente_id}).json()
    assert len(vehiculos) == 2
    assert all(v["cliente_id"] == cliente_id for v in vehiculos)


# ---------- Mecánicos y repuestos ----------
def test_listar_solo_mecanicos_activos(api):
    inactivo = nuevo_mecanico(api, activo=False)
    activos = api.get("/mecanicos", params={"solo_activos": True}).json()
    assert all(m["activo"] for m in activos)
    assert inactivo["id"] not in [m["id"] for m in activos]


def test_repuesto_con_precio_invalido(api):
    assert api.post("/repuestos", json={"nombre": "Tornillo", "precio": 0}).status_code == 400


def test_no_se_borra_repuesto_usado_en_una_orden(api):
    repuesto = nuevo_repuesto(api)
    orden = nueva_orden(api)
    crear(api, f"/ordenes/{orden['id']}/repuestos", {"repuesto_id": repuesto["id"], "cantidad": 1})
    assert api.delete(f"/repuestos/{repuesto['id']}").status_code == 400


# ---------- Órdenes ----------
def test_orden_nueva_empieza_recibida_con_fecha_de_hoy(api):
    orden = nueva_orden(api)
    assert orden["estado"] == "recibido"
    assert orden["fecha_ingreso"] == date.today().isoformat()


def test_orden_con_mecanico_inactivo(api):
    datos = {
        "vehiculo_id": nuevo_vehiculo(api)["id"],
        "mecanico_id": nuevo_mecanico(api, activo=False)["id"],
    }
    r = api.post("/ordenes", json=datos)
    assert r.status_code == 400
    assert "no está activo" in r.json()["detail"]


def test_total_de_orden_de_los_datos_de_prueba(api):
    # Orden 1: mano de obra 300 + 1 filtro de aceite (120) + 4 litros de aceite (180 c/u)
    assert api.get("/ordenes/1/total").json() == {
        "orden_id": 1,
        "mano_obra": 300,
        "repuestos": 840,
        "total": 1140,
    }


def test_repuestos_descuentan_inventario_y_suman_al_total(api):
    repuesto = nuevo_repuesto(api, precio=100, existencia=5)
    orden = nueva_orden(api, mano_obra=250)
    ruta = f"/ordenes/{orden['id']}/repuestos"

    crear(api, ruta, {"repuesto_id": repuesto["id"], "cantidad": 2})
    linea = crear(api, ruta, {"repuesto_id": repuesto["id"], "cantidad": 1})
    assert linea["cantidad"] == 3
    assert linea["subtotal"] == 300
    assert len(api.get(ruta).json()) == 1
    assert existencia(api, repuesto["id"]) == 2

    r = api.post(ruta, json={"repuesto_id": repuesto["id"], "cantidad": 10})
    assert r.status_code == 400
    assert existencia(api, repuesto["id"]) == 2
    assert api.get(f"/ordenes/{orden['id']}/total").json()["total"] == 550

    assert api.delete(f"{ruta}/{linea['id']}").status_code == 200
    assert existencia(api, repuesto["id"]) == 5
    assert api.get(f"/ordenes/{orden['id']}/total").json()["total"] == 250


def test_no_se_quita_un_repuesto_de_otra_orden(api):
    repuesto = nuevo_repuesto(api)
    orden_a, orden_b = nueva_orden(api), nueva_orden(api)
    linea = crear(api, f"/ordenes/{orden_a['id']}/repuestos", {"repuesto_id": repuesto["id"], "cantidad": 1})
    assert api.delete(f"/ordenes/{orden_b['id']}/repuestos/{linea['id']}").status_code == 404


def test_avanzar_estado_hasta_entregar(api):
    orden = nueva_orden(api)
    ruta = f"/ordenes/{orden['id']}/avanzar"
    estados = [api.post(ruta).json()["estado"] for _ in range(2)]
    assert estados == ["en reparacion", "listo"]

    # Para entregar hay que calificar el trabajo
    r = api.post(ruta)
    assert r.status_code == 400
    assert "Califique" in r.json()["detail"]
    entregada = api.post(ruta, json={"calificacion": "bien"}).json()
    assert entregada["estado"] == "entregado"
    assert entregada["calificacion"] == "bien"
    assert api.post(ruta, json={"calificacion": "bien"}).status_code == 400


def test_orden_lista_o_entregada_no_se_modifica(api):
    repuesto = nuevo_repuesto(api)
    orden = nueva_orden(api)
    api.post(f"/ordenes/{orden['id']}/avanzar")
    api.post(f"/ordenes/{orden['id']}/avanzar")

    datos = {k: orden[k] for k in ("vehiculo_id", "mecanico_id", "mano_obra")}
    assert api.put(f"/ordenes/{orden['id']}", json=datos).status_code == 400
    r = api.post(f"/ordenes/{orden['id']}/repuestos", json={"repuesto_id": repuesto["id"], "cantidad": 1})
    assert r.status_code == 400
    assert api.delete(f"/ordenes/{orden['id']}").status_code == 400


def test_eliminar_orden_devuelve_repuestos(api):
    repuesto = nuevo_repuesto(api, existencia=5)
    orden = nueva_orden(api)
    crear(api, f"/ordenes/{orden['id']}/repuestos", {"repuesto_id": repuesto["id"], "cantidad": 4})
    assert existencia(api, repuesto["id"]) == 1

    assert api.delete(f"/ordenes/{orden['id']}").status_code == 200
    assert existencia(api, repuesto["id"]) == 5
    assert api.get(f"/ordenes/{orden['id']}").status_code == 404


def test_filtrar_ordenes_por_estado(api):
    orden = nueva_orden(api)
    api.post(f"/ordenes/{orden['id']}/avanzar")
    en_reparacion = api.get("/ordenes", params={"estado": "en reparacion"}).json()
    assert orden["id"] in [o["id"] for o in en_reparacion]
    assert all(o["estado"] == "en reparacion" for o in en_reparacion)
    assert api.get("/ordenes", params={"estado": "perdida"}).status_code == 400
