import os
import sqlite3
from contextlib import contextmanager

CARPETA = os.path.dirname(os.path.abspath(__file__))
RUTA_BD = os.getenv("TALLER_BD", os.path.join(CARPETA, "taller.db"))
RUTA_SCRIPT = os.path.join(CARPETA, "crear_bd.sql")
CARPETA_MIGRACIONES = os.path.join(CARPETA, "migraciones")

# Versión de la estructura que trae crear_bd.sql y migración que lleva a cada versión
VERSION_BD = 3
MIGRACIONES = {2: "002_roles_y_creditos.sql", 3: "003_equipos.sql"}


@contextmanager
def obtener_conexion():
    """Abre una conexión, confirma los cambios si todo sale bien y la cierra siempre."""
    con = sqlite3.connect(RUTA_BD)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def ejecutar_script(con: sqlite3.Connection, ruta: str) -> None:
    """Ejecuta un archivo .sql en una sola transacción: si falla, no queda nada a medias."""
    with open(ruta, encoding="utf-8") as archivo:
        script = archivo.read()
    con.executescript(f"BEGIN;\n{script}\nCOMMIT;")


def inicializar_bd():
    """Crea la base con crear_bd.sql si no tiene tablas; si es de una versión anterior, la actualiza."""
    with obtener_conexion() as con:
        tiene_tablas = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' LIMIT 1"
        ).fetchone()
        if not tiene_tablas:
            ejecutar_script(con, RUTA_SCRIPT)
            return
        version = con.execute("PRAGMA user_version").fetchone()[0]
        for numero, archivo in sorted(MIGRACIONES.items()):
            if numero > version:
                ejecutar_script(con, os.path.join(CARPETA_MIGRACIONES, archivo))
