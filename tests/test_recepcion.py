from itertools import count

import pytest
from fastapi.testclient import TestClient

from main import app

numeros = count(1)


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def recepcion(cliente, entrar):
    return entrar(cliente, "recepcion")


@pytest.fixture(scope="module")
def admin(cliente, entrar):
    return entrar(cliente, "admin")


def crear(cliente, encabezado, ruta, datos):
    r = cliente.post(ruta, json=datos, headers=encabezado)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def proyecto(cliente, recepcion, admin, entrar):
    """Proyecto nuevo con su líder (con cuenta), un auto estándar y mano de obra de L 500."""
    n = next(numeros)
    lider = crear(cliente, recepcion, "/mecanicos", {"nombre": f"Mecánico recepción {n}"})
    datos = {"username": f"rec_{n}", "password": "secreto123", "rol": "mecanico", "mecanico_id": lider["id"]}
    crear(cliente, admin, "/usuarios", datos)
    dueno = crear(cliente, recepcion, "/clientes", {"nombre": "Cliente de cobro", "telefono": "9999-1111"})
    vehiculo = crear(
        cliente,
        recepcion,
        "/vehiculos",
        {"placa": f"REC-{n:04d}", "marca": "Honda", "modelo": "Fit", "anio": 2018, "cliente_id": dueno["id"]},
    )
    orden = crear(
        cliente,
        recepcion,
        "/ordenes",
        {
            "vehiculo_id": vehiculo["id"],
            "mecanico_id": lider["id"],
            "mano_obra": 500,
            "diagnostico": "No enciende",
            "indicaciones": "Llamar al cliente antes de cambiar la batería",
        },
    )
    repuesto = crear(cliente, recepcion, "/repuestos", {"nombre": f"Repuesto {n}", "precio": 100, "existencia": 5})
    return {
        "orden": orden,
        "vehiculo": vehiculo,
        "lider": lider,
        "mecanico": entrar(cliente, f"rec_{n}", "secreto123"),
        "repuesto": repuesto,
    }


# ---------- Proyectos ----------
def test_el_proyecto_guarda_las_indicaciones_del_cliente(cliente, proyecto):
    assert proyecto["orden"]["indicaciones"] == "Llamar al cliente antes de cambiar la batería"
    trabajo = cliente.get(f"/mecanico/trabajos/{proyecto['orden']['id']}", headers=proyecto["mecanico"]).json()
    assert trabajo["indicaciones"] == "Llamar al cliente antes de cambiar la batería"


# ---------- Cobros ----------
def test_cobro_en_partes_hasta_pagar(cliente, recepcion, proyecto):
    ruta = f"/ordenes/{proyecto['orden']['id']}"
    cobro = cliente.get(f"{ruta}/cobro", headers=recepcion).json()
    assert (cobro["total"], cobro["pagado"], cobro["saldo"], cobro["estado_pago"]) == (500, 0, 500, "pendiente")

    anticipo = crear(cliente, recepcion, f"{ruta}/pagos", {"monto": 200, "metodo": "efectivo"})
    assert (anticipo["pagado"], anticipo["saldo"], anticipo["estado_pago"]) == (200, 300, "parcial")
    assert anticipo["pagos"][0]["registrado_por"] == "recepcion"

    r = cliente.post(f"{ruta}/pagos", json={"monto": 301, "metodo": "tarjeta"}, headers=recepcion)
    assert r.status_code == 400 and "mayor que el saldo" in r.json()["detail"]

    final = crear(cliente, recepcion, f"{ruta}/pagos", {"monto": 300, "metodo": "transferencia", "referencia": "TRF-1"})
    assert (final["saldo"], final["estado_pago"]) == (0, "pagado")
    r = cliente.post(f"{ruta}/pagos", json={"monto": 1, "metodo": "efectivo"}, headers=recepcion)
    assert r.status_code == 400 and "ya está pagado" in r.json()["detail"]


def test_el_total_incluye_el_material_enviado(cliente, recepcion, proyecto):
    ruta = f"/ordenes/{proyecto['orden']['id']}"
    crear(cliente, recepcion, f"{ruta}/repuestos", {"repuesto_id": proyecto["repuesto"]["id"], "cantidad": 2})
    assert cliente.get(f"{ruta}/cobro", headers=recepcion).json()["total"] == 700


def test_lista_de_cobros_por_estado(cliente, recepcion, proyecto):
    pendientes = cliente.get("/cobros?estado_pago=pendiente", headers=recepcion).json()
    assert proyecto["orden"]["id"] in [c["id"] for c in pendientes]
    assert all(c["estado_pago"] == "pendiente" for c in pendientes)
    # Los datos de prueba traen la orden 3 con un anticipo
    assert any(c["id"] == 3 for c in cliente.get("/cobros?estado_pago=parcial", headers=recepcion).json())


def test_solo_la_administracion_anula_pagos(cliente, recepcion, admin, entrar, proyecto):
    cobro = crear(cliente, recepcion, f"/ordenes/{proyecto['orden']['id']}/pagos", {"monto": 100, "metodo": "efectivo"})
    pago_id = cobro["pagos"][0]["id"]
    assert cliente.delete(f"/pagos/{pago_id}", headers=recepcion).status_code == 403
    assert cliente.delete(f"/pagos/{pago_id}", headers=admin).status_code == 200
    assert cliente.get(f"/ordenes/{proyecto['orden']['id']}/cobro", headers=recepcion).json()["pagado"] == 0


def test_el_mecanico_no_ve_los_cobros(cliente, proyecto):
    assert cliente.get("/cobros", headers=proyecto["mecanico"]).status_code == 403


# ---------- Peticiones de material ----------
def test_peticion_enviada_desde_el_almacen(cliente, recepcion, proyecto):
    orden_id, repuesto = proyecto["orden"]["id"], proyecto["repuesto"]
    almacen = cliente.get("/mecanico/repuestos", headers=proyecto["mecanico"]).json()
    assert "precio" not in almacen[0]

    datos = {"repuesto_id": repuesto["id"], "cantidad": 3, "motivo": "Se dañaron al desmontar"}
    peticion = crear(cliente, proyecto["mecanico"], f"/mecanico/trabajos/{orden_id}/peticiones", datos)
    assert peticion["estado"] == "pendiente" and peticion["mecanico"] == proyecto["lider"]["nombre"]
    assert any(p["id"] == peticion["id"] for p in cliente.get("/peticiones?estado=pendiente", headers=recepcion).json())

    enviada = cliente.post(f"/peticiones/{peticion['id']}/enviar", headers=recepcion).json()
    assert enviada["estado"] == "enviada" and enviada["existencia"] == 2
    assert cliente.post(f"/peticiones/{peticion['id']}/enviar", headers=recepcion).status_code == 400

    trabajo = cliente.get(f"/mecanico/trabajos/{orden_id}", headers=proyecto["mecanico"]).json()
    assert {"repuesto": repuesto["nombre"], "cantidad": 3} in trabajo["repuestos"]
    assert trabajo["peticiones"][0]["estado"] == "enviada"


def test_peticion_sin_existencia_y_rechazo(cliente, recepcion, proyecto):
    orden_id, repuesto = proyecto["orden"]["id"], proyecto["repuesto"]
    ruta = f"/mecanico/trabajos/{orden_id}/peticiones"
    mucha = crear(cliente, proyecto["mecanico"], ruta, {"repuesto_id": repuesto["id"], "cantidad": 9})
    r = cliente.post(f"/peticiones/{mucha['id']}/enviar", headers=recepcion)
    assert r.status_code == 400 and "existencia" in r.json()["detail"]

    rechazada = cliente.post(
        f"/peticiones/{mucha['id']}/rechazar", json={"respuesta": "No hay tantas"}, headers=recepcion
    ).json()
    assert rechazada["estado"] == "rechazada" and rechazada["respuesta"] == "No hay tantas"


def test_no_se_pide_material_de_trabajos_ajenos_o_terminados(cliente, recepcion, proyecto):
    datos = {"repuesto_id": proyecto["repuesto"]["id"], "cantidad": 1}
    assert cliente.post("/mecanico/trabajos/1/peticiones", json=datos, headers=proyecto["mecanico"]).status_code == 404
    orden_id = proyecto["orden"]["id"]
    for _ in range(2):
        cliente.post(f"/ordenes/{orden_id}/avanzar", headers=recepcion)
    r = cliente.post(f"/mecanico/trabajos/{orden_id}/peticiones", json=datos, headers=proyecto["mecanico"])
    assert r.status_code == 400


# ---------- Puntuaciones ----------
def test_ajuste_manual_de_creditos(cliente, recepcion, proyecto):
    ruta = f"/mecanicos/{proyecto['lider']['id']}/creditos"
    datos = {"puntos": 30, "motivo": "Se quedó a terminar un trabajo urgente", "orden_id": proyecto["orden"]["id"]}
    assert cliente.post(ruta, json=datos, headers=recepcion).json()["creditos"] == 30
    assert cliente.post(ruta, json={"puntos": -50, "motivo": "Dejó el área sucia"}, headers=recepcion).json()["creditos"] == 0

    historial = cliente.get(ruta, headers=recepcion).json()
    assert historial[0]["puntos"] == -30  # nunca baja de 0: solo se restó lo que tenía
    assert f"proyecto #{proyecto['orden']['id']}" in historial[1]["motivo"]


def test_ajuste_invalido(cliente, recepcion, proyecto):
    ruta = f"/mecanicos/{proyecto['lider']['id']}/creditos"
    assert cliente.post(ruta, json={"puntos": 0, "motivo": "Nada que ajustar"}, headers=recepcion).status_code == 400
    assert cliente.post(ruta, json={"puntos": 500, "motivo": "Demasiado"}, headers=recepcion).status_code == 400
    otro = {"puntos": 5, "motivo": "Proyecto ajeno", "orden_id": 1}
    assert cliente.post(ruta, json=otro, headers=recepcion).status_code == 400
    assert cliente.post(ruta, json={"puntos": 5, "motivo": "Sin permiso"}, headers=proyecto["mecanico"]).status_code == 403


# ---------- Historial de vehículos ----------
def test_historial_del_vehiculo(cliente, recepcion, proyecto):
    crear(cliente, recepcion, f"/ordenes/{proyecto['orden']['id']}/pagos", {"monto": 150, "metodo": "efectivo"})
    historial = cliente.get(f"/vehiculos/{proyecto['vehiculo']['id']}/historial", headers=recepcion).json()
    assert len(historial) == 1
    assert historial[0] == {
        **historial[0],
        "id": proyecto["orden"]["id"],
        "lider": proyecto["lider"]["nombre"],
        "total": 500,
        "pagado": 150,
    }
    # La Toyota Hilux de los datos de prueba tiene su cambio de aceite pagado
    hilux = cliente.get("/vehiculos/1/historial", headers=recepcion).json()
    assert hilux[0]["total"] == hilux[0]["pagado"] == 1140
