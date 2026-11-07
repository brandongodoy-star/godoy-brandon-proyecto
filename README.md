# godoy-brandon-proyecto

API de un taller mecánico hecha con FastAPI y SQLite.

## Cómo ejecutarla (PowerShell)

1. Crea el entorno virtual e instala las dependencias:

   ```powershell
   python -m venv venv
   venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Define la clave secreta que firma los tokens. La app no arranca sin ella y no debe subirse a Git:

   ```powershell
   $env:TALLER_CLAVE_SECRETA = python -c "import secrets; print(secrets.token_hex(32))"
   ```

   La variable dura lo que dure esa terminal. Si cambias la clave, los tokens anteriores dejan de servir.

3. Inicia la API. La primera vez crea `taller.db` a partir de `crear_bd.sql`:

   ```powershell
   uvicorn main:app --reload
   ```

   La documentación queda en http://127.0.0.1:8000/docs

4. En `/docs`, registra un usuario en `POST /auth/registro` y luego usa el botón **Authorize** para iniciar sesión. Todos los módulos piden ese inicio de sesión.

## Módulos

| Módulo | Ruta | Además del CRUD |
|---|---|---|
| Clientes | `/clientes` | |
| Vehículos | `/vehiculos` | Filtrar por `?cliente_id=` |
| Mecánicos | `/mecanicos` | Filtrar con `?solo_activos=true` |
| Repuestos | `/repuestos` | |
| Órdenes de servicio | `/ordenes` | Filtrar por `?estado=` o `?vehiculo_id=` |

Rutas propias de una orden:

- `POST /ordenes/{id}/repuestos`: agrega un repuesto y lo descuenta del inventario.
- `GET /ordenes/{id}/repuestos`: lista los repuestos usados en la orden.
- `DELETE /ordenes/{id}/repuestos/{detalle_id}`: quita un repuesto y lo devuelve al inventario.
- `POST /ordenes/{id}/avanzar`: pasa al siguiente estado (`recibido` → `en reparacion` → `listo` → `entregado`).
- `GET /ordenes/{id}/total`: suma la mano de obra y los repuestos.

Reglas del taller:

- Una orden solo se puede editar, eliminar o cambiar sus repuestos mientras está `recibido` o `en reparacion`.
- No se puede usar un repuesto si no hay existencia suficiente.
- No se puede asignar una orden a un mecánico inactivo.
- No se puede borrar un registro que otros usan (por ejemplo, un cliente con vehículos o un mecánico con órdenes). A un mecánico que ya no trabaja se le marca `activo: false`.
- El total usa el precio actual de cada repuesto.

La lógica sigue el diagrama UML: `repositorios.py` tiene `RepositorioBase` con las operaciones comunes y un repositorio por tabla. Los datos que se reciben se validan con los modelos de `modelos.py`.

## Pruebas

```powershell
pytest
```

Las pruebas usan una base temporal y su propia clave, así que no tocan `taller.db`.
