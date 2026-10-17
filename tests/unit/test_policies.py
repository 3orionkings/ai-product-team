"""Unit tests for ai_product_team.policies and the shipped policies/*.json.

Covers: loading the real policy set; authority.json validating against policy-authority and encoding the
PRD section 10 matrix for every role type and special id with R3 non-executable; budgets matching the
registry budget modes plus wall-clock and task timeout; risk ordering, ``risk_at_least`` and keyword
triggers that only ever raise; review-independence and data-handling invariants; redaction patterns that
compile, catch common secret shapes and leave benign receipt text alone; dated routing keywords with
phrases drawn from each workflow's title and inputs; and every load-time check refusing a mutated copy
with ValidationError or PolicyError. Temporary policy trees use tempfile; nothing is written into the
repository tree.
"""

from __future__ import annotations

import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from ai_product_team import policies as P
from ai_product_team import validation as V
from ai_product_team.errors import NotFoundError, PolicyError, ValidationError

REPO = Path(__file__).resolve().parents[2]
POLICY_DIR = REPO / "policies"
WORKFLOWS = json.loads((REPO / "registry" / "workflows.json").read_text(encoding="utf-8"))


def _docs() -> dict:
    return {attr: json.loads((POLICY_DIR / name).read_text(encoding="utf-8")) for attr, name in P.POLICY_FILES.items()}


_DOCS = _docs()


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.docs = copy.deepcopy(_DOCS)

    def build(self) -> P.Policies:
        return P.Policies.from_data(self.root, self.docs)

    def assertRefused(self, exc_type, fragment: str) -> None:
        with self.assertRaises(exc_type) as ctx:
            self.build()
        self.assertIn(fragment, str(ctx.exception) + " " + " ".join(getattr(ctx.exception, "errors", [])))


class RealPolicies(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policies = P.Policies.load(REPO)

    def test_every_file_is_loaded_as_dict(self) -> None:
        for attr in P.POLICY_FILES:
            self.assertIsInstance(getattr(self.policies, attr), dict, attr)
        self.assertEqual(sorted(P.POLICY_FILES.values()), sorted(p.name for p in POLICY_DIR.glob("*.json")))
        self.assertEqual({}, self.policies.extra)

    def test_every_file_is_dated(self) -> None:
        for attr in P.POLICY_FILES:
            doc = getattr(self.policies, attr)
            dated = doc.get("as_of") if attr == "routing_keywords" else doc.get("dated")
            self.assertRegex(dated, r"^\d{4}-\d{2}-\d{2}$", attr)
            self.assertTrue(doc.get("source"), attr)

    # authority -----------------------------------------------------------------------------------

    def test_authority_validates_against_schema(self) -> None:
        self.assertEqual([], V.validate(self.policies.authority, V.load_schema("policy-authority")))

    def test_authority_covers_every_role_type_and_special_id(self) -> None:
        roles = self.policies.authority["roles"]
        self.assertEqual(set(P.ROLE_TYPES), set(roles))
        for role_type, rights in roles.items():
            self.assertEqual(set(P.ACTIONS), set(rights), role_type)
        self.assertEqual({"human-owner", "decision-authority", "independent-auditor"}, set(self.policies.authority["special"]))

    def test_authority_matches_prd_matrix(self) -> None:
        right = self.policies.right
        # Specialist row and the contract's literal example
        self.assertEqual({"propose": True, "review": "assigned_only", "adjudicate": False, "accept": False, "execute": "declared_scope"}, self.policies.rights("specialist"))
        # Manager: no judicial authority, no protected acceptance, no broader authority from title
        self.assertFalse(right("manager", "adjudicate"))
        self.assertFalse(right("manager", "accept"))
        self.assertFalse(right("manager", "execute"))
        # Director: acceptance only through explicit human delegation; no automatic external effects
        self.assertEqual("explicit_human_delegation_only", right("leader", "accept"))
        self.assertFalse(right("leader", "execute"))
        # Challenger: synthetic/local checks only
        self.assertIn("synthetic", right("challenger", "execute"))
        self.assertFalse(right("challenger", "accept"))
        # Judge: adjudicates its assigned question, accepts nothing, executes nothing
        self.assertEqual("assigned_question", right("judge", "adjudicate"))
        self.assertFalse(right("judge", "accept"))
        self.assertFalse(right("judge", "execute"))
        # Decision Authority: within explicit delegation only; acceptance is not execution
        self.assertEqual("delegation_only", right("decision_maker", "accept"))
        self.assertFalse(right("decision_maker", "execute"))
        self.assertEqual(self.policies.rights("decision_maker"), self.policies.rights("decision-authority"))
        # Independent Auditor: accepts its own audit output, reproduces authorized checks
        self.assertEqual("own_audit_output", right("auditor", "accept"))
        self.assertEqual("reproduce_authorized_checks", right("auditor", "execute"))
        self.assertEqual(self.policies.rights("auditor"), self.policies.rights("independent-auditor"))
        # Human owner: the only unconditional acceptor; executes personally
        self.assertIs(True, right("human-owner", "accept"))
        self.assertEqual("personally", right("human-owner", "execute"))
        for principal in list(P.ROLE_TYPES) + ["decision-authority", "independent-auditor"]:
            self.assertIsNot(True, right(principal, "accept"), principal)
            self.assertIsNot(True, right(principal, "execute"), principal)

    def test_risk_tiers_in_authority(self) -> None:
        tiers = self.policies.authority["risk_tiers"]
        self.assertEqual(["R0", "R1", "R2", "R3"], list(tiers))
        self.assertEqual("recommendation", tiers["R0"]["autonomous"])
        self.assertEqual("reversible_local_change_with_delegation", tiers["R1"]["autonomous"])
        self.assertIs(False, tiers["R2"]["autonomous"])
        self.assertEqual(["independent_review", "human_acceptance"], tiers["R2"]["requires"])
        self.assertIs(False, tiers["R3"]["autonomous"])
        self.assertIs(False, tiers["R3"]["executable_in_v0_1"])
        self.assertFalse(self.policies.executable("R3"))
        self.assertTrue(self.policies.executable("R0"))
        self.assertEqual(tiers["R2"], self.policies.tier("R2"))

    def test_rights_lookup_errors(self) -> None:
        with self.assertRaises(NotFoundError):
            self.policies.rights("wizard")
        with self.assertRaises(ValidationError):
            self.policies.right("specialist", "fly")

    # budgets -------------------------------------------------------------------------------------

    def test_budget_modes_match_registry(self) -> None:
        for name, expected in WORKFLOWS["budget_modes"].items():
            mode = self.policies.mode(name)
            for key in ("max_worker_tasks", "concurrent_workers", "max_challenge_rounds"):
                self.assertEqual(expected[key], mode[key], f"{name}.{key}")
        self.assertEqual(["focused", "standard", "deep"], self.policies.modes())

    def test_wallclock_and_timeouts(self) -> None:
        self.assertEqual({"focused": 1800, "standard": 5400, "deep": 10800}, self.policies.budgets["wallclock_limit_s"])
        self.assertEqual(900, self.policies.budgets["task_timeout_s"])
        self.assertEqual(900, self.policies.task_timeout_s())
        self.assertEqual(5400, self.policies.wallclock_limit_s("standard"))
        mode = self.policies.mode("deep")
        self.assertEqual(10800, mode["wallclock_limit_s"])
        self.assertEqual(900, mode["task_timeout_s"])
        self.assertIsNone(mode["tokens_cap"])
        self.assertEqual(24, mode["max_worker_tasks"])

    def test_unknown_mode(self) -> None:
        with self.assertRaises(NotFoundError) as ctx:
            self.policies.mode("turbo")
        self.assertEqual(["focused", "standard", "deep"], ctx.exception.details["modes"])

    # risk ----------------------------------------------------------------------------------------

    def test_risk_order_and_at_least(self) -> None:
        self.assertEqual(["R0", "R1", "R2", "R3"], self.policies.risk_order())
        self.assertEqual("R2", self.policies.risk_at_least("R1", "R2"))
        self.assertEqual("R2", self.policies.risk_at_least("R2", "R1"))
        self.assertEqual("R3", self.policies.risk_at_least("R3", "R0"))
        self.assertEqual("R1", self.policies.risk_at_least("R1", "R1"))
        for a in self.policies.risk_order():
            for b in self.policies.risk_order():
                result = self.policies.risk_at_least(a, b)
                self.assertGreaterEqual(self.policies.risk_rank(result), max(self.policies.risk_rank(a), self.policies.risk_rank(b)))
        with self.assertRaises(ValidationError):
            self.policies.risk_at_least("R1", "R9")

    def test_keyword_triggers_present_and_only_raise(self) -> None:
        keywords = {t["keyword"]: t["min_risk"] for t in self.policies.risk["keyword_triggers"]}
        for word in ("deploy", "publish", "send", "pay", "payment", "delete", "drop", "production", "broaden"):
            self.assertEqual("R3", keywords[word], word)
        for word in ("permission", "credential", "secret", "access"):
            self.assertEqual("R2", keywords[word], word)
        self.assertIs(False, self.policies.risk["model_may_lower_policy_minimum"])
        self.assertTrue(any("cannot lower" in rule for rule in self.policies.risk["rules"]))
        self.assertEqual(["deploy", "credential"], [t["keyword"] for t in self.policies.risk_triggers("Deploy this and rotate the credential")])
        self.assertEqual([], self.policies.risk_triggers("summarize this design"))
        self.assertEqual([], self.policies.risk_triggers("the deployment sender paid productions"), "whole words only")
        self.assertEqual("R0", self.policies.risk_floor("summarize this design"))
        self.assertEqual("R2", self.policies.risk_floor("change the permission model"))
        self.assertEqual("R3", self.policies.risk_floor("please send the email", "R1"))
        self.assertEqual("R2", self.policies.risk_floor("summarize this", "R2"), "the base is never lowered")
        with self.assertRaises(ValidationError):
            self.policies.risk_floor("x", "R9")

    def test_tier_table(self) -> None:
        tiers = {t["id"]: t for t in self.policies.risk["tiers"]}
        self.assertEqual(["R0", "R1", "R2", "R3"], list(tiers))
        self.assertIn("Deploy", tiers["R3"]["example"])
        self.assertIn("human action request", tiers["R3"]["default_authority"])

    # review independence -------------------------------------------------------------------------

    def test_review_independence_rules(self) -> None:
        rules = self.policies.review_independence["rules"]
        self.assertIs(True, rules["author_cannot_review_own_artifact"])
        self.assertIs(True, rules["same_session_is_conflict"])
        self.assertIs(True, rules["same_native_child_id_is_conflict"])
        self.assertIs(True, rules["unknown_origin_is_unverified"])
        self.assertIs(False, rules["manager_review_is_independent_audit"])
        self.assertIs(False, rules["other_model_family_implies_independence"])
        outcomes = self.policies.review_independence["outcomes"]
        self.assertEqual("conflict", outcomes["author_equals_reviewer"]["conflict_check"])
        self.assertEqual("unverified", outcomes["unknown_session"]["conflict_check"])
        self.assertEqual("independence_unverified", outcomes["unknown_session"]["reason"])
        self.assertIs(False, outcomes["manager_of_author_team"]["independent"])
        self.assertEqual({"verified", "unverified", "conflict"}, set(self.policies.review_independence["conflict_check_values"]))

    # data handling -------------------------------------------------------------------------------

    def test_data_handling_defaults(self) -> None:
        dh = self.policies.data_handling
        self.assertIs(False, dh["telemetry"])
        self.assertIs(False, dh["prompt_upload"])
        self.assertIs(False, dh["trace_transmission"])
        self.assertIs(True, dh["public_export_requires_allowlist"])
        self.assertIs(True, dh["demos"]["synthetic_only"])
        self.assertEqual("synthetic", dh["demos"]["access_classification"])

    def test_redaction_patterns_compile_and_match_secret_shapes(self) -> None:
        patterns = self.policies.redaction_patterns()
        rules = self.policies.redaction_rules()
        self.assertEqual(len(rules), len(patterns))
        self.assertTrue(all(isinstance(p, str) for p in patterns))
        compiled = [re.compile(p) for p in patterns]
        samples = {
            "aws_access_key_id": "key AKIAIOSFODNN7EXAMPLE used",
            "bearer_token": "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.abcdefghijklmnop",
            "private_key_block": "-----BEGIN RSA PRIVATE KEY-----\nMIIEow\n-----END RSA PRIVATE KEY-----",
            "generic_api_key_assignment": "API_KEY = 'ZmFrZV9rZXlfdmFsdWVfMTIzNDU2'",
            "generic_api_key_assignment#2": 'password: "correct-horse-battery-staple"',
            "openai_style_key": "sk-abcdefghijklmnopqrstuvwxyz012345",
            "github_token": "ghp_" + "A" * 36,
            "slack_token": "xoxb-1234567890-abcdefghij",
            "google_api_key": "AIza" + "B" * 35,
            "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r_wW1gFWFOEjXk",
        }
        by_name = {r["name"]: re.compile(r["pattern"]) for r in rules}
        for name, text in samples.items():
            base = name.split("#")[0]
            self.assertTrue(by_name[base].search(text), f"{base} must match {text!r}")
            self.assertTrue(any(c.search(text) for c in compiled), name)

    def test_email_redaction_is_optional_and_off(self) -> None:
        entries = {e["name"]: e for e in self.policies.data_handling["redaction"]["patterns"]}
        self.assertIs(False, entries["email_address"]["enabled"])
        self.assertIs(True, entries["email_address"].get("optional"))
        self.assertNotIn(entries["email_address"]["pattern"], self.policies.redaction_patterns())
        self.assertTrue(re.search(entries["email_address"]["pattern"], "mail someone@example.org now"))

    def test_redaction_leaves_benign_receipts_alone(self) -> None:
        benign = (
            "Ran 12 tests in 0.034s\nOK\n"
            "token count: 12; access log shows 3 requests; password policy updated\n"
            "AKIA is a prefix; bearer of bad news; secret_key length must be 40\n"
            "git commit 9fceb02d0ae598e95dc970b74767f19372d61af8\n"
        )
        for rule in self.policies.redaction_rules():
            self.assertIsNone(re.search(rule["pattern"], benign), rule["name"])
        self.assertEqual("[REDACTED:<name>]", self.policies.redaction_replacement())

    # routing keywords ----------------------------------------------------------------------------

    def test_routing_keywords_dated_and_complete(self) -> None:
        rk = self.policies.routing_keywords
        self.assertEqual("2026-10-17", rk["as_of"])
        workflows = self.policies.workflow_keywords()
        self.assertEqual([w["id"] for w in WORKFLOWS["workflows"]], list(workflows))
        for workflow in WORKFLOWS["workflows"]:
            phrases = workflows[workflow["id"]]
            self.assertTrue(4 <= len(phrases) <= 8, f"{workflow['id']} has {len(phrases)} phrases")
            self.assertEqual(len(set(phrases)), len(phrases), workflow["id"])
            haystack = (workflow["title"] + " " + " ".join(workflow["inputs"])).lower()
            self.assertTrue(any(p in haystack for p in phrases), f"{workflow['id']}: no phrase drawn from title/inputs")
            self.assertIn(workflow["name"].replace("-", " "), phrases, f"{workflow['id']}: the workflow name itself is a phrase")

    def test_external_and_narrow_lists(self) -> None:
        external = self.policies.external_action_keywords()
        for word in ("deploy", "publish", "send", "pay", "production"):
            self.assertIn(word, external)
        narrow = self.policies.narrow_request_patterns()
        for phrase in ("summarize", "reword", "rewrite one requirement"):
            self.assertIn(phrase, narrow)
        self.assertFalse(set(external) & set(narrow))
        routes = self.policies.routing_keywords["narrow_routes"]
        self.assertEqual(["context-analyst", "claim-checker"], routes["summarize"])
        self.assertEqual(["requirements-writer"], routes["reword"])
        self.assertTrue(set(routes) <= set(narrow))


class LoadFromDirectory(Base):
    def _write(self, docs: dict | None = None) -> None:
        policy_dir = self.root / "policies"
        policy_dir.mkdir(exist_ok=True)
        for attr, name in P.POLICY_FILES.items():
            (policy_dir / name).write_text(json.dumps((docs or self.docs)[attr]), encoding="utf-8")

    def test_round_trip(self) -> None:
        self._write()
        loaded = P.Policies.load(self.root)
        self.assertEqual(self.docs["authority"], loaded.authority)
        self.assertEqual(self.docs["budgets"], loaded.budgets)
        self.assertEqual(self.root, loaded.root)

    def test_extra_policy_files_are_exposed(self) -> None:
        self._write()
        (self.root / "policies" / "compatibility.json").write_text(json.dumps({"dated": "2026-10-17", "hosts": {}}), encoding="utf-8")
        loaded = P.Policies.load(self.root)
        self.assertEqual({"compatibility": {"dated": "2026-10-17", "hosts": {}}}, loaded.extra)

    def test_missing_file_raises_not_found(self) -> None:
        self._write()
        (self.root / "policies" / "risk.json").unlink()
        with self.assertRaises(NotFoundError):
            P.Policies.load(self.root)
        with self.assertRaises(NotFoundError):
            P.Policies.load(self.root / "nowhere")

    def test_invalid_json_raises_validation_error(self) -> None:
        self._write()
        (self.root / "policies" / "budgets.json").write_text("{", encoding="utf-8")
        with self.assertRaises(ValidationError):
            P.Policies.load(self.root)

    def test_from_data_requires_every_document(self) -> None:
        del self.docs["risk"]
        with self.assertRaises(NotFoundError):
            self.build()
        self.docs = copy.deepcopy(_DOCS)
        self.docs["budgets"] = []
        with self.assertRaises(ValidationError):
            self.build()


class AuthorityChecks(Base):
    def test_schema_violation(self) -> None:
        self.docs["authority"]["roles"]["specialist"]["propose"] = 3
        self.assertRefused(ValidationError, "/roles/specialist/propose")
        self.docs = copy.deepcopy(_DOCS)
        self.docs["authority"]["unexpected"] = True
        self.assertRefused(ValidationError, "unexpected")

    def test_missing_role_type(self) -> None:
        del self.docs["authority"]["roles"]["judge"]
        self.assertRefused(ValidationError, "/roles/judge")

    def test_missing_action(self) -> None:
        del self.docs["authority"]["roles"]["judge"]["accept"]
        self.assertRefused(ValidationError, "/roles/judge/accept")

    def test_missing_human_owner(self) -> None:
        del self.docs["authority"]["special"]["human-owner"]
        self.assertRefused(ValidationError, "/special/human-owner")

    def test_missing_tier(self) -> None:
        del self.docs["authority"]["risk_tiers"]["R2"]
        self.assertRefused(ValidationError, "/risk_tiers/R2")

    def test_r3_execution_is_refused(self) -> None:
        self.docs["authority"]["risk_tiers"]["R3"]["executable_in_v0_1"] = True
        with self.assertRaises(PolicyError) as ctx:
            self.build()
        self.assertEqual("r3_execution_forbidden", ctx.exception.details["reason"])

    def test_r3_autonomy_is_refused(self) -> None:
        self.docs["authority"]["risk_tiers"]["R3"]["autonomous"] = "recommendation"
        with self.assertRaises(PolicyError):
            self.build()
        self.docs = copy.deepcopy(_DOCS)
        del self.docs["authority"]["risk_tiers"]["R3"]["executable_in_v0_1"]
        with self.assertRaises(PolicyError):
            self.build()

    def test_unconditional_acceptance_is_refused_for_non_humans(self) -> None:
        self.docs["authority"]["roles"]["manager"]["accept"] = True
        with self.assertRaises(PolicyError) as ctx:
            self.build()
        self.assertEqual("unconditional_acceptance", ctx.exception.details["reason"])
        self.docs = copy.deepcopy(_DOCS)
        self.docs["authority"]["special"]["decision-authority"]["accept"] = True
        with self.assertRaises(PolicyError):
            self.build()


class BudgetChecks(Base):
    def test_missing_wallclock_for_mode(self) -> None:
        del self.docs["budgets"]["wallclock_limit_s"]["deep"]
        self.assertRefused(ValidationError, "/wallclock_limit_s/deep")

    def test_wallclock_disagreement(self) -> None:
        self.docs["budgets"]["modes"]["deep"]["wallclock_limit_s"] = 1
        self.assertRefused(ValidationError, "/modes/deep/wallclock_limit_s")

    def test_bad_mode_values(self) -> None:
        self.docs["budgets"]["modes"]["focused"]["max_worker_tasks"] = "four"
        self.assertRefused(ValidationError, "/modes/focused/max_worker_tasks")
        self.docs = copy.deepcopy(_DOCS)
        self.docs["budgets"]["modes"]["focused"]["concurrent_workers"] = 0
        self.assertRefused(ValidationError, "/modes/focused/concurrent_workers")

    def test_missing_task_timeout(self) -> None:
        del self.docs["budgets"]["task_timeout_s"]
        self.assertRefused(ValidationError, "/task_timeout_s")

    def test_unknown_wallclock_mode(self) -> None:
        self.docs["budgets"]["wallclock_limit_s"]["turbo"] = 10
        self.assertRefused(ValidationError, "/wallclock_limit_s/turbo")


class RiskChecks(Base):
    def test_order_must_contain_every_tier(self) -> None:
        self.docs["risk"]["order"] = ["R0", "R1", "R2"]
        self.assertRefused(ValidationError, "'R3' is missing")

    def test_tiers_must_match_order(self) -> None:
        self.docs["risk"]["tiers"].pop()
        self.assertRefused(ValidationError, "no entry for tier 'R3'")

    def test_trigger_min_risk_must_be_known(self) -> None:
        self.docs["risk"]["keyword_triggers"][0]["min_risk"] = "R7"
        self.assertRefused(ValidationError, "/keyword_triggers/0/min_risk")

    def test_trigger_keyword_must_be_non_empty(self) -> None:
        self.docs["risk"]["keyword_triggers"][0]["keyword"] = " "
        self.assertRefused(ValidationError, "/keyword_triggers/0/keyword")

    def test_model_may_not_lower_minimum(self) -> None:
        self.docs["risk"]["model_may_lower_policy_minimum"] = True
        self.assertRefused(ValidationError, "/model_may_lower_policy_minimum")


class IndependenceAndDataChecks(Base):
    def test_manager_review_cannot_become_independent(self) -> None:
        self.docs["review_independence"]["rules"]["manager_review_is_independent_audit"] = True
        self.assertRefused(ValidationError, "/rules/manager_review_is_independent_audit")

    def test_author_review_rule_cannot_be_disabled(self) -> None:
        self.docs["review_independence"]["rules"]["author_cannot_review_own_artifact"] = False
        self.assertRefused(ValidationError, "/rules/author_cannot_review_own_artifact")

    def test_telemetry_cannot_be_enabled(self) -> None:
        self.docs["data_handling"]["telemetry"] = True
        self.assertRefused(ValidationError, "/telemetry")

    def test_public_export_allowlist_required(self) -> None:
        self.docs["data_handling"]["public_export_requires_allowlist"] = False
        self.assertRefused(ValidationError, "/public_export_requires_allowlist")

    def test_demos_synthetic_only(self) -> None:
        self.docs["data_handling"]["demos"]["synthetic_only"] = False
        self.assertRefused(ValidationError, "/demos/synthetic_only")

    def test_bad_regex_refused(self) -> None:
        self.docs["data_handling"]["redaction"]["patterns"][0]["pattern"] = "("
        self.assertRefused(ValidationError, "does not compile")

    def test_duplicate_pattern_name_refused(self) -> None:
        patterns = self.docs["data_handling"]["redaction"]["patterns"]
        patterns.append(dict(patterns[0]))
        self.assertRefused(ValidationError, "duplicate")

    def test_enabled_defaults_to_true(self) -> None:
        patterns = self.docs["data_handling"]["redaction"]["patterns"]
        del patterns[0]["enabled"]
        policies = self.build()
        self.assertIn(patterns[0]["pattern"], policies.redaction_patterns())


class RoutingKeywordChecks(Base):
    def test_as_of_must_be_a_date(self) -> None:
        self.docs["routing_keywords"]["as_of"] = "yesterday"
        self.assertRefused(ValidationError, "/as_of")

    def test_workflow_keys_and_phrases(self) -> None:
        self.docs["routing_keywords"]["workflows"]["shape-feature"] = ["x"]
        self.assertRefused(ValidationError, "/workflows/shape-feature")
        self.docs = copy.deepcopy(_DOCS)
        self.docs["routing_keywords"]["workflows"]["W02"] = []
        self.assertRefused(ValidationError, "/workflows/W02")

    def test_lists_must_be_non_empty_strings(self) -> None:
        self.docs["routing_keywords"]["external_action_keywords"] = []
        self.assertRefused(ValidationError, "/external_action_keywords")
        self.docs = copy.deepcopy(_DOCS)
        self.docs["routing_keywords"]["narrow_request_patterns"] = ["summarize", 3]
        self.assertRefused(ValidationError, "/narrow_request_patterns")


if __name__ == "__main__":
    unittest.main()
