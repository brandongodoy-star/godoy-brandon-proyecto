PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS pagos;
DROP TABLE IF EXISTS peticiones;
DROP TABLE IF EXISTS notificaciones;
DROP TABLE IF EXISTS reportes;
DROP TABLE IF EXISTS equipo_orden;
DROP TABLE IF EXISTS movimientos_credito;
DROP TABLE IF EXISTS usuarios;
DROP TABLE IF EXISTS detalle_orden;
DROP TABLE IF EXISTS ordenes_servicio;
DROP TABLE IF EXISTS repuestos;
DROP TABLE IF EXISTS mecanicos;
DROP TABLE IF EXISTS vehiculos;
DROP TABLE IF EXISTS clientes;

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
    categoria  TEXT NOT NULL DEFAULT 'estandar' CHECK (categoria IN ('estandar', 'premium', 'lujo')),
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

CREATE TABLE mecanicos (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre             TEXT NOT NULL,
    especialidad       TEXT,
    activo             INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    telefono           TEXT,
    correo             TEXT,
    fecha_contratacion TEXT,
    creditos           INTEGER NOT NULL DEFAULT 0 CHECK (creditos >= 0)
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
    calificacion  TEXT CHECK (calificacion IN ('excelente', 'bien', 'con problemas', 'rehacer')),
    indicaciones  TEXT,  -- lo que pidió o avisó el cliente; los mecánicos también lo ven
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

-- Las cuentas las crea la empresa. Una cuenta de mecánico se vincula con su ficha de mecánico.
CREATE TABLE usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    rol           TEXT NOT NULL CHECK (rol IN ('administrador', 'recepcion', 'mecanico')),
    nombre        TEXT,
    mecanico_id   INTEGER REFERENCES mecanicos(id)
);
CREATE UNIQUE INDEX idx_usuarios_mecanico ON usuarios(mecanico_id);

-- Cada vez que los créditos de un mecánico suben o bajan queda una línea aquí
CREATE TABLE movimientos_credito (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mecanico_id INTEGER NOT NULL REFERENCES mecanicos(id),
    orden_id    INTEGER REFERENCES ordenes_servicio(id) ON DELETE SET NULL,
    puntos      INTEGER NOT NULL,
    motivo      TEXT NOT NULL,
    fecha       TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Avisos que los mecánicos envían a recepción
CREATE TABLE notificaciones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo        TEXT NOT NULL CHECK (tipo IN ('listo', 'avance', 'reporte')),
    mensaje     TEXT NOT NULL,
    orden_id    INTEGER REFERENCES ordenes_servicio(id) ON DELETE SET NULL,
    mecanico_id INTEGER REFERENCES mecanicos(id),
    leida       INTEGER NOT NULL DEFAULT 0 CHECK (leida IN (0, 1)),
    fecha       TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Informes de los mecánicos sobre el equipo, los repuestos o la seguridad del taller.
-- «desempeno» es el reporte del líder de un trabajo sobre un miembro de su equipo (sobre_mecanico_id).
CREATE TABLE reportes (
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

-- Equipo de cada orden: el líder es ordenes_servicio.mecanico_id y aquí van los demás.
-- El líder asigna la tarea de cada miembro y califica su trabajo.
CREATE TABLE equipo_orden (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    orden_id     INTEGER NOT NULL REFERENCES ordenes_servicio(id) ON DELETE CASCADE,
    mecanico_id  INTEGER NOT NULL REFERENCES mecanicos(id),
    tarea        TEXT,
    calificacion TEXT CHECK (calificacion IN ('excelente', 'bien', 'con problemas', 'rehacer')),
    UNIQUE (orden_id, mecanico_id)
);

-- Pagos del cliente por cada proyecto (puede pagar en partes, por ejemplo con un anticipo)
CREATE TABLE pagos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    orden_id       INTEGER NOT NULL REFERENCES ordenes_servicio(id),
    monto          REAL NOT NULL CHECK (monto > 0),
    metodo         TEXT NOT NULL CHECK (metodo IN ('efectivo', 'tarjeta', 'transferencia')),
    referencia     TEXT,
    registrado_por TEXT,
    fecha          TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Materiales que los mecánicos piden al almacén; recepción los envía o los rechaza
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

INSERT INTO vehiculos (placa, marca, modelo, anio, cliente_id, categoria) VALUES
('HAB-1234', 'Toyota',        'Hilux',    2018, 1,  'premium'),
('PCA-5678', 'Honda',         'Civic',    2015, 2,  'estandar'),
('HBC-9012', 'Nissan',        'Frontier', 2020, 3,  'premium'),
('HCD-3456', 'Toyota',        'Corolla',  2012, 4,  'estandar'),
('HDE-7890', 'Mazda',         'CX-5',     2019, 5,  'premium'),
('HEF-2345', 'Hyundai',       'Elantra',  2017, 6,  'estandar'),
('HFG-6789', 'Kia',           'Sportage', 2021, 7,  'premium'),
('HGH-1357', 'Ford',          'Ranger',   2016, 8,  'estandar'),
('HHI-2468', 'Chevrolet',     'Spark',    2014, 9,  'estandar'),
('HIJ-3579', 'Mitsubishi',    'L200',     2013, 10, 'estandar'),
('HKL-4821', 'BMW',           'X5',       2022, 3,  'lujo'),
('HLM-9036', 'Mercedes-Benz', 'Clase C',  2021, 6,  'lujo');

INSERT INTO mecanicos (nombre, especialidad, activo, telefono, correo, fecha_contratacion, creditos) VALUES
('Marvin Cruz',   'Motor',               1, '9811-2201', 'marvin.cruz@taller.hn',   '2018-03-12', 320),
('Oscar Lagos',   'Frenos y suspensión', 1, '9822-3302', 'oscar.lagos@taller.hn',   '2021-07-01', 80),
('Denis Soto',    'Electricidad',        1, '9833-4403', 'denis.soto@taller.hn',    '2020-01-15', 150),
('Wilmer Paz',    'Transmisión',         1, '9844-5504', 'wilmer.paz@taller.hn',    '2022-05-09', 120),
('Hugo Banegas',  'Mecánica general',    0, '9855-6605', 'hugo.banegas@taller.hn',  '2016-11-20', 30);

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

INSERT INTO ordenes_servicio (vehiculo_id, mecanico_id, fecha_ingreso, diagnostico, estado, mano_obra, calificacion) VALUES
(1,  1, '2026-10-01', 'Cambio de aceite y filtros',   'entregado',     300.00,  'excelente'),
(2,  2, '2026-10-03', 'Frenos desgastados',           'entregado',     500.00,  'bien'),
(3,  3, '2026-10-05', 'Batería descargada',           'listo',         200.00,  NULL),
(4,  1, '2026-10-08', 'Falla en bujías',              'en reparacion', 400.00,  NULL),
(5,  4, '2026-10-10', 'Ruido en la transmisión',      'en reparacion', 1200.00, NULL),
(6,  2, '2026-10-12', 'Amortiguadores débiles',       'recibido',      800.00,  NULL),
(7,  1, '2026-10-15', 'Cambio de banda',              'recibido',      700.00,  NULL),
(8,  3, '2026-10-18', 'Revisión eléctrica',           'listo',         350.00,  NULL),
(9,  2, '2026-10-20', 'Cambio de pastillas',          'entregado',     450.00,  'excelente'),
(10, 4, '2026-10-22', 'Sobrecalentamiento del motor', 'recibido',      600.00,  NULL),
(11, 1, '2026-10-24', 'Revisión de los 40,000 km',    'recibido',      2500.00, NULL);

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

-- El historial explica los créditos de cada mecánico (la suma da su total)
INSERT INTO movimientos_credito (mecanico_id, orden_id, puntos, motivo, fecha) VALUES
(1, NULL, 290, 'Créditos por experiencia previa', '2026-09-30 08:00:00'),
(2, NULL, 50,  'Créditos por experiencia previa', '2026-09-30 08:00:00'),
(3, NULL, 150, 'Créditos por experiencia previa', '2026-09-30 08:00:00'),
(4, NULL, 120, 'Créditos por experiencia previa', '2026-09-30 08:00:00'),
(5, NULL, 30,  'Créditos por experiencia previa', '2026-09-30 08:00:00'),
(1, 1,    30,  'Orden #1 calificada «excelente» (auto premium)', '2026-10-02 16:30:00'),
(2, 2,    10,  'Orden #2 calificada «bien» (auto estándar)',     '2026-10-04 11:15:00'),
(2, 9,    20,  'Orden #9 calificada «excelente» (auto estándar)', '2026-10-21 15:45:00');

INSERT INTO equipo_orden (orden_id, mecanico_id, tarea) VALUES
(5,  2, 'Revisar soportes y suspensión trasera'),
(7,  3, 'Revisar el sistema eléctrico del arranque'),
(11, 4, 'Cambio de aceite de la transmisión'),
(11, 2, NULL);

UPDATE ordenes_servicio SET indicaciones = 'Llamar antes de cambiar piezas caras' WHERE id = 5;
UPDATE ordenes_servicio SET indicaciones = 'El cliente necesita el carro el viernes' WHERE id = 11;

-- Pagos: las entregadas están pagadas y la orden 3 tiene un anticipo
INSERT INTO pagos (orden_id, monto, metodo, referencia, registrado_por, fecha) VALUES
(1, 1140.00, 'efectivo',      NULL,       'recepcion', '2026-10-02 16:30:00'),
(2, 1150.00, 'tarjeta',       'POS-4410', 'recepcion', '2026-10-04 11:15:00'),
(9, 1100.00, 'transferencia', 'TRF-2087', 'recepcion', '2026-10-21 15:45:00'),
(3, 1000.00, 'efectivo',      NULL,       'recepcion', '2026-10-05 09:10:00');

INSERT INTO peticiones (orden_id, mecanico_id, repuesto_id, cantidad, motivo, fecha) VALUES
(5, 2, 8, 2, 'Los amortiguadores traseros también están vencidos', '2026-10-11 10:20:00');

PRAGMA user_version = 4;
