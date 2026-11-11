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


# ---------- Ayudantes ----------
def crear(cliente, encabezado, ruta, datos):
    r = cliente.post(ruta, json=datos, headers=encabezado)
    assert r.status_code == 201, r.text
    return r.json()


def nuevo_mecanico_con_cuenta(cliente, recepcion, admin, entrar):
    """Crea un mecánico nuevo (0 créditos, Aprendiz) con su cuenta y devuelve (ficha, encabezado)."""
    n = next(numeros)
    ficha = crear(cliente, recepcion, "/mecanicos", {"nombre": f"Mecánico de prueba {n}"})
    usuario = f"mec_prueba_{n}"
    datos = {"username": usuario, "password": "secreto123", "rol": "mecanico", "mecanico_id": ficha["id"]}
    crear(cliente, admin, "/usuarios", datos)
    return ficha, entrar(cliente, usuario, "secreto123")


def nuevo_vehiculo(cliente, recepcion, categoria="estandar"):
    dueno = crear(cliente, recepcion, "/clientes", {"nombre": "Dueño de prueba", "telefono": "9999-0000"})
    datos = {
        "placa": f"MEC-{next(numeros):04d}",
        "marca": "Toyota",
        "modelo": "Yaris",
        "anio": 2020,
        "cliente_id": dueno["id"],
        "categoria": categoria,
    }
    return crear(cliente, recepcion, "/vehiculos", datos)


def nueva_orden(cliente, recepcion, mecanico_id, vehiculo_id):
    datos = {"vehiculo_id": vehiculo_id, "mecanico_id": mecanico_id, "diagnostico": "Revisión general"}
    return crear(cliente, recepcion, "/ordenes", datos)


def notificaciones(cliente, recepcion, orden_id):
    return [n for n in cliente.get("/notificaciones", headers=recepcion).json() if n["orden_id"] == orden_id]


# ---------- Acceso ----------
def test_el_mecanico_solo_ve_sus_trabajos(cliente, recepcion, entrar):
    mecanico = entrar(cliente, "mecanico")
    mecanico_id = cliente.get("/auth/yo", headers=mecanico).json()["mecanico_id"]
    propias = {o["id"] for o in cliente.get("/ordenes", headers=recepcion).json() if o["mecanico_id"] == mecanico_id}
    trabajos = cliente.get("/mecanico/trabajos", headers=mecanico).json()
    assert {t["id"] for t in trabajos} == propias
    assert "mano_obra" not in trabajos[0] and "telefono" not in trabajos[0]

    ajena = next(o["id"] for o in cliente.get("/ordenes", headers=recepcion).json() if o["mecanico_id"] != mecanico_id)
    assert cliente.get(f"/mecanico/trabajos/{ajena}", headers=mecanico).status_code == 404
    assert cliente.post(f"/mecanico/trabajos/{ajena}/empezar", headers=mecanico).status_code == 404


def test_mecanico_inactivo_no_entra_a_su_area(cliente, recepcion, admin, entrar):
    ficha, mecanico = nuevo_mecanico_con_cuenta(cliente, recepcion, admin, entrar)
    datos = {"nombre": ficha["nombre"], "activo": False}
    assert cliente.put(f"/mecanicos/{ficha['id']}", json=datos, headers=recepcion).status_code == 200
    assert cliente.get("/mecanico/perfil", headers=mecanico).status_code == 403


# ---------- Un trabajo de principio a fin ----------
def test_flujo_de_un_trabajo(cliente, recepcion, admin, entrar):
    ficha, mecanico = nuevo_mecanico_con_cuenta(cliente, recepcion, admin, entrar)
    orden = nueva_orden(cliente, recepcion, ficha["id"], nuevo_vehiculo(cliente, recepcion)["id"])
    ruta = f"/mecanico/trabajos/{orden['id']}"

    assert cliente.get(ruta, headers=mecanico).json()["estado"] == "recibido"
    assert cliente.post(f"{ruta}/listo", headers=mecanico).status_code == 400
    assert cliente.post(f"{ruta}/empezar", headers=mecanico).json()["estado"] == "en reparacion"
    assert cliente.post(f"{ruta}/empezar", headers=mecanico).status_code == 400

    # Todavía no está listo: avisa a recepción cómo va
    r = cliente.post(f"{ruta}/aviso", json={"mensaje": "Falta la bomba de agua"}, headers=mecanico)
    assert r.status_code == 200
    avisos = notificaciones(cliente, recepcion, orden["id"])
    assert avisos[0]["tipo"] == "avance" and "Falta la bomba de agua" in avisos[0]["mensaje"]

    # Ya está listo: recepción recibe la notificación con la nota
    listo = cliente.post(f"{ruta}/listo", json={"nota": "Se cambió el aceite"}, headers=mecanico).json()
    assert listo["estado"] == "listo"
    aviso_listo = notificaciones(cliente, recepcion, orden["id"])[0]
    assert aviso_listo["tipo"] == "listo" and "Se cambió el aceite" in aviso_listo["mensaje"]
    assert aviso_listo["leida"] is False
    assert cliente.post(f"{ruta}/aviso", json={"mensaje": "Otra cosa"}, headers=mecanico).status_code == 400

    # Recepción entrega y califica: el mecánico gana créditos
    r = cliente.post(f"/ordenes/{orden['id']}/avanzar", json={"calificacion": "excelente"}, headers=recepcion)
    assert r.json()["estado"] == "entregado"
    detalle = cliente.get(ruta, headers=mecanico).json()
    assert detalle["calificacion"] == "excelente" and detalle["creditos"] == 20
    perfil = cliente.get("/mecanico/perfil", headers=mecanico).json()
    assert perfil["creditos"] == 20
    assert perfil["historial"][0]["puntos"] == 20
    assert perfil["estadisticas"]["entregados"] == 1
    assert perfil["estadisticas"]["calificaciones"]["excelente"] == 1


def test_los_creditos_no_bajan_de_cero(cliente, recepcion, admin, entrar):
    ficha, mecanico = nuevo_mecanico_con_cuenta(cliente, recepcion, admin, entrar)
    orden = nueva_orden(cliente, recepcion, ficha["id"], nuevo_vehiculo(cliente, recepcion)["id"])
    for _ in range(2):
        cliente.post(f"/ordenes/{orden['id']}/avanzar", headers=recepcion)
    cliente.post(f"/ordenes/{orden['id']}/avanzar", json={"calificacion": "rehacer"}, headers=recepcion)
    perfil = cliente.get("/mecanico/perfil", headers=mecanico).json()
    assert perfil["creditos"] == 0
    assert perfil["estadisticas"]["calificaciones"]["rehacer"] == 1


# ---------- Niveles ----------
def test_el_nivel_limita_que_autos_se_le_asignan(cliente, recepcion, admin, entrar):
    ficha, _ = nuevo_mecanico_con_cuenta(cliente, recepcion, admin, entrar)
    lujo = nuevo_vehiculo(cliente, recepcion, "lujo")
    premium = nuevo_vehiculo(cliente, recepcion, "premium")
    for vehiculo in (lujo, premium):
        datos = {"vehiculo_id": vehiculo["id"], "mecanico_id": ficha["id"]}
        r = cliente.post("/ordenes", json=datos, headers=recepcion)
        assert r.status_code == 400
        assert "Aprendiz" in r.json()["detail"]

    # Con los ajustes de recepción llega a Maestro y ya puede trabajar autos de lujo
    for _ in range(3):
        datos = {"puntos": 100, "motivo": "Experiencia comprobada"}
        cliente.post(f"/mecanicos/{ficha['id']}/creditos", json=datos, headers=recepcion)
    maestro = cliente.get(f"/mecanicos/{ficha['id']}", headers=recepcion).json()
    assert maestro["nivel"] == "Maestro"
    nueva_orden(cliente, recepcion, ficha["id"], lujo["id"])


def test_conserva_trabajos_que_ya_tenia(cliente, recepcion, admin, entrar):
    ficha, _ = nuevo_mecanico_con_cuenta(cliente, recepcion, admin, entrar)
    vehiculo = nuevo_vehiculo(cliente, recepcion)
    orden = nueva_orden(cliente, recepcion, ficha["id"], vehiculo["id"])
    # El auto cambia a lujo después de asignado: la orden se puede seguir editando
    cambio = {k: vehiculo[k] for k in ("placa", "marca", "modelo", "anio", "cliente_id")}
    r = cliente.put(f"/vehiculos/{vehiculo['id']}", json={**cambio, "categoria": "lujo"}, headers=admin)
    assert r.status_code == 200
    datos = {"vehiculo_id": vehiculo["id"], "mecanico_id": ficha["id"], "diagnostico": "Actualizado"}
    assert cliente.put(f"/ordenes/{orden['id']}", json=datos, headers=recepcion).status_code == 200


def test_perfil_muestra_nivel_y_siguiente(cliente, entrar):
    perfil = cliente.get("/mecanico/perfil", headers=entrar(cliente, "mecanico")).json()
    assert perfil["usuario"] == "mecanico"
    assert perfil["nivel"]["nombre"] == "Maestro"
    assert perfil["nivel"]["categorias"] == ["estandar", "premium", "lujo"]
    assert perfil["nivel"]["siguiente"] is None
    assert sum(m["puntos"] for m in perfil["historial"]) == perfil["creditos"]


# ---------- Reportes y notificaciones ----------
def test_reportes_del_mecanico(cliente, recepcion, admin, entrar):
    ficha, mecanico = nuevo_mecanico_con_cuenta(cliente, recepcion, admin, entrar)
    orden = nueva_orden(cliente, recepcion, ficha["id"], nuevo_vehiculo(cliente, recepcion)["id"])
    reporte = {"tipo": "equipo", "titulo": "Gata hidráulica dañada", "descripcion": "Pierde aceite y no sube."}

    ajena = cliente.post("/mecanico/reportes", json={**reporte, "orden_id": 1}, headers=mecanico)
    assert ajena.status_code == 404
    creado = crear(cliente, mecanico, "/mecanico/reportes", {**reporte, "orden_id": orden["id"]})
    assert creado["estado"] == "abierto" and creado["mecanico"] == ficha["nombre"]
    assert [r["id"] for r in cliente.get("/mecanico/reportes", headers=mecanico).json()] == [creado["id"]]

    # Recepción lo ve, recibe el aviso y lo resuelve; el mecánico no ve la lista general
    assert cliente.get("/reportes", headers=mecanico).status_code == 403
    assert any(r["id"] == creado["id"] for r in cliente.get("/reportes?estado=abierto", headers=recepcion).json())
    assert notificaciones(cliente, recepcion, orden["id"])[0]["tipo"] == "reporte"
    resuelto = cliente.post(f"/reportes/{creado['id']}/resolver", headers=recepcion).json()
    assert resuelto["estado"] == "resuelto"


def test_reporte_con_datos_invalidos(cliente, recepcion, admin, entrar):
    _, mecanico = nuevo_mecanico_con_cuenta(cliente, recepcion, admin, entrar)
    datos = {"tipo": "chisme", "titulo": "x", "descripcion": "corto"}
    assert cliente.post("/mecanico/reportes", json=datos, headers=mecanico).status_code == 400


def test_marcar_notificaciones_como_leidas(cliente, recepcion):
    no_leidas = cliente.get("/notificaciones?solo_no_leidas=true", headers=recepcion).json()
    assert no_leidas
    primera = no_leidas[0]["id"]
    assert cliente.post(f"/notificaciones/{primera}/leida", headers=recepcion).status_code == 200
    restantes = cliente.get("/notificaciones?solo_no_leidas=true", headers=recepcion).json()
    assert primera not in [n["id"] for n in restantes]
    cliente.post("/notificaciones/leer-todas", headers=recepcion)
    assert cliente.get("/notificaciones?solo_no_leidas=true", headers=recepcion).json() == []
