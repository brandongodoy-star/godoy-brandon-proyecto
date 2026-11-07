import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from database import inicializar_bd
from routers import auth


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    inicializar_bd()
    yield


app = FastAPI(
    title="API Taller Mecánico",
    description="Órdenes de reparación de vehículos, repuestos y mecánicos.",
    version="1.0.0",
    lifespan=ciclo_de_vida,
)

app.include_router(auth.router)


@app.exception_handler(sqlite3.IntegrityError)
def manejar_integridad(request: Request, error: sqlite3.IntegrityError):
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


@app.get("/", tags=["Inicio"])
def inicio():
    return {"mensaje": "API del Taller Mecánico funcionando. Documentación en /docs"}
