import csv
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# CSV column map (actual header names in entities.csv)
ENTITY_ID_COL   = "entity_id:ID(Entity)"
NAME_COL        = "name"
NORM_NAME_COL   = "normalized_name"
TYPE_COL        = "type"
LABEL_COL       = ":LABEL"

# Columns considered required (non-empty)
REQUIRED_COLS = [ENTITY_ID_COL, NAME_COL, TYPE_COL, LABEL_COL]

def is_empty(value: str) -> bool:
    """Returns True if a value is absent or whitespace-only."""
    return value is None or str(value).strip() == ""

def validate_csv(csv_path: Path) -> dict:
    """Reads and validates the Layer 1 entities CSV file.
    
    Checks performed per row:
      1. entity_id exists and is non-empty.
      2. entity_id is unique (no duplicate IDs).
      3. name exists and is non-empty.
      4. type exists and is non-empty.
      5. :LABEL exists and is non-empty.
      6. normalized_name (canonical name) is unique across all rows.
      7. Row is not completely empty.
      
    Returns:
        dict: Validation result in the required report format.
    """
    total_rows = 0
    valid_rows = 0
    duplicates = []
    errors = []
    
    seen_entity_ids: Dict[str, int] = {}        # entity_id -> first row number
    seen_canonical_names: Dict[str, int] = {}   # normalized_name -> first row number
    
    logger.info(f"Validating CSV file: {csv_path}")

    if not csv_path.exists():
        msg = f"CSV file not found: {csv_path}"
        logger.error(msg)
        return {"total_rows": 0, "valid_rows": 0, "duplicates": [], "errors": [msg]}

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        
        # Verify expected header columns exist
        if reader.fieldnames is None:
            msg = "CSV file has no header row."
            logger.error(msg)
            return {"total_rows": 0, "valid_rows": 0, "duplicates": [], "errors": [msg]}
        
        missing_headers = [col for col in REQUIRED_COLS if col not in reader.fieldnames]
        if missing_headers:
            msg = f"Missing required header column(s): {missing_headers}"
            logger.error(msg)
            return {"total_rows": 0, "valid_rows": 0, "duplicates": [], "errors": [msg]}
        
        for line_num, row in enumerate(reader, start=2):  # start=2: line 1 is the header
            # 7. Detect completely empty rows (all values blank)
            all_values = [str(v).strip() for v in row.values() if v is not None]
            if not any(all_values):
                logger.warning(f"Line {line_num}: Empty row detected. Skipping.")
                continue
            
            total_rows += 1
            row_errors = []
            is_duplicate = False
            
            # Extract key fields
            entity_id   = str(row.get(ENTITY_ID_COL, "")).strip()
            name        = str(row.get(NAME_COL, "")).strip()
            norm_name   = str(row.get(NORM_NAME_COL, "")).strip()
            node_type   = str(row.get(TYPE_COL, "")).strip()
            label       = str(row.get(LABEL_COL, "")).strip()
            
            # 1. entity_id exists
            if is_empty(entity_id):
                row_errors.append(f"Line {line_num}: Missing 'entity_id'.")
            
            # 2. entity_id unique
            if entity_id:
                if entity_id in seen_entity_ids:
                    msg = f"Line {line_num}: Duplicate entity_id '{entity_id}' (first seen at line {seen_entity_ids[entity_id]})."
                    logger.warning(msg)
                    duplicates.append(msg)
                    is_duplicate = True
                else:
                    seen_entity_ids[entity_id] = line_num
            
            # 3. name exists
            if is_empty(name):
                row_errors.append(f"Line {line_num} ({entity_id or '?'}): Missing 'name'.")
            
            # 4. type exists
            if is_empty(node_type):
                row_errors.append(f"Line {line_num} ({entity_id or '?'}): Missing 'type'.")
            
            # 5. labels exist and valid
            if is_empty(label):
                row_errors.append(f"Line {line_num} ({entity_id or '?'}): Missing ':LABEL'.")
            elif "Entity" not in label.split(";"):
                row_errors.append(f"Line {line_num} ({entity_id or '?'}): ':LABEL' does not include 'Entity' base label (got: '{label}').")
            
            # 6. Duplicate canonical (normalized) name check
            if not is_empty(norm_name):
                if norm_name in seen_canonical_names:
                    msg = (
                        f"Line {line_num} ({entity_id or '?'}): "
                        f"Duplicate normalized_name '{norm_name}' "
                        f"(first seen at line {seen_canonical_names[norm_name]})."
                    )
                    logger.warning(msg)
                    duplicates.append(msg)
                    is_duplicate = True
                else:
                    seen_canonical_names[norm_name] = line_num
            
            # Collect row-level errors
            if row_errors:
                for err in row_errors:
                    logger.error(err)
                    errors.extend(row_errors)
            
            # Count valid rows (no errors, not a duplicate)
            if not row_errors and not is_duplicate:
                valid_rows += 1
    
    logger.info(f"Validation complete. Total rows: {total_rows}, Valid: {valid_rows}, "
                f"Duplicates: {len(duplicates)}, Errors: {len(errors)}")

    return {
        "total_rows": total_rows,
        "valid_rows": valid_rows,
        "duplicates": duplicates,
        "errors": errors
    }

def write_report(report_path: Path, report: dict) -> None:
    """Writes the validation report JSON to disk."""
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Validation report written to: {report_path}")
    except Exception as e:
        logger.error(f"Failed to write validation report: {e}")

def main() -> None:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parents[1]
    
    csv_path    = project_root / "data" / "layer1" / "entities.csv"
    report_path = project_root / "reports" / "entity_validation_report.json"
    
    report = validate_csv(csv_path)
    write_report(report_path, report)
    
    print("=== CSV Validation Complete ===")
    print(f"Total Rows:  {report['total_rows']}")
    print(f"Valid Rows:  {report['valid_rows']}")
    print(f"Duplicates:  {len(report['duplicates'])}")
    print(f"Errors:      {len(report['errors'])}")

if __name__ == "__main__":
    main()
