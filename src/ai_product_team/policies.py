"""Policy loader: reads ``policies/*.json`` and exposes them as validated plain dicts with small helpers.

Single responsibility: make the dated policy files (authority, budgets, risk, review independence, data
handling, routing keywords) available to the controller, router, decisions and receipts modules in one
validated object. ``authority.json`` is validated against ``schemas/policy-authority.schema.json``; the
other files are checked for the shape the contract fixes. Invariants the architecture states as
non-negotiable are enforced at load time so that an edited file cannot quietly widen authority: no tier
grants autonomous or executable R3, telemetry stays off, the author never reviews its own artifact, a
manager review is never an independent audit, and a model never lowers an explicit policy minimum.

The helpers here only read policy: ``mode()`` merges a budget mode with its wall-clock and task timeout,
``risk_at_least()`` returns the higher of two tiers, ``risk_triggers()`` matches the keyword triggers that
raise risk, and ``redaction_patterns()`` lists the enabled secret-shaped regexes for receipt logs.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from ai_product_team import validation as _validation
from ai_product_team.errors import NotFoundError, PolicyError, ValidationError

__all__ = [
    "POLICY_FILES",
    "ROLE_TYPES",
    "ACTIONS",
    "DEFAULT_RISK_ORDER",
    "Policies",
]

#: Attribute name → file under ``policies/``. Every file is required.
POLICY_FILES: dict[str, str] = {
    "authority": "authority.json",
    "budgets": "budgets.json",
    "risk": "risk.json",
    "review_independence": "review-independence.json",
    "data_handling": "data-handling.json",
    "routing_keywords": "routing-keywords.json",
}

#: The role types every rights table must cover (contract section 3 ``role_type`` enum).
ROLE_TYPES: tuple[str, ...] = (
    "leader",
    "orchestrator",
    "manager",
    "specialist",
    "steward",
    "reviewer",
    "builder",
    "executor",
    "adversarial_orchestrator",
    "challenger",
    "judge",
    "decision_maker",
    "auditor",
)
#: Actions a rights table grants or withholds.
ACTIONS: tuple[str, ...] = ("propose", "review", "adjudicate", "accept", "execute")
DEFAULT_RISK_ORDER: tuple[str, ...] = ("R0", "R1", "R2", "R3")
_REQUIRED_SPECIAL = ("human-owner",)
_REQUIRED_MODE_KEYS = ("max_worker_tasks", "concurrent_workers", "max_challenge_rounds")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise NotFoundError(f"policy file not found: {path}", details={"path": str(path)})
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{path.name} is not valid JSON: {exc.msg}", errors=[f"/: {exc.msg} (line {exc.lineno})"], details={"path": str(path)}) from exc


def _load_schema(root: Path, name: str) -> dict[str, Any]:
    local = root / "schemas" / f"{name}{_validation.SCHEMA_SUFFIX}"
    if local.is_file():
        try:
            return json.loads(local.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValidationError(f"schema {local.name} is not valid JSON: {exc.msg}", details={"path": str(local)}) from exc
    return _validation.load_schema(name)


@dataclass(frozen=True)
class Policies:
    """Validated policy documents as plain dicts, plus read-only helpers."""

    root: Path
    authority: dict[str, Any]
    budgets: dict[str, Any]
    risk: dict[str, Any]
    review_independence: dict[str, Any]
    data_handling: dict[str, Any]
    routing_keywords: dict[str, Any]
    extra: dict[str, dict[str, Any]] = field(default_factory=dict, repr=False)

    # -- construction --------------------------------------------------------------------------------

    @classmethod
    def load(cls, root: Path) -> "Policies":
        """Read every ``<root>/policies/*.json`` and validate it.

        Raises :class:`NotFoundError` for a missing required file, :class:`ValidationError` for a file
        that is not JSON or has the wrong shape, and :class:`PolicyError` when a file would grant what the
        architecture forbids (for example an executable R3 tier).
        """
        root = Path(root)
        policy_dir = root / "policies"
        documents: dict[str, Any] = {}
        for attr, file_name in POLICY_FILES.items():
            documents[attr] = _read_json(policy_dir / file_name)
        if policy_dir.is_dir():
            known = set(POLICY_FILES.values())
            for path in sorted(policy_dir.glob("*.json")):
                if path.name not in known:
                    documents[path.stem] = _read_json(path)
        return cls.from_data(root, documents)

    @classmethod
    def from_data(cls, root: Path, documents: Mapping[str, Any]) -> "Policies":
        """Build from already-parsed documents keyed by attribute name (``authority`` ...) or extra file stem."""
        root = Path(root)
        missing = [attr for attr in POLICY_FILES if attr not in documents]
        if missing:
            raise NotFoundError(f"policy documents missing: {missing}", details={"missing": missing})
        for attr in POLICY_FILES:
            if not isinstance(documents[attr], dict):
                raise ValidationError(f"policies/{POLICY_FILES[attr]} must be a JSON object", errors=[f"/: expected object"])
        extra = {key: value for key, value in documents.items() if key not in POLICY_FILES and isinstance(value, dict)}
        policies = cls(
            root=root,
            authority=dict(documents["authority"]),
            budgets=dict(documents["budgets"]),
            risk=dict(documents["risk"]),
            review_independence=dict(documents["review_independence"]),
            data_handling=dict(documents["data_handling"]),
            routing_keywords=dict(documents["routing_keywords"]),
            extra=extra,
        )
        policies._validate_all(root)
        return policies

    # -- validation ----------------------------------------------------------------------------------

    def _validate_all(self, root: Path) -> None:
        self._validate_risk()
        self._validate_authority(root)
        self._validate_budgets()
        self._validate_review_independence()
        self._validate_data_handling()
        self._validate_routing_keywords()

    @staticmethod
    def _fail(file_name: str, errors: list[str]) -> None:
        if errors:
            raise ValidationError(f"policies/{file_name} is invalid", errors=errors, details={"file": f"policies/{file_name}"})

    def _validate_risk(self) -> None:
        errors: list[str] = []
        order = self.risk.get("order")
        if not isinstance(order, list) or not order or not all(isinstance(t, str) for t in order) or len(set(order)) != len(order):
            errors.append("/order: must be a non-empty list of unique tier ids")
            order = []
        for required in DEFAULT_RISK_ORDER:
            if required not in order:
                errors.append(f"/order: tier {required!r} is missing")
        tiers = self.risk.get("tiers")
        if not isinstance(tiers, list):
            errors.append("/tiers: must be a list of tier objects")
        else:
            ids = []
            for index, tier in enumerate(tiers):
                if not isinstance(tier, dict) or not isinstance(tier.get("id"), str):
                    errors.append(f"/tiers/{index}: must be an object with a string id")
                    continue
                ids.append(tier["id"])
                if tier["id"] not in order:
                    errors.append(f"/tiers/{index}/id: {tier['id']!r} is not in /order")
            for tier_id in order:
                if tier_id not in ids:
                    errors.append(f"/tiers: no entry for tier {tier_id!r}")
        triggers = self.risk.get("keyword_triggers")
        if not isinstance(triggers, list) or not triggers:
            errors.append("/keyword_triggers: must be a non-empty list")
        else:
            for index, trigger in enumerate(triggers):
                if not isinstance(trigger, dict):
                    errors.append(f"/keyword_triggers/{index}: must be an object")
                    continue
                keyword = trigger.get("keyword")
                if not isinstance(keyword, str) or not keyword.strip():
                    errors.append(f"/keyword_triggers/{index}/keyword: must be a non-empty string")
                if trigger.get("min_risk") not in order:
                    errors.append(f"/keyword_triggers/{index}/min_risk: {trigger.get('min_risk')!r} is not a known tier")
        if self.risk.get("model_may_lower_policy_minimum") is not False:
            errors.append("/model_may_lower_policy_minimum: must be false (a model cannot lower an explicit policy minimum)")
        self._fail(POLICY_FILES["risk"], errors)

    def _validate_authority(self, root: Path) -> None:
        schema = _load_schema(root, "policy-authority")
        errors = _validation.validate(self.authority, schema)
        self._fail(POLICY_FILES["authority"], errors)
        roles = self.authority.get("roles", {})
        for role_type in ROLE_TYPES:
            if role_type not in roles:
                errors.append(f"/roles/{role_type}: rights for role type {role_type!r} are missing")
            else:
                for action in ACTIONS:
                    if action not in roles[role_type]:
                        errors.append(f"/roles/{role_type}/{action}: right is missing")
        special = self.authority.get("special", {})
        for principal in _REQUIRED_SPECIAL:
            if principal not in special:
                errors.append(f"/special/{principal}: rights for {principal!r} are missing")
        tiers = self.authority.get("risk_tiers", {})
        for tier_id in self.risk_order():
            if tier_id not in tiers:
                errors.append(f"/risk_tiers/{tier_id}: tier {tier_id!r} from risk.json is missing")
        self._fail(POLICY_FILES["authority"], errors)
        top = self.risk_order()[-1]
        top_tier = tiers.get(top, {})
        if top_tier.get("autonomous") not in (False, None) or top_tier.get("executable_in_v0_1") is not False:
            raise PolicyError(
                f"authority.json grants {top} autonomy or execution; no tier may execute {top} in v0.1",
                details={"tier": top, "value": top_tier, "reason": "r3_execution_forbidden"},
            )
        for principal, rights in list(roles.items()) + list(special.items()):
            if principal == "human-owner":
                continue
            if rights.get("accept") is True:
                raise PolicyError(
                    f"authority.json grants unconditional acceptance to {principal!r}; only the human owner accepts unconditionally",
                    details={"principal": principal, "reason": "unconditional_acceptance"},
                )

    def _validate_budgets(self) -> None:
        errors: list[str] = []
        modes = self.budgets.get("modes")
        if not isinstance(modes, dict) or not modes:
            errors.append("/modes: must be a non-empty object keyed by budget mode")
            modes = {}
        wallclock = self.budgets.get("wallclock_limit_s")
        if not isinstance(wallclock, dict):
            errors.append("/wallclock_limit_s: must be an object keyed by budget mode")
            wallclock = {}
        for name, mode in modes.items():
            if not isinstance(mode, dict):
                errors.append(f"/modes/{name}: must be an object")
                continue
            for key in _REQUIRED_MODE_KEYS:
                if not _is_int(mode.get(key)) or mode[key] < 0:
                    errors.append(f"/modes/{name}/{key}: must be a non-negative integer")
            if _is_int(mode.get("concurrent_workers")) and mode["concurrent_workers"] < 1:
                errors.append(f"/modes/{name}/concurrent_workers: must be at least 1")
            limit = wallclock.get(name)
            if not _is_int(limit) or limit <= 0:
                errors.append(f"/wallclock_limit_s/{name}: must be a positive integer")
            elif "wallclock_limit_s" in mode and mode["wallclock_limit_s"] != limit:
                errors.append(f"/modes/{name}/wallclock_limit_s: {mode['wallclock_limit_s']!r} disagrees with /wallclock_limit_s/{name} {limit!r}")
        for name in wallclock:
            if name not in modes:
                errors.append(f"/wallclock_limit_s/{name}: no such mode under /modes")
        timeout = self.budgets.get("task_timeout_s")
        if not _is_int(timeout) or timeout <= 0:
            errors.append("/task_timeout_s: must be a positive integer")
        self._fail(POLICY_FILES["budgets"], errors)

    def _validate_review_independence(self) -> None:
        errors: list[str] = []
        rules = self.review_independence.get("rules")
        if not isinstance(rules, dict):
            errors.append("/rules: must be an object")
            rules = {}
        expected = {
            "author_cannot_review_own_artifact": True,
            "same_session_is_conflict": True,
            "unknown_origin_is_unverified": True,
            "manager_review_is_independent_audit": False,
        }
        for key, value in expected.items():
            if rules.get(key) is not value:
                errors.append(f"/rules/{key}: must be {str(value).lower()}")
        self._fail(POLICY_FILES["review_independence"], errors)

    def _validate_data_handling(self) -> None:
        errors: list[str] = []
        if self.data_handling.get("telemetry") is not False:
            errors.append("/telemetry: must be false")
        if self.data_handling.get("public_export_requires_allowlist") is not True:
            errors.append("/public_export_requires_allowlist: must be true")
        demos = self.data_handling.get("demos")
        if not isinstance(demos, dict) or demos.get("synthetic_only") is not True:
            errors.append("/demos/synthetic_only: must be true")
        redaction = self.data_handling.get("redaction")
        patterns = redaction.get("patterns") if isinstance(redaction, dict) else None
        if not isinstance(patterns, list) or not patterns:
            errors.append("/redaction/patterns: must be a non-empty list")
        else:
            names: set[str] = set()
            for index, entry in enumerate(patterns):
                if not isinstance(entry, dict):
                    errors.append(f"/redaction/patterns/{index}: must be an object")
                    continue
                name = entry.get("name")
                if not isinstance(name, str) or not name:
                    errors.append(f"/redaction/patterns/{index}/name: must be a non-empty string")
                elif name in names:
                    errors.append(f"/redaction/patterns/{index}/name: duplicate {name!r}")
                else:
                    names.add(name)
                pattern = entry.get("pattern")
                if not isinstance(pattern, str) or not pattern:
                    errors.append(f"/redaction/patterns/{index}/pattern: must be a non-empty string")
                else:
                    try:
                        re.compile(pattern)
                    except re.error as exc:
                        errors.append(f"/redaction/patterns/{index}/pattern: does not compile ({exc})")
                if "enabled" in entry and not isinstance(entry["enabled"], bool):
                    errors.append(f"/redaction/patterns/{index}/enabled: must be a boolean")
        self._fail(POLICY_FILES["data_handling"], errors)

    def _validate_routing_keywords(self) -> None:
        errors: list[str] = []
        as_of = self.routing_keywords.get("as_of")
        if not isinstance(as_of, str) or not _DATE_RE.match(as_of):
            errors.append("/as_of: must be a YYYY-MM-DD date string")
        workflows = self.routing_keywords.get("workflows")
        if not isinstance(workflows, dict) or not workflows:
            errors.append("/workflows: must be a non-empty object keyed by workflow id")
        else:
            for workflow_id, phrases in workflows.items():
                if not re.match(r"^W[0-9]{2}$", workflow_id):
                    errors.append(f"/workflows/{workflow_id}: key must be a workflow id like W01")
                if not isinstance(phrases, list) or not phrases or not all(isinstance(p, str) and p.strip() for p in phrases):
                    errors.append(f"/workflows/{workflow_id}: must be a non-empty list of phrases")
        for key in ("external_action_keywords", "narrow_request_patterns"):
            value = self.routing_keywords.get(key)
            if not isinstance(value, list) or not value or not all(isinstance(p, str) and p.strip() for p in value):
                errors.append(f"/{key}: must be a non-empty list of strings")
        self._fail(POLICY_FILES["routing_keywords"], errors)

    # -- budgets -------------------------------------------------------------------------------------

    def modes(self) -> list[str]:
        """Budget mode names in file order."""
        return list(self.budgets["modes"].keys())

    def mode(self, name: str) -> dict[str, Any]:
        """Budget limits for ``name`` merged with its ``wallclock_limit_s`` and the default ``task_timeout_s``."""
        try:
            base = self.budgets["modes"][name]
        except KeyError:
            raise NotFoundError(f"unknown budget mode {name!r}", details={"mode": name, "modes": self.modes()}) from None
        merged = dict(base)
        merged["wallclock_limit_s"] = self.budgets["wallclock_limit_s"][name]
        merged.setdefault("task_timeout_s", self.budgets["task_timeout_s"])
        merged.setdefault("tokens_cap", None)
        return merged

    def wallclock_limit_s(self, name: str) -> int:
        """Wall-clock ceiling in seconds for a budget mode."""
        return int(self.mode(name)["wallclock_limit_s"])

    def task_timeout_s(self) -> int:
        """Default per-task timeout in seconds."""
        return int(self.budgets["task_timeout_s"])

    # -- risk ----------------------------------------------------------------------------------------

    def risk_order(self) -> list[str]:
        """Risk tiers from lowest to highest."""
        return list(self.risk["order"])

    def risk_rank(self, tier: str) -> int:
        """Position of ``tier`` in the order; unknown tiers raise :class:`ValidationError`."""
        order = self.risk_order()
        if tier not in order:
            raise ValidationError(f"unknown risk tier {tier!r}", errors=[f"/risk_tier: {tier!r} is not one of {order}"])
        return order.index(tier)

    def risk_at_least(self, a: str, b: str) -> str:
        """The higher of two tiers. Risk is only ever raised: ``risk_at_least(policy_min, proposed)`` never lowers it."""
        return a if self.risk_rank(a) >= self.risk_rank(b) else b

    def risk_triggers(self, text: str) -> list[dict[str, Any]]:
        """Keyword triggers whose keyword occurs in ``text`` (case-insensitive, whole words), in file order."""
        matches: list[dict[str, Any]] = []
        for trigger in self.risk["keyword_triggers"]:
            keyword = trigger["keyword"]
            if re.search(r"(?<![a-z0-9])" + re.escape(keyword.lower()) + r"(?![a-z0-9])", text.lower()):
                matches.append(dict(trigger))
        return matches

    def risk_floor(self, text: str, base: str = "R0") -> str:
        """``base`` raised by every matching trigger's ``min_risk``; never lower than ``base``."""
        tier = base
        self.risk_rank(tier)
        for trigger in self.risk_triggers(text):
            tier = self.risk_at_least(tier, trigger["min_risk"])
        return tier

    def tier(self, tier: str) -> dict[str, Any]:
        """The authority entry for a tier (``autonomous``, ``requires``, ``executable_in_v0_1``)."""
        self.risk_rank(tier)
        return dict(self.authority["risk_tiers"][tier])

    def executable(self, tier: str) -> bool:
        """Whether any code path may execute at this tier in v0.1 (always false for the top tier)."""
        return self.tier(tier).get("executable_in_v0_1") is True

    # -- authority -----------------------------------------------------------------------------------

    def rights(self, principal: str) -> dict[str, Any]:
        """Rights table for a special id (``human-owner``, ``decision-authority``) or a role type.

        Special ids take precedence over role types. Unknown principals raise :class:`NotFoundError`.
        """
        special = self.authority.get("special", {})
        if principal in special:
            return dict(special[principal])
        roles = self.authority.get("roles", {})
        if principal in roles:
            return dict(roles[principal])
        raise NotFoundError(f"no authority entry for {principal!r}", details={"principal": principal})

    def right(self, principal: str, action: str) -> bool | str:
        """One right: ``True``, ``False`` or a qualifier string such as ``assigned_only``. Missing → ``False``."""
        if action not in ACTIONS:
            raise ValidationError(f"unknown action {action!r}", errors=[f"/action: {action!r} is not one of {list(ACTIONS)}"])
        return self.rights(principal).get(action, False)

    # -- data handling -------------------------------------------------------------------------------

    def redaction_rules(self) -> list[dict[str, Any]]:
        """Enabled redaction entries (``name``, ``pattern`` and any notes); ``enabled`` defaults to true."""
        return [dict(entry) for entry in self.data_handling["redaction"]["patterns"] if entry.get("enabled", True)]

    def redaction_patterns(self) -> list[str]:
        """Regex strings for the enabled redaction rules, for receipts and exports."""
        return [entry["pattern"] for entry in self.redaction_rules()]

    def redaction_replacement(self) -> str:
        """Replacement template; ``<name>`` is substituted with the rule name."""
        value = self.data_handling["redaction"].get("replacement")
        return value if isinstance(value, str) and value else "[REDACTED]"

    # -- routing -------------------------------------------------------------------------------------

    def workflow_keywords(self) -> dict[str, list[str]]:
        """Trigger phrases per workflow id."""
        return {key: list(value) for key, value in self.routing_keywords["workflows"].items()}

    def external_action_keywords(self) -> list[str]:
        """Phrases that mark a request as an external action (routing forces the top risk tier)."""
        return list(self.routing_keywords["external_action_keywords"])

    def narrow_request_patterns(self) -> list[str]:
        """Phrases that mark a narrow request which must yield a narrow plan."""
        return list(self.routing_keywords["narrow_request_patterns"])
