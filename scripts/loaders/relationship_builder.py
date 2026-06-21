import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple
from neo4j_connection import Neo4jConnection

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def build_relationships(conn: Neo4jConnection) -> Tuple[int, List[str], List[str]]:
    """Finds nodes with related_entities and connects them with RELATED_TO relationships."""
    relationships_created = 0
    missing_entities: Set[str] = set()
    errors: List[str] = []

    try:
        # 1. Fetch all existing entity names to optimize target checks
        logger.info("Fetching existing entity names from Neo4j...")
        existing_nodes = conn.execute_query("MATCH (e:Entity) RETURN e.name AS name")
        existing_names = {row["name"].strip() for row in existing_nodes if row.get("name")}
        logger.info(f"Found {len(existing_names)} existing entity name(s) in the database.")

        # 2. Fetch all nodes with related_entities field
        logger.info("Querying nodes with 'related_entities' property...")
        source_nodes = conn.execute_query(
            "MATCH (e:Entity) WHERE e.related_entities IS NOT NULL RETURN e.name AS name, e.related_entities AS related_entities"
        )
        
        logger.info(f"Processing {len(source_nodes)} source node(s) containing ontology references...")

        for row in source_nodes:
            source_name = row.get("name")
            related_entities = row.get("related_entities")
            
            if not source_name or not isinstance(source_name, str):
                continue
                
            source_name = source_name.strip()
            
            if not isinstance(related_entities, list):
                continue

            for target_name in related_entities:
                if not isinstance(target_name, str):
                    continue
                    
                target_name = target_name.strip()
                if not target_name:
                    continue

                if target_name in existing_names:
                    try:
                        # 3. Target exists: MERGE the relationship
                        query = """
                        MATCH (s:Entity {name: $source_name})
                        MATCH (t:Entity {name: $target_name})
                        MERGE (s)-[r:RELATED_TO]->(t)
                        RETURN count(r) as count
                        """
                        result = conn.execute_query(query, {
                            "source_name": source_name,
                            "target_name": target_name
                        })
                        
                        logger.info(f"Created RELATED_TO relationship: {source_name} -> {target_name}")
                        relationships_created += 1
                    except Exception as e:
                        err_msg = f"Error creating relationship {source_name} -> {target_name}: {e}"
                        logger.error(err_msg, exc_info=True)
                        errors.append(err_msg)
                else:
                    # 4. Target missing: track it
                    logger.warning(f"Target node '{target_name}' not found for relationship from '{source_name}'. Skipping.")
                    missing_entities.add(target_name)

    except Exception as e:
        err_msg = f"Failed to execute relationship builder logic: {e}"
        logger.error(err_msg, exc_info=True)
        errors.append(err_msg)

    return relationships_created, sorted(list(missing_entities)), errors

def generate_report(report_path: Path, relationships_created: int, missing_entities: List[str], errors: List[str]) -> None:
    """Generates the relationship_report.json verification file."""
    report = {
        "relationships_created": relationships_created,
        "missing_entities": missing_entities,
        "errors": errors
    }
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Relationship report written to {report_path}")
    except Exception as e:
        logger.error(f"Failed to generate relationship report: {e}")

def main() -> None:
    # Resolve project paths
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parents[1]
    report_path = project_root / "relationship_report.json"

    logger.info("Initializing relationship builder connection...")
    conn = Neo4jConnection()
    
    relationships_created = 0
    missing_entities = []
    errors = []

    try:
        conn.connect()
        relationships_created, missing_entities, errors = build_relationships(conn)
    except Exception as e:
        err_msg = f"Fatal builder connection error: {e}"
        logger.error(err_msg, exc_info=True)
        errors.append(err_msg)
    finally:
        conn.close()

    # Generate final report
    generate_report(report_path, relationships_created, missing_entities, errors)

    print("=== Relationship Build Complete ===")
    print(f"Relationships Created: {relationships_created}")
    print(f"Missing Entities Skipped: {len(missing_entities)}")
    print(f"Errors: {len(errors)}")

if __name__ == "__main__":
    main()
