import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from database import inicializar_bd
from routers import (
    auth,
    clientes,
    mecanico,
    mecanicos,
    notificaciones,
    ordenes,
    reportes,
    repuestos,
    usuarios,
    vehiculos,
)
from seguridad import crear_cuentas_iniciales


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    inicializar_bd()
    crear_cuentas_iniciales()
    yield


app = FastAPI(
    title="API Taller Mecánico",
    description="Órdenes de reparación de vehículos, repuestos y mecánicos.",
    version="1.0.0",
    lifespan=ciclo_de_vida,
)

app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(mecanico.router)
app.include_router(notificaciones.router)
app.include_router(reportes.router)
app.include_router(clientes.router)
app.include_router(vehiculos.router)
app.include_router(mecanicos.router)
app.include_router(repuestos.router)
app.include_router(ordenes.router)


@app.exception_handler(sqlite3.IntegrityError)
def manejar_integridad(request: Request, error: sqlite3.IntegrityError):
    if "UNIQUE" in str(error):
        return JSONResponse(
            status_code=409,
            content={"detail": "Ya existe un registro con ese valor (por ejemplo, la placa)"},
        )
    if request.method == "DELETE":
        mensaje = "No se puede eliminar: hay otros registros que dependen de este"
    else:
        mensaje = "Datos inválidos: verifique que los registros relacionados existan"
    return JSONResponse(status_code=400, content={"detail": mensaje})


@app.exception_handler(RequestValidationError)
def manejar_validacion(request: Request, error: RequestValidationError):
    errores = [
        f"{'.'.join(str(p) for p in e['loc'][1:])}: {e['msg']}" for e in error.errors()
    ]
    return JSONResponse(status_code=400, content={"detail": errores})


# La interfaz web se sirve en la raíz. Va al final para no tapar las rutas de la API.
CARPETA_FRONTEND = Path(__file__).resolve().parent / "frontend"
app.mount("/", StaticFiles(directory=CARPETA_FRONTEND, html=True), name="frontend")
