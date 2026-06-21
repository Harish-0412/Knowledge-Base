// ============================================================================
// UNIQUE CONSTRAINTS
// ============================================================================
// Ensure entity_id is globally unique per node label.
// Note: If you choose to apply a secondary label (e.g., :Entity) to all nodes,
// a single constraint on :Entity(entity_id) can be used.

CREATE CONSTRAINT hardware_id_unique IF NOT EXISTS FOR (n:Hardware) REQUIRE n.entity_id IS UNIQUE;
CREATE CONSTRAINT firmware_id_unique IF NOT EXISTS FOR (n:Firmware) REQUIRE n.entity_id IS UNIQUE;
CREATE CONSTRAINT operating_system_id_unique IF NOT EXISTS FOR (n:OperatingSystem) REQUIRE n.entity_id IS UNIQUE;
CREATE CONSTRAINT driver_id_unique IF NOT EXISTS FOR (n:Driver) REQUIRE n.entity_id IS UNIQUE;
CREATE CONSTRAINT security_component_id_unique IF NOT EXISTS FOR (n:SecurityComponent) REQUIRE n.entity_id IS UNIQUE;
CREATE CONSTRAINT agent_id_unique IF NOT EXISTS FOR (n:Agent) REQUIRE n.entity_id IS UNIQUE;
CREATE CONSTRAINT management_tool_id_unique IF NOT EXISTS FOR (n:ManagementTool) REQUIRE n.entity_id IS UNIQUE;
CREATE CONSTRAINT vendor_id_unique IF NOT EXISTS FOR (n:Vendor) REQUIRE n.entity_id IS UNIQUE;
CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (n:Document) REQUIRE n.entity_id IS UNIQUE;
CREATE CONSTRAINT rule_id_unique IF NOT EXISTS FOR (n:Rule) REQUIRE n.entity_id IS UNIQUE;
CREATE CONSTRAINT device_id_unique IF NOT EXISTS FOR (n:Device) REQUIRE n.entity_id IS UNIQUE;


// ============================================================================
// INDEXES
// ============================================================================
// Create indexes on 'name' and 'layer' properties for lookup performance.
// Since 'type' in this ontology represents the node label, the label itself acts
// as a natural index structure, but if 'type' is also stored as a property,
// additional indexes can be added.

// Hardware Indexes
CREATE INDEX hardware_name_idx IF NOT EXISTS FOR (n:Hardware) ON (n.name);
CREATE INDEX hardware_layer_idx IF NOT EXISTS FOR (n:Hardware) ON (n.layer);

// Firmware Indexes
CREATE INDEX firmware_name_idx IF NOT EXISTS FOR (n:Firmware) ON (n.name);
CREATE INDEX firmware_layer_idx IF NOT EXISTS FOR (n:Firmware) ON (n.layer);

// OperatingSystem Indexes
CREATE INDEX operating_system_name_idx IF NOT EXISTS FOR (n:OperatingSystem) ON (n.name);
CREATE INDEX operating_system_layer_idx IF NOT EXISTS FOR (n:OperatingSystem) ON (n.layer);

// Driver Indexes
CREATE INDEX driver_name_idx IF NOT EXISTS FOR (n:Driver) ON (n.name);
CREATE INDEX driver_layer_idx IF NOT EXISTS FOR (n:Driver) ON (n.layer);

// SecurityComponent Indexes
CREATE INDEX security_component_name_idx IF NOT EXISTS FOR (n:SecurityComponent) ON (n.name);
CREATE INDEX security_component_layer_idx IF NOT EXISTS FOR (n:SecurityComponent) ON (n.layer);

// Agent Indexes
CREATE INDEX agent_name_idx IF NOT EXISTS FOR (n:Agent) ON (n.name);
CREATE INDEX agent_layer_idx IF NOT EXISTS FOR (n:Agent) ON (n.layer);

// ManagementTool Indexes
CREATE INDEX management_tool_name_idx IF NOT EXISTS FOR (n:ManagementTool) ON (n.name);
CREATE INDEX management_tool_layer_idx IF NOT EXISTS FOR (n:ManagementTool) ON (n.layer);

// Vendor Indexes
CREATE INDEX vendor_name_idx IF NOT EXISTS FOR (n:Vendor) ON (n.name);
CREATE INDEX vendor_layer_idx IF NOT EXISTS FOR (n:Vendor) ON (n.layer);

// Document Indexes
CREATE INDEX document_name_idx IF NOT EXISTS FOR (n:Document) ON (n.name);
CREATE INDEX document_layer_idx IF NOT EXISTS FOR (n:Document) ON (n.layer);

// Rule Indexes
CREATE INDEX rule_name_idx IF NOT EXISTS FOR (n:Rule) ON (n.name);
CREATE INDEX rule_layer_idx IF NOT EXISTS FOR (n:Rule) ON (n.layer);

// Device Indexes
CREATE INDEX device_name_idx IF NOT EXISTS FOR (n:Device) ON (n.name);
CREATE INDEX device_layer_idx IF NOT EXISTS FOR (n:Device) ON (n.layer);
