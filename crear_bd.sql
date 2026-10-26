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
('Carlos Mejía',    '9988-1122', 'Barrio Abajo, Comayagua'),
('Ana Rivera',      '9876-3344', 'Col. Las Colinas'),
('Luis Martínez',   '9765-4455', 'Barrio Arriba'),
('María Pineda',    '3344-5566', 'Col. Esperanza'),
('José Hernández',  '8899-6677', 'Col. Jardines'),
('Sofía Reyes',     '9911-7788', 'Barrio San Sebastián'),
('Pedro Alvarado',  '3322-8899', 'Col. Valle de Ángeles'),
('Karla Medina',    '9433-1010', 'Barrio El Centro'),
('Roberto Flores',  '8765-2020', 'Col. Los Pinos'),
('Elena Castro',    '9234-3030', 'La Libertad');

INSERT INTO vehiculos (placa, marca, modelo, anio, cliente_id) VALUES
('HAB-1234', 'Toyota',     'Hilux',   2018, 1),
('PCA-5678', 'Honda',      'Civic',   2015, 2),
('HBC-9012', 'Nissan',     'Frontier',2020, 3),
('HCD-3456', 'Toyota',     'Corolla', 2012, 4),
('HDE-7890', 'Mazda',      'CX-5',    2019, 5),
('HEF-2345', 'Hyundai',    'Elantra', 2017, 6),
('HFG-6789', 'Kia',        'Sportage',2021, 7),
('HGH-1357', 'Ford',       'Ranger',  2016, 8),
('HHI-2468', 'Chevrolet',  'Spark',   2014, 9),
('HIJ-3579', 'Mitsubishi', 'L200',    2013, 10);

INSERT INTO mecanicos (nombre, especialidad, activo) VALUES
('Marvin Cruz',   'Motor',            1),
('Oscar Lagos',   'Frenos y suspensión', 1),
('Denis Soto',    'Electricidad',     1),
('Wilmer Paz',    'Transmisión',      1),
('Hugo Banegas',  'Mecánica general', 0);

INSERT INTO repuestos (nombre, precio, existencia) VALUES
('Filtro de aceite',      120.00, 40),
('Aceite de motor 1L',    180.00, 100),
('Pastillas de freno',    650.00, 20),
('Bujía',                  95.00, 60),
('Batería 12V',          2200.00, 8),
('Filtro de aire',        250.00, 30),
('Banda de distribución', 900.00, 12),
('Amortiguador',         1500.00, 10),
('Bomba de agua',        1200.00, 6),
('Faja serpentina',       450.00, 15);

INSERT INTO ordenes_servicio (vehiculo_id, mecanico_id, fecha_ingreso, diagnostico, estado, mano_obra) VALUES
(1,  1, '2026-10-01', 'Cambio de aceite y filtros',   'entregado',     300.00),
(2,  2, '2026-10-03', 'Frenos desgastados',           'entregado',     500.00),
(3,  3, '2026-10-05', 'Batería descargada',           'listo',         200.00),
(4,  1, '2026-10-08', 'Falla en bujías',              'en reparacion', 400.00),
(5,  4, '2026-10-10', 'Ruido en la transmisión',      'en reparacion', 1200.00),
(6,  2, '2026-10-12', 'Amortiguadores débiles',       'recibido',      800.00),
(7,  1, '2026-10-15', 'Cambio de banda',              'recibido',      700.00),
(8,  3, '2026-10-18', 'Revisión eléctrica',           'listo',         350.00),
(9,  2, '2026-10-20', 'Cambio de pastillas',          'entregado',     450.00),
(10, 4, '2026-10-22', 'Sobrecalentamiento del motor', 'recibido',     600.00);

INSERT INTO detalle_orden (orden_id, repuesto_id, cantidad) VALUES
(1, 1, 1), (1, 2, 4),
(2, 3, 1),
(3, 5, 1),
(4, 4, 4),
(5, 10, 1),
(6, 8, 2),
(7, 7, 1),
(8, 4, 2),
(9, 3, 1),
(10, 9, 1), (10, 2, 2);