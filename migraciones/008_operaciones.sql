-- Talleres, auxiliares de operaciones y traslado, tareas de traslado, copias en PDF de los reportes
-- y confirmación de «recibido» del material enviado a los mecánicos.

CREATE TABLE talleres (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre    TEXT NOT NULL UNIQUE,
    direccion TEXT NOT NULL,
    telefono  TEXT,
    encargado TEXT,
    horario   TEXT,
    capacidad INTEGER CHECK (capacidad IS NULL OR capacidad > 0),
    activo    INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);
INSERT INTO talleres (nombre, direccion, telefono, encargado, horario, capacidad) VALUES
('Taller Central',                 'Bulevar Morazán, frente a la gasolinera Uno', '2232-1100', 'Marvin Cruz', 'Lunes a sábado, 7:00 a. m. a 5:00 p. m.', 8),
('Taller Norte',                   'Col. Kennedy, salida al norte',              '2245-3300', 'Denis Soto',  'Lunes a viernes, 8:00 a. m. a 5:00 p. m.', 5),
('Taller de Carrocería y Pintura', 'Barrio La Granja, 2.ª avenida',              '2238-7700', 'Wilmer Paz',  'Lunes a viernes, 7:30 a. m. a 4:30 p. m.', 4);

ALTER TABLE mecanicos ADD COLUMN taller_id INTEGER REFERENCES talleres(id);
-- Los mecánicos de los datos de ejemplo van a su taller; los demás, al Taller Central
UPDATE mecanicos SET taller_id = CASE
    WHEN nombre IN ('Denis Soto', 'Hugo Banegas', 'Josué Martínez') THEN 2
    WHEN nombre = 'Wilmer Paz' THEN 3
    ELSE 1 END;

-- Nuevo rol «auxiliar». SQLite no permite cambiar un CHECK: la tabla se crea de nuevo con los mismos datos.
CREATE TABLE usuarios_nueva (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    rol           TEXT NOT NULL CHECK (rol IN ('administrador', 'recepcion', 'mecanico', 'auxiliar')),
    nombre        TEXT,
    mecanico_id   INTEGER REFERENCES mecanicos(id)
);
INSERT INTO usuarios_nueva (id, username, password_hash, rol, nombre, mecanico_id)
    SELECT id, username, password_hash, rol, nombre, mecanico_id FROM usuarios;
DROP TABLE usuarios;
ALTER TABLE usuarios_nueva RENAME TO usuarios;
CREATE UNIQUE INDEX idx_usuarios_mecanico ON usuarios(mecanico_id);

ALTER TABLE reportes ADD COLUMN pdf BLOB;
ALTER TABLE peticiones ADD COLUMN recibida_en TEXT;
ALTER TABLE mensajes ADD COLUMN peticion_id INTEGER REFERENCES peticiones(id) ON DELETE SET NULL;

-- Tareas de los auxiliares de operaciones y traslado: llevar piezas a los talleres, recibir
-- producto nuevo del proveedor y traer o llevar vehículos. Recepción las asigna (o quedan para
-- cualquier auxiliar); el auxiliar las acepta y las marca como realizadas.
CREATE TABLE tareas (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo         TEXT NOT NULL CHECK (tipo IN ('entregar_pieza', 'recibir_producto', 'traer_vehiculo',
                                               'llevar_vehiculo', 'otro')),
    titulo       TEXT NOT NULL,
    detalle      TEXT,
    taller_id    INTEGER REFERENCES talleres(id) ON DELETE SET NULL,
    orden_id     INTEGER REFERENCES ordenes_servicio(id) ON DELETE SET NULL,
    vehiculo_id  INTEGER REFERENCES vehiculos(id) ON DELETE SET NULL,
    repuesto_id  INTEGER REFERENCES repuestos(id) ON DELETE SET NULL,
    cantidad     INTEGER CHECK (cantidad IS NULL OR cantidad > 0),
    peticion_id  INTEGER REFERENCES peticiones(id) ON DELETE SET NULL,
    asignado_a   INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    estado       TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'aceptada', 'realizada')),
    creada_por   TEXT,
    nota         TEXT,  -- lo que anotó el auxiliar al terminar
    fecha        TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    aceptada_en  TEXT,
    realizada_en TEXT
);

PRAGMA user_version = 8;
