-- 020_triples_schema.sql
-- Triple store schema for knowledge graph data

-- Triples Table
-- Generic subject-predicate-object triples with type information
CREATE TABLE IF NOT EXISTS triples (
    id BIGSERIAL PRIMARY KEY,
    subject_id TEXT NOT NULL,              -- Format: 'prefix:id', e.g., 'customer:123', 'order:FM-1001'
    predicate TEXT NOT NULL,               -- Property name from ontology_properties
    object_value TEXT NOT NULL,            -- The value (literal or entity reference)
    object_type TEXT NOT NULL,             -- 'string', 'int', 'float', 'timestamp', 'date', 'bool', 'entity_ref'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Prevent duplicate triples (same subject-predicate-object)
    CONSTRAINT uq_triple UNIQUE (subject_id, predicate, object_value)
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_triples_subject ON triples(subject_id);
CREATE INDEX IF NOT EXISTS idx_triples_predicate ON triples(predicate);
CREATE INDEX IF NOT EXISTS idx_triples_subject_predicate ON triples(subject_id, predicate);
CREATE INDEX IF NOT EXISTS idx_triples_object_value ON triples(object_value) WHERE object_type = 'entity_ref';
CREATE INDEX IF NOT EXISTS idx_triples_updated_at ON triples(updated_at);

-- Update timestamp trigger
CREATE TRIGGER triples_updated_at
    BEFORE UPDATE ON triples
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Helper view: Map subjects to their classes based on prefix
CREATE OR REPLACE VIEW subject_classes AS
SELECT DISTINCT
    t.subject_id,
    oc.class_name,
    oc.id AS class_id
FROM triples t
JOIN ontology_classes oc
    ON split_part(t.subject_id, ':', 1) = oc.prefix;

-- Insert migration record
INSERT INTO schema_migrations (version) VALUES ('020_triples_schema')
ON CONFLICT (version) DO NOTHING;
