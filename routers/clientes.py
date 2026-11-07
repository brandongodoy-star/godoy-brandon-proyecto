from fastapi import APIRouter, Depends, status

from database import obtener_conexion
from modelos import ClienteEntrada, ClienteRespuesta, MensajeRespuesta
from repositorios import RepositorioCliente
from seguridad import obtener_usuario_actual

router = APIRouter(
    prefix="/clientes", tags=["Clientes"], dependencies=[Depends(obtener_usuario_actual)]
)


@router.get("", response_model=list[ClienteRespuesta])
def listar_clientes():
    with obtener_conexion() as con:
        return RepositorioCliente(con).obtener_todos()


@router.get("/{cliente_id}", response_model=ClienteRespuesta)
def obtener_cliente(cliente_id: int):
    with obtener_conexion() as con:
        return RepositorioCliente(con).obtener_por_id(cliente_id)


@router.post("", response_model=ClienteRespuesta, status_code=status.HTTP_201_CREATED)
def crear_cliente(datos: ClienteEntrada):
    with obtener_conexion() as con:
        return RepositorioCliente(con).crear(datos.model_dump(mode="json"))


@router.put("/{cliente_id}", response_model=ClienteRespuesta)
def actualizar_cliente(cliente_id: int, datos: ClienteEntrada):
    with obtener_conexion() as con:
        return RepositorioCliente(con).actualizar(cliente_id, datos.model_dump(mode="json"))


@router.delete("/{cliente_id}", response_model=MensajeRespuesta)
def eliminar_cliente(cliente_id: int):
    with obtener_conexion() as con:
        RepositorioCliente(con).eliminar(cliente_id)
    return {"mensaje": "Cliente eliminado"}
