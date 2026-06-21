# file: ComplianceEngine/version_comparator.py
import re
from typing import Union, Tuple

def parse_version(v_str: str) -> Union[Tuple[int, ...], str]:
    """
    Parses a version string into a tuple of integers for semantic versions,
    or a lowercase string for named releases and unknown versions.
    """
    if v_str is None:
        return ""
    if not isinstance(v_str, str):
        v_str = str(v_str)
        
    v_str = v_str.strip()
    
    # Try to parse as clean dot-separated integers (semantic style)
    parts = v_str.split('.')
    parsed_parts = []
    is_semantic = True
    for p in parts:
        if p.isdigit():
            parsed_parts.append(int(p))
        else:
            # Handle versions with suffixes, e.g. 2.18.1-rc1 -> leading digits '2', '18', '1'
            match = re.match(r'^(\d+)', p)
            if match:
                parsed_parts.append(int(match.group(1)))
            else:
                is_semantic = False
                break
                
    if is_semantic and parsed_parts:
        return tuple(parsed_parts)
        
    # Fallback to lowercase string for comparison
    return v_str.lower()

def compare_versions(v1_str: str, op: str, v2_str: str) -> bool:
    """
    Compares two version strings using the specified operator.
    Supports: '>', '>=', '<', '<=', '=='
    Handles semantic versions, named releases, and unknown/none values.
    """
    if v1_str is None or v2_str is None:
        if op == "==":
            return v1_str == v2_str
        elif op == "!=":
            return v1_str != v2_str
        return False
        
    p1 = parse_version(v1_str)
    p2 = parse_version(v2_str)
    
    # If both are semantic tuples, pad them to equal length with zeros
    if isinstance(p1, tuple) and isinstance(p2, tuple):
        max_len = max(len(p1), len(p2))
        t1 = p1 + (0,) * (max_len - len(p1))
        t2 = p2 + (0,) * (max_len - len(p2))
        val1, val2 = t1, t2
    else:
        # Otherwise, compare as strings
        val1, val2 = str(p1), str(p2)
        
    if op == "==":
        return val1 == val2
    elif op == "!=":
        return val1 != val2
    elif op == ">":
        return val1 > val2
    elif op == ">=":
        return val1 >= val2
    elif op == "<":
        return val1 < val2
    elif op == "<=":
        return val1 <= val2
    else:
        raise ValueError(f"Unsupported operator: {op}")
