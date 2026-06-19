# Knowledge Base Question and Answer Guide

## Current Knowledge Base

The QA script reads only these local sources:

- Registry: `ontology/releases/v1.1-rc2/canonical_entity_registry.json`
- Entity details: `Domain_layer/working/v1.1/*.json`
- Registry version: `1.1.0-rc2`
- Entity count: 54

The script does not call an LLM, use internet search, load example answers, or generate technical facts. Entity matching uses only an exact normalized canonical name or exact normalized alias. It does not use fuzzy or substring matching.

## Running Questions

Ask one question from PowerShell:

```powershell
python scripts/kb_question_answer.py --question "What is BIOS?"
```

Start an interactive session:

```powershell
python scripts/kb_question_answer.py --interactive
```

The output is JSON in single-question mode. The `answer`, `matched_entity_id`, `source_file`, and `evidence_fields` values show what was retrieved and where it came from.

## Supported Questions

### 1. Entity Definition

Templates:

- `What is <canonical name>?`
- `Define <canonical name>`
- `Explain <canonical name>`

Verified example:

```text
Question: What is Configuration Baseline?
Answer: Configuration Baseline: Documented and approved collection of configuration settings that represents the desired state for managed endpoints.
Entity: MGT-009
Source: management.json, fields canonical_name and description
```

### 2. Purpose

Template:

- `What is the purpose of <canonical name>?`

Verified example:

```text
Question: What is the purpose of Endpoint Agent?
Answer: Endpoint Agent purpose: Provide an endpoint-resident communication and execution component for approved management or security operations.
Entity: MGT-010
Source: management.json, field purpose
```

### 3. Layer Classification

Template:

- `Which layer contains <canonical name>?`

Verified example:

```text
Question: Which layer contains Secure Boot?
Answer: Secure Boot is in the Security Layer.
Entity: SEC-002
Source: security.json, registry field layer
```

### 4. Type and Subtype

Template:

- `What type of entity is <canonical name>?`

Verified example:

```text
Question: What type of entity is Linux Kernel?
Answer: Linux Kernel has type 'OperatingSystem' and subtype 'Kernel'.
Entity: OS-008
Source: operating_system.json, registry fields type and subtype
```

### 5. Alias Lookup

Templates:

- `What does <alias> refer to?`
- `What does <alias> stand for?`

Verified example:

```text
Question: What does Basic Input/Output System refer to?
Answer: Basic Input/Output System refers to BIOS. Other aliases include: Basic Input/Output System, Legacy BIOS, PC BIOS, ROM BIOS, System BIOS, Traditional BIOS.
Entity: FW-001
Source: firmware.json, registry fields aliases and canonical_name
```

### 6. Keyword Lookup

Template:

- `Which entities relate to <exact stored keyword>?`

Verified example:

```text
Question: Which entities relate to measured boot?
Answer: UEFI
Entity IDs: FW-002
Source: firmware.json, field keywords
```

Keyword matching is exact after case and whitespace normalization. A concept appearing in a description but not in `keywords` is not treated as a keyword match.

### 7. Related Concepts

Template:

- `Which concepts are related to <canonical name>?`

Verified example:

```text
Question: Which concepts are related to UEFI?
Answer: Related concepts for UEFI: BIOS, Secure Boot, TPM, GPT, EFI System Partition, OS Bootloader, Measured Boot, ACPI, SMBIOS, Embedded Controller Firmware, Firmware Update Utility, CSM
Entity: FW-002
Source: firmware.json, field related_entities
```

These are stored provisional related-concept values. They do not imply semantic relationships such as `SUPPORTS`, `REQUIRES`, or `DEPENDS_ON`.

### 8. Cross-Domain Firmware-to-Security Lookup

Supported question:

- `Which security concepts are referenced by firmware entities?`

Verified result:

```text
Answer: BitLocker, Secure Boot, TPM
Source: Firmware related_entities resolved to registry entities whose knowledge_category is Security
```

### 9. Unsupported Compatibility Questions

Examples:

- `Does BIOS support Windows 11?`
- `Is Driver Signing compatible with Linux?`
- `Does UEFI require TPM?`

Expected response:

```text
Status: unsupported_by_current_kb
Answer: Compatibility relationships are not explicitly stored in the current knowledge base.
Confidence: 0.0
```

The script must not infer compatibility from descriptions, keywords, or `related_entities`.

### 10. Unknown Entities

Example:

- `What is EntityThatDoesNotExist?`

Expected response:

```text
Status: not_found
Matched entity: null
Confidence: 0.0
```

The script does not construct a definition for an unknown entity.

## Response Fields

| Field | Meaning |
|---|---|
| `answer_status` | `answered`, `not_found`, `ambiguous`, or `unsupported_by_current_kb` |
| `answer` | Text assembled only from the cited KB fields, or a refusal/not-found message |
| `matched_entity_id` | Stable entity ID when one entity was retrieved |
| `canonical_name` | Canonical registry name |
| `source_file` | Domain Layer JSON file containing the entity details |
| `evidence_fields` | Exact KB fields used to build the answer |
| `confidence` | `1.0` for an exact supported retrieval and `0.0` for no answer |
| `candidate_entity_ids` | IDs returned by collection queries or ambiguous identity lookup |

## Entity Inventory

### Firmware (12)

ACPI, BIOS, EFI System Partition, Embedded Controller Firmware, Firmware Update Utility, GPT, Measured Boot, Network Firmware, OS Bootloader, PXE Boot, Storage Firmware, UEFI.

### Operating System (12)

Debian, Linux, Linux Kernel, RHEL, Ubuntu, Ubuntu Pro, Windows, Windows 10, Windows 11, Windows NT Kernel, XNU Kernel, macOS.

### Driver (8)

Audio Driver, Chipset Driver, Driver Signing, Graphics Driver, NDIS, Network Driver, Storage Driver, WDDM.

### Security (12)

Antivirus, AppArmor, BitLocker, EDR Agent, FileVault, Gatekeeper, LUKS, SELinux, Secure Boot, Secure Enclave, System Integrity Protection, TPM.

### Management (10)

Active Directory, Configuration Baseline, Endpoint Agent, Endpoint Manager, Group Policy, Monitoring Agent, Patch Manager, SIEM, WSUS, Windows Update.

## Grounding and Safety Rules

1. Use a canonical entity name or a stored alias.
2. Treat `not_found` as no KB answer; do not ask the script to guess.
3. Treat `unsupported_by_current_kb` as a hard refusal, especially for compatibility or semantic relationship questions.
4. Check `matched_entity_id`, `source_file`, and `evidence_fields` with every answer.
5. A retrieved answer is faithful to the current KB, but entities marked `verification_status: review_required` are not yet externally source-verified.
6. `related_entities` is provisional and must not be interpreted as a specific technical relationship.

## Verifying the QA System

Run the retrieval-only QA tests:

```powershell
python -m unittest tests.test_kb_question_answer -v
```

Run the complete repository suite:

```powershell
python -m unittest discover -s tests -v
```

The QA suite dynamically derives expected answers from RC2 and the Domain Layer. It does not contain a mock-answer fixture. It checks all 54 definitions, all 54 purposes, all layers and types, 186 unique aliases, all 54 related-concept lists, keyword lookup, cross-domain lookup, compatibility refusal, and unknown-entity refusal.
