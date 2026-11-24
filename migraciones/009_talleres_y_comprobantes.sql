-- Los talleres del edificio están en el mismo lugar: la dirección solo la llevan los de afuera.
-- Cada pago, anticipo y venta guarda su comprobante en PDF, y el historial apunta a él.

-- SQLite no permite quitar un NOT NULL: la tabla se crea de nuevo con los mismos datos.
-- (database.py desactiva las llaves foráneas mientras migra y las revisa al terminar.)
CREATE TABLE talleres_nueva (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre    TEXT NOT NULL UNIQUE,
    ubicacion TEXT NOT NULL DEFAULT 'edificio' CHECK (ubicacion IN ('edificio', 'externo')),
    direccion TEXT,  -- solo los talleres de afuera; los del edificio están todos en el mismo lugar
    telefono  TEXT,
    encargado TEXT,
    horario   TEXT,
    capacidad INTEGER CHECK (capacidad IS NULL OR capacidad > 0),  -- vehículos que caben a la vez
    activo    INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);
INSERT INTO talleres_nueva (id, nombre, ubicacion, direccion, telefono, encargado, horario, capacidad, activo)
    SELECT id, nombre, 'edificio', NULL, telefono, encargado, horario, capacidad, activo FROM talleres;
DROP TABLE talleres;
ALTER TABLE talleres_nueva RENAME TO talleres;
INSERT INTO talleres (nombre, ubicacion, direccion, telefono, encargado, horario) VALUES
('Rectificadora El Pistón', 'externo', 'Col. Miraflores, bulevar Suyapa, frente al parque', '2231-4455', 'Óscar Medina',
 'Lunes a viernes, 8:00 a. m. a 5:00 p. m.');

ALTER TABLE pagos ADD COLUMN pdf BLOB;
ALTER TABLE ventas ADD COLUMN pdf BLOB;
ALTER TABLE movimientos ADD COLUMN pago_id INTEGER REFERENCES pagos(id) ON DELETE SET NULL;
ALTER TABLE movimientos ADD COLUMN venta_id INTEGER REFERENCES ventas(id) ON DELETE SET NULL;

-- El historial que ya existía se une con su pago (misma orden, monto y fecha)
UPDATE movimientos SET pago_id = (
    SELECT p.id FROM pagos p
    WHERE p.orden_id = movimientos.orden_id AND p.monto = movimientos.monto AND p.fecha = movimientos.fecha
    ORDER BY p.id LIMIT 1
) WHERE tipo IN ('pago', 'anticipo');
UPDATE movimientos SET venta_id = (
    SELECT v.id FROM ventas v
    WHERE v.repuesto_id = movimientos.repuesto_id AND v.total = movimientos.monto AND v.fecha = movimientos.fecha
    ORDER BY v.id LIMIT 1
) WHERE tipo = 'venta';

PRAGMA user_version = 9;
