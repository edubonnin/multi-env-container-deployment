-- Inicialización de la base de datos para el entorno de desarrollo
-- Crea la estructura necesaria y carga datos de ejemplo

CREATE TABLE IF NOT EXISTS health_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP,
    status VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS cars (
    id SERIAL PRIMARY KEY,
    brand VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    year INTEGER NOT NULL CHECK (year >= 1886),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_cars_brand_model_year
    ON cars (brand, model, year);

INSERT INTO cars (brand, model, year)
VALUES
    ('Toyota', 'Corolla', 2020),
    ('Ford', 'Mustang', 1969),
    ('Tesla', 'Model 3', 2023),
    ('Volkswagen', 'Golf', 2018),
    ('Renault', 'Clio', 2019)
ON CONFLICT (brand, model, year) DO NOTHING;
