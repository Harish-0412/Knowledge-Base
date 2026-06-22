# NORMALIZATION — Rules and Inventory

Normalization is the bridge between human/LLM text and machine-executable compliance logic.

## Why Normalize?

Documents and inventories may use different names for the same concept:

```text
BIOS / System BIOS / Dell BIOS
VMware ESXi 5.1.x / ESXi 5.1 / VMware vSphere Hypervisor 5.1
Intel(R) Xeon(R) CPU E5-2400 v2 / Intel Xeon E5-2400 V2 family
```

Without normalization, rules and devices will not match reliably.

## Normalization Happens At Three Points

1. After LLM rule extraction.
2. After human edits/approval.
3. During inventory ingestion.

## Component Alias Map

```json
{
  "BIOS": "bios",
  "System BIOS": "bios",
  "Operating System": "os",
  "OS": "os",
  "Host Bus Adapter": "hba",
  "HBA": "hba",
  "RAID Controller": "raid_controller",
  "Security Agent": "agent"
}
```

## Operator Normalization

```json
{
  "or later": ">=",
  "minimum": ">=",
  "at least": ">=",
  "not earlier than": ">=",
  "earlier than": "<",
  "below": "<",
  "older than": "<",
  "not supported": "not_in",
  "incompatible": "not_in"
}
```

## Version Normalization Examples

| Raw | Normalized | Scheme |
|---|---|---|
| `02.00.21` | `2.0.21` | semantic |
| `v2.0.21` | `2.0.21` | semantic |
| `5.1.x` | `5.1.x` | wildcard |
| `Windows Server 2012 R2` | `windows_server_2012_r2` | named_release |
| `A12` | `12` | vendor_letter_numeric |

## LLM Use in Normalization

LLM is not used by default. Use it only for:

- invalid JSON repair
- ambiguous component family mapping
- low-confidence normalization suggestion

All suggestions must still pass deterministic validation and human review.
