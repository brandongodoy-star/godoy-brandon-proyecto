from itertools import count

import pytest
from fastapi.testclient import TestClient

from main import app

numeros = count(1)

PAGADOR = {
    "pagador_nombres": "María José",
    "pagador_apellidos": "López Cruz",
    "pagador_identidad": "0801-1995-12345",
    "pagador_correo": "maria.lopez@correo.hn",
}
TARJETA = {"metodo": "tarjeta", "tarjeta_marca": "Visa", "tarjeta_ultimos4": "4821", "autorizacion": "458712"}


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
    """Proyecto activo (L 1000 de mano de obra) con su líder, que tiene cuenta."""
    n = next(numeros)
    lider = crear(cliente, recepcion, "/mecanicos", {"nombre": f"Mecánico de pagos {n}"})
    datos = {"username": f"pag_{n}", "password": "secreto123", "rol": "mecanico", "mecanico_id": lider["id"]}
    crear(cliente, admin, "/usuarios", datos)
    dueno = crear(cliente, recepcion, "/clientes", {"nombre": "Cliente de pagos", "telefono": "9999-3333"})
    vehiculo = crear(
        cliente, recepcion, "/vehiculos",
        {"placa": f"PAG-{n:04d}", "marca": "Nissan", "modelo": "Versa", "anio": 2021, "cliente_id": dueno["id"]},
    )
    orden = crear(
        cliente, recepcion, "/ordenes", {"vehiculo_id": vehiculo["id"], "mecanico_id": lider["id"], "mano_obra": 1000}
    )
    repuesto = crear(cliente, recepcion, "/repuestos", {"nombre": f"Repuesto de pagos {n}", "precio": 250, "existencia": 6})
    return {"orden": orden, "lider": lider, "mecanico": entrar(cliente, f"pag_{n}", "secreto123"), "repuesto": repuesto}


def movimientos(cliente, recepcion, *tipos):
    consulta = "&".join(f"tipo={t}" for t in tipos)
    return cliente.get(f"/movimientos?{consulta}", headers=recepcion).json()


# ---------- Pagos y anticipos ----------
def test_anticipo_y_pago_con_datos_de_quien_paga(cliente, recepcion, proyecto):
    ruta = f"/ordenes/{proyecto['orden']['id']}"
    cobro = crear(cliente, recepcion, f"{ruta}/pagos", {"monto": 400, "tipo": "anticipo", "metodo": "efectivo", **PAGADOR})
    anticipo = cobro["pagos"][0]
    assert (anticipo["tipo"], anticipo["pagador_nombres"], anticipo["pagador_identidad"]) == (
        "anticipo", "María José", "0801-1995-12345"
    )
    for _ in range(2):
        cliente.post(f"{ruta}/avanzar", headers=recepcion)

    # Con el trabajo listo ya no se aceptan anticipos, solo pagos
    r = cliente.post(f"{ruta}/pagos", json={"monto": 100, "tipo": "anticipo", "metodo": "efectivo", **PAGADOR}, headers=recepcion)
    assert r.status_code == 400 and "anticipos" in r.json()["detail"]
    final = crear(cliente, recepcion, f"{ruta}/pagos", {"monto": 600, **TARJETA, **PAGADOR})
    assert final["estado_pago"] == "pagado"
    pago = final["pagos"][1]
    assert (pago["tipo"], pago["tarjeta_marca"], pago["tarjeta_ultimos4"], pago["autorizacion"]) == ("pago", "Visa", "4821", "458712")


@pytest.mark.parametrize(
    "cambio",
    [
        {"pagador_nombres": ""},  # sin nombre
        {"pagador_identidad": "08@01"},  # identidad con caracteres raros
        {"pagador_correo": "no-es-correo"},
        {"metodo": "tarjeta"},  # tarjeta sin marca, dígitos ni autorización
        {**TARJETA, "tarjeta_ultimos4": "4111111111111111"},  # nunca el número completo
        {"metodo": "transferencia", "referencia": "TRF-9"},  # transferencia sin banco
    ],
)
def test_datos_de_pago_invalidos(cliente, recepcion, proyecto, cambio):
    datos = {"monto": 100, "metodo": "efectivo", **PAGADOR, **cambio}
    assert cliente.post(f"/ordenes/{proyecto['orden']['id']}/pagos", json=datos, headers=recepcion).status_code == 400


def test_transferencia_guarda_banco_y_referencia(cliente, recepcion, proyecto):
    datos = {"monto": 100, "metodo": "transferencia", "banco": "BAC Credomatic", "referencia": "TRF-55", **PAGADOR}
    pago = crear(cliente, recepcion, f"/ordenes/{proyecto['orden']['id']}/pagos", datos)["pagos"][0]
    assert (pago["banco"], pago["referencia"], pago["tarjeta_ultimos4"]) == ("BAC Credomatic", "TRF-55", None)


# ---------- Venta de producto individual ----------
def test_venta_de_un_repuesto_suelto(cliente, recepcion, proyecto):
    repuesto = proyecto["repuesto"]
    venta = crear(cliente, recepcion, "/ventas", {"repuesto_id": repuesto["id"], "cantidad": 2, **TARJETA, **PAGADOR})
    assert (venta["repuesto"], venta["cantidad"], venta["precio_unitario"], venta["total"]) == (repuesto["nombre"], 2, 250, 500)
    assert cliente.get(f"/repuestos/{repuesto['id']}", headers=recepcion).json()["existencia"] == 4
    assert any(v["id"] == venta["id"] for v in cliente.get("/ventas", headers=recepcion).json())

    r = cliente.post("/ventas", json={"repuesto_id": repuesto["id"], "cantidad": 10, "metodo": "efectivo", **PAGADOR}, headers=recepcion)
    assert r.status_code == 400 and "quedan 4" in r.json()["detail"]
    assert movimientos(cliente, recepcion, "venta")[0]["monto"] == 500


# ---------- Historial de movimientos ----------
def test_historial_de_movimientos(cliente, recepcion, admin, proyecto):
    orden_id, repuesto = proyecto["orden"]["id"], proyecto["repuesto"]
    crear(cliente, recepcion, f"/ordenes/{orden_id}/pagos", {"monto": 300, "tipo": "anticipo", "metodo": "efectivo", **PAGADOR})
    linea = crear(cliente, recepcion, f"/ordenes/{orden_id}/repuestos", {"repuesto_id": repuesto["id"], "cantidad": 1})
    cliente.delete(f"/ordenes/{orden_id}/repuestos/{linea['id']}", headers=recepcion)

    usados = movimientos(cliente, recepcion, "repuesto_usado", "repuesto_devuelto")
    assert [m["tipo"] for m in usados[:2]] == ["repuesto_devuelto", "repuesto_usado"]
    assert usados[0]["usuario"] == "recepcion" and usados[0]["repuesto"] == repuesto["nombre"]
    anticipo = movimientos(cliente, recepcion, "anticipo")[0]
    assert anticipo["monto"] == 300 and "María José López Cruz" in anticipo["descripcion"]

    pago_id = cliente.get(f"/ordenes/{orden_id}/cobro", headers=recepcion).json()["pagos"][0]["id"]
    cliente.delete(f"/pagos/{pago_id}", headers=admin)
    anulado = movimientos(cliente, recepcion, "pago_anulado")[0]
    assert anulado["monto"] == -300 and anulado["usuario"] == "admin"
    assert cliente.get("/movimientos", headers=proyecto["mecanico"]).status_code == 403


def test_aceptar_una_solicitud_manda_el_material(cliente, recepcion, proyecto):
    orden_id, repuesto = proyecto["orden"]["id"], proyecto["repuesto"]
    peticion = crear(
        cliente, proyecto["mecanico"], f"/mecanico/trabajos/{orden_id}/peticiones", {"repuesto_id": repuesto["id"], "cantidad": 2}
    )
    cliente.post(f"/peticiones/{peticion['id']}/enviar", headers=recepcion)

    trabajo = cliente.get(f"/mecanico/trabajos/{orden_id}", headers=proyecto["mecanico"]).json()
    assert {"repuesto": repuesto["nombre"], "cantidad": 2} in trabajo["repuestos"]
    aviso = cliente.get("/mecanico/mensajes", headers=proyecto["mecanico"]).json()[0]
    assert aviso["asunto"] == f"Material enviado: {repuesto['nombre']} × 2"
    aceptada = movimientos(cliente, recepcion, "solicitud_aceptada")[0]
    assert aceptada["orden_id"] == orden_id and aceptada["cantidad"] == 2


# ---------- Mensajería en los dos sentidos ----------
def test_el_mecanico_con_proyecto_activo_escribe_a_recepcion(cliente, recepcion, proyecto):
    orden_id = proyecto["orden"]["id"]
    datos = {"asunto": "Necesito una gata", "texto": "La del puesto 2 no sube.", "orden_id": orden_id}
    enviado = crear(cliente, proyecto["mecanico"], "/mecanico/mensajes", datos)
    assert (enviado["direccion"], enviado["remitente"]) == ("a_recepcion", proyecto["lider"]["nombre"])

    recibidos = cliente.get("/mensajes?direccion=a_recepcion", headers=recepcion).json()
    assert recibidos[0]["id"] == enviado["id"] and recibidos[0]["leido"] is False
    assert cliente.post(f"/mensajes/{enviado['id']}/leido", headers=recepcion).status_code == 200
    # El mecánico ve su mensaje en la conversación, pero no lo puede marcar él como leído
    propios = cliente.get("/mecanico/mensajes", headers=proyecto["mecanico"]).json()
    assert any(m["id"] == enviado["id"] and m["direccion"] == "a_recepcion" for m in propios)
    assert cliente.post(f"/mecanico/mensajes/{enviado['id']}/leido", headers=proyecto["mecanico"]).status_code == 404


def test_sin_proyecto_activo_no_puede_escribir(cliente, recepcion, proyecto):
    orden_id = proyecto["orden"]["id"]
    datos = {"asunto": "Consulta", "texto": "¿Hay trabajo para mí?"}
    assert cliente.post("/mecanico/mensajes", json={**datos, "orden_id": 1}, headers=proyecto["mecanico"]).status_code == 404
    for _ in range(2):
        cliente.post(f"/ordenes/{orden_id}/avanzar", headers=recepcion)
    r = cliente.post("/mecanico/mensajes", json=datos, headers=proyecto["mecanico"])
    assert r.status_code == 403 and "proyecto activo" in r.json()["detail"]
