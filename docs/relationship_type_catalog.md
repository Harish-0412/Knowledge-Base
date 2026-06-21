# Relationship Type Catalog v1.0

## Purpose and Boundaries

This catalog defines the controlled meaning of the 20 Relationship Ontology v1.0 predicates. It does not create relationship instances, define domain/range rules, convert `RELATED_TO` staging edges, or assert that any real entities are related.

Every example below is illustrative synthetic data, not a verified production fact. Canonical edges are stored only from source to target. Virtual inverse labels support query and display language; they are not stored predicates and must not be materialized as duplicate edges.

`RELATED_TO` is excluded because it is a provisional staging edge without approved semantic meaning. Only `IS_A` is transitive in v1.0. No other predicate is transitively inferred because multi-hop structural, functional, dependency, lifecycle, and compatibility reasoning can produce unsafe claims. Compatibility predicates are not symmetric: claims can be directional, versioned, platform-specific, vendor-specific, and conditioned differently in each direction.

High-risk predicates require authoritative evidence because requirements, dependencies, lifecycle status, support, compatibility, and conflicts can affect operational decisions. Domain/range restrictions will be defined in the later `relationship_rules.json`; this catalog intentionally defines meaning without constraining entity types.

## Predicate Selection

| Intent | Correct predicate | Avoid |
|---|---|---|
| A is a subtype of B | `IS_A` | `PART_OF` |
| A is a component of B | `PART_OF` | `IS_A` |
| A realizes an interface or specification B | `IMPLEMENTS` | `USES` |
| A directly consumes B | `USES` | `DEPENDS_ON` without dependency evidence |
| A starts or activates B | `INITIALIZES` | `MANAGES` |
| A makes capability B available | `ENABLES` | `REQUIRES` |
| A controls B's operational state | `MANAGES` | `MONITORS` |
| A observes B | `MONITORS` | `MANAGES` |
| A provides security protection for B | `PROTECTS` | a generic security association |
| A changes B's settings | `CONFIGURES` | `UPDATES` |
| A applies an update to B | `UPDATES` | `CONFIGURES` |
| B is mandatory for A | `REQUIRES` | `ENABLES` or `USES` |
| A has an operational dependency on B | `DEPENDS_ON` | `USES` |
| A executes on B | `RUNS_ON` | `INSTALLED_ON` |
| A is deployed on B | `INSTALLED_ON` | `RUNS_ON` |
| A supersedes predecessor B | `REPLACES` | `DEPRECATED_BY` |
| A is formally deprecated in favour of B | `DEPRECATED_BY` | `REPLACES` |
| A officially supports B | `SUPPORTS` | inferred `COMPATIBLE_WITH` |
| A can operate with B under documented conditions | `COMPATIBLE_WITH` | `SUPPORTS` without official commitment |
| A is documented to malfunction with B | `CONFLICTS_WITH` | unsupported suspicion |

## Taxonomic

### IS_A

- **Display/category:** Is A; Taxonomic
- **Meaning:** The source is a more specific kind or subtype of the target.
- **Roles/inverse:** specific subtype -> general type; virtual inverse `HAS_SUBTYPE`.
- **Policies:** low risk; evidence recommended; conditions optional; minimum confidence 0.70.
- **Behavior:** transitive; not symmetric; not reflexive; inverse not materialized.
- **Correct illustration:** `Synthetic subtype IS_A Synthetic parent type`.
- **Incorrect illustration:** `Synthetic component IS_A Synthetic system` when the component is a part, not a subtype.
- **Choose it when:** classification is the intent. Choose `PART_OF` for composition.

## Structural

### IMPLEMENTS

- **Display/category:** Implements; Structural
- **Meaning:** The source concretely realizes the specification, standard, interface, or abstract capability represented by the target.
- **Roles/inverse:** concrete implementation -> implemented specification or abstraction; `IMPLEMENTED_BY`.
- **Policies:** medium risk; evidence required; conditions required when non-universal; minimum confidence 0.80.
- **Behavior:** non-transitive, non-symmetric, non-reflexive; inverse virtual only.
- **Correct illustration:** `Synthetic component IMPLEMENTS Synthetic interface`.
- **Incorrect illustration:** using `IMPLEMENTS` because two concepts have similar descriptions.
- **Choose it when:** realization of an abstraction is documented; use `USES` when the source only consumes the target.

### PART_OF

- **Display/category:** Part Of; Structural
- **Meaning:** The source is a direct constituent component or structural part of the target.
- **Roles/inverse:** component -> containing whole; `HAS_PART`.
- **Policies:** low risk; evidence recommended; conditions required when non-universal; minimum confidence 0.75.
- **Behavior:** deliberately non-transitive in v1.0; non-symmetric and non-reflexive; inverse virtual only.
- **Correct illustration:** `Synthetic component PART_OF Synthetic system`.
- **Incorrect illustration:** inferring that a nested subcomponent is automatically part of every ancestor.
- **Choose it when:** direct composition is intended; use `IS_A` for subtype classification.

### USES

- **Display/category:** Uses; Structural
- **Meaning:** The source directly consumes the target while performing its function.
- **Roles/inverse:** user -> used resource or capability; `USED_BY`.
- **Policies:** medium risk; evidence required; conditions required when non-universal; minimum confidence 0.80.
- **Behavior:** non-transitive, non-symmetric and non-reflexive; inverse virtual only.
- **Correct illustration:** `Synthetic service USES Synthetic interface`.
- **Incorrect illustration:** using `USES` for optional background context with no direct consumption.
- **Choose it when:** direct use is known but mandatory dependency is not; use `DEPENDS_ON` when operation relies on the target.

## Functional

All functional predicates are medium risk, require evidence, have minimum confidence 0.80, and require conditions for non-universal assertions. They are non-transitive, non-symmetric and non-reflexive.

### CONFIGURES

- **Display/category/policies:** Configures; Functional; medium risk; evidence required; conditions required when non-universal; minimum confidence 0.80; non-transitive and non-symmetric.
- **Meaning/roles/inverse:** The source changes or enforces settings on the target; configuration controller -> configured entity; `CONFIGURED_BY`.
- **Correct illustration:** `Synthetic policy controller CONFIGURES Synthetic endpoint`.
- **Incorrect illustration:** using it for installation, patch delivery, passive observation, or generic administration.
- **Choose it over:** `UPDATES` when settings, rather than software or content versions, are changed.

### ENABLES

- **Display/category/policies:** Enables; Functional; medium risk; evidence required; conditions required when non-universal; minimum confidence 0.80; non-transitive and non-symmetric.
- **Meaning/roles/inverse:** The source makes the target capability possible or available; enabler -> enabled capability; `ENABLED_BY`.
- **Correct illustration:** `Synthetic mechanism ENABLES Synthetic capability`.
- **Incorrect illustration:** using it when the target is mandatory for the source.
- **Choose it over:** `REQUIRES` when the direction is enabler-to-capability rather than requiring-entity-to-prerequisite.

### INITIALIZES

- **Display/category/policies:** Initializes; Functional; medium risk; evidence required; conditions required when non-universal; minimum confidence 0.80; non-transitive and non-symmetric.
- **Meaning/roles/inverse:** The source initializes the target during startup, boot, or activation; initializer -> initialized entity; `INITIALIZED_BY`.
- **Correct illustration:** `Synthetic startup component INITIALIZES Synthetic device`.
- **Incorrect illustration:** describing ongoing administration after startup.
- **Choose it over:** `MANAGES` when the asserted action is specifically initialization.

### MANAGES

- **Display/category/policies:** Manages; Functional; medium risk; evidence required; conditions required when non-universal; minimum confidence 0.80; non-transitive and non-symmetric.
- **Meaning/roles/inverse:** The source administers, controls, or governs the target's operational state; manager -> managed entity; `MANAGED_BY`.
- **Correct illustration:** `Synthetic controller MANAGES Synthetic endpoint`.
- **Incorrect illustration:** describing telemetry collection without control.
- **Choose it over:** `MONITORS` only when active control or governance is evidenced.

### MONITORS

- **Display/category/policies:** Monitors; Functional; medium risk; evidence required; conditions required when non-universal; minimum confidence 0.80; non-transitive and non-symmetric.
- **Meaning/roles/inverse:** The source observes or collects status, health, telemetry, or events from the target; observer -> observed entity; `MONITORED_BY`.
- **Correct illustration:** `Synthetic observer MONITORS Synthetic endpoint`.
- **Incorrect illustration:** describing configuration changes or operational control.
- **Choose it over:** `MANAGES` for passive observation and data collection.

### PROTECTS

- **Display/category/policies:** Protects; Functional; medium risk; evidence required; conditions required when non-universal; minimum confidence 0.80; non-transitive and non-symmetric.
- **Meaning/roles/inverse:** The source provides a security protection function for the target; protection mechanism -> protected entity; `PROTECTED_BY`.
- **Correct illustration:** `Synthetic control PROTECTS Synthetic resource`.
- **Incorrect illustration:** linking any security concept to an entity without a documented protection function.
- **Choose it when:** a specific protective function and target are evidenced, not merely associated.

### UPDATES

- **Display/category/policies:** Updates; Functional; medium risk; evidence required; conditions required when non-universal; minimum confidence 0.80; non-transitive and non-symmetric.
- **Meaning/roles/inverse:** The source delivers, applies, or orchestrates an update to the target; update provider -> updated entity; `UPDATED_BY`.
- **Correct illustration:** `Synthetic update service UPDATES Synthetic component`.
- **Incorrect illustration:** describing generic management or a settings-only change.
- **Choose it over:** `CONFIGURES` when update delivery or application is the asserted action.

## Dependency

### DEPENDS_ON

- **Display/category:** Depends On; Dependency
- **Meaning:** The source operationally relies on the target without necessarily having a formally published mandatory requirement.
- **Roles/inverse:** dependent entity -> operational dependency; `DEPENDENCY_OF`.
- **Policies:** high risk; authoritative evidence required; conditions required when non-universal; minimum confidence 0.90.
- **Behavior:** non-transitive, non-symmetric, non-reflexive; inverse virtual only.
- **Correct illustration:** `Synthetic service DEPENDS_ON Synthetic runtime`.
- **Incorrect illustration:** inferring a dependency because the source merely uses the target, or propagating dependency through a chain.
- **Choose it over:** `USES` when operation relies on the target; choose `REQUIRES` when a formal mandatory requirement is established.

### INSTALLED_ON

- **Display/category:** Installed On; Dependency
- **Meaning:** The source is deployed or installed on the target endpoint, operating system, or platform.
- **Roles/inverse:** installed artifact -> installation host; `HAS_INSTALLED`.
- **Policies:** medium risk; evidence required; conditions required; minimum confidence 0.80; default scope conditional.
- **Behavior:** non-transitive, non-symmetric, non-reflexive; inverse virtual only.
- **Correct illustration:** `Synthetic agent INSTALLED_ON Synthetic endpoint`.
- **Incorrect illustration:** describing a built-in structural component as installed when composition is the intended fact.
- **Choose it over:** `RUNS_ON` when deployment location, not runtime execution, is asserted.

### REQUIRES

- **Display/category:** Requires; Dependency
- **Meaning:** The target is mandatory for the source under the stated scope and conditions.
- **Roles/inverse:** requiring entity -> mandatory requirement; `REQUIRED_BY`.
- **Policies:** high risk; authoritative evidence required; conditions required when non-universal; minimum confidence 0.90.
- **Behavior:** non-transitive, non-symmetric, non-reflexive; inverse virtual only.
- **Correct illustration:** `Synthetic feature REQUIRES Synthetic prerequisite`.
- **Incorrect illustration:** treating an optional integration or useful capability as mandatory.
- **Choose it over:** `ENABLES`, `USES`, or `DEPENDS_ON` only when authoritative evidence establishes necessity.

### RUNS_ON

- **Display/category:** Runs On; Dependency
- **Meaning:** The source executes within or on the target operating system or execution platform.
- **Roles/inverse:** executing software -> execution host; `HOSTS`.
- **Policies:** medium risk; evidence required; conditions required; minimum confidence 0.80; default scope conditional.
- **Behavior:** non-transitive, non-symmetric, non-reflexive; inverse virtual only.
- **Correct illustration:** `Synthetic application RUNS_ON Synthetic platform`.
- **Incorrect illustration:** claiming runtime execution from installation or compatibility alone.
- **Choose it over:** `INSTALLED_ON` when execution, rather than deployment location, is evidenced.

## Lifecycle

Lifecycle predicates are high risk, require authoritative evidence, use minimum confidence 0.90, default to conditional scope, and are non-transitive, non-symmetric, and non-reflexive.

### DEPRECATED_BY

- **Display/category/policies:** Deprecated By; Lifecycle; high risk; authoritative evidence required; conditions required; minimum confidence 0.90; non-transitive and non-symmetric.
- **Meaning/roles/inverse:** The source has been formally deprecated in favour of the target; deprecated concept -> preferred successor; `DEPRECATES`.
- **Correct illustration:** `Synthetic legacy feature DEPRECATED_BY Synthetic successor` backed by a formal notice.
- **Incorrect illustration:** assuming deprecation because another technology is newer.
- **Choose it over:** `REPLACES` when the primary fact is an explicit deprecation decision.

### REPLACES

- **Display/category/policies:** Replaces; Lifecycle; high risk; authoritative evidence required; conditions required; minimum confidence 0.90; non-transitive and non-symmetric.
- **Meaning/roles/inverse:** The source supersedes the target as a successor technology or concept; successor -> superseded predecessor; `REPLACED_BY`.
- **Correct illustration:** `Synthetic successor REPLACES Synthetic predecessor` backed by an authoritative succession statement.
- **Incorrect illustration:** using it merely because the source has a later date.
- **Choose it over:** `DEPRECATED_BY` when the asserted direction is successor-to-predecessor supersession.

## Compatibility

Compatibility predicates are high risk, require authoritative evidence and explicit conditions, use minimum confidence 0.90, and default to conditional scope. They are non-transitive, non-symmetric, non-reflexive, and never create automatic reverse edges.

### COMPATIBLE_WITH

- **Display/category/policies:** Compatible With; Compatibility; high risk; authoritative evidence and conditions always required; minimum confidence 0.90; non-transitive and non-symmetric.
- **Meaning/roles/inverse:** The source can operate with the target under documented conditions; evaluated entity -> documented counterpart; virtual display inverse `COMPATIBLE_WITH`.
- **Correct illustration:** `Synthetic component COMPATIBLE_WITH Synthetic platform under stated test conditions`.
- **Incorrect illustration:** inferring compatibility from co-occurrence, installation, or one successful observation.
- **Choose it over:** `SUPPORTS` when documented operability exists without an official support commitment; use `CONFLICTS_WITH` for documented malfunction.

### CONFLICTS_WITH

- **Display/category/policies:** Conflicts With; Compatibility; high risk; authoritative evidence and conditions always required; minimum confidence 0.90; non-transitive and non-symmetric.
- **Meaning/roles/inverse:** The source is documented to conflict or operate incorrectly with the target under specified conditions; affected entity -> conflicting counterpart; virtual display inverse `CONFLICTS_WITH`.
- **Correct illustration:** `Synthetic component CONFLICTS_WITH Synthetic platform under stated test conditions`.
- **Incorrect illustration:** recording suspicion, absence of support, or an unverified failure.
- **Choose it over:** `COMPATIBLE_WITH` only when authoritative evidence documents conflict or incorrect operation.

### SUPPORTS

- **Display/category/policies:** Supports; Compatibility; high risk; authoritative evidence and conditions always required; minimum confidence 0.90; non-transitive and non-symmetric.
- **Meaning/roles/inverse:** The source officially supports operation, integration, or use with the target under defined conditions; supporting product or authority -> supported entity; `SUPPORTED_BY`.
- **Correct illustration:** `Synthetic vendor product SUPPORTS Synthetic platform under stated conditions`.
- **Incorrect illustration:** treating inferred compatibility or observed operation as an official support commitment.
- **Choose it over:** `COMPATIBLE_WITH` only when an authoritative source explicitly states support.

## Storage and Query Guidance

Store one canonical edge with the catalog's source and target roles. Query layers may render the `virtual_inverse_label` when traversing backwards, but must not write a second inverse relationship. `materialize_inverse` is false for every v1.0 predicate. Any future inference beyond `IS_A` transitivity requires explicit governance and must not be inferred from this candidate catalog alone.
