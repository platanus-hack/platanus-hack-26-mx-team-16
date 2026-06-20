from src.common.domain.exceptions.processing import InvalidValidationRulesError

ALLOWED_MISSING_HANDLING = {"skip", "fail", "pass", "ignore"}


def validate_document_type_validation_rules(rules: list) -> list[dict]:
    if not isinstance(rules, list):
        raise InvalidValidationRulesError("validation_rules must be a list")

    seen_ids: set[str] = set()
    normalized: list[dict] = []

    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise InvalidValidationRulesError(f"rule[{idx}] must be an object")

        rule_id = rule.get("id")
        prompt = rule.get("prompt")
        enabled = rule.get("enabled", True)
        name = rule.get("name")
        missing_handling = rule.get("missing_handling", rule.get("missingHandling", "fail"))

        if not isinstance(rule_id, str) or not rule_id.strip():
            raise InvalidValidationRulesError(f"rule[{idx}] missing required 'id'")
        if rule_id in seen_ids:
            raise InvalidValidationRulesError(f"duplicate rule id '{rule_id}'")
        seen_ids.add(rule_id)

        if not isinstance(prompt, str) or not prompt.strip():
            raise InvalidValidationRulesError(f"rule '{rule_id}' missing required 'prompt'")

        if not isinstance(enabled, bool):
            raise InvalidValidationRulesError(f"rule '{rule_id}' 'enabled' must be boolean")

        if name is not None and not isinstance(name, str):
            raise InvalidValidationRulesError(f"rule '{rule_id}' 'name' must be a string")

        if missing_handling not in ALLOWED_MISSING_HANDLING:
            raise InvalidValidationRulesError(
                f"rule '{rule_id}' 'missing_handling' must be one of {sorted(ALLOWED_MISSING_HANDLING)}"
            )

        normalized.append(
            {
                "id": rule_id,
                "name": (name or "").strip() or rule_id,
                "prompt": prompt,
                "enabled": enabled,
                "missing_handling": missing_handling,
            }
        )

    return normalized
