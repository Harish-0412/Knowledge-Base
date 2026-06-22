from dataclasses import dataclass
import json
import re
from typing import Any


@dataclass
class JsonRepairResult:
    ok: bool
    data: Any | None
    error: str | None = None


def repair_json(value: Any) -> JsonRepairResult:
    if isinstance(value, (dict, list)):
        return JsonRepairResult(ok=True, data=value)
    if not isinstance(value, str):
        return JsonRepairResult(ok=False, data=None, error="LLM output was not JSON text.")

    candidates = [
        value,
        _strip_markdown_fences(value),
    ]
    extracted = _extract_first_json(candidates[-1])
    if extracted:
        candidates.append(extracted)

    for candidate in candidates:
        try:
            return JsonRepairResult(ok=True, data=json.loads(candidate))
        except json.JSONDecodeError:
            continue

    return JsonRepairResult(ok=False, data=None, error="Unable to parse or repair LLM JSON output.")


def _strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()
    return stripped


def _extract_first_json(text: str) -> str | None:
    stripped = text.strip()
    starts = [index for index, char in enumerate(stripped) if char in "[{"]
    for start in starts:
        opener = stripped[start]
        closer = "}" if opener == "{" else "]"
        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(stripped)):
            char = stripped[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    return stripped[start : index + 1]
    return None
