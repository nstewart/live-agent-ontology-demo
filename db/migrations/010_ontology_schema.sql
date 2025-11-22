-- 010_ontology_schema.sql
-- Ontology schema for class and property definitions

-- Ontology Classes
-- Defines the types of entities in the knowledge graph
CREATE TABLE IF NOT EXISTS ontology_classes (
    id SERIAL PRIMARY KEY,
    class_name TEXT UNIQUE NOT NULL,      -- Human readable name: 'Customer', 'Order'
    prefix TEXT UNIQUE NOT NULL,           -- Subject ID prefix: 'customer', 'order'
    description TEXT,
    parent_class_id INT REFERENCES ontology_classes(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for parent class lookups (hierarchy)
CREATE INDEX IF NOT EXISTS idx_ontology_classes_parent ON ontology_classes(parent_class_id);

-- Ontology Properties
-- Defines the allowed properties/predicates for each class
CREATE TABLE IF NOT EXISTS ontology_properties (
    id SERIAL PRIMARY KEY,
    prop_name TEXT UNIQUE NOT NULL,        -- Property name: 'customer_name', 'order_status'
    domain_class_id INT NOT NULL REFERENCES ontology_classes(id) ON DELETE CASCADE,
    range_kind TEXT NOT NULL,              -- 'string', 'int', 'float', 'timestamp', 'date', 'bool', 'entity_ref'
    range_class_id INT REFERENCES ontology_classes(id) ON DELETE SET NULL,  -- For entity_ref types
    is_multi_valued BOOLEAN NOT NULL DEFAULT TRUE,
    is_required BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Ensure range_class_id is set when range_kind is 'entity_ref'
    CONSTRAINT chk_entity_ref_has_range CHECK (
        range_kind != 'entity_ref' OR range_class_id IS NOT NULL
    )
);

-- Indexes for property lookups
CREATE INDEX IF NOT EXISTS idx_ontology_properties_domain ON ontology_properties(domain_class_id);
CREATE INDEX IF NOT EXISTS idx_ontology_properties_range_class ON ontology_properties(range_class_id);

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ontology_classes_updated_at
    BEFORE UPDATE ON ontology_classes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER ontology_properties_updated_at
    BEFORE UPDATE ON ontology_properties
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert migration record
INSERT INTO schema_migrations (version) VALUES ('010_ontology_schema')
ON CONFLICT (version) DO NOTHING;
