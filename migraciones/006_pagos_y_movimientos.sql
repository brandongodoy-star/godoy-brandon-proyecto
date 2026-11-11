-- Mensajería en los dos sentidos, datos de quien paga, anticipos, venta de repuestos
-- e historial de movimientos.

ALTER TABLE mensajes ADD COLUMN direccion TEXT NOT NULL DEFAULT 'a_mecanico'
    CHECK (direccion IN ('a_mecanico', 'a_recepcion'));

ALTER TABLE pagos ADD COLUMN tipo TEXT NOT NULL DEFAULT 'pago' CHECK (tipo IN ('pago', 'anticipo'));
ALTER TABLE pagos ADD COLUMN pagador_nombres TEXT;
ALTER TABLE pagos ADD COLUMN pagador_apellidos TEXT;
ALTER TABLE pagos ADD COLUMN pagador_identidad TEXT;
ALTER TABLE pagos ADD COLUMN pagador_correo TEXT;
ALTER TABLE pagos ADD COLUMN tarjeta_marca TEXT;
ALTER TABLE pagos ADD COLUMN tarjeta_ultimos4 TEXT;
ALTER TABLE pagos ADD COLUMN tarjeta_titular TEXT;
ALTER TABLE pagos ADD COLUMN autorizacion TEXT;
ALTER TABLE pagos ADD COLUMN banco TEXT;

CREATE TABLE ventas (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    repuesto_id       INTEGER NOT NULL REFERENCES repuestos(id),
    cantidad          INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario   REAL NOT NULL CHECK (precio_unitario > 0),
    total             REAL NOT NULL CHECK (total > 0),
    metodo            TEXT NOT NULL CHECK (metodo IN ('efectivo', 'tarjeta', 'transferencia')),
    referencia        TEXT,
    pagador_nombres   TEXT NOT NULL,
    pagador_apellidos TEXT NOT NULL,
    pagador_identidad TEXT NOT NULL,
    pagador_correo    TEXT,
    tarjeta_marca     TEXT,
    tarjeta_ultimos4  TEXT,
    tarjeta_titular   TEXT,
    autorizacion      TEXT,
    banco             TEXT,
    registrado_por    TEXT,
    fecha             TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE movimientos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo        TEXT NOT NULL CHECK (tipo IN ('pago', 'anticipo', 'pago_anulado', 'venta',
                                              'solicitud_aceptada', 'repuesto_usado', 'repuesto_devuelto')),
    descripcion TEXT NOT NULL,
    monto       REAL,
    cantidad    INTEGER,
    repuesto_id INTEGER REFERENCES repuestos(id) ON DELETE SET NULL,
    orden_id    INTEGER REFERENCES ordenes_servicio(id) ON DELETE SET NULL,
    usuario     TEXT,
    fecha       TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- El historial arranca con lo que ya había: pagos, repuestos usados y solicitudes aceptadas
INSERT INTO movimientos (tipo, descripcion, monto, orden_id, usuario, fecha)
SELECT tipo, CASE tipo WHEN 'anticipo' THEN 'Anticipo' ELSE 'Pago' END || ' del proyecto #' || orden_id,
       monto, orden_id, registrado_por, fecha
FROM pagos;

INSERT INTO movimientos (tipo, descripcion, cantidad, repuesto_id, orden_id, fecha)
SELECT 'repuesto_usado', r.nombre || ' × ' || d.cantidad || ' en el proyecto #' || d.orden_id,
       d.cantidad, d.repuesto_id, d.orden_id, o.fecha_ingreso || ' 08:00:00'
FROM detalle_orden d JOIN repuestos r ON r.id = d.repuesto_id JOIN ordenes_servicio o ON o.id = d.orden_id;

INSERT INTO movimientos (tipo, descripcion, cantidad, repuesto_id, orden_id, fecha)
SELECT 'solicitud_aceptada', 'Solicitud de ' || m.nombre || ': ' || r.nombre || ' × ' || p.cantidad
       || ' al proyecto #' || p.orden_id,
       p.cantidad, p.repuesto_id, p.orden_id, COALESCE(p.fecha_respuesta, p.fecha)
FROM peticiones p JOIN repuestos r ON r.id = p.repuesto_id JOIN mecanicos m ON m.id = p.mecanico_id
WHERE p.estado = 'enviada';

PRAGMA user_version = 6;
