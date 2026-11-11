-- Mensajes de recepción a los mecánicos y penalización al resolver un reporte del líder.

ALTER TABLE reportes ADD COLUMN penalizacion INTEGER;
ALTER TABLE reportes ADD COLUMN comentario TEXT;

CREATE TABLE mensajes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mecanico_id INTEGER NOT NULL REFERENCES mecanicos(id),
    remitente   TEXT NOT NULL,
    asunto      TEXT NOT NULL,
    texto       TEXT NOT NULL,
    orden_id    INTEGER REFERENCES ordenes_servicio(id) ON DELETE SET NULL,
    leido       INTEGER NOT NULL DEFAULT 0 CHECK (leido IN (0, 1)),
    fecha       TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

PRAGMA user_version = 5;
