CREATE CONSTRAINT entity_id_unique IF NOT EXISTS FOR (n:Entity) REQUIRE n.entity_id IS UNIQUE;
CREATE INDEX entity_name IF NOT EXISTS FOR (n:Entity) ON (n.name);
CREATE INDEX entity_normalized_name IF NOT EXISTS FOR (n:Entity) ON (n.normalized_name);
CREATE INDEX operating_system_name IF NOT EXISTS FOR (n:OperatingSystem) ON (n.name);
CREATE INDEX security_component_name IF NOT EXISTS FOR (n:SecurityComponent) ON (n.name);
