"""
scripts/analysis/component_type_analyzer.py

Purpose:
Analyze a device inventory JSON file and produce inventory statistics.
"""

import sys
import json
import logging
from pathlib import Path
from collections import Counter
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def analyze_inventory(json_path: Path) -> Dict[str, Any]:
    """Analyzes device inventory from a JSON file.
    
    Checks performed:
    - Path existence and type
    - Parsing validity
    - Root level list structure
    
    Returns:
        Dict[str, Any]: Stats matching the report format.
    """
    logger.info(f"Analyzing inventory JSON file: {json_path}")
    
    if not json_path.exists():
        msg = f"File does not exist: {json_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)
        
    if not json_path.is_file():
        msg = f"Path is not a file: {json_path}"
        logger.error(msg)
        raise ValueError(msg)
        
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON format: {e}"
        logger.error(msg)
        raise ValueError(msg) from e
    except Exception as e:
        msg = f"Failed to read file: {e}"
        logger.error(msg)
        raise RuntimeError(msg) from e

    if not isinstance(data, list):
        msg = "JSON root is not a list. Expected a list of devices."
        logger.error(msg)
        raise TypeError(msg)

    device_count = len(data)
    component_count = 0
    type_counter = Counter()

    for idx, device in enumerate(data):
        if not isinstance(device, dict):
            logger.warning(f"Device at index {idx} is not a JSON object (dict). Skipping.")
            continue
            
        components = device.get("components")
        if not isinstance(components, list):
            logger.warning(f"Device '{device.get('device_id', f'index_{idx}')}' components field is not a list. Skipping components.")
            continue
            
        for comp in components:
            if not isinstance(comp, dict):
                continue
            component_count += 1
            comp_type = comp.get("component_type")
            if comp_type is not None:
                type_str = str(comp_type).strip().lower()
                if type_str:
                    type_counter[type_str] += 1
                else:
                    type_counter["unknown"] += 1
            else:
                type_counter["unknown"] += 1

    return {
        "devices": device_count,
        "components": component_count,
        "unique_component_types": dict(type_counter)
    }


def main():
    if len(sys.argv) < 2:
        logger.error("Usage: python scripts/analysis/component_type_analyzer.py <path_to_inventory_json>")
        sys.exit(1)
        
    json_path_str = sys.argv[1]
    json_path = Path(json_path_str)
    
    try:
        results = analyze_inventory(json_path)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)
        
    # Output to console matching the requested structure
    print("==================================================")
    print("Inventory Analysis Report")
    print("=========================")
    print()
    print(f"Devices: {results['devices']}")
    print()
    print(f"Components: {results['components']}")
    print()
    print("Unique Component Types:")
    print()
    for comp_type, count in sorted(results["unique_component_types"].items()):
        print(f"{comp_type}: {count}")
    print()
    print("==================================================")
    
    # Save the output summary report to reports/component_type_summary.json
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parents[1]
    report_path = project_root / "reports" / "component_type_summary.json"
    
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Inventory summary report generated at: {report_path}")
    except Exception as e:
        logger.error(f"Failed to generate summary report file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
