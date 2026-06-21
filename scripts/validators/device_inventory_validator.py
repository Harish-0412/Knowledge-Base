"""
scripts/validators/device_inventory_validator.py

Purpose:
Validate device inventory before loading.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def validate_inventory(json_path: Path, report_path: Path) -> None:
    """Validates the structure, key existence, duplicate values, and readiness block for inventory JSON."""
    logger.info(f"Starting inventory validation. Input: {json_path}")
    logger.info(f"Validation report target: {report_path}")

    # Initialize report structure
    report = {
        "devices": 0,
        "components": 0,
        "warnings": [],
        "errors": []
    }

    if not json_path.exists():
        err_msg = f"Inventory file not found at: {json_path}"
        logger.error(err_msg)
        report["errors"].append(err_msg)
        write_report(report_path, report)
        return

    if not json_path.is_file():
        err_msg = f"Inventory path is not a file: {json_path}"
        logger.error(err_msg)
        report["errors"].append(err_msg)
        write_report(report_path, report)
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        err_msg = f"Failed to parse JSON inventory data: {e}"
        logger.error(err_msg)
        report["errors"].append(err_msg)
        write_report(report_path, report)
        return
    except Exception as e:
        err_msg = f"Error reading inventory file: {e}"
        logger.error(err_msg)
        report["errors"].append(err_msg)
        write_report(report_path, report)
        return

    if not isinstance(data, list):
        err_msg = "Root of inventory JSON must be a list of device objects."
        logger.error(err_msg)
        report["errors"].append(err_msg)
        write_report(report_path, report)
        return

    seen_device_ids = set()
    seen_component_ids = set()

    for dev_idx, dev in enumerate(data):
        report["devices"] += 1
        dev_context = f"Device at index {dev_idx}"
        
        # 1. Check device_id exists
        dev_id = dev.get("device_id")
        if dev_id is None or str(dev_id).strip() == "":
            report["errors"].append(f"{dev_context}: missing 'device_id'")
            dev_id_str = f"unknown_index_{dev_idx}"
        else:
            dev_id_str = str(dev_id).strip()
            
            # 3. Check no duplicate device_id
            if dev_id_str in seen_device_ids:
                report["errors"].append(f"{dev_context}: duplicate device_id '{dev_id_str}'")
            else:
                seen_device_ids.add(dev_id_str)
                
        # 8. Check readiness block exists
        readiness = dev.get("readiness")
        if readiness is None or not isinstance(readiness, dict):
            report["errors"].append(f"Device '{dev_id_str}': missing or invalid 'readiness' block")
            
        # Get components list
        components = dev.get("components")
        if components is None or not isinstance(components, list):
            report["errors"].append(f"Device '{dev_id_str}': 'components' field is missing or not a list")
            continue
            
        for comp_idx, comp in enumerate(components):
            report["components"] += 1
            comp_context = f"Device '{dev_id_str}' component at index {comp_idx}"
            
            # 2. Check component_instance_id exists
            comp_inst_id = comp.get("component_instance_id")
            if comp_inst_id is None or str(comp_inst_id).strip() == "":
                report["errors"].append(f"{comp_context}: missing 'component_instance_id'")
                comp_id_str = f"unknown_comp_{comp_idx}"
            else:
                comp_id_str = str(comp_inst_id).strip()
                
                # 4. Check no duplicate component_instance_id
                if comp_id_str in seen_component_ids:
                    report["errors"].append(f"{comp_context}: duplicate component_instance_id '{comp_id_str}'")
                else:
                    seen_component_ids.add(comp_id_str)
                    
            # 5. Check component_type exists
            comp_type = comp.get("component_type")
            if comp_type is None or str(comp_type).strip() == "":
                report["errors"].append(f"Component '{comp_id_str}' (Device '{dev_id_str}'): missing 'component_type'")
                
            # 6. Check component_name exists
            comp_name = comp.get("component_name")
            if comp_name is None or str(comp_name).strip() == "":
                report["errors"].append(f"Component '{comp_id_str}' (Device '{dev_id_str}'): missing 'component_name'")
                
            # 7. Check status exists
            status = comp.get("status")
            if status is None or str(status).strip() == "":
                report["errors"].append(f"Component '{comp_id_str}' (Device '{dev_id_str}'): missing 'status'")

            # Optional/Warning check: missing version fields (raw or normalized)
            version_raw = comp.get("version_raw")
            version_norm = comp.get("version_normalized")
            is_raw_empty = version_raw is None or not str(version_raw).strip()
            is_norm_empty = version_norm is None or not str(version_norm).strip()
            
            if is_raw_empty or is_norm_empty:
                missing_fields = []
                if is_raw_empty:
                    missing_fields.append("version_raw")
                if is_norm_empty:
                    missing_fields.append("version_normalized")
                report["warnings"].append(
                    f"Component '{comp_id_str}' (Device '{dev_id_str}'): missing version field(s): {', '.join(missing_fields)}"
                )

    logger.info(
        f"Validation complete: {report['devices']} devices, {report['components']} components checked. "
        f"Errors: {len(report['errors'])}, Warnings: {len(report['warnings'])}"
    )

    write_report(report_path, report)


def write_report(report_path: Path, report: dict) -> None:
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Inventory validation report written to: {report_path}")
    except Exception as e:
        logger.error(f"Failed to write validation report: {e}")


def main():
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parents[1]
    
    # Check if a custom file path is provided as a command-line argument
    if len(sys.argv) > 1:
        json_path = Path(sys.argv[1])
    else:
        json_path = project_root / "mock_inventory(2).json"
        
    report_path = project_root / "reports" / "device_inventory_validation_report.json"
    validate_inventory(json_path, report_path)


if __name__ == "__main__":
    main()
