// ============================================================================
// ENDPOINT KNOWLEDGE BASE ONTOLOGY DESIGN SCHEMA
// ============================================================================
// This schema file explains the ontology structure for the Endpoint Knowledge Base (endpoint-kb).
// It maps the structural relationships between hardware elements, software agents, security policies, 
// and management layers on endpoints.

// ----------------------------------------------------------------------------
// 1. NODE TYPES (LABELS)
// ----------------------------------------------------------------------------
// - Device: A physical or virtual computing endpoint.
// - Hardware: Physical hardware components (e.g., CPU, Motherboard, TPM chip).
// - Firmware: Low-level software/code embedded directly in hardware (e.g., UEFI, BIOS).
// - OperatingSystem: Core operating system software (e.g., Windows 11, Linux Kernel).
// - Driver: Kernel/user mode drivers facilitating hardware-OS interaction.
// - SecurityComponent: Active endpoint security mechanisms (e.g., Antivirus engine, EDR engine, Firewall).
// - Agent: Lightweight client application or service running on the host (e.g., telemetry agent, backup agent).
// - ManagementTool: Tools used to configure/control endpoints (e.g., SCCM, MDM, Group Policy).
// - Vendor: The manufacturer or software publisher (e.g., Intel, Microsoft, CrowdStrike).
// - Document: Standard documents, configurations, specifications, or reference guides.
// - Rule: Defined security rules, policies, or signatures (e.g., YARA rule, registry hardening rule).

// ----------------------------------------------------------------------------
// 2. RELATIONSHIP TYPES
// ----------------------------------------------------------------------------
// - INSTALLED_ON: Used to map which components (OperatingSystem, Agent, SecurityComponent, Driver) live on which Device.
//     (:Agent) -[:INSTALLED_ON]-> (:Device)
//
// - RUNS_ON: Maps dependencies to the execution environment (e.g., Software runs on OS, OS runs on Hardware).
//     (:OperatingSystem) -[:RUNS_ON]-> (:Hardware)
//     (:Driver) -[:RUNS_ON]-> (:OperatingSystem)
//
// - REQUIRES: Strict functional requirement dependencies between components.
//     (:SecurityComponent) -[:REQUIRES]-> (:Firmware) (e.g., EDR requiring Secure Boot)
//
// - DEPENDS_ON: Generic dependencies between software agents or services.
//     (:Agent) -[:DEPENDS_ON]-> (:Driver)
//
// - SUPPORTS: Optional support relationship.
//     (:Firmware) -[:SUPPORTS]-> (:OperatingSystem)
//
// - INITIALIZES: Start/boot path initialization.
//     (:Firmware) -[:INITIALIZES]-> (:OperatingSystem)
//
// - ENABLES: Setting up/turning on capability.
//     (:Driver) -[:ENABLES]-> (:Hardware)
//
// - MANAGES: Control plane relationship.
//     (:ManagementTool) -[:MANAGES]-> (:Device)
//
// - UPDATES: Component update pipeline.
//     (:Agent) -[:UPDATES]-> (:Firmware)
//
// - PROVIDED_BY: Link back to the responsible builder/entity.
//     (:Hardware) -[:PROVIDED_BY]-> (:Vendor)
//
// - REPLACED_BY: Versioning or migration path.
//     (:Firmware) -[:REPLACED_BY]-> (:Firmware)
//
// - CONFLICTS_WITH: Incompatibility relationships.
//     (:SecurityComponent) -[:CONFLICTS_WITH]-> (:SecurityComponent)

// ----------------------------------------------------------------------------
// 3. SAMPLE CYPHER SCHEMA REPRESENTATION
// ----------------------------------------------------------------------------
/*
   (Vendor) <---[:PROVIDED_BY]--- (Hardware) <---[:RUNS_ON]--- (OperatingSystem) <---[:INSTALLED_ON]--- (Device)
                                                                    ^
                                                                    | [:RUNS_ON]
                                                                 (Driver) <---[:DEPENDS_ON]--- (Agent)
*/
