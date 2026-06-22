from pydantic import ValidationError

from app.schemas.normalized_rule import NormalizedRuleCandidate


class SchemaValidationService:
    def validate_normalized_candidate(self, normalized: dict) -> tuple[bool, list[dict]]:
        try:
            NormalizedRuleCandidate.model_validate(normalized)
        except ValidationError as exc:
            return False, exc.errors()
        return True, []
