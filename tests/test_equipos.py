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


@pytest.fixture
def equipo(cliente, recepcion, admin, entrar):
    """Una orden nueva con un líder y dos miembros, cada uno con su cuenta.

    Devuelve un diccionario con la orden, las fichas y el encabezado de cada uno.
    """
    personas = {}
    for papel in ("lider", "ana", "beto"):
        n = next(numeros)
        ficha = crear(cliente, recepcion, "/mecanicos", {"nombre": f"Mecánico de equipo {n}"})
        usuario = f"equipo_{n}"
        datos = {"username": usuario, "password": "secreto123", "rol": "mecanico", "mecanico_id": ficha["id"]}
        crear(cliente, admin, "/usuarios", datos)
        personas[papel] = {"ficha": ficha, "encabezado": entrar(cliente, usuario, "secreto123")}
    dueno = crear(cliente, recepcion, "/clientes", {"nombre": "Dueño de equipo", "telefono": "9999-0000"})
    vehiculo = crear(
        cliente,
        recepcion,
        "/vehiculos",
        {"placa": f"EQP-{next(numeros):04d}", "marca": "Kia", "modelo": "Rio", "anio": 2020, "cliente_id": dueno["id"]},
    )
    orden = crear(
        cliente,
        recepcion,
        "/ordenes",
        {
            "vehiculo_id": vehiculo["id"],
            "mecanico_id": personas["lider"]["ficha"]["id"],
            "equipo": [personas["ana"]["ficha"]["id"], personas["beto"]["ficha"]["id"]],
        },
    )
    return {"orden": orden, **personas}


def crear(cliente, encabezado, ruta, datos):
    r = cliente.post(ruta, json=datos, headers=encabezado)
    assert r.status_code == 201, r.text
    return r.json()


def ruta(equipo, extra=""):
    return f"/mecanico/trabajos/{equipo['orden']['id']}{extra}"


def miembro_id(equipo, papel):
    return equipo[papel]["ficha"]["id"]


def calificar_a_todos(cliente, equipo, calificacion="bien"):
    for papel in ("ana", "beto"):
        r = cliente.put(
            ruta(equipo, f"/equipo/{miembro_id(equipo, papel)}"),
            json={"calificacion": calificacion},
            headers=equipo["lider"]["encabezado"],
        )
        assert r.status_code == 200, r.text


# ---------- Recepción arma el equipo ----------
def test_recepcion_asigna_lider_y_equipo(cliente, recepcion, equipo):
    orden = cliente.get(f"/ordenes/{equipo['orden']['id']}", headers=recepcion).json()
    assert orden["mecanico_id"] == miembro_id(equipo, "lider")
    assert orden["equipo"] == [miembro_id(equipo, "ana"), miembro_id(equipo, "beto")]


def test_el_lider_no_puede_ser_tambien_miembro(cliente, recepcion, equipo):
    orden = equipo["orden"]
    datos = {"vehiculo_id": orden["vehiculo_id"], "mecanico_id": orden["mecanico_id"], "equipo": [orden["mecanico_id"]]}
    assert cliente.put(f"/ordenes/{orden['id']}", json=datos, headers=recepcion).status_code == 400


def test_miembro_inexistente_o_inactivo(cliente, recepcion, equipo):
    orden = equipo["orden"]
    base = {"vehiculo_id": orden["vehiculo_id"], "mecanico_id": orden["mecanico_id"]}
    assert cliente.put(f"/ordenes/{orden['id']}", json={**base, "equipo": [99999]}, headers=recepcion).status_code == 404
    # Hugo Banegas (5) está inactivo en los datos de prueba
    r = cliente.put(f"/ordenes/{orden['id']}", json={**base, "equipo": [5]}, headers=recepcion)
    assert r.status_code == 400 and "no está activo" in r.json()["detail"]


def test_cambiar_el_equipo_conserva_lo_de_quien_sigue(cliente, recepcion, equipo):
    lider = equipo["lider"]["encabezado"]
    cliente.put(ruta(equipo, f"/equipo/{miembro_id(equipo, 'ana')}"), json={"tarea": "Frenos"}, headers=lider)
    orden = equipo["orden"]
    datos = {"vehiculo_id": orden["vehiculo_id"], "mecanico_id": orden["mecanico_id"], "equipo": [miembro_id(equipo, "ana")]}
    assert cliente.put(f"/ordenes/{orden['id']}", json=datos, headers=recepcion).status_code == 200

    detalle = cliente.get(ruta(equipo), headers=lider).json()
    miembros = [m for m in detalle["equipo"] if not m["es_lider"]]
    assert [(m["mecanico_id"], m["tarea"]) for m in miembros] == [(miembro_id(equipo, "ana"), "Frenos")]
    # Beto ya no forma parte: deja de ver el trabajo
    assert cliente.get(ruta(equipo), headers=equipo["beto"]["encabezado"]).status_code == 404


# ---------- Lo que ve cada uno ----------
def test_todos_ven_el_trabajo_y_su_equipo(cliente, equipo):
    for papel, es_lider in (("lider", True), ("ana", False), ("beto", False)):
        encabezado = equipo[papel]["encabezado"]
        trabajos = cliente.get("/mecanico/trabajos", headers=encabezado).json()
        trabajo = next(t for t in trabajos if t["id"] == equipo["orden"]["id"])
        assert trabajo["soy_lider"] is es_lider
        assert trabajo["lider"] == equipo["lider"]["ficha"]["nombre"]

        detalle = cliente.get(ruta(equipo), headers=encabezado).json()
        assert len(detalle["equipo"]) == 3
        assert detalle["equipo"][0]["es_lider"]
        assert detalle["puedo_dirigir"] is es_lider


def test_los_miembros_no_dirigen(cliente, equipo):
    ana = equipo["ana"]["encabezado"]
    assert cliente.post(ruta(equipo, "/empezar"), headers=ana).status_code == 403
    assert cliente.post(ruta(equipo, "/listo"), headers=ana).status_code == 403
    r = cliente.put(ruta(equipo, f"/equipo/{miembro_id(equipo, 'beto')}"), json={"calificacion": "rehacer"}, headers=ana)
    assert r.status_code == 403
    reporte = {"sobre_mecanico_id": miembro_id(equipo, "beto"), "titulo": "Queja", "descripcion": "No vino a trabajar."}
    assert cliente.post(ruta(equipo, "/reportes-equipo"), json=reporte, headers=ana).status_code == 403
    # Pero sí puede avisar a recepción cómo va
    assert cliente.post(ruta(equipo, "/aviso"), json={"mensaje": "Falta una pieza"}, headers=ana).status_code == 200


# ---------- El líder dirige mientras dura el trabajo ----------
def test_el_lider_asigna_tareas_y_califica(cliente, equipo):
    lider = equipo["lider"]["encabezado"]
    r = cliente.put(
        ruta(equipo, f"/equipo/{miembro_id(equipo, 'ana')}"),
        json={"tarea": "Cambiar pastillas de freno"},
        headers=lider,
    )
    ana = next(m for m in r.json()["equipo"] if m["mecanico_id"] == miembro_id(equipo, "ana"))
    assert ana["tarea"] == "Cambiar pastillas de freno" and ana["calificacion"] is None

    # Calificar no borra la tarea que ya tenía
    r = cliente.put(ruta(equipo, f"/equipo/{miembro_id(equipo, 'ana')}"), json={"calificacion": "excelente"}, headers=lider)
    ana = next(m for m in r.json()["equipo"] if m["mecanico_id"] == miembro_id(equipo, "ana"))
    assert ana == {**ana, "tarea": "Cambiar pastillas de freno", "calificacion": "excelente"}

    # El miembro ve su tarea
    detalle = cliente.get(ruta(equipo), headers=equipo["ana"]["encabezado"]).json()
    assert any(m["tarea"] == "Cambiar pastillas de freno" for m in detalle["equipo"])


def test_el_lider_solo_dirige_a_su_equipo(cliente, equipo):
    lider = equipo["lider"]["encabezado"]
    assert cliente.put(ruta(equipo, "/equipo/1"), json={"tarea": "x"}, headers=lider).status_code == 404
    reporte = {"sobre_mecanico_id": 1, "titulo": "Ajeno", "descripcion": "No es de mi equipo."}
    assert cliente.post(ruta(equipo, "/reportes-equipo"), json=reporte, headers=lider).status_code == 404


def test_reportes_del_lider_sobre_su_equipo(cliente, recepcion, equipo):
    lider = equipo["lider"]["encabezado"]
    datos = {"sobre_mecanico_id": miembro_id(equipo, "beto"), "titulo": "Llegó tarde", "descripcion": "Llegó una hora tarde."}
    reporte = crear(cliente, lider, ruta(equipo, "/reportes-equipo"), datos)
    assert reporte["tipo"] == "desempeno"
    assert reporte["sobre_mecanico"] == equipo["beto"]["ficha"]["nombre"]

    # Lo ve el líder dentro del trabajo, no el miembro reportado
    assert [r["id"] for r in cliente.get(ruta(equipo), headers=lider).json()["reportes_equipo"]] == [reporte["id"]]
    assert cliente.get(ruta(equipo), headers=equipo["beto"]["encabezado"]).json()["reportes_equipo"] == []
    # Recepción lo recibe como reporte y como notificación
    assert any(r["id"] == reporte["id"] for r in cliente.get("/reportes", headers=recepcion).json())
    avisos = [n for n in cliente.get("/notificaciones", headers=recepcion).json() if n["orden_id"] == equipo["orden"]["id"]]
    assert avisos[0]["tipo"] == "reporte" and "Llegó tarde" in avisos[0]["mensaje"]


def test_para_terminar_debe_calificar_a_todos(cliente, equipo):
    lider = equipo["lider"]["encabezado"]
    cliente.post(ruta(equipo, "/empezar"), headers=lider)
    r = cliente.post(ruta(equipo, "/listo"), headers=lider)
    assert r.status_code == 400 and "cada miembro" in r.json()["detail"]
    calificar_a_todos(cliente, equipo)
    assert cliente.post(ruta(equipo, "/listo"), headers=lider).json()["estado"] == "listo"


def test_al_terminar_pierde_los_permisos_de_lider(cliente, equipo):
    lider = equipo["lider"]["encabezado"]
    cliente.post(ruta(equipo, "/empezar"), headers=lider)
    calificar_a_todos(cliente, equipo)
    detalle = cliente.post(ruta(equipo, "/listo"), headers=lider).json()
    assert detalle["puedo_dirigir"] is False

    r = cliente.put(ruta(equipo, f"/equipo/{miembro_id(equipo, 'ana')}"), json={"calificacion": "rehacer"}, headers=lider)
    assert r.status_code == 400 and "permisos de líder" in r.json()["detail"]
    reporte = {"sobre_mecanico_id": miembro_id(equipo, "ana"), "titulo": "Tarde", "descripcion": "Ya terminó el trabajo."}
    assert cliente.post(ruta(equipo, "/reportes-equipo"), json=reporte, headers=lider).status_code == 400


# ---------- Créditos al entregar ----------
def test_creditos_del_lider_y_del_equipo(cliente, recepcion, equipo):
    lider = equipo["lider"]["encabezado"]
    cliente.post(ruta(equipo, "/empezar"), headers=lider)
    cliente.put(ruta(equipo, f"/equipo/{miembro_id(equipo, 'ana')}"), json={"calificacion": "excelente"}, headers=lider)
    cliente.put(ruta(equipo, f"/equipo/{miembro_id(equipo, 'beto')}"), json={"calificacion": "con problemas"}, headers=lider)
    cliente.post(ruta(equipo, "/listo"), headers=lider)
    cliente.post(f"/ordenes/{equipo['orden']['id']}/avanzar", json={"calificacion": "bien"}, headers=recepcion)

    creditos = {
        papel: cliente.get("/mecanico/perfil", headers=equipo[papel]["encabezado"]).json()["creditos"]
        for papel in ("lider", "ana", "beto")
    }
    # Auto estándar. Líder: «bien» de recepción = +10.
    # Ana: (10 de recepción + 20 de «excelente» del líder) / 2 = 15.
    # Beto: (10 + -10 de «con problemas») / 2 = 0.
    assert creditos == {"lider": 10, "ana": 15, "beto": 0}

    historial = cliente.get("/mecanico/perfil", headers=equipo["ana"]["encabezado"]).json()["historial"]
    assert "líder «excelente»" in historial[0]["motivo"]
