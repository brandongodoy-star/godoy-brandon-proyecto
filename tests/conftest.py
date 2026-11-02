import os
import tempfile

# Se configuran antes de importar la app para no tocar taller.db ni pedir una clave real
os.environ["TALLER_BD"] = os.path.join(tempfile.mkdtemp(), "prueba.db")
os.environ["TALLER_CLAVE_SECRETA"] = "clave-solo-para-las-pruebas-automaticas-del-taller"
