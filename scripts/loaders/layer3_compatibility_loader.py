import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add script directory to sys.path to find neo4j_connection
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir))
from neo4j_connection import Neo4jConnection


class Layer3CompatibilityLoader:
    """Loads Layer 3 compatibility rules into Neo4j while preserving all semantics."""
    
    def __init__(self, conn: Neo4jConnection):
        self.conn = conn
        self.stats = {
            "rules_loaded": 0,
            "rules_updated": 0,
            "version_constraints_loaded": 0,
            "version_constraints_updated": 0,
            "evidence_loaded": 0,
            "evidence_updated": 0,
            "remediations_loaded": 0,
            "remediations_updated": 0,
            "relationships_created": 0,
            "errors": []
        }
    
    def load_compatibility_rules(self, json_path: Path) -> Dict[str, Any]:
        """Main entry point for loading compatibility rules."""
        logger.info(f"Loading compatibility rules from: {json_path}")
        
        # Load and validate JSON
        rules_data = self._load_json_file(json_path)
        if not rules_data:
            return self._generate_report()
        
        rules = rules_data.get("rules", [])
        logger.info(f"Found {len(rules)} rules to load")
        
        # Load each rule
        for rule in rules:
            try:
                self._load_single_rule(rule)
            except Exception as e:
                error_msg = f"Failed to load rule {rule.get('rule_id', 'UNKNOWN')}: {e}"
                logger.error(error_msg, exc_info=True)
                self.stats["errors"].append(error_msg)
        
        return self._generate_report()
    
    def _load_json_file(self, json_path: Path) -> Optional[Dict[str, Any]]:
        """Load and validate the JSON file."""
        if not json_path.exists():
            error_msg = f"Rules JSON file not found at: {json_path}"
            logger.error(error_msg)
            self.stats["errors"].append(error_msg)
            return None
        
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Successfully loaded JSON file")
            return data
        except Exception as e:
            error_msg = f"Failed to parse JSON file: {e}"
            logger.error(error_msg, exc_info=True)
            self.stats["errors"].append(error_msg)
            return None
    
    def _load_single_rule(self, rule: Dict[str, Any]) -> None:
        """Load a single compatibility rule and all its dependencies."""
        rule_id = rule.get("rule_id")
        if not rule_id:
            raise ValueError("Rule missing rule_id")
        
        logger.info(f"Loading rule: {rule_id}")
        
        # Create/update CompatibilityRule node
        is_new_rule = self._create_compatibility_rule_node(rule)
        if is_new_rule:
            self.stats["rules_loaded"] += 1
        else:
            self.stats["rules_updated"] += 1
        
        # Create VersionConstraint nodes for subject
        subject = rule.get("subject", {})
        if subject:
            self._create_version_constraint_from_entity(subject, is_subject=True)
        
        # Create VersionConstraint nodes for object
        obj = rule.get("object", {})
        if obj:
            self._create_version_constraint_from_entity(obj, is_subject=False)
        
        # Create VersionConstraint nodes for conditions
        conditions = rule.get("conditions", [])
        for condition in conditions:
            self._create_version_constraint_from_condition(condition)
        
        # Create Evidence nodes
        evidence_list = rule.get("evidence", [])
        for evidence in evidence_list:
            self._create_evidence_node(evidence)
            self._create_has_evidence_relationship(rule_id, evidence.get("evidence_id"))
        
        # Create Remediation nodes
        remediations = rule.get("remediations", [])
        for remediation in remediations:
            self._create_remediation_node(remediation)
            self._create_has_remediation_relationship(rule_id, remediation.get("remediation_id"))
        
        # Create TARGETS relationship to Layer 1 Entity
        subject_entity_id = subject.get("entity_id")
        if subject_entity_id:
            self._create_targets_relationship(rule_id, subject_entity_id)
        
        # Create HAS_CONSTRAINT relationship to object
        obj_entity_id = obj.get("entity_id")
        if obj_entity_id:
            obj_vc = obj.get("version_constraint", {})
            self._create_has_constraint_relationship(
                rule_id, 
                obj_entity_id, 
                obj_vc.get("operator", ""),
                obj_vc.get("version_normalized", "")
            )
        
        # Create HAS_CONDITION relationships
        for condition in conditions:
            self._create_has_condition_relationship(
                rule_id,
                condition.get("entity_id", ""),
                condition.get("operator", ""),
                condition.get("version_normalized", "")
            )
    
    def _create_compatibility_rule_node(self, rule: Dict[str, Any]) -> bool:
        """Create or update a CompatibilityRule node. Returns True if new node created."""
        rule_id = rule.get("rule_id")
        
        # Build properties
        properties = {
            "rule_id": rule_id,
            "rule_type": rule.get("rule_type"),
            "predicate": rule.get("predicate"),
            "severity": rule.get("severity"),
            "confidence": rule.get("confidence"),
            "approval_status": rule.get("approval_status"),
            "verification_status": rule.get("verification_status"),
            "source_document_id": rule.get("source_document_id"),
            "source_release": rule.get("source_release"),
            "compatibility_ontology_version": rule.get("compatibility_ontology_version"),
            "created_timestamp": rule.get("created_timestamp"),
            "updated_timestamp": rule.get("updated_timestamp"),
            "status": rule.get("status"),
            "condition_logic": rule.get("condition_logic"),
            "outcome": rule.get("outcome"),
            "assertion_scope": rule.get("assertion_scope")
        }
        
        query = """
        MERGE (r:CompatibilityRule {rule_id: $rule_id})
        ON CREATE SET r.created_at = datetime(), r._is_new = true
        ON MATCH SET r._is_new = false
        SET r += $properties
        WITH r, r._is_new AS is_new
        REMOVE r._is_new
        RETURN is_new
        """
        
        try:
            results = self.conn.execute_query(query, {
                "rule_id": rule_id,
                "properties": properties
            })
            is_new = results[0].get("is_new", False) if results else False
            return is_new
        except Exception as e:
            logger.error(f"Failed to create CompatibilityRule node: {e}", exc_info=True)
            raise
    
    def _create_version_constraint_from_entity(self, entity: Dict[str, Any], is_subject: bool) -> None:
        """Create or update a VersionConstraint node from an entity object."""
        entity_id = entity.get("entity_id")
        if not entity_id:
            return
        
        vc = entity.get("version_constraint", {})
        if not vc:
            return
        
        properties = {
            "entity_id": entity_id,
            "entity_name": entity.get("entity_name"),
            "entity_kind": entity.get("entity_kind"),
            "operator": vc.get("operator"),
            "version_raw": vc.get("version_raw"),
            "version_normalized": vc.get("version_normalized"),
            "version_scheme": vc.get("version_scheme"),
            "requirement_kind": vc.get("requirement_kind")
        }
        
        query = """
        MERGE (vc:VersionConstraint {
            entity_id: $entity_id,
            operator: $operator,
            version_normalized: $version_normalized
        })
        ON CREATE SET vc.created_at = datetime(), vc._is_new = true
        ON MATCH SET vc._is_new = false
        SET vc += $properties
        WITH vc, vc._is_new AS is_new
        REMOVE vc._is_new
        RETURN is_new
        """
        
        try:
            results = self.conn.execute_query(query, {
                "entity_id": entity_id,
                "operator": vc.get("operator", ""),
                "version_normalized": vc.get("version_normalized", ""),
                "properties": properties
            })
            is_new = results[0].get("is_new", False) if results else False
            if is_new:
                self.stats["version_constraints_loaded"] += 1
            else:
                self.stats["version_constraints_updated"] += 1
        except Exception as e:
            logger.error(f"Failed to create VersionConstraint node: {e}", exc_info=True)
            raise
    
    def _create_version_constraint_from_condition(self, condition: Dict[str, Any]) -> None:
        """Create or update a VersionConstraint node from a condition object."""
        entity_id = condition.get("entity_id")
        if not entity_id:
            return
        
        properties = {
            "entity_id": entity_id,
            "entity_name": condition.get("entity_name"),
            "entity_kind": condition.get("entity_kind"),
            "operator": condition.get("operator"),
            "version_raw": condition.get("version_raw"),
            "version_normalized": condition.get("version_normalized"),
            "version_scheme": condition.get("version_scheme"),
            "requirement_kind": "exact_version"  # Conditions are typically exact versions
        }
        
        query = """
        MERGE (vc:VersionConstraint {
            entity_id: $entity_id,
            operator: $operator,
            version_normalized: $version_normalized
        })
        ON CREATE SET vc.created_at = datetime(), vc._is_new = true
        ON MATCH SET vc._is_new = false
        SET vc += $properties
        WITH vc, vc._is_new AS is_new
        REMOVE vc._is_new
        RETURN is_new
        """
        
        try:
            results = self.conn.execute_query(query, {
                "entity_id": entity_id,
                "operator": condition.get("operator", ""),
                "version_normalized": condition.get("version_normalized", ""),
                "properties": properties
            })
            is_new = results[0].get("is_new", False) if results else False
            if is_new:
                self.stats["version_constraints_loaded"] += 1
            else:
                self.stats["version_constraints_updated"] += 1
        except Exception as e:
            logger.error(f"Failed to create VersionConstraint node from condition: {e}", exc_info=True)
            raise
    
    def _create_evidence_node(self, evidence: Dict[str, Any]) -> None:
        """Create or update an Evidence node."""
        evidence_id = evidence.get("evidence_id")
        if not evidence_id:
            return
        
        properties = {
            "evidence_id": evidence_id,
            "source_document_id": evidence.get("source_document_id"),
            "source_chunk_id": evidence.get("source_chunk_id"),
            "source_page": evidence.get("source_page"),
            "source_excerpt": evidence.get("source_excerpt"),
            "confidence_score": evidence.get("confidence_score"),
            "verification_status": evidence.get("verification_status"),
            "extraction_method": evidence.get("extraction_method"),
            "source_type": evidence.get("source_type")
        }
        
        query = """
        MERGE (e:Evidence {evidence_id: $evidence_id})
        ON CREATE SET e.created_at = datetime(), e._is_new = true
        ON MATCH SET e._is_new = false
        SET e += $properties
        WITH e, e._is_new AS is_new
        REMOVE e._is_new
        RETURN is_new
        """
        
        try:
            results = self.conn.execute_query(query, {
                "evidence_id": evidence_id,
                "properties": properties
            })
            is_new = results[0].get("is_new", False) if results else False
            if is_new:
                self.stats["evidence_loaded"] += 1
            else:
                self.stats["evidence_updated"] += 1
        except Exception as e:
            logger.error(f"Failed to create Evidence node: {e}", exc_info=True)
            raise
    
    def _create_remediation_node(self, remediation: Dict[str, Any]) -> None:
        """Create or update a Remediation node."""
        remediation_id = remediation.get("remediation_id")
        if not remediation_id:
            return
        
        properties = {
            "remediation_id": remediation_id,
            "remediation_type": remediation.get("remediation_type"),
            "target_entity_id": remediation.get("target_entity_id"),
            "target_component_name": remediation.get("target_component_name"),
            "operator": remediation.get("operator"),
            "target_version": remediation.get("target_version"),
            "sequence_order": remediation.get("sequence_order"),
            "remediation_hint": remediation.get("remediation_hint")
        }
        
        query = """
        MERGE (rem:Remediation {remediation_id: $remediation_id})
        ON CREATE SET rem.created_at = datetime(), rem._is_new = true
        ON MATCH SET rem._is_new = false
        SET rem += $properties
        WITH rem, rem._is_new AS is_new
        REMOVE rem._is_new
        RETURN is_new
        """
        
        try:
            results = self.conn.execute_query(query, {
                "remediation_id": remediation_id,
                "properties": properties
            })
            is_new = results[0].get("is_new", False) if results else False
            if is_new:
                self.stats["remediations_loaded"] += 1
            else:
                self.stats["remediations_updated"] += 1
        except Exception as e:
            logger.error(f"Failed to create Remediation node: {e}", exc_info=True)
            raise
    
    def _create_targets_relationship(self, rule_id: str, entity_id: str) -> None:
        """Create TARGETS relationship from rule to Layer 1 Entity."""
        query = """
        MATCH (r:CompatibilityRule {rule_id: $rule_id})
        MATCH (e:Entity {entity_id: $entity_id})
        MERGE (r)-[:TARGETS]->(e)
        RETURN count(*) AS created
        """
        
        try:
            results = self.conn.execute_query(query, {
                "rule_id": rule_id,
                "entity_id": entity_id
            })
            if results:
                self.stats["relationships_created"] += 1
        except Exception as e:
            logger.error(f"Failed to create TARGETS relationship: {e}", exc_info=True)
            raise
    
    def _create_has_constraint_relationship(
        self, 
        rule_id: str, 
        entity_id: str, 
        operator: str, 
        version_normalized: str
    ) -> None:
        """Create HAS_CONSTRAINT relationship from rule to VersionConstraint."""
        query = """
        MATCH (r:CompatibilityRule {rule_id: $rule_id})
        MATCH (vc:VersionConstraint {
            entity_id: $entity_id,
            operator: $operator,
            version_normalized: $version_normalized
        })
        MERGE (r)-[:HAS_CONSTRAINT]->(vc)
        RETURN count(*) AS created
        """
        
        try:
            results = self.conn.execute_query(query, {
                "rule_id": rule_id,
                "entity_id": entity_id,
                "operator": operator,
                "version_normalized": version_normalized
            })
            if results:
                self.stats["relationships_created"] += 1
        except Exception as e:
            logger.error(f"Failed to create HAS_CONSTRAINT relationship: {e}", exc_info=True)
            raise
    
    def _create_has_condition_relationship(
        self, 
        rule_id: str, 
        entity_id: str, 
        operator: str, 
        version_normalized: str
    ) -> None:
        """Create HAS_CONDITION relationship from rule to VersionConstraint."""
        query = """
        MATCH (r:CompatibilityRule {rule_id: $rule_id})
        MATCH (vc:VersionConstraint {
            entity_id: $entity_id,
            operator: $operator,
            version_normalized: $version_normalized
        })
        MERGE (r)-[:HAS_CONDITION]->(vc)
        RETURN count(*) AS created
        """
        
        try:
            results = self.conn.execute_query(query, {
                "rule_id": rule_id,
                "entity_id": entity_id,
                "operator": operator,
                "version_normalized": version_normalized
            })
            if results:
                self.stats["relationships_created"] += 1
        except Exception as e:
            logger.error(f"Failed to create HAS_CONDITION relationship: {e}", exc_info=True)
            raise
    
    def _create_has_evidence_relationship(self, rule_id: str, evidence_id: str) -> None:
        """Create HAS_EVIDENCE relationship from rule to Evidence."""
        if not evidence_id:
            return
        
        query = """
        MATCH (r:CompatibilityRule {rule_id: $rule_id})
        MATCH (e:Evidence {evidence_id: $evidence_id})
        MERGE (r)-[:HAS_EVIDENCE]->(e)
        RETURN count(*) AS created
        """
        
        try:
            results = self.conn.execute_query(query, {
                "rule_id": rule_id,
                "evidence_id": evidence_id
            })
            if results:
                self.stats["relationships_created"] += 1
        except Exception as e:
            logger.error(f"Failed to create HAS_EVIDENCE relationship: {e}", exc_info=True)
            raise
    
    def _create_has_remediation_relationship(self, rule_id: str, remediation_id: str) -> None:
        """Create HAS_REMEDIATION relationship from rule to Remediation."""
        if not remediation_id:
            return
        
        query = """
        MATCH (r:CompatibilityRule {rule_id: $rule_id})
        MATCH (rem:Remediation {remediation_id: $remediation_id})
        MERGE (r)-[:HAS_REMEDIATION]->(rem)
        RETURN count(*) AS created
        """
        
        try:
            results = self.conn.execute_query(query, {
                "rule_id": rule_id,
                "remediation_id": remediation_id
            })
            if results:
                self.stats["relationships_created"] += 1
        except Exception as e:
            logger.error(f"Failed to create HAS_REMEDIATION relationship: {e}", exc_info=True)
            raise
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate the load report."""
        return {
            "rules_loaded": self.stats["rules_loaded"],
            "rules_updated": self.stats["rules_updated"],
            "version_constraints_loaded": self.stats["version_constraints_loaded"],
            "version_constraints_updated": self.stats["version_constraints_updated"],
            "evidence_loaded": self.stats["evidence_loaded"],
            "evidence_updated": self.stats["evidence_updated"],
            "remediations_loaded": self.stats["remediations_loaded"],
            "remediations_updated": self.stats["remediations_updated"],
            "relationships_created": self.stats["relationships_created"],
            "errors": self.stats["errors"]
        }


def main() -> None:
    """Main entry point for the Layer 3 Compatibility Loader."""
    # Resolve project root and input/output paths
    project_root = script_dir.parents[1]
    json_path = project_root / "CompatibilityLayer" / "rules" / "candidate" / "compatibility_rule_candidates.json"
    report_path = project_root / "reports" / "layer3_load_report.json"
    
    logger.info("Starting Layer 3 Compatibility Loader.")
    logger.info(f"Loading rules from: {json_path}")
    
    conn = Neo4jConnection()
    loader = Layer3CompatibilityLoader(conn)
    
    try:
        conn.connect()
        report = loader.load_compatibility_rules(json_path)
    except Exception as e:
        error_msg = f"Fatal loader database failure: {e}"
        logger.error(error_msg, exc_info=True)
        report = {
            "rules_loaded": 0,
            "rules_updated": 0,
            "version_constraints_loaded": 0,
            "version_constraints_updated": 0,
            "evidence_loaded": 0,
            "evidence_updated": 0,
            "remediations_loaded": 0,
            "remediations_updated": 0,
            "relationships_created": 0,
            "errors": [error_msg]
        }
    finally:
        conn.close()
    
    # Generate load report
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Layer 3 load report written to: {report_path}")
    except Exception as e:
        logger.error(f"Failed to generate load report file: {e}")
    
    # Output stats summary
    print("=== Layer 3 Compatibility Load Complete ===")
    print(f"Rules Loaded (New): {report['rules_loaded']}")
    print(f"Rules Updated (Existing): {report['rules_updated']}")
    print(f"Version Constraints Loaded: {report['version_constraints_loaded']}")
    print(f"Version Constraints Updated: {report['version_constraints_updated']}")
    print(f"Evidence Loaded: {report['evidence_loaded']}")
    print(f"Evidence Updated: {report['evidence_updated']}")
    print(f"Remediations Loaded: {report['remediations_loaded']}")
    print(f"Remediations Updated: {report['remediations_updated']}")
    print(f"Relationships Created: {report['relationships_created']}")
    print(f"Errors: {len(report['errors'])}")
    
    if report['errors']:
        print("\nErrors:")
        for error in report['errors']:
            print(f"  - {error}")


if __name__ == "__main__":
    main()
