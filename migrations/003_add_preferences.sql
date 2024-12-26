CREATE TABLE property_preferences (
    id SERIAL PRIMARY KEY,
    property_url TEXT NOT NULL,
    status VARCHAR(10) NOT NULL CHECK (status IN ('liked', 'disliked')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(property_url)
);

-- Add index for faster lookups
CREATE INDEX idx_property_preferences_url ON property_preferences(property_url); 