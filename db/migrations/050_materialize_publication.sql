-- Create publication for Materialize to subscribe to
-- This enables logical replication of the triples table

-- Create publication for Materialize source
CREATE PUBLICATION IF NOT EXISTS mz_source FOR TABLE triples;

-- Ensure wal_level is set to logical (requires PostgreSQL restart if changed)
-- ALTER SYSTEM SET wal_level = 'logical';
