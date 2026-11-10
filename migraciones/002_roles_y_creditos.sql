-- Actualiza una base creada antes de los roles y los créditos, sin borrar sus datos.
-- Las bases nuevas no la necesitan: crear_bd.sql ya trae todo esto.

ALTER TABLE vehiculos ADD COLUMN categoria TEXT NOT NULL DEFAULT 'estandar'
    CHECK (categoria IN ('estandar', 'premium', 'lujo'));

ALTER TABLE mecanicos ADD COLUMN telefono TEXT;
ALTER TABLE mecanicos ADD COLUMN correo TEXT;
ALTER TABLE mecanicos ADD COLUMN fecha_contratacion TEXT;
ALTER TABLE mecanicos ADD COLUMN creditos INTEGER NOT NULL DEFAULT 0 CHECK (creditos >= 0);

ALTER TABLE ordenes_servicio ADD COLUMN calificacion TEXT
    CHECK (calificacion IN ('excelente', 'bien', 'con problemas', 'rehacer'));

-- Antes cualquiera tenía acceso a todo, así que las cuentas que ya existían quedan como administrador
ALTER TABLE usuarios ADD COLUMN rol TEXT NOT NULL DEFAULT 'administrador'
    CHECK (rol IN ('administrador', 'recepcion', 'mecanico'));
ALTER TABLE usuarios ADD COLUMN nombre TEXT;
ALTER TABLE usuarios ADD COLUMN mecanico_id INTEGER REFERENCES mecanicos(id);
CREATE UNIQUE INDEX idx_usuarios_mecanico ON usuarios(mecanico_id);

CREATE TABLE movimientos_credito (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mecanico_id INTEGER NOT NULL REFERENCES mecanicos(id),
    orden_id    INTEGER REFERENCES ordenes_servicio(id) ON DELETE SET NULL,
    puntos      INTEGER NOT NULL,
    motivo      TEXT NOT NULL,
    fecha       TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE notificaciones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo        TEXT NOT NULL CHECK (tipo IN ('listo', 'avance', 'reporte')),
    mensaje     TEXT NOT NULL,
    orden_id    INTEGER REFERENCES ordenes_servicio(id) ON DELETE SET NULL,
    mecanico_id INTEGER REFERENCES mecanicos(id),
    leida       INTEGER NOT NULL DEFAULT 0 CHECK (leida IN (0, 1)),
    fecha       TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE reportes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mecanico_id INTEGER NOT NULL REFERENCES mecanicos(id),
    orden_id    INTEGER REFERENCES ordenes_servicio(id) ON DELETE SET NULL,
    tipo        TEXT NOT NULL CHECK (tipo IN ('equipo', 'repuestos', 'seguridad', 'otro')),
    titulo      TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    estado      TEXT NOT NULL DEFAULT 'abierto' CHECK (estado IN ('abierto', 'resuelto')),
    fecha       TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

PRAGMA user_version = 2;
