import os
import json
import shutil
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def import_data():
    # Resolve paths relative to this script
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parents[1]
    
    source_dir = project_root / "Knowledge-Base" / "Domain_layer" / "normalized"
    dest_dir = project_root / "data" / "entities"
    
    logger.info(f"Source directory: {source_dir}")
    logger.info(f"Destination directory: {dest_dir}")
    
    # 1. Verify source folder exists
    if not source_dir.exists():
        logger.error(f"Source folder does not exist: {source_dir}")
        print(f"Error: Source folder does not exist: {source_dir}")
        return

    # 2. Verify destination folder exists (Create if missing)
    if not dest_dir.exists():
        logger.info(f"Destination folder does not exist. Creating: {dest_dir}")
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create destination folder: {e}", exc_info=True)
            print(f"Error: Failed to create destination folder: {e}")
            return

    files_to_copy = [
        "drivers.json",
        "firmware.json",
        "management.json",
        "operating_system.json",
        "security.json"
    ]
    
    copied_count = 0
    
    # 3. Copy and validate files
    for filename in files_to_copy:
        src_file = source_dir / filename
        dest_file = dest_dir / filename
        
        if not src_file.exists():
            logger.warning(f"Expected source file not found: {src_file}")
            print(f"Warning: Expected source file not found: {filename}")
            continue
            
        try:
            # Copy file preserving metadata/permissions if possible
            shutil.copy2(src_file, dest_file)
            logger.info(f"Copied {filename} to {dest_dir}")
            
            # Validate that the copied file is valid JSON
            with open(dest_file, "r", encoding="utf-8") as f:
                json.load(f)
                
            print(f"Copied {filename}")
            copied_count += 1
            
        except json.JSONDecodeError as jde:
            logger.error(f"Validation failed: Copied file {filename} is not valid JSON. Error: {jde}")
            print(f"Error: Copied file {filename} contains invalid JSON.")
            # Optionally remove the invalid file to avoid pollution
            if dest_file.exists():
                dest_file.unlink()
        except Exception as e:
            logger.error(f"Failed to process {filename}: {e}", exc_info=True)
            print(f"Error: Failed to copy/validate {filename}: {e}")

    # 4. Print summary
    print(f"\nTotal files copied: {copied_count}")

def main():
    import_data()

if __name__ == "__main__":
    main()
