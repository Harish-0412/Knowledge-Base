# Relationship Guide

## Governed Model

Relationship Ontology `1.0.0` defines 20 approved predicates. Store only canonical source-to-target assertions. Virtual inverses are query conveniences and are not materialized. Every source and target must exist in the declared registry, and every record must satisfy schema, domain/range, evidence, condition, confidence, cycle, contradiction, and approval rules.

The examples below are the catalog's illustrative syntax, not production facts.

## Approved Relationship Types

### IS_A

Purpose: Source is a more specific kind or subtype of target. Direction: specific subtype to general type. Example: `Synthetic subtype IS_A Synthetic parent type`. Validation: same category; optional conditions; evidence recommended; minimum confidence `0.70`; cycles prohibited.

### PART_OF

Purpose: Source is a constituent component of target. Direction: component to containing whole. Example: `Synthetic component PART_OF Synthetic system`. Validation: conditions required for non-universal scope; evidence recommended; minimum confidence `0.75`; cycles prohibited.

### IMPLEMENTS

Purpose: Source concretely implements a specification, standard, interface, or abstraction represented by target. Direction: implementation to implemented abstraction. Example: `Synthetic component IMPLEMENTS Synthetic interface`. Validation: evidence required; conditions required for non-universal scope; minimum confidence `0.80`.

### USES

Purpose: Source directly uses target while performing its function. Direction: user to used resource or capability. Example: `Synthetic service USES Synthetic interface`. Validation: evidence required; conditions required for non-universal scope; minimum confidence `0.80`.

### INITIALIZES

Purpose: Source initializes target during startup, boot, or device activation. Direction: initializer to initialized entity. Example: `Synthetic startup component INITIALIZES Synthetic device`. Validation: evidence required; conditions required for non-universal scope; minimum confidence `0.80`.

### ENABLES

Purpose: Source makes a target capability possible or available. Direction: enabler to enabled capability. Example: `Synthetic mechanism ENABLES Synthetic capability`. Validation: evidence required; conditions required for non-universal scope; minimum confidence `0.80`.

### MANAGES

Purpose: Source administers, controls, or governs target's operational state. Direction: manager to managed entity. Example: `Synthetic controller MANAGES Synthetic endpoint`. Validation: governed Management source domain; evidence required; conditions required for non-universal scope; minimum confidence `0.80`.

### MONITORS

Purpose: Source observes or collects status, health, telemetry, or events from target. Direction: observer to observed entity. Example: `Synthetic observer MONITORS Synthetic endpoint`. Validation: evidence required; conditions required for non-universal scope; minimum confidence `0.80`.

### PROTECTS

Purpose: Source provides a security protection function for target. Direction: protection mechanism to protected entity. Example: `Synthetic control PROTECTS Synthetic resource`. Validation: governed Security source domain; evidence required; conditions required for non-universal scope; minimum confidence `0.80`.

### CONFIGURES

Purpose: Source changes or enforces configuration settings on target. Direction: configuration controller to configured entity. Example: `Synthetic policy controller CONFIGURES Synthetic endpoint`. Validation: evidence required; conditions required for non-universal scope; minimum confidence `0.80`.

### UPDATES

Purpose: Source delivers, applies, or manages an update to target. Direction: update provider to updated entity. Example: `Synthetic update service UPDATES Synthetic component`. Validation: evidence required; conditions required for non-universal scope; minimum confidence `0.80`.

### REQUIRES

Purpose: Target is mandatory for source under specified scope and conditions. Direction: requiring entity to mandatory prerequisite. Example: `Synthetic feature REQUIRES Synthetic prerequisite`. Validation: authoritative evidence required; conditions required for non-universal scope; minimum confidence `0.90`; cycles prohibited.

### DEPENDS_ON

Purpose: Source operationally depends on target without necessarily asserting a formal published requirement. Direction: dependent entity to operational dependency. Example: `Synthetic service DEPENDS_ON Synthetic runtime`. Validation: authoritative evidence required; conditions required for non-universal scope; minimum confidence `0.90`; cycles require review.

### RUNS_ON

Purpose: Source executes within or on target operating system or execution platform. Direction: executing software to execution host. Example: `Synthetic application RUNS_ON Synthetic platform`. Validation: target range is governed execution-host categories/types; evidence required; conditions required for non-universal scope; minimum confidence `0.80`.

### INSTALLED_ON

Purpose: Source is deployed or installed on target endpoint, operating system, or platform. Direction: installed artifact to installation host. Example: `Synthetic agent INSTALLED_ON Synthetic endpoint`. Validation: target range is governed installation-host categories/types; evidence required; conditions required for non-universal scope; minimum confidence `0.80`.

### REPLACES

Purpose: Source supersedes target as a successor technology or concept. Direction: successor to predecessor. Example: `Synthetic successor REPLACES Synthetic predecessor`. Validation: authoritative evidence required; conditions required for non-universal scope; minimum confidence `0.90`; reciprocal or cyclic replacement is prohibited.

### DEPRECATED_BY

Purpose: Source has been formally deprecated in favor of target. Direction: deprecated concept to preferred successor. Example: `Synthetic legacy feature DEPRECATED_BY Synthetic successor`. Validation: authoritative evidence required; conditions required for non-universal scope; minimum confidence `0.90`; cycles prohibited.

### SUPPORTS

Purpose: Source officially supports operation, integration, or use with target under defined conditions. Direction: supporting product or authority to supported entity. Example: `Synthetic vendor product SUPPORTS Synthetic platform under stated conditions`. Validation: authoritative evidence and structured conditions always required; minimum confidence `0.90`; contradictions require review or rejection.

### COMPATIBLE_WITH

Purpose: Source can operate with target under explicitly documented conditions. Direction: evaluated entity to compatible counterpart. Example: `Synthetic component COMPATIBLE_WITH Synthetic platform under stated test conditions`. Validation: authoritative evidence and structured conditions always required; minimum confidence `0.90`; conflicting assertions are prohibited. Store canonical direction only.

### CONFLICTS_WITH

Purpose: Source is documented to conflict or operate incorrectly with target under specified conditions. Direction: affected entity to conflicting counterpart. Example: `Synthetic component CONFLICTS_WITH Synthetic platform under stated conditions`. Validation: authoritative evidence and structured conditions always required; minimum confidence `0.90`; contradictory approved assertions are prohibited.

## Approval And Import

Candidate records are not production facts. Only records with `approval_status=approved`, human-consistent verification, required evidence, no validation errors or warnings, and a production validation PASS are eligible for import. `RELATED_TO`, fixtures, rejected records, deprecated records, and virtual inverse labels are not importable as approved semantic edges.
