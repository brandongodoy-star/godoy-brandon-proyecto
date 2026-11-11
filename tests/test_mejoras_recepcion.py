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


def nuevo_mecanico(cliente, recepcion, admin, entrar):
    """Mecánico libre con su cuenta: devuelve (ficha, encabezado)."""
    n = next(numeros)
    ficha = crear(cliente, recepcion, "/mecanicos", {"nombre": f"Mecánico mejora {n}"})
    datos = {"username": f"mej_{n}", "password": "secreto123", "rol": "mecanico", "mecanico_id": ficha["id"]}
    crear(cliente, admin, "/usuarios", datos)
    return ficha, entrar(cliente, f"mej_{n}", "secreto123")


def nuevo_vehiculo(cliente, recepcion):
    dueno = crear(cliente, recepcion, "/clientes", {"nombre": "Cliente mejora", "telefono": "9999-2222"})
    datos = {"placa": f"MEJ-{next(numeros):04d}", "marca": "Kia", "modelo": "Picanto", "anio": 2019, "cliente_id": dueno["id"]}
    return crear(cliente, recepcion, "/vehiculos", datos)


def nuevo_proyecto(cliente, recepcion, lider_id, equipo=()):
    datos = {
        "vehiculo_id": nuevo_vehiculo(cliente, recepcion)["id"],
        "mecanico_id": lider_id,
        "equipo": list(equipo),
        "diagnostico": "Ruido al frenar",
    }
    return crear(cliente, recepcion, "/ordenes", datos)


# ---------- Disponibilidad ----------
def test_un_mecanico_ocupado_no_esta_disponible(cliente, recepcion, admin, entrar):
    lider, _ = nuevo_mecanico(cliente, recepcion, admin, entrar)
    acompanante, _ = nuevo_mecanico(cliente, recepcion, admin, entrar)
    nuevo_proyecto(cliente, recepcion, lider["id"], [acompanante["id"]])

    otro, _ = nuevo_mecanico(cliente, recepcion, admin, entrar)
    datos = {"vehiculo_id": nuevo_vehiculo(cliente, recepcion)["id"], "mecanico_id": lider["id"]}
    r = cliente.post("/ordenes", json=datos, headers=recepcion)
    assert r.status_code == 400 and "no está disponible" in r.json()["detail"]
    datos = {**datos, "mecanico_id": otro["id"], "equipo": [acompanante["id"]]}
    assert cliente.post("/ordenes", json=datos, headers=recepcion).status_code == 400


def test_al_terminar_vuelve_a_estar_disponible(cliente, recepcion, admin, entrar):
    lider, _ = nuevo_mecanico(cliente, recepcion, admin, entrar)
    proyecto = nuevo_proyecto(cliente, recepcion, lider["id"])
    for _ in range(2):
        cliente.post(f"/ordenes/{proyecto['id']}/avanzar", headers=recepcion)
    nuevo_proyecto(cliente, recepcion, lider["id"])


def test_editar_un_proyecto_no_choca_con_su_propio_equipo(cliente, recepcion, admin, entrar):
    lider, _ = nuevo_mecanico(cliente, recepcion, admin, entrar)
    acompanante, _ = nuevo_mecanico(cliente, recepcion, admin, entrar)
    proyecto = nuevo_proyecto(cliente, recepcion, lider["id"], [acompanante["id"]])
    datos = {
        "vehiculo_id": proyecto["vehiculo_id"],
        "mecanico_id": lider["id"],
        "equipo": [acompanante["id"]],
        "diagnostico": "Ruido al frenar y vibración",
    }
    assert cliente.put(f"/ordenes/{proyecto['id']}", json=datos, headers=recepcion).status_code == 200


# ---------- Resultados del líder ----------
def test_recepcion_ve_lo_que_califico_el_lider(cliente, recepcion, admin, entrar):
    lider, encabezado_lider = nuevo_mecanico(cliente, recepcion, admin, entrar)
    acompanante, _ = nuevo_mecanico(cliente, recepcion, admin, entrar)
    proyecto = nuevo_proyecto(cliente, recepcion, lider["id"], [acompanante["id"]])
    ruta = f"/mecanico/trabajos/{proyecto['id']}"
    cliente.put(f"{ruta}/equipo/{acompanante['id']}", json={"tarea": "Pastillas", "calificacion": "bien"}, headers=encabezado_lider)

    equipo = cliente.get(f"/ordenes/{proyecto['id']}/equipo", headers=recepcion).json()
    assert [(m["nombre"], m["es_lider"], m["calificacion"]) for m in equipo] == [
        (lider["nombre"], True, None),
        (acompanante["nombre"], False, "bien"),
    ]


# ---------- Reportes con penalización ----------
@pytest.fixture
def reporte_del_lider(cliente, recepcion, admin, entrar):
    lider, encabezado_lider = nuevo_mecanico(cliente, recepcion, admin, entrar)
    reportado, encabezado_reportado = nuevo_mecanico(cliente, recepcion, admin, entrar)
    cliente.post(f"/mecanicos/{reportado['id']}/creditos", json={"puntos": 50, "motivo": "Créditos iniciales"}, headers=recepcion)
    proyecto = nuevo_proyecto(cliente, recepcion, lider["id"], [reportado["id"]])
    datos = {"sobre_mecanico_id": reportado["id"], "titulo": "Dejó el puesto", "descripcion": "Se fue sin avisar a media reparación."}
    reporte = crear(cliente, encabezado_lider, f"/mecanico/trabajos/{proyecto['id']}/reportes-equipo", datos)
    return {"reporte": reporte, "reportado": reportado, "encabezado": encabezado_reportado}


def test_resolver_con_penalizacion_baja_la_fama_y_avisa_al_reportado(cliente, recepcion, reporte_del_lider):
    reporte, encabezado = reporte_del_lider["reporte"], reporte_del_lider["encabezado"]
    datos = {"penalizacion": 20, "comentario": "Primera falta"}
    resuelto = cliente.post(f"/reportes/{reporte['id']}/resolver", json=datos, headers=recepcion).json()
    assert (resuelto["estado"], resuelto["penalizacion"], resuelto["comentario"]) == ("resuelto", 20, "Primera falta")

    perfil = cliente.get("/mecanico/perfil", headers=encabezado).json()
    assert perfil["creditos"] == 30
    assert perfil["historial"][0]["puntos"] == -20

    mensajes = cliente.get("/mecanico/mensajes", headers=encabezado).json()
    assert "Dejó el puesto" in mensajes[0]["asunto"]
    assert "20 créditos" in mensajes[0]["texto"] and "Primera falta" in mensajes[0]["texto"]
    assert cliente.post(f"/reportes/{reporte['id']}/resolver", headers=recepcion).status_code == 400


def test_la_penalizacion_es_entera_y_limitada(cliente, recepcion, reporte_del_lider):
    ruta = f"/reportes/{reporte_del_lider['reporte']['id']}/resolver"
    for penalizacion in (2.5, -5, 101):
        assert cliente.post(ruta, json={"penalizacion": penalizacion}, headers=recepcion).status_code == 400


def test_sin_penalizacion_igual_le_llega_el_reporte(cliente, recepcion, reporte_del_lider):
    cliente.post(f"/reportes/{reporte_del_lider['reporte']['id']}/resolver", headers=recepcion)
    mensajes = cliente.get("/mecanico/mensajes", headers=reporte_del_lider["encabezado"]).json()
    assert "no le bajó créditos" in mensajes[0]["texto"]


def test_no_se_penaliza_un_reporte_que_no_es_sobre_un_mecanico(cliente, recepcion, admin, entrar):
    _, encabezado = nuevo_mecanico(cliente, recepcion, admin, entrar)
    reporte = crear(cliente, encabezado, "/mecanico/reportes", {"tipo": "equipo", "titulo": "Gata rota", "descripcion": "No sube."})
    r = cliente.post(f"/reportes/{reporte['id']}/resolver", json={"penalizacion": 10}, headers=recepcion)
    assert r.status_code == 400


# ---------- Mensajes ----------
def test_mensajes_a_los_mecanicos(cliente, recepcion, admin, entrar):
    ana, encabezado_ana = nuevo_mecanico(cliente, recepcion, admin, entrar)
    beto, encabezado_beto = nuevo_mecanico(cliente, recepcion, admin, entrar)
    datos = {"mecanico_ids": [ana["id"], beto["id"]], "asunto": "Reunión", "texto": "Mañana a las 7 a. m. en el taller."}
    enviados = crear(cliente, recepcion, "/mensajes", datos)
    assert len(enviados) == 2 and enviados[0]["remitente"] == "Recepción"

    bandeja = cliente.get("/mecanico/mensajes", headers=encabezado_ana).json()
    assert [(m["asunto"], m["leido"]) for m in bandeja] == [("Reunión", False)]
    # Ana no puede marcar el mensaje de Beto
    de_beto = cliente.get("/mecanico/mensajes", headers=encabezado_beto).json()[0]["id"]
    assert cliente.post(f"/mecanico/mensajes/{de_beto}/leido", headers=encabezado_ana).status_code == 404
    assert cliente.post(f"/mecanico/mensajes/{bandeja[0]['id']}/leido", headers=encabezado_ana).status_code == 200
    assert cliente.get("/mecanico/mensajes", headers=encabezado_ana).json()[0]["leido"] is True


def test_mensaje_invalido_o_sin_permiso(cliente, recepcion, admin, entrar):
    _, encabezado = nuevo_mecanico(cliente, recepcion, admin, entrar)
    assert cliente.post("/mensajes", json={"mecanico_ids": [], "asunto": "Hola", "texto": "Nadie"}, headers=recepcion).status_code == 400
    assert cliente.post("/mensajes", json={"mecanico_ids": [99999], "asunto": "Hola", "texto": "Fantasma"}, headers=recepcion).status_code == 404
    assert cliente.post("/mensajes", json={"mecanico_ids": [1], "asunto": "Hola", "texto": "Yo"}, headers=encabezado).status_code == 403


# ---------- Problemas que surgieron ----------
def test_el_trabajo_muestra_los_problemas_que_surgieron(cliente, recepcion, admin, entrar):
    lider, encabezado = nuevo_mecanico(cliente, recepcion, admin, entrar)
    proyecto = nuevo_proyecto(cliente, recepcion, lider["id"])
    ruta = f"/mecanico/trabajos/{proyecto['id']}"
    cliente.post(f"{ruta}/empezar", headers=encabezado)
    cliente.post(f"{ruta}/aviso", json={"mensaje": "El disco también está rayado"}, headers=encabezado)
    novedades = cliente.get(ruta, headers=encabezado).json()["novedades"]
    assert len(novedades) == 1
    assert novedades[0]["tipo"] == "avance" and "disco también está rayado" in novedades[0]["mensaje"]
    assert novedades[0]["mecanico"] == lider["nombre"]
