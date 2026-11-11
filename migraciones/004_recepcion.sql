-- Área de recepción: indicaciones del cliente en cada proyecto, cobros y peticiones de material.

ALTER TABLE ordenes_servicio ADD COLUMN indicaciones TEXT;

CREATE TABLE pagos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    orden_id       INTEGER NOT NULL REFERENCES ordenes_servicio(id),
    monto          REAL NOT NULL CHECK (monto > 0),
    metodo         TEXT NOT NULL CHECK (metodo IN ('efectivo', 'tarjeta', 'transferencia')),
    referencia     TEXT,
    registrado_por TEXT,
    fecha          TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE peticiones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    orden_id        INTEGER NOT NULL REFERENCES ordenes_servicio(id) ON DELETE CASCADE,
    mecanico_id     INTEGER NOT NULL REFERENCES mecanicos(id),
    repuesto_id     INTEGER NOT NULL REFERENCES repuestos(id),
    cantidad        INTEGER NOT NULL CHECK (cantidad > 0),
    motivo          TEXT,
    estado          TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'enviada', 'rechazada')),
    respuesta       TEXT,
    fecha           TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    fecha_respuesta TEXT
);

PRAGMA user_version = 4;
