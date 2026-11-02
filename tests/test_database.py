import sqlite3

import pytest

import database


def contar(ruta, tabla):
    con = sqlite3.connect(ruta)
    try:
        return con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
    finally:
        con.close()


@pytest.fixture
def ruta_bd(tmp_path, monkeypatch):
    ruta = tmp_path / "taller.db"
    monkeypatch.setattr(database, "RUTA_BD", str(ruta))
    return ruta


def test_base_nueva_carga_datos_de_prueba(ruta_bd):
    database.inicializar_bd()
    assert contar(ruta_bd, "clientes") == 10
    assert contar(ruta_bd, "vehiculos") == 10
    assert contar(ruta_bd, "mecanicos") == 5
    assert contar(ruta_bd, "repuestos") == 10
    assert contar(ruta_bd, "ordenes_servicio") == 10
    assert contar(ruta_bd, "detalle_orden") == 12


def test_archivo_vacio_se_inicializa(ruta_bd):
    ruta_bd.touch()
    database.inicializar_bd()
    assert contar(ruta_bd, "clientes") == 10


def test_no_borra_datos_existentes(ruta_bd):
    database.inicializar_bd()
    with database.obtener_conexion() as con:
        con.execute("INSERT INTO clientes (nombre, telefono) VALUES ('Nuevo', '9999-0000')")
    database.inicializar_bd()
    assert contar(ruta_bd, "clientes") == 11


def test_script_con_error_no_deja_base_a_medio_crear(ruta_bd, tmp_path, monkeypatch):
    script = tmp_path / "malo.sql"
    script.write_text("CREATE TABLE a (id INTEGER); ESTO NO ES SQL;", encoding="utf-8")
    monkeypatch.setattr(database, "RUTA_SCRIPT", str(script))
    with pytest.raises(sqlite3.Error):
        database.inicializar_bd()
    con = sqlite3.connect(ruta_bd)
    try:
        assert con.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0] == 0
    finally:
        con.close()
