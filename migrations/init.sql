CREATE TABLE runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL, -- 'running', 'completed', 'failed'
    total_properties INT,
    error_message TEXT
);

CREATE TABLE properties (
    id SERIAL PRIMARY KEY,
    run_id INT REFERENCES runs(id),
    location VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,
    price INT NOT NULL,
    common_costs INT,
    total_price INT,
    total_area FLOAT,
    floor INT,
    total_floors INT,
    furnished BOOLEAN,
    has_gym BOOLEAN,
    original_url TEXT NOT NULL,
    google_maps_link TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE property_images (
    id SERIAL PRIMARY KEY,
    property_id INT REFERENCES properties(id),
    image_url TEXT NOT NULL
);

CREATE TABLE metro_stations (
    id SERIAL PRIMARY KEY,
    property_id INT REFERENCES properties(id),
    name VARCHAR(100) NOT NULL,
    walking_minutes INT NOT NULL,
    distance_meters INT NOT NULL
); 