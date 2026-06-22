# MOCK_DATA_GUIDE — 200-Device Inventory

## Goal

Create realistic mock inventory that demonstrates compatibility, warnings, critical violations, unknown data, and rollout-readiness failures.

## Dataset Size

- 200 devices total
- 120 compliant
- 35 warning
- 30 critical
- 10 blocked
- 5 unknown/missing data
- At least 28 not rollout-ready for operational reasons

## Device Mix

| Type | Count |
|---|---:|
| Dell PowerEdge R420 servers | 70 |
| Dell PowerEdge R730 servers | 40 |
| Dell Latitude laptops | 50 |
| Lenovo ThinkPad laptops | 25 |
| HP workstations | 15 |

## Required Component Types

Each device should have most of these:

```text
bios
cpu
os
firmware
driver
agent
hba or raid_controller for servers
network_adapter
storage_controller
tpm for laptops/workstations
```

## Realistic Scenarios to Include

### Scenario 1: BIOS too old
CPU or OS requires a newer BIOS.

### Scenario 2: Compound known issue
OS + HBA + CPU combination requires a newer BIOS.

### Scenario 3: Firmware-agent dependency
Agent 5.x requires firmware >= 6.0.

### Scenario 4: Driver incompatible with firmware
Network driver 1.8.0 is incompatible with NIC firmware < 6.0.

### Scenario 5: Missing data
Device has unknown BIOS or missing HBA firmware.

### Scenario 6: Operational readiness failure
Device is compatible but blocked because it is offline, has pending reboot, low disk, low battery, or unhealthy agent.

## Example Device

```json
{
  "device_id": "DEV-000015",
  "inventory_snapshot_id": "INV-000001",
  "hostname": "prod-r420-015",
  "serial_number": "SN-R420-0015",
  "asset_tag": "ASSET-0015",
  "device_type": "server",
  "manufacturer": "Dell",
  "model": "PowerEdge R420",
  "model_normalized": "dell_poweredge_r420",
  "department": "Infrastructure",
  "location": "DC-Rack-05",
  "owner_team": "Platform SRE",
  "environment": "production",
  "lifecycle_status": "active",
  "last_seen_at": "2026-06-19T09:30:00Z",
  "components": [
    {
      "component_instance_id": "COMP-000101",
      "device_id": "DEV-000015",
      "component_type": "bios",
      "component_name": "System BIOS",
      "vendor": "Dell",
      "version_raw": "02.00.21",
      "version_normalized": "2.0.21",
      "version_scheme": "semantic",
      "status": "installed"
    }
  ],
  "readiness": {
    "agent_health": "healthy",
    "pending_reboot": false,
    "disk_free_gb": 64,
    "battery_percent": null,
    "ac_power_connected": true,
    "bitlocker_suspended": true,
    "maintenance_window_available": true,
    "network_reachable": true,
    "last_seen_within_hours": 2
  },
  "metadata": {}
}
```
