// Layer 2 Inventory Neo4j constraints
// Run after loading InventoryLayer/neo4j CSV files if using LOAD CSV.
// For neo4j-admin database import, uniqueness is enforced by unique import IDs during import.

CREATE CONSTRAINT device_id_unique IF NOT EXISTS
FOR (n:Device) REQUIRE n.device_id IS UNIQUE;

CREATE CONSTRAINT installed_bios_import_id_unique IF NOT EXISTS
FOR (n:InstalledBIOS) REQUIRE n.import_id IS UNIQUE;

CREATE CONSTRAINT installed_firmware_import_id_unique IF NOT EXISTS
FOR (n:InstalledFirmware) REQUIRE n.import_id IS UNIQUE;

CREATE CONSTRAINT installed_os_import_id_unique IF NOT EXISTS
FOR (n:InstalledOS) REQUIRE n.import_id IS UNIQUE;

CREATE CONSTRAINT installed_driver_import_id_unique IF NOT EXISTS
FOR (n:InstalledDriver) REQUIRE n.import_id IS UNIQUE;

CREATE CONSTRAINT vendor_name_unique IF NOT EXISTS
FOR (n:Vendor) REQUIRE n.vendor_name IS UNIQUE;
