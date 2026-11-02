import os
import sqlite3
from contextlib import contextmanager

CARPETA = os.path.dirname(os.path.abspath(__file__))
RUTA_BD = os.getenv("TALLER_BD", os.path.join(CARPETA, "taller.db"))
RUTA_SCRIPT = os.path.join(CARPETA, "crear_bd.sql")


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


def inicializar_bd():
    """Crea la base con crear_bd.sql solo si todavía no existe."""
    if os.path.exists(RUTA_BD):
        return
    with open(RUTA_SCRIPT, encoding="utf-8") as archivo:
        script = archivo.read()
    with obtener_conexion() as con:
        con.executescript(script)
