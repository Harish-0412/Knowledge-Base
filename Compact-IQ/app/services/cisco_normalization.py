import re
from itertools import zip_longest
from typing import Any


CISCO_IOS_XE_TRAINS = {
    "amsterdam",
    "cupertino",
    "dublin",
    "fuji",
    "gibraltar",
}


def is_cisco_switch_model(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(re.match(r"^C(?:9200|9200L|9200CX|9300|9400|9500|9600)[A-Z0-9-]*$", text, re.IGNORECASE))


def is_cisco_network_module(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(re.match(r"^C(?:9200|9300|9500|9600)-NM-[A-Z0-9-]+(?:\s+\d+)?$", text, re.IGNORECASE))


def normalize_cisco_ios_xe_version(version: str) -> str:
    return str(version or "").strip()


def parse_cisco_ios_xe_release(text: Any) -> dict[str, str | None]:
    raw = str(text or "").strip()
    match = re.search(
        r"Cisco\s+IOS\s+XE(?:\s+(?P<train>[A-Za-z]+))?\s+(?P<version>\d+(?:\.\d+){1,3}[a-z]?)\b",
        raw,
        flags=re.IGNORECASE,
    )
    if not match:
        version_match = re.search(r"\b(?P<version>\d+(?:\.\d+){1,3}[a-z]?)\b", raw, flags=re.IGNORECASE)
        return {
            "component_type": "network_os",
            "component_name": "Cisco IOS XE",
            "component_family": None,
            "version_raw": version_match.group("version") if version_match else None,
            "version_normalized": normalize_cisco_ios_xe_version(version_match.group("version")) if version_match else None,
            "version_scheme": "cisco_ios_xe_unknown",
        }

    train = match.group("train")
    version = match.group("version")
    family = train if train and train.lower() in CISCO_IOS_XE_TRAINS else None
    return {
        "component_type": "network_os",
        "component_name": "Cisco IOS XE",
        "component_family": family,
        "version_raw": version,
        "version_normalized": normalize_cisco_ios_xe_version(version),
        "version_scheme": "cisco_ios_xe",
    }


def compare_cisco_ios_xe_versions(a: str, b: str) -> int:
    parsed_a = _version_parts(a)
    parsed_b = _version_parts(b)
    for left, right in zip_longest(parsed_a[0], parsed_b[0], fillvalue=0):
        if left < right:
            return -1
        if left > right:
            return 1
    if parsed_a[1] < parsed_b[1]:
        return -1
    if parsed_a[1] > parsed_b[1]:
        return 1
    return 0


def _version_parts(version: str) -> tuple[list[int], str]:
    match = re.match(r"^(?P<num>\d+(?:\.\d+)*)(?P<suffix>[a-z]?)$", str(version or "").strip(), re.IGNORECASE)
    if not match:
        return [], ""
    return [int(part) for part in match.group("num").split(".")], match.group("suffix").lower()
