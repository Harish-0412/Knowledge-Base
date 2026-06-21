# file: d:\Fazmina\endpoint-kb\ReasoningLayer\query_understanding\device_resolver.py
from __future__ import annotations
import re
import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class DeviceResolver:
    """
    Resolves natural language device placeholders (e.g., 'Laptop001') to
    actual graph device IDs (e.g., 'DEV-DELL-0011') dynamically based on
    device model classifications in the inventory.
    """
    
    # Classification rules matching model names to device categories
    LAPTOP_KEYWORDS = ["latitude", "thinkpad", "elitebook", "probook", "zbook", "book"]
    SERVER_KEYWORDS = ["poweredge", "proliant", "thinksystem", "dl360", "dl380", "ml350", "sr630", "sr650", "st650"]
    WORKSTATION_KEYWORDS = ["precision", "thinkstation", "z2 tower", "station"]
    DESKTOP_KEYWORDS = ["optiplex", "elitedesk", "thinkcentre"]
    
    def __init__(self, csv_path: Optional[Path] = None, neo4j_connector = None) -> None:
        self.csv_path = csv_path or Path(__file__).resolve().parents[2] / "InventoryLayer" / "neo4j" / "device_nodes.csv"
        self.connector = neo4j_connector
        self._cached_mappings: Dict[str, Dict[str, str]] = {}
        
    def _load_inventory_devices(self) -> List[dict]:
        """Loads all devices from Neo4j, falling back to CSV if offline."""
        devices = []
        if self.connector and self.connector.available:
            try:
                rows = self.connector.run("MATCH (d:Device) RETURN d")
                for r in rows:
                    node = r.get("d", {})
                    devices.append({
                        "device_id": node.get("device_id"),
                        "device_name": node.get("device_name"),
                        "device_model": node.get("device_model")
                    })
            except Exception as e:
                logger.warning(f"Neo4j retrieval failed in resolver, falling back to CSV: {e}")
                
        if not devices and self.csv_path.exists():
            try:
                with open(self.csv_path, mode="r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        devices.append({
                            "device_id": row.get("device_id") or row.get(":ID(Device)"),
                            "device_name": row.get("device_name"),
                            "device_model": row.get("device_model")
                        })
            except Exception as e:
                logger.error(f"Failed to read fallback CSV in resolver: {e}")
        return devices

    def _classify_device_type(self, model: str) -> str:
        """Classifies a model string into category types."""
        model_lower = str(model).lower()
        if any(kw in model_lower for kw in self.LAPTOP_KEYWORDS):
            return "laptop"
        if any(kw in model_lower for kw in self.SERVER_KEYWORDS):
            return "server"
        if any(kw in model_lower for kw in self.WORKSTATION_KEYWORDS):
            return "workstation"
        if any(kw in model_lower for kw in self.DESKTOP_KEYWORDS):
            return "desktop"
        return "device"

    def _build_mappings(self) -> Dict[str, Dict[str, str]]:
        """Builds sorted lists of actual device IDs grouped by category."""
        devices = self._load_inventory_devices()
        categories: Dict[str, List[str]] = {
            "laptop": [],
            "server": [],
            "workstation": [],
            "desktop": [],
            "device": []
        }
        
        for dev in devices:
            dev_id = dev["device_id"]
            model = dev["device_model"]
            category = self._classify_device_type(model)
            
            categories[category].append(dev_id)
            categories["device"].append(dev_id)  # All devices can be looked up as 'DeviceXXX'
            
        # Sort each list to guarantee stable, deterministic mappings
        mappings: Dict[str, Dict[str, str]] = {}
        for cat, dev_ids in categories.items():
            dev_ids.sort()
            cat_map = {}
            for i, dev_id in enumerate(dev_ids):
                cat_map[f"{cat.capitalize()}{i+1:03d}"] = dev_id
                cat_map[f"{cat.capitalize()}{i+1}"] = dev_id
            mappings[cat] = cat_map
            
        return mappings

    def get_mappings(self) -> Dict[str, Dict[str, str]]:
        """Returns cached or newly built mapping dictionaries."""
        if not self._cached_mappings:
            self._cached_mappings = self._build_mappings()
        return self._cached_mappings

    def resolve(self, placeholder_name: str) -> Optional[str]:
        """
        Resolves a placeholder name (e.g. 'Laptop001') to a real device_id (e.g. 'DEV-DELL-0011').
        """
        if not placeholder_name:
            return None
            
        # Parse placeholder pattern
        match = re.match(r"^([A-Za-z]+)(\d+)$", placeholder_name.strip())
        if not match:
            # If it is already in the database ID format (e.g. DEV-DELL-0011), return as-is
            return placeholder_name
            
        category_name = match.group(1).lower()
        index = int(match.group(2))
        
        mappings = self.get_mappings()
        cat_key = category_name if category_name in mappings else "device"
        cat_map = mappings[cat_key]
        
        padded_key = f"{cat_key.capitalize()}{index:03d}"
        unpadded_key = f"{cat_key.capitalize()}{index}"
        
        return cat_map.get(padded_key) or cat_map.get(unpadded_key) or None
