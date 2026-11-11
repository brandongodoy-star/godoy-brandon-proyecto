# godoy-brandon-proyecto

API de un taller mecánico hecha con FastAPI y SQLite.

## Cómo ejecutarla (PowerShell)

1. Crea el entorno virtual e instala las dependencias:

   ```powershell
   python -m venv venv
   venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Inicia la API. La primera vez crea `taller.db` a partir de `crear_bd.sql` y la clave secreta que firma los tokens:

   ```powershell
   uvicorn main:app --reload
   ```

   Si el puerto 8000 está ocupado por otra API, agrega `--port 8001` y usa ese número en las direcciones.

   La clave se guarda en el archivo `.clave_secreta`, que Git ignora para que nunca se suba. Si lo borras se crea una nueva y los tokens anteriores dejan de servir. En un servidor real se puede usar la variable de entorno `TALLER_CLAVE_SECRETA` en su lugar.

3. Abre http://127.0.0.1:8000 e inicia sesión con una de las cuentas de la empresa (abajo).

   La documentación de la API queda en http://127.0.0.1:8000/docs. Ahí usa el botón **Authorize** con una de esas cuentas.

Si ya tenías una `taller.db` de antes, la API la actualiza sola al arrancar sin borrar tus datos. Las cuentas que ya existían quedan como administrador.

## Cuentas y roles

No hay registro público: las cuentas las entrega la empresa. La primera vez se crean estas tres:

| Usuario | Contraseña | Rol | Qué puede hacer |
|---|---|---|---|
| `admin` | `Admin2026!` | Administración | Todo, y además crear y eliminar cuentas |
| `recepcion` | `Recepcion2026!` | Recepción | Clientes, vehículos, mecánicos, repuestos y órdenes |
| `mecanico` | `Mecanico2026!` | Mecánico | Solo su área: sus trabajos, sus reportes y su perfil |

**Cambie estas contraseñas** después de entrar (`POST /auth/cambiar-password`, o desde «Mi perfil» en el caso del mecánico). La cuenta `mecanico` queda vinculada al primer mecánico activo. Para otros mecánicos, el administrador crea una cuenta en **Cuentas** y elige su ficha.

## Área del mecánico

El mecánico entra a una interfaz limitada, sin precios ni datos de contacto de los clientes:

- **Mis trabajos:** los vehículos que le asignó recepción, como líder o como parte del equipo. Cualquiera del equipo puede enviar un aviso a recepción si todavía no está listo (por ejemplo, «falta un repuesto»). Cada aviso llega a recepción como notificación.
- **Reportes:** informa fallas de equipo o herramientas, falta de repuestos, problemas de seguridad u otros. También llegan a recepción.
- **Mi perfil:** sus datos personales, sus números, su historial de créditos y el cambio de contraseña.

### Equipo y líder del trabajo

Recepción arma el equipo de cada orden: elige el **líder del trabajo** (se sugiere el de más créditos, pero lo elige a mano) y los demás mecánicos que lo acompañan. Dentro de cada trabajo hay una sección **Equipo** con todos sus miembros y la tarea de cada uno.

El líder administra ese trabajo, y solo ese, mientras está «recibido» o «en reparación»:

- Asigna una tarea a cada miembro y califica su trabajo.
- Reporta a un miembro si hace falta. El reporte se queda dentro del trabajo (no en la sección Reportes), le llega a recepción y el miembro reportado no lo ve.
- Es el único que empieza la reparación y la marca como lista. Para marcarla lista debe haber calificado a todo el equipo.

Al marcar el trabajo como listo, el líder pierde estos permisos. Los miembros pueden ser de menor nivel que el auto, para que aprendan junto al líder; el líder sí debe tener el nivel.

### Créditos (fama) y niveles

Al entregar una orden, recepción califica el trabajo. El líder gana o pierde los créditos de esa calificación. Cada miembro del equipo recibe la mitad según la calificación de recepción y la otra mitad según lo calificó su líder. Los autos más valiosos valen más:

| Calificación | Estándar | Premium | Lujo |
|---|---|---|---|
| Excelente | +20 | +30 | +40 |
| Bien | +10 | +15 | +20 |
| Con problemas | -10 | -15 | -20 |
| Hubo que rehacerlo | -25 | -37 | -50 |

Los créditos nunca bajan de 0. Con más créditos el mecánico sube de nivel y puede recibir mejores autos:

| Nivel | Desde | Autos que puede trabajar |
|---|---|---|
| Aprendiz | 0 | Estándar |
| Técnico | 100 | Estándar y Premium |
| Maestro | 250 | Estándar, Premium y Lujo |

Por ejemplo, en un auto estándar que recepción califica «bien» (+10), un miembro que su líder calificó «excelente» (+20) gana (10 + 20) / 2 = 15.

Recepción no puede poner como líder a un mecánico con menos nivel que la categoría del auto. Si baja de nivel, conserva los trabajos que ya tenía. Las reglas están en `creditos.py`.

Además, desde cada trabajo cualquier miembro del equipo puede **pedir material** al almacén (repuesto, cantidad y para qué). Ve si su petición está pendiente, enviada o rechazada.

## Área de recepción

Recepción (y administración) tiene más poder que los mecánicos:

| Sección | Qué hace |
|---|---|
| **Proyectos** | Proyectos de trabajo: vehículo, datos del cliente, problema, **indicaciones del cliente** (los mecánicos también las ven), mecánico líder y equipo. Al abrir uno se ve su costo, lo pagado y el saldo. |
| **Bandeja** | Recibe lo que mandan los mecánicos: **peticiones de material** (enviar o rechazar con un motivo), **reportes** (incluidos los del líder sobre su equipo; se marcan como resueltos) y **avisos** (trabajo listo, cómo va). |
| **Cobros** | Total, pagado y saldo de cada proyecto. Se cobra en partes (anticipos) con efectivo, tarjeta o transferencia, sin pasarse del saldo. Solo administración puede anular un pago. |
| **Almacén** | Inventario de repuestos. Con «Enviar» se manda material a un proyecto activo: se descuenta del almacén y se suma al costo. |
| **Puntuaciones** | Ranking de mecánicos, proyectos listos para calificar y **ajuste manual de créditos** (de -100 a 100, con motivo y proyecto opcional). El mecánico ve el motivo en su historial. |
| **Vehículos** | Registro de vehículos; con el reloj se abre su **historial**: todos sus proyectos, cuánto se ha gastado y cuánto se debe. |

Entregar un proyecto con saldo pendiente es posible: el sistema avisa cuánto debe el cliente, y el saldo queda en Cobros.

## Interfaz web

La carpeta `frontend/` tiene la página que FastAPI sirve en la raíz (`index.html`, `estilos.css` y `app.js`, sin librerías externas). Lo que se ve depende del rol:

- **Administración y recepción:** Resumen, Proyectos (tablero por estado), Bandeja, Cobros, Almacén, Puntuaciones, Vehículos, Clientes y Mecánicos. **Cuentas** es solo para administración.
- **Mecánico:** el área descrita arriba.

La página pide sus archivos con un número de versión (`app.js?v=7`). Si se cambian, hay que subir ese número en `index.html` para que los navegadores bajen la versión nueva.

Tiene modo claro u oscuro y diseño adaptado al celular. La sesión se guarda solo mientras la pestaña esté abierta.

## Módulos

| Módulo | Ruta | Además del CRUD |
|---|---|---|
| Clientes | `/clientes` | |
| Vehículos | `/vehiculos` | Filtrar por `?cliente_id=` |
| Mecánicos | `/mecanicos` | Filtrar con `?solo_activos=true` |
| Repuestos | `/repuestos` | |
| Órdenes de servicio | `/ordenes` | Filtrar por `?estado=` o `?vehiculo_id=` |
| Cuentas (solo administración) | `/usuarios` | Sin edición: se crean y se eliminan |
| Área del mecánico | `/mecanico/...` | Perfil, trabajos, avisos, reportes, y equipo del líder (`/mecanico/trabajos/{id}/equipo/{miembro}` y `/reportes-equipo`) |
| Notificaciones y reportes | `/notificaciones`, `/reportes` | Para administración y recepción |
| Peticiones de material | `/peticiones` | Enviar (`/{id}/enviar`) o rechazar (`/{id}/rechazar`) |
| Cobros | `/cobros`, `/ordenes/{id}/cobro`, `/ordenes/{id}/pagos` | Anular: `DELETE /pagos/{id}` (solo administración) |
| Créditos e historial | `/mecanicos/{id}/creditos`, `/vehiculos/{id}/historial` | Ajuste manual de créditos e historial de un vehículo |

Rutas propias de una orden:

- `POST /ordenes/{id}/repuestos`: agrega un repuesto y lo descuenta del inventario.
- `GET /ordenes/{id}/repuestos`: lista los repuestos usados en la orden.
- `DELETE /ordenes/{id}/repuestos/{detalle_id}`: quita un repuesto y lo devuelve al inventario.
- `POST /ordenes/{id}/avanzar`: pasa al siguiente estado (`recibido` → `en reparacion` → `listo` → `entregado`). Para entregar se envía `{"calificacion": "excelente" | "bien" | "con problemas" | "rehacer"}`.
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
