"""Policy engine: maps tool invocations to ALLOW / DENY / REQUIRE_APPROVAL."""

import fnmatch

from packages.policy.models import DEFAULT_RULES, PolicyAction, PolicyRule


class PolicyEngine:
    def __init__(self, rules: list[PolicyRule] | None = None):
        self._rules: dict[str, PolicyRule] = {
            rule.tool: rule for rule in (rules if rules is not None else DEFAULT_RULES)
        }

    def list_rules(self) -> list[PolicyRule]:
        return list(self._rules.values())

    def set_rule(self, rule: PolicyRule) -> None:
        self._rules[rule.tool] = rule

    def check(self, tool_name: str) -> PolicyAction:
        rule = self._match(tool_name)
        if rule is None:
            # Unknown tools require approval rather than running unchecked.
            return PolicyAction.REQUIRE_APPROVAL
        return rule.action

    def reason(self, tool_name: str) -> str:
        rule = self._match(tool_name)
        return rule.reason if rule else "no explicit rule"

    def _match(self, tool_name: str) -> PolicyRule | None:
        if tool_name in self._rules:
            return self._rules[tool_name]
        for pattern, rule in self._rules.items():
            if fnmatch.fnmatch(tool_name, pattern):
                return rule
        return None
