-- Fecha límite en que el cliente quiere de vuelta su vehículo (opcional: «No especificó»).

ALTER TABLE ordenes_servicio ADD COLUMN fecha_limite TEXT;

PRAGMA user_version = 7;
