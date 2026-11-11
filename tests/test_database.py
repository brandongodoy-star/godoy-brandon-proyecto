import sqlite3
from pathlib import Path

import pytest

import database

# Copia del crear_bd.sql de antes de los roles y los créditos, para probar la migración
VERSION_1 = Path(__file__).parent / "bd_version_1.sql"


def contar(ruta, tabla):
    con = sqlite3.connect(ruta)
    try:
        return con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
    finally:
        con.close()


def version(ruta):
    con = sqlite3.connect(ruta)
    try:
        return con.execute("PRAGMA user_version").fetchone()[0]
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
    assert contar(ruta_bd, "vehiculos") == 12
    assert contar(ruta_bd, "mecanicos") == 5
    assert contar(ruta_bd, "repuestos") == 10
    assert contar(ruta_bd, "ordenes_servicio") == 11
    assert contar(ruta_bd, "detalle_orden") == 12
    assert contar(ruta_bd, "equipo_orden") == 4
    assert contar(ruta_bd, "pagos") == 4
    assert contar(ruta_bd, "peticiones") == 1
    assert version(ruta_bd) == database.VERSION_BD


def test_creditos_de_prueba_coinciden_con_su_historial(ruta_bd):
    database.inicializar_bd()
    con = sqlite3.connect(ruta_bd)
    try:
        filas = con.execute(
            """
            SELECT m.creditos, COALESCE(SUM(c.puntos), 0) FROM mecanicos m
            LEFT JOIN movimientos_credito c ON c.mecanico_id = m.id GROUP BY m.id
            """
        ).fetchall()
    finally:
        con.close()
    assert all(creditos == suma for creditos, suma in filas)


def test_actualiza_una_base_de_la_version_anterior(ruta_bd):
    # Base creada con el crear_bd.sql de antes de los roles, con una cuenta y datos propios
    con = sqlite3.connect(ruta_bd)
    con.executescript(VERSION_1.read_text(encoding="utf-8"))
    con.execute("INSERT INTO usuarios (username, password_hash) VALUES ('viejo', 'x')")
    con.execute("INSERT INTO clientes (nombre, telefono) VALUES ('Propio', '9999-0000')")
    con.commit()
    con.close()

    database.inicializar_bd()

    assert version(ruta_bd) == database.VERSION_BD
    assert contar(ruta_bd, "clientes") == 11
    con = sqlite3.connect(ruta_bd)
    try:
        assert con.execute("SELECT rol FROM usuarios WHERE username = 'viejo'").fetchone()[0] == "administrador"
        assert {c for (c,) in con.execute("SELECT DISTINCT categoria FROM vehiculos")} == {"estandar"}
        assert con.execute("SELECT SUM(creditos) FROM mecanicos").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM reportes").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM equipo_orden").fetchone()[0] == 0
    finally:
        con.close()

    # Arrancar otra vez no vuelve a migrar ni falla
    database.inicializar_bd()
    assert contar(ruta_bd, "clientes") == 11


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


def test_la_migracion_de_equipos_conserva_los_reportes(ruta_bd):
    # Base en la versión 2 (con roles y créditos) que ya tiene un reporte guardado
    con = sqlite3.connect(ruta_bd)
    con.executescript(VERSION_1.read_text(encoding="utf-8"))
    con.executescript((Path(database.CARPETA_MIGRACIONES) / database.MIGRACIONES[2]).read_text(encoding="utf-8"))
    con.execute(
        "INSERT INTO reportes (mecanico_id, tipo, titulo, descripcion) VALUES (1, 'equipo', 'Gata', 'No sube')"
    )
    con.commit()
    con.close()
    assert version(ruta_bd) == 2

    database.inicializar_bd()

    assert version(ruta_bd) == database.VERSION_BD
    con = sqlite3.connect(ruta_bd)
    try:
        fila = con.execute("SELECT titulo, tipo, sobre_mecanico_id FROM reportes").fetchone()
        assert fila == ("Gata", "equipo", None)
        # El nuevo tipo «desempeno» ya se acepta
        con.execute(
            "INSERT INTO reportes (mecanico_id, tipo, titulo, descripcion, sobre_mecanico_id) "
            "VALUES (1, 'desempeno', 'Tarde', 'Llegó tarde', 2)"
        )
    finally:
        con.close()
