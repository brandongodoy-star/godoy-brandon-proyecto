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


@pytest.fixture(scope="module")
def auxiliar(cliente, entrar):
    return entrar(cliente, "auxiliar")


def crear(cliente, encabezado, ruta, datos):
    r = cliente.post(ruta, json=datos, headers=encabezado)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def proyecto(cliente, recepcion, admin, entrar):
    """Proyecto activo cuyo líder (con cuenta) trabaja en un taller nuevo."""
    n = next(numeros)
    taller = crear(cliente, recepcion, "/talleres", {"nombre": f"Taller de prueba {n}", "direccion": "Col. Palmira, calle 5"})
    lider = crear(cliente, recepcion, "/mecanicos", {"nombre": f"Mecánico de operaciones {n}", "taller_id": taller["id"]})
    crear(cliente, admin, "/usuarios", {"username": f"ope_{n}", "password": "secreto123", "rol": "mecanico", "mecanico_id": lider["id"]})
    dueno = crear(cliente, recepcion, "/clientes", {"nombre": "Cliente de operaciones", "telefono": "9999-5555"})
    vehiculo = crear(
        cliente, recepcion, "/vehiculos",
        {"placa": f"OPE-{n:04d}", "marca": "Mazda", "modelo": "3", "anio": 2020, "cliente_id": dueno["id"]},
    )
    orden = crear(cliente, recepcion, "/ordenes", {"vehiculo_id": vehiculo["id"], "mecanico_id": lider["id"]})
    repuesto = crear(cliente, recepcion, "/repuestos", {"nombre": f"Pieza de operaciones {n}", "precio": 90, "existencia": 20})
    return {
        "taller": taller, "lider": lider, "orden": orden, "vehiculo": vehiculo, "repuesto": repuesto,
        "mecanico": entrar(cliente, f"ope_{n}", "secreto123"),
    }


# ---------- Talleres ----------
def test_talleres_y_mecanicos(cliente, recepcion, proyecto):
    taller = cliente.get(f"/talleres/{proyecto['taller']['id']}", headers=recepcion).json()
    assert (taller["mecanicos"], taller["activo"]) == (1, True)
    assert any(t["nombre"] == "Taller Central" for t in cliente.get("/talleres", headers=recepcion).json())

    datos = {**{k: taller[k] for k in ("nombre", "direccion")}, "horario": "Lunes a viernes", "capacidad": 6}
    assert cliente.put(f"/talleres/{taller['id']}", json=datos, headers=recepcion).json()["capacidad"] == 6
    # Con mecánicos no se elimina; un taller inexistente no se puede asignar
    assert cliente.delete(f"/talleres/{taller['id']}", headers=recepcion).status_code == 400
    r = cliente.post("/mecanicos", json={"nombre": "Sin sede", "taller_id": 99999}, headers=recepcion)
    assert r.status_code == 404


def test_solo_el_personal_maneja_talleres(cliente, auxiliar, proyecto):
    assert cliente.get("/talleres", headers=auxiliar).status_code == 403
    assert cliente.get("/talleres", headers=proyecto["mecanico"]).status_code == 403


# ---------- Auxiliar de operaciones y traslado ----------
def test_el_auxiliar_solo_entra_a_su_area(cliente, auxiliar, entrar):
    yo = cliente.get("/auth/yo", headers=auxiliar).json()
    assert yo["rol"] == "auxiliar"
    for ruta in ("/ordenes", "/clientes", "/tareas", "/mecanico/trabajos"):
        assert cliente.get(ruta, headers=auxiliar).status_code == 403
    assert cliente.get("/auxiliar/tareas", headers=entrar(cliente, "recepcion")).status_code == 403


def test_recepcion_asigna_y_el_auxiliar_la_realiza(cliente, recepcion, auxiliar, proyecto):
    vehiculo, taller = proyecto["vehiculo"], proyecto["taller"]
    tarea = crear(cliente, recepcion, "/tareas", {"tipo": "traer_vehiculo", "orden_id": proyecto["orden"]["id"], "taller_id": taller["id"]})
    assert tarea["titulo"] == f"Traer {vehiculo['placa']} (Mazda 3) al {taller['nombre']}"
    assert (tarea["estado"], tarea["vehiculo_id"], tarea["asignado_a"]) == ("pendiente", vehiculo["id"], None)

    # Sin auxiliar asignado le aparece a todos; al aceptarla pasa a sus trabajos
    assert any(t["id"] == tarea["id"] for t in cliente.get("/auxiliar/tareas", headers=auxiliar).json())
    ruta = f"/auxiliar/tareas/{tarea['id']}"
    assert cliente.post(f"{ruta}/realizada", headers=auxiliar).status_code == 400  # todavía no la aceptó
    aceptada = cliente.post(f"{ruta}/aceptar", headers=auxiliar).json()
    assert (aceptada["estado"], aceptada["auxiliar"]) == ("aceptada", "Auxiliar de Operaciones")
    hecha = cliente.post(f"{ruta}/realizada", json={"nota": "Lo dejé en el puesto 3"}, headers=auxiliar).json()
    assert (hecha["estado"], hecha["nota"]) == ("realizada", "Lo dejé en el puesto 3") and hecha["realizada_en"]
    # Recepción lo ve como realizado y ya no se puede cancelar
    assert any(t["id"] == tarea["id"] for t in cliente.get("/tareas?estado=realizada", headers=recepcion).json())
    assert cliente.delete(f"/tareas/{tarea['id']}", headers=recepcion).status_code == 400


def test_recibir_producto_nuevo_entra_al_almacen(cliente, recepcion, auxiliar, proyecto):
    repuesto = proyecto["repuesto"]
    tarea = crear(cliente, recepcion, "/tareas", {"tipo": "recibir_producto", "repuesto_id": repuesto["id"], "cantidad": 15})
    assert tarea["titulo"] == f"Recibir {repuesto['nombre']} × 15 del proveedor"
    cliente.post(f"/auxiliar/tareas/{tarea['id']}/aceptar", headers=auxiliar)
    cliente.post(f"/auxiliar/tareas/{tarea['id']}/realizada", headers=auxiliar)
    assert cliente.get(f"/repuestos/{repuesto['id']}", headers=recepcion).json()["existencia"] == 35


@pytest.mark.parametrize(
    "datos",
    [
        {"tipo": "recibir_producto"},  # sin repuesto ni cantidad
        {"tipo": "traer_vehiculo", "taller_id": 1},  # sin vehículo
        {"tipo": "llevar_vehiculo", "vehiculo_id": 1},  # sin taller
        {"tipo": "otro"},  # sin título
        {"tipo": "entregar_pieza", "titulo": "Llevar algo"},  # esa la crea el sistema
        {"tipo": "otro", "titulo": "Lavar el auto", "asignado_a": 1},  # la cuenta 1 no es auxiliar
    ],
)
def test_tareas_invalidas(cliente, recepcion, datos):
    assert cliente.post("/tareas", json=datos, headers=recepcion).status_code in (400, 404)


def test_cancelar_una_tarea_pendiente(cliente, recepcion, auxiliar):
    tarea = crear(cliente, recepcion, "/tareas", {"tipo": "otro", "titulo": "Recoger llantas en la vulcanizadora"})
    assert cliente.delete(f"/tareas/{tarea['id']}", headers=recepcion).status_code == 200
    assert cliente.post(f"/auxiliar/tareas/{tarea['id']}/aceptar", headers=auxiliar).status_code == 404


# ---------- Petición aprobada: traslado, «producto enviado» y «recibido» ----------
def test_peticion_aprobada_hasta_que_el_mecanico_la_recibe(cliente, recepcion, admin, auxiliar, proyecto):
    orden_id, repuesto, taller = proyecto["orden"]["id"], proyecto["repuesto"], proyecto["taller"]
    mecanico = proyecto["mecanico"]
    peticion = crear(cliente, mecanico, f"/mecanico/trabajos/{orden_id}/peticiones", {"repuesto_id": repuesto["id"], "cantidad": 3})
    cliente.post(f"/peticiones/{peticion['id']}/enviar", headers=recepcion)

    # Los auxiliares reciben la tarea de llevar la pieza al taller del mecánico
    tarea = next(t for t in cliente.get("/auxiliar/tareas", headers=auxiliar).json() if t["peticion_id"] == peticion["id"])
    assert tarea["tipo"] == "entregar_pieza" and tarea["titulo"] == f"Llevar {repuesto['nombre']} × 3 al {taller['nombre']}"
    assert cliente.delete(f"/tareas/{tarea['id']}", headers=recepcion).status_code == 400

    # El mecánico recibe «Producto enviado» con el botón «Recibido»
    aviso = next(m for m in cliente.get("/mecanico/mensajes", headers=mecanico).json() if m["peticion_id"] == peticion["id"])
    assert aviso["asunto"].startswith("Producto enviado") and aviso["recibida_en"] is None

    cliente.post(f"/auxiliar/tareas/{tarea['id']}/aceptar", headers=auxiliar)
    cliente.post(f"/auxiliar/tareas/{tarea['id']}/realizada", headers=auxiliar)
    recibida = cliente.post(f"/mecanico/peticiones/{peticion['id']}/recibido", headers=mecanico).json()
    assert recibida["recibida_en"] and recibida["estado_traslado"] == "realizada"
    assert cliente.post(f"/mecanico/peticiones/{peticion['id']}/recibido", headers=mecanico).status_code == 400

    # El historial de entregas lo ven recepción y administración
    for encabezado in (recepcion, admin):
        entrega = next(e for e in cliente.get("/peticiones/entregas", headers=encabezado).json() if e["id"] == peticion["id"])
        assert (entrega["taller"], entrega["auxiliar"], entrega["estado_traslado"]) == (taller["nombre"], "Auxiliar de Operaciones", "realizada")
        assert entrega["recibida_en"] and entrega["entregada_en"]
    assert cliente.get("/peticiones/entregas", headers=mecanico).status_code == 403


def test_no_se_recibe_lo_ajeno_ni_lo_pendiente(cliente, recepcion, entrar, proyecto):
    orden_id, repuesto = proyecto["orden"]["id"], proyecto["repuesto"]
    peticion = crear(cliente, proyecto["mecanico"], f"/mecanico/trabajos/{orden_id}/peticiones", {"repuesto_id": repuesto["id"], "cantidad": 1})
    assert cliente.post(f"/mecanico/peticiones/{peticion['id']}/recibido", headers=proyecto["mecanico"]).status_code == 400
    cliente.post(f"/peticiones/{peticion['id']}/enviar", headers=recepcion)
    otro = entrar(cliente, "mecanico")
    assert cliente.post(f"/mecanico/peticiones/{peticion['id']}/recibido", headers=otro).status_code == 404


# ---------- Copias en PDF de los reportes ----------
def test_el_reporte_se_guarda_en_pdf(cliente, recepcion, admin, entrar, proyecto):
    datos = {"tipo": "equipo", "titulo": "Elevador del puesto 4 trabado", "descripcion": "No baja del todo; huele a aceite quemado.",
             "orden_id": proyecto["orden"]["id"]}
    reporte = crear(cliente, proyecto["mecanico"], "/mecanico/reportes", datos)
    assert reporte["tiene_pdf"] is True

    for encabezado, ruta in ((proyecto["mecanico"], "/mecanico/reportes"), (recepcion, "/reportes"), (admin, "/reportes")):
        r = cliente.get(f"{ruta}/{reporte['id']}/pdf", headers=encabezado)
        assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
        assert r.content.startswith(b"%PDF-1.4") and r.content.rstrip().endswith(b"%%EOF")
        assert "Elevador del puesto 4 trabado".encode("cp1252") in r.content
        assert proyecto["vehiculo"]["placa"].encode() in r.content
    assert f'reporte-{reporte["id"]}.pdf' in r.headers["content-disposition"]

    # Otro mecánico no puede bajar la copia ajena
    assert cliente.get(f"/mecanico/reportes/{reporte['id']}/pdf", headers=entrar(cliente, "mecanico")).status_code == 404
    assert all("pdf" not in r for r in cliente.get("/reportes", headers=recepcion).json())


def test_el_reporte_del_lider_tambien_tiene_pdf(cliente, recepcion, proyecto):
    acompanante = crear(cliente, recepcion, "/mecanicos", {"nombre": "Acompañante con reporte"})
    orden = proyecto["orden"]
    cambio = {k: orden[k] for k in ("vehiculo_id", "mecanico_id", "fecha_ingreso")}
    cliente.put(f"/ordenes/{orden['id']}", json={**cambio, "equipo": [acompanante["id"]]}, headers=recepcion)
    datos = {"sobre_mecanico_id": acompanante["id"], "titulo": "Llegó tarde", "descripcion": "Llegó una hora tarde sin avisar."}
    reporte = crear(cliente, proyecto["mecanico"], f"/mecanico/trabajos/{orden['id']}/reportes-equipo", datos)
    contenido = cliente.get(f"/reportes/{reporte['id']}/pdf", headers=recepcion).content
    assert b"Acompa\xf1ante con reporte" in contenido  # la ñ va en WinAnsi


# ---------- Talleres del edificio y de afuera ----------
def test_talleres_del_edificio_y_de_afuera(cliente, recepcion):
    adentro = crear(cliente, recepcion, "/talleres", {"nombre": "Taller de Llantas", "direccion": "No hace falta"})
    assert (adentro["ubicacion"], adentro["direccion"]) == ("edificio", None)  # todos están en el mismo lugar

    sin_direccion = {"nombre": "Pintura Express", "ubicacion": "externo"}
    assert cliente.post("/talleres", json=sin_direccion, headers=recepcion).status_code == 400
    afuera = crear(cliente, recepcion, "/talleres", {**sin_direccion, "direccion": "Col. Alameda, 4.ª calle"})
    assert (afuera["ubicacion"], afuera["direccion"]) == ("externo", "Col. Alameda, 4.ª calle")
    ubicaciones = {t["nombre"]: t["ubicacion"] for t in cliente.get("/talleres", headers=recepcion).json()}
    assert ubicaciones["Taller Central"] == "edificio" and ubicaciones["Rectificadora El Pistón"] == "externo"


# ---------- Comprobantes en PDF de los cobros ----------
PAGADOR = {"pagador_nombres": "Sofía", "pagador_apellidos": "Núñez", "pagador_identidad": "0801-1992-33333"}


def test_cada_cobro_guarda_su_comprobante(cliente, recepcion, admin, proyecto):
    orden_id = proyecto["orden"]["id"]
    tarjeta = {"metodo": "tarjeta", "tarjeta_marca": "Visa", "tarjeta_ultimos4": "4821", "autorizacion": "998877"}
    # El proyecto de prueba no tiene mano de obra: con un repuesto ya tiene algo que cobrar (L 90)
    crear(cliente, recepcion, f"/ordenes/{orden_id}/repuestos", {"repuesto_id": proyecto["repuesto"]["id"], "cantidad": 1})
    cobro = crear(cliente, recepcion, f"/ordenes/{orden_id}/pagos", {"monto": 50, "tipo": "anticipo", **tarjeta, **PAGADOR})
    pago_id = cobro["pagos"][0]["id"]
    venta = crear(cliente, recepcion, "/ventas", {"repuesto_id": proyecto["repuesto"]["id"], "cantidad": 1, "metodo": "efectivo", **PAGADOR})

    pdf = cliente.get(f"/pagos/{pago_id}/pdf", headers=recepcion)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-1.4")
    assert f"comprobante-P-{pago_id:06d}.pdf" in pdf.headers["content-disposition"]
    for texto in ("Comprobante de pago anticipado", "Visa terminada en 4821", "Sofía Núñez", proyecto["vehiculo"]["placa"]):
        assert texto.encode("cp1252") in pdf.content
    assert b"4111" not in pdf.content
    assert "Comprobante de venta".encode("cp1252") in cliente.get(f"/ventas/{venta['id']}/pdf", headers=recepcion).content

    # El historial de movimientos apunta a cada comprobante
    movimientos = cliente.get("/movimientos?tipo=anticipo&tipo=venta", headers=recepcion).json()
    assert any(m["pago_id"] == pago_id for m in movimientos) and any(m["venta_id"] == venta["id"] for m in movimientos)

    # En administración: el archivo con el PDF y la nota del sistema
    archivo = cliente.get("/comprobantes", headers=admin).json()
    del_pago = next(c for c in archivo if c["pdf"] == f"/pagos/{pago_id}/pdf")
    assert (del_pago["tipo"], del_pago["numero"], del_pago["pagador"]) == ("anticipo", f"P-{pago_id:06d}", "Sofía Núñez")
    assert del_pago["nota"] == f"Anticipo del proyecto #{orden_id} · Sofía Núñez · tarjeta"
    assert any(c["pdf"] == f"/ventas/{venta['id']}/pdf" and c["tipo"] == "venta" for c in archivo)
    assert cliente.get("/comprobantes", headers=recepcion).status_code == 403


def test_los_cobros_viejos_generan_su_comprobante(cliente, recepcion):
    # Los pagos de los datos de prueba no tenían PDF: se crea la primera vez que se pide
    r = cliente.get("/pagos/1/pdf", headers=recepcion)
    assert r.status_code == 200 and b"P-000001" in r.content
    assert cliente.get("/pagos/99999/pdf", headers=recepcion).status_code == 404
