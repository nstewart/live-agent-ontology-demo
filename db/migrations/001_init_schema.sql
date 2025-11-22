-- 001_init_schema.sql
-- Base schema initialization for FreshMart Digital Twin

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schema version tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Insert this migration
INSERT INTO schema_migrations (version) VALUES ('001_init_schema')
ON CONFLICT (version) DO NOTHING;
