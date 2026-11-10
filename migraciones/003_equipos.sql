-- Agrega los equipos de trabajo: cada orden tiene un líder (ordenes_servicio.mecanico_id)
-- y miembros. El líder les asigna tareas, los califica y puede reportarlos.

CREATE TABLE equipo_orden (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    orden_id     INTEGER NOT NULL REFERENCES ordenes_servicio(id) ON DELETE CASCADE,
    mecanico_id  INTEGER NOT NULL REFERENCES mecanicos(id),
    tarea        TEXT,
    calificacion TEXT CHECK (calificacion IN ('excelente', 'bien', 'con problemas', 'rehacer')),
    UNIQUE (orden_id, mecanico_id)
);

-- Los reportes ganan el tipo «desempeno» y el mecánico del que tratan.
-- SQLite no permite cambiar un CHECK, así que la tabla se crea de nuevo con los mismos datos.
CREATE TABLE reportes_nueva (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    mecanico_id       INTEGER NOT NULL REFERENCES mecanicos(id),
    orden_id          INTEGER REFERENCES ordenes_servicio(id) ON DELETE SET NULL,
    tipo              TEXT NOT NULL CHECK (tipo IN ('equipo', 'repuestos', 'seguridad', 'otro', 'desempeno')),
    titulo            TEXT NOT NULL,
    descripcion       TEXT NOT NULL,
    estado            TEXT NOT NULL DEFAULT 'abierto' CHECK (estado IN ('abierto', 'resuelto')),
    fecha             TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    sobre_mecanico_id INTEGER REFERENCES mecanicos(id)
);
INSERT INTO reportes_nueva (id, mecanico_id, orden_id, tipo, titulo, descripcion, estado, fecha)
    SELECT id, mecanico_id, orden_id, tipo, titulo, descripcion, estado, fecha FROM reportes;
DROP TABLE reportes;
ALTER TABLE reportes_nueva RENAME TO reportes;

PRAGMA user_version = 3;
