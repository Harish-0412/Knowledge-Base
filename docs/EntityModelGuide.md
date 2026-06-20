# Entity Model Guide

## Purpose

The Domain Knowledge Layer represents stable technology concepts used by compatibility and configuration-compliance reasoning. The governed entity source is `ontology/releases/v1.1-rc2/canonical_entity_registry.json`; descriptive knowledge remains in `Domain_layer/working/v1.1-rc2/`.

## Entity Structure

| Field | Meaning |
|---|---|
| `entity_id` | Immutable, globally unique identifier and cross-layer join key. |
| `name` | Human-readable name in Domain Layer source files. The registry publishes it as `canonical_name`. |
| `type` | Broad semantic class, such as `Driver`, `Firmware`, `OperatingSystem`, `SecurityComponent`, or `ManagementTool`. |
| `subtype` | More specific governed classification within the type. |
| `layer` | Architectural layer to which the entity belongs. |
| `aliases` | Alternate names that resolve to the same entity; aliases never create new identities. |
| `keywords` | Stored search and discovery terms from the Domain Layer source. Keywords are not entities or aliases unless separately governed. |
| `related_entities` | Source-authored reference values. Only validated canonical resolutions may become governed relationship candidates. |

Registry records also contain normalized names, knowledge category, source file, lifecycle status, concept scope, vendor, verification status, and provenance.

## ID Assignment

IDs use the established category namespace plus a zero-padded sequence, for example `DRV-001`, `FW-006`, `OS-010`, `SEC-001`, and `MGT-010`. Before assigning a new ID, enumerate every existing ID in that namespace and select the next unused value. IDs are never recycled, renumbered, or changed after release.

An ID prefix records assignment history, not necessarily the entity's current category. The approved namespace exceptions are therefore preserved: `FW-007` belongs to Management, `FW-011` belongs to Operating System, and `OS-010` belongs to Management.

## Aliases And Keywords

Aliases are normalized for exact lookup and must be non-empty and non-duplicative after normalization. A unique alias may resolve to one canonical entity; an ambiguous alias must not be resolved automatically. Fuzzy similarity alone is never sufficient for identity resolution.

Keywords support retrieval but do not assert identity or graph semantics. A capability, product feature, or vague phrase must not become an entity merely because it appears as a keyword.

## Categories

The current governed categories are Driver, Firmware, Management, Operating System, and Security. Category controls source organization and relationship domain/range validation. Type and subtype provide finer meaning; category alone does not prove compatibility or dependency.

## Current Examples

- `DRV-001` has canonical name `Graphics Driver`, type `Driver`, subtype `Graphics Driver`, and layer `Driver Layer`. Its aliases include `GPU Driver` and `Display Driver` in the registry.
- `FW-006` has canonical name `ACPI`, remains in Firmware under an approved Shared Platform modeling limitation, and retains its stable ID.
- `OS-010` has canonical name `Ubuntu Pro`, type `ManagementTool`, category Management, and retains its legacy OS namespace ID by governance decision.
- `MGT-009` and `MGT-010` are the approved Configuration Baseline and Endpoint Agent core entities introduced in RC2.

These examples describe stored entities only. They do not assert compatibility or production relationships.

## Change Control

Entity additions and modifications follow `ontology/governance/ontology_governance.json`. Released IDs and canonical names are immutable. Deprecation retains the original identity and requires traceable migration guidance.
