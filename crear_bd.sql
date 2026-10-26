PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS detalle_orden;
DROP TABLE IF EXISTS ordenes_servicio;
DROP TABLE IF EXISTS repuestos;
DROP TABLE IF EXISTS mecanicos;
DROP TABLE IF EXISTS vehiculos;
DROP TABLE IF EXISTS clientes;
DROP TABLE IF EXISTS usuarios;

CREATE TABLE clientes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre    TEXT NOT NULL,
    telefono  TEXT NOT NULL,
    direccion TEXT
);

CREATE TABLE vehiculos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    placa      TEXT NOT NULL UNIQUE,
    marca      TEXT NOT NULL,
    modelo     TEXT NOT NULL,
    anio       INTEGER NOT NULL CHECK (anio BETWEEN 1950 AND 2100),
    cliente_id INTEGER NOT NULL,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

CREATE TABLE mecanicos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre       TEXT NOT NULL,
    especialidad TEXT,
    activo       INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);

CREATE TABLE repuestos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre     TEXT NOT NULL,
    precio     REAL NOT NULL CHECK (precio > 0),
    existencia INTEGER NOT NULL DEFAULT 0 CHECK (existencia >= 0)
);

CREATE TABLE ordenes_servicio (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    vehiculo_id   INTEGER NOT NULL,
    mecanico_id   INTEGER NOT NULL,
    fecha_ingreso TEXT NOT NULL,
    diagnostico   TEXT,
    estado        TEXT NOT NULL DEFAULT 'recibido'
                  CHECK (estado IN ('recibido', 'en reparacion', 'listo', 'entregado')),
    mano_obra     REAL NOT NULL DEFAULT 0 CHECK (mano_obra >= 0),
    FOREIGN KEY (vehiculo_id) REFERENCES vehiculos(id),
    FOREIGN KEY (mecanico_id) REFERENCES mecanicos(id)
);

CREATE TABLE detalle_orden (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    orden_id    INTEGER NOT NULL,
    repuesto_id INTEGER NOT NULL,
    cantidad    INTEGER NOT NULL CHECK (cantidad > 0),
    FOREIGN KEY (orden_id) REFERENCES ordenes_servicio(id),
    FOREIGN KEY (repuesto_id) REFERENCES repuestos(id)
);

CREATE TABLE usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

INSERT INTO clientes (nombre, telefono, direccion) VALUES
('Carlos Mejía', '9988-1122', 'Barrio Abajo, Comayagua'),
('Ana Rivera',   '9876-3344', 'Col. Las Colinas');


INSERT INTO vehiculos (placa, marca, modelo, anio, cliente_id) VALUES
('HAB-1234', 'Toyota', 'Hilux', 2018, 1),
('PCA-5678', 'Honda',  'Civic', 2015, 2);