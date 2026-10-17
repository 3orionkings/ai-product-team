"""Registry loader: reads ``registry/{agents,skills,workflows}.json`` and validates them.

Single responsibility: turn the three registry documents into typed, frozen records with derived
indexes (teams, reporting chain, skill usage, body paths) and report every structural and referential
rule from ``docs/architecture/controller-contracts.md`` section 4. The loader never judges whether a
role is *implemented*: a record in JSON is metadata, and a missing role body or skill directory is
reported as ``not_authored`` rather than as a hard failure (M1 runs before M3 authors them).

Loading is tolerant and validation is exhaustive. ``Registry.load`` (or ``Registry.from_data`` for an
in-memory copy) builds what it can from malformed input and ``validate()`` returns every issue as
``"<pointer>: [<code>] <message>"`` where the pointer names the registry file and JSON location.
``hard_issues()`` excludes ``not_authored``; ``ensure_valid()`` raises :class:`ValidationError` when any
hard issue remains.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from ai_product_team import validation as _validation
from ai_product_team.errors import NotFoundError, ValidationError

__all__ = [
    "HUMAN_OWNER",
    "PROPOSAL_OWNER",
    "EXPECTED_AGENT_COUNT",
    "EXPECTED_TEAM_COUNT",
    "LEADERSHIP_TEAM",
    "LEADERSHIP_TEAM_SIZE",
    "STANDARD_TEAM_SIZE",
    "MANAGER_TYPES",
    "Agent",
    "Skill",
    "Stage",
    "Workflow",
    "Team",
    "Issue",
    "Registry",
]

#: The human principal that terminates every reporting chain. Not an agent; never counted.
HUMAN_OWNER = "human-owner"
#: Symbolic stage role bound at runtime to the author of the frozen proposal (needs ``role_binding``).
PROPOSAL_OWNER = "proposal-owner"

EXPECTED_AGENT_COUNT = 64
EXPECTED_TEAM_COUNT = 11
LEADERSHIP_TEAM = "leadership"
LEADERSHIP_TEAM_SIZE = 4
STANDARD_TEAM_SIZE = 6

#: Role types allowed to manage a team or a workflow (the Adversarial Orchestrator manages the challenge team).
MANAGER_TYPES: frozenset[str] = frozenset({"manager", "adversarial_orchestrator"})
_LEADER_TYPES: frozenset[str] = frozenset({"leader"})

_AGENTS_FILE = "agents.json"
_SKILLS_FILE = "skills.json"
_WORKFLOWS_FILE = "workflows.json"
_DEFAULT_SKILL_DIR_TEMPLATE = "skills/<name>"
_DEFAULT_SKILL_BODY = "SKILL.md"


# --------------------------------------------------------------------------------------------------
# Records
# --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Agent:
    """One role from ``registry/agents.json``; fields mirror the JSON record."""

    number: int | None
    id: str
    native_name: str
    name: str
    type: str
    team: str
    reports_to: str
    reviewed_by: str
    description: str
    skill_ids: tuple[str, ...]
    input_contract: str
    output_contract: str
    distinctive_rule: str
    negative_test: str
    write_scope: str
    may_dispatch: bool
    acceptance_authority: str
    status: str
    dispatch_condition: str


@dataclass(frozen=True)
class Skill:
    """One shared method skill from ``registry/skills.json``."""

    id: str
    name: str
    title: str
    summary: str
    provenance: Mapping[str, Any]


@dataclass(frozen=True)
class Stage:
    """One node of a workflow DAG."""

    id: str
    title: str
    role: str
    work: str
    artifact: str
    conditional: str | None = None
    review: bool = False
    independence_required: bool = False
    write_scope: str | None = None
    may_return: tuple[str, ...] = ()
    delegates_to: str | None = None
    role_binding: str | None = None


@dataclass(frozen=True)
class Workflow:
    """One workflow recipe from ``registry/workflows.json``."""

    id: str
    name: str
    entry_skill: str
    title: str
    manager: str
    min_risk: str
    core_cross_host: bool
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    stages: tuple[Stage, ...]
    conditional_specialists: tuple[str, ...]
    acceptance: tuple[str, ...]
    fixture: Mapping[str, Any]

    def stage(self, stage_id: str) -> Stage:
        """Return the stage with ``stage_id`` or raise :class:`NotFoundError`."""
        for stage in self.stages:
            if stage.id == stage_id:
                return stage
        raise NotFoundError(f"workflow {self.id} has no stage {stage_id!r}", details={"workflow": self.id, "stage": stage_id})


@dataclass(frozen=True)
class Team:
    """A team from the ``teams`` list, with its members derived from the agents."""

    id: str
    name: str
    leader: str | None
    manager: str | None
    members: tuple[str, ...] = ()


@dataclass(frozen=True)
class Issue:
    """One validation finding. ``code`` is stable and machine-checkable; ``pointer`` locates the record."""

    code: str
    pointer: str
    message: str

    def __str__(self) -> str:
        return f"{self.pointer}: [{self.code}] {self.message}"


# --------------------------------------------------------------------------------------------------
# Coercion helpers (tolerant: validation reports the schema failures, the loader only has to survive them)
# --------------------------------------------------------------------------------------------------


def _str(value: Any, default: str = "") -> str:
    return value if isinstance(value, str) else default


def _opt_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _bool(value: Any, default: bool = False) -> bool:
    return value if isinstance(value, bool) else default


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _str_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _mapping(value: Any) -> Mapping[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _records(doc: Any, key: str) -> list[Any]:
    if isinstance(doc, dict) and isinstance(doc.get(key), list):
        return list(doc[key])
    return []


def _agent_from(record: Mapping[str, Any]) -> Agent:
    return Agent(
        number=_int(record.get("number")),
        id=_str(record.get("id")),
        native_name=_str(record.get("native_name")),
        name=_str(record.get("name")),
        type=_str(record.get("type")),
        team=_str(record.get("team")),
        reports_to=_str(record.get("reports_to")),
        reviewed_by=_str(record.get("reviewed_by")),
        description=_str(record.get("description")),
        skill_ids=_str_tuple(record.get("skill_ids")),
        input_contract=_str(record.get("input_contract")),
        output_contract=_str(record.get("output_contract")),
        distinctive_rule=_str(record.get("distinctive_rule")),
        negative_test=_str(record.get("negative_test")),
        write_scope=_str(record.get("write_scope")),
        may_dispatch=_bool(record.get("may_dispatch")),
        acceptance_authority=_str(record.get("acceptance_authority")),
        status=_str(record.get("status")),
        dispatch_condition=_str(record.get("dispatch_condition")),
    )


def _skill_from(record: Mapping[str, Any]) -> Skill:
    return Skill(
        id=_str(record.get("id")),
        name=_str(record.get("name")),
        title=_str(record.get("title")),
        summary=_str(record.get("summary")),
        provenance=_mapping(record.get("provenance")),
    )


def _stage_from(record: Mapping[str, Any]) -> Stage:
    return Stage(
        id=_str(record.get("id")),
        title=_str(record.get("title")),
        role=_str(record.get("role")),
        work=_str(record.get("work")),
        artifact=_str(record.get("artifact")),
        conditional=_opt_str(record.get("conditional")),
        review=_bool(record.get("review")),
        independence_required=_bool(record.get("independence_required")),
        write_scope=_opt_str(record.get("write_scope")),
        may_return=_str_tuple(record.get("may_return")),
        delegates_to=_opt_str(record.get("delegates_to")),
        role_binding=_opt_str(record.get("role_binding")),
    )


def _workflow_from(record: Mapping[str, Any]) -> Workflow:
    raw_stages = record.get("stages")
    stages = tuple(_stage_from(s) for s in raw_stages if isinstance(s, dict)) if isinstance(raw_stages, list) else ()
    return Workflow(
        id=_str(record.get("id")),
        name=_str(record.get("name")),
        entry_skill=_str(record.get("entry_skill")),
        title=_str(record.get("title")),
        manager=_str(record.get("manager")),
        min_risk=_str(record.get("min_risk")),
        core_cross_host=_bool(record.get("core_cross_host")),
        inputs=_str_tuple(record.get("inputs")),
        outputs=_str_tuple(record.get("outputs")),
        stages=stages,
        conditional_specialists=_str_tuple(record.get("conditional_specialists")),
        acceptance=_str_tuple(record.get("acceptance")),
        fixture=_mapping(record.get("fixture")),
    )


def _team_from(record: Mapping[str, Any], members: Iterable[str]) -> Team:
    return Team(
        id=_str(record.get("id")),
        name=_str(record.get("name")),
        leader=_opt_str(record.get("leader")),
        manager=_opt_str(record.get("manager")),
        members=tuple(members),
    )


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise NotFoundError(f"registry file not found: {path}", details={"path": str(path)})
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{path.name} is not valid JSON: {exc.msg}", errors=[f"/: {exc.msg} (line {exc.lineno})"], details={"path": str(path)}) from exc


def _load_record_schema(root: Path, name: str) -> dict[str, Any]:
    """Prefer ``<root>/schemas/<name>.schema.json``; fall back to the package schema directory."""
    local = root / "schemas" / f"{name}{_validation.SCHEMA_SUFFIX}"
    if local.is_file():
        try:
            return json.loads(local.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValidationError(f"schema {local.name} is not valid JSON: {exc.msg}", details={"path": str(local)}) from exc
    return _validation.load_schema(name)


# --------------------------------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Registry:
    """Typed view over the three registry documents plus derived indexes.

    ``workflows`` is keyed by both workflow id (``W02``) and name (``shape-feature``); iterate
    ``workflow_ids`` to visit each workflow once. ``agents`` and ``skills`` are keyed by id; ``skills``
    additionally resolves skill names. Raw documents are retained so ``validate()`` can report duplicate
    ids and schema failures that the keyed dictionaries necessarily collapse.
    """

    root: Path
    agents: dict[str, Agent]
    skills: dict[str, Skill]
    workflows: dict[str, Workflow]
    teams: dict[str, Team]
    predicates: dict[str, str]
    budget_modes: dict[str, Any]
    skill_dir_template: str
    skill_body_name: str
    raw_agents: list[Any] = field(repr=False)
    raw_skills: list[Any] = field(repr=False)
    raw_workflows: list[Any] = field(repr=False)
    raw_teams: list[Any] = field(repr=False)
    documents: dict[str, Any] = field(repr=False)

    # -- construction --------------------------------------------------------------------------------

    @classmethod
    def load(cls, root: Path) -> "Registry":
        """Read ``<root>/registry/{agents,skills,workflows}.json`` and build the registry.

        Raises :class:`NotFoundError` when a file is missing and :class:`ValidationError` when one is not
        JSON. Referential problems do not raise here; call :meth:`validate`.
        """
        root = Path(root)
        registry_dir = root / "registry"
        agents_doc = _read_json(registry_dir / _AGENTS_FILE)
        skills_doc = _read_json(registry_dir / _SKILLS_FILE)
        workflows_doc = _read_json(registry_dir / _WORKFLOWS_FILE)
        return cls.from_data(root, agents_doc, skills_doc, workflows_doc)

    @classmethod
    def from_data(cls, root: Path, agents_doc: Any, skills_doc: Any, workflows_doc: Any) -> "Registry":
        """Build a registry from already-parsed documents (tests mutate copies and call this)."""
        root = Path(root)
        raw_agents = _records(agents_doc, "agents")
        raw_teams = _records(agents_doc, "teams")
        raw_skills = _records(skills_doc, "skills")
        raw_workflows = _records(workflows_doc, "workflows")

        agents: dict[str, Agent] = {}
        for record in raw_agents:
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                agents.setdefault(record["id"], _agent_from(record))

        skills: dict[str, Skill] = {}
        for record in raw_skills:
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                skill = _skill_from(record)
                skills.setdefault(skill.id, skill)
                if skill.name:
                    skills.setdefault(skill.name, skill)

        workflows: dict[str, Workflow] = {}
        for record in raw_workflows:
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                workflow = _workflow_from(record)
                workflows.setdefault(workflow.id, workflow)
                if workflow.name:
                    workflows.setdefault(workflow.name, workflow)

        members_by_team: dict[str, list[str]] = {}
        for agent in agents.values():
            members_by_team.setdefault(agent.team, []).append(agent.id)
        teams: dict[str, Team] = {}
        for record in raw_teams:
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                teams.setdefault(record["id"], _team_from(record, members_by_team.get(record["id"], [])))

        predicates: dict[str, str] = {}
        if isinstance(workflows_doc, dict) and isinstance(workflows_doc.get("predicates"), dict):
            predicates = {k: v for k, v in workflows_doc["predicates"].items() if isinstance(k, str) and isinstance(v, str)}
        budget_modes: dict[str, Any] = {}
        if isinstance(workflows_doc, dict) and isinstance(workflows_doc.get("budget_modes"), dict):
            budget_modes = dict(workflows_doc["budget_modes"])

        template = _DEFAULT_SKILL_DIR_TEMPLATE
        body_name = _DEFAULT_SKILL_BODY
        if isinstance(skills_doc, dict) and isinstance(skills_doc.get("naming"), dict):
            declared = skills_doc["naming"].get("skill_directory")
            if isinstance(declared, str) and "<name>" in declared:
                parts = Path(declared)
                if parts.suffix:  # "skills/aipt-method-<name>/SKILL.md" names the body file too
                    template = parts.parent.as_posix()
                    body_name = parts.name
                else:
                    template = parts.as_posix()

        return cls(
            root=root,
            agents=agents,
            skills=skills,
            workflows=workflows,
            teams=teams,
            predicates=predicates,
            budget_modes=budget_modes,
            skill_dir_template=template,
            skill_body_name=body_name,
            raw_agents=raw_agents,
            raw_skills=raw_skills,
            raw_workflows=raw_workflows,
            raw_teams=raw_teams,
            documents={"agents": agents_doc, "skills": skills_doc, "workflows": workflows_doc},
        )

    # -- lookups -------------------------------------------------------------------------------------

    @property
    def workflow_ids(self) -> list[str]:
        """Workflow ids in document order, each once (``workflows`` holds every workflow twice)."""
        seen: list[str] = []
        for workflow in self.workflows.values():
            if workflow.id not in seen:
                seen.append(workflow.id)
        return seen

    @property
    def skill_ids(self) -> list[str]:
        """Skill ids (``S01``...) in document order, each once."""
        seen: list[str] = []
        for skill in self.skills.values():
            if skill.id not in seen:
                seen.append(skill.id)
        return seen

    def agent(self, agent_id: str) -> Agent:
        """Return the agent or raise :class:`NotFoundError`."""
        try:
            return self.agents[agent_id]
        except KeyError:
            raise NotFoundError(f"unknown agent id {agent_id!r}", details={"agent_id": agent_id}) from None

    def skill(self, key: str) -> Skill:
        """Return a skill by id (``S12``) or name (``evidence-and-lineage``) or raise :class:`NotFoundError`."""
        try:
            return self.skills[key]
        except KeyError:
            raise NotFoundError(f"unknown skill {key!r}", details={"skill": key}) from None

    def workflow(self, key: str) -> Workflow:
        """Return a workflow by id (``W02``) or name (``shape-feature``) or raise :class:`NotFoundError`."""
        try:
            return self.workflows[key]
        except KeyError:
            raise NotFoundError(f"unknown workflow {key!r}", details={"workflow": key}) from None

    def is_role(self, role_id: str) -> bool:
        """True when ``role_id`` names an agent or the human owner (the two things a reference may point at)."""
        return role_id == HUMAN_OWNER or role_id in self.agents

    # -- derived indexes -----------------------------------------------------------------------------

    def skill_used_by(self, skill_id: str) -> list[str]:
        """Sorted ids of the agents whose ``skill_ids`` include ``skill_id`` (id or name)."""
        if skill_id in self.skills:
            skill_id = self.skills[skill_id].id
        return sorted(agent.id for agent in self.agents.values() if skill_id in agent.skill_ids)

    def reporting_chain(self, agent_id: str) -> list[str]:
        """Ids from the agent's ``reports_to`` up to and including ``human-owner`` (the agent itself excluded).

        Raises :class:`NotFoundError` for an unknown agent and :class:`ValidationError` when the chain
        cycles or dangles instead of terminating at the human owner.
        """
        start = self.agent(agent_id)
        chain: list[str] = []
        seen = {start.id}
        current = start.reports_to
        while True:
            if current == HUMAN_OWNER:
                chain.append(current)
                return chain
            if current in seen:
                raise ValidationError(
                    f"reports_to cycle reached from {agent_id!r} at {current!r}",
                    errors=[f"/agents/{agent_id}/reports_to: cycle through {current!r}"],
                    details={"agent_id": agent_id, "chain": chain},
                )
            if current not in self.agents:
                raise ValidationError(
                    f"reports_to of {agent_id!r} dangles at {current!r}",
                    errors=[f"/agents/{agent_id}/reports_to: {current!r} is not an agent or human-owner"],
                    details={"agent_id": agent_id, "chain": chain},
                )
            chain.append(current)
            seen.add(current)
            current = self.agents[current].reports_to

    def _first_ancestor_of_type(self, agent_id: str, types: frozenset[str]) -> str | None:
        for ancestor in self._safe_chain(agent_id):
            if ancestor in self.agents and self.agents[ancestor].type in types:
                return ancestor
        return None

    def _safe_chain(self, agent_id: str) -> list[str]:
        """Reporting chain that stops (instead of raising) on a cycle or dangling reference."""
        agent = self.agent(agent_id)
        chain: list[str] = []
        seen = {agent.id}
        current = agent.reports_to
        while current and current not in seen:
            chain.append(current)
            if current not in self.agents:
                break
            seen.add(current)
            current = self.agents[current].reports_to
        return chain

    def manager_of(self, agent_id: str) -> str | None:
        """Nearest manager-type ancestor in the reporting chain, or ``None`` (managers and leadership have none)."""
        return self._first_ancestor_of_type(agent_id, MANAGER_TYPES)

    def director_of(self, agent_id: str) -> str | None:
        """Nearest leader-type ancestor (director) in the reporting chain, or ``None``."""
        return self._first_ancestor_of_type(agent_id, _LEADER_TYPES)

    def team_of(self, agent_id: str) -> Team | None:
        """The agent's team record, or ``None`` when its team id is not declared."""
        return self.teams.get(self.agent(agent_id).team)

    # -- paths ---------------------------------------------------------------------------------------

    def role_body_path(self, agent_id: str) -> Path:
        """``<root>/agents/<id>.md`` for a known agent."""
        return self.root / "agents" / f"{self.agent(agent_id).id}.md"

    def skill_dir(self, skill_id: str) -> Path:
        """Directory holding the skill body, following the ``naming.skill_directory`` template in skills.json.

        With the shipped registry this is ``<root>/skills/aipt-method-<name>/``; without a template it is
        ``<root>/skills/<name>/``. Accepts a skill id or name.
        """
        skill = self.skill(skill_id)
        return self.root / self.skill_dir_template.replace("<name>", skill.name)

    def skill_body_path(self, skill_id: str) -> Path:
        """``skill_dir(skill_id) / SKILL.md`` (body file name taken from the naming template)."""
        return self.skill_dir(skill_id) / self.skill_body_name

    def workflow_body_path(self, key: str) -> Path:
        """``<root>/workflows/<name>.md`` for a known workflow (id or name)."""
        return self.root / "workflows" / f"{self.workflow(key).name}.md"

    # -- validation ----------------------------------------------------------------------------------

    def validate(self) -> list[str]:
        """Every issue as ``"<pointer>: [<code>] <message>"``; empty when the registry is fully valid and authored."""
        return [str(issue) for issue in self.issues()]

    def hard_issues(self) -> list[Issue]:
        """Issues other than ``not_authored`` (which only means the body has not been written yet)."""
        return [issue for issue in self.issues() if issue.code != "not_authored"]

    def ensure_valid(self) -> None:
        """Raise :class:`ValidationError` listing every hard issue; ``not_authored`` alone does not raise."""
        hard = self.hard_issues()
        if hard:
            raise ValidationError(
                f"registry has {len(hard)} validation issue(s)",
                errors=[str(issue) for issue in hard],
                details={"codes": sorted({issue.code for issue in hard})},
            )

    def issues(self) -> list[Issue]:
        """Run every rule from contract section 4 and return structured findings in a deterministic order."""
        out: list[Issue] = []
        self._check_document_shapes(out)
        self._check_schemas(out)
        self._check_duplicates(out)
        self._check_counts(out)
        self._check_agent_references(out)
        self._check_reporting_tree(out)
        self._check_teams(out)
        self._check_skills(out)
        self._check_workflows(out)
        self._check_authored(out)
        return out

    # individual rules ------------------------------------------------------------------------------

    def _check_document_shapes(self, out: list[Issue]) -> None:
        for file_name, key in ((_AGENTS_FILE, "agents"), (_AGENTS_FILE, "teams"), (_SKILLS_FILE, "skills"), (_WORKFLOWS_FILE, "workflows"), (_WORKFLOWS_FILE, "predicates")):
            doc = self.documents.get(file_name.split(".")[0])
            expected = dict if key == "predicates" else list
            if not isinstance(doc, dict):
                out.append(Issue("document_shape", f"registry/{file_name}#/", "top-level value must be an object"))
                continue
            if not isinstance(doc.get(key), expected):
                out.append(Issue("document_shape", f"registry/{file_name}#/{key}", f"'{key}' must be a {expected.__name__}"))

    def _check_schemas(self, out: list[Issue]) -> None:
        for file_name, records, schema_name in (
            (_AGENTS_FILE, self.raw_agents, "registry-agent"),
            (_SKILLS_FILE, self.raw_skills, "registry-skill"),
            (_WORKFLOWS_FILE, self.raw_workflows, "registry-workflow"),
        ):
            schema = _load_record_schema(self.root, schema_name)
            list_key = file_name.split(".")[0]
            for index, record in enumerate(records):
                prefix = f"registry/{file_name}#/{list_key}/{index}"
                for error in _validation.validate(record, schema):
                    pointer, _, message = error.partition(": ")
                    pointer = "" if pointer == "/" else pointer
                    out.append(Issue("schema", f"{prefix}{pointer}", message))

    def _check_duplicates(self, out: list[Issue]) -> None:
        def dupes(records: list[Any], key: str, file_name: str, list_key: str, code: str = "duplicate_id") -> None:
            seen: dict[Any, int] = {}
            for index, record in enumerate(records):
                if not isinstance(record, dict) or key not in record:
                    continue
                value = record[key]
                try:
                    hash(value)
                except TypeError:
                    continue
                if value in seen:
                    out.append(Issue(code, f"registry/{file_name}#/{list_key}/{index}/{key}", f"duplicate {key} {value!r} (first at index {seen[value]})"))
                else:
                    seen[value] = index

        dupes(self.raw_agents, "id", _AGENTS_FILE, "agents")
        dupes(self.raw_agents, "number", _AGENTS_FILE, "agents", code="duplicate_number")
        dupes(self.raw_agents, "native_name", _AGENTS_FILE, "agents", code="duplicate_native_name")
        dupes(self.raw_teams, "id", _AGENTS_FILE, "teams")
        dupes(self.raw_skills, "id", _SKILLS_FILE, "skills")
        dupes(self.raw_skills, "name", _SKILLS_FILE, "skills", code="duplicate_name")
        dupes(self.raw_workflows, "id", _WORKFLOWS_FILE, "workflows")
        dupes(self.raw_workflows, "name", _WORKFLOWS_FILE, "workflows", code="duplicate_name")
        for index, record in enumerate(self.raw_workflows):
            if isinstance(record, dict) and isinstance(record.get("stages"), list):
                seen: dict[str, int] = {}
                for s_index, stage in enumerate(record["stages"]):
                    if isinstance(stage, dict) and isinstance(stage.get("id"), str):
                        if stage["id"] in seen:
                            out.append(Issue("duplicate_stage", f"registry/{_WORKFLOWS_FILE}#/workflows/{index}/stages/{s_index}/id", f"duplicate stage id {stage['id']!r}"))
                        else:
                            seen[stage["id"]] = s_index

    def _check_counts(self, out: list[Issue]) -> None:
        if len(self.raw_agents) != EXPECTED_AGENT_COUNT:
            out.append(Issue("agent_count", f"registry/{_AGENTS_FILE}#/agents", f"expected exactly {EXPECTED_AGENT_COUNT} agents, found {len(self.raw_agents)}"))
        if len(self.raw_teams) != EXPECTED_TEAM_COUNT:
            out.append(Issue("team_count", f"registry/{_AGENTS_FILE}#/teams", f"expected exactly {EXPECTED_TEAM_COUNT} teams, found {len(self.raw_teams)}"))

    def _check_agent_references(self, out: list[Issue]) -> None:
        for index, record in enumerate(self.raw_agents):
            if not isinstance(record, dict):
                continue
            prefix = f"registry/{_AGENTS_FILE}#/agents/{index}"
            for key in ("reports_to", "reviewed_by"):
                target = record.get(key)
                if isinstance(target, str) and not self.is_role(target):
                    out.append(Issue("dangling_reference", f"{prefix}/{key}", f"{key} {target!r} is not an agent id or {HUMAN_OWNER!r}"))
            team = record.get("team")
            if isinstance(team, str) and team not in self.teams:
                out.append(Issue("unknown_team", f"{prefix}/team", f"team {team!r} is not declared in the teams list"))
            if record.get("may_dispatch") is True and record.get("type") != "orchestrator":
                out.append(Issue("dispatch_flag", f"{prefix}/may_dispatch", "may_dispatch is true only for the root orchestrator"))
            native = record.get("native_name")
            agent_id = record.get("id")
            if isinstance(native, str) and isinstance(agent_id, str) and native != f"aipt-{agent_id}":
                out.append(Issue("native_name_mismatch", f"{prefix}/native_name", f"native_name must be 'aipt-{agent_id}', found {native!r}"))

    def _check_reporting_tree(self, out: list[Issue]) -> None:
        index_of = {record.get("id"): i for i, record in enumerate(self.raw_agents) if isinstance(record, dict)}
        reported: set[str] = set()
        for agent_id, agent in self.agents.items():
            seen = [agent_id]
            current = agent.reports_to
            while current and current != HUMAN_OWNER and current in self.agents:
                if current in seen:
                    loop = seen[seen.index(current):]  # members in walk order, one each
                    start = loop.index(min(loop))  # rotate so the report is independent of walk order
                    loop = loop[start:] + loop[:start]
                    cycle = loop + [loop[0]]
                    key = loop[0]
                    if key not in reported:
                        reported.add(key)
                        out.append(Issue("reports_to_cycle", f"registry/{_AGENTS_FILE}#/agents/{index_of.get(key, 0)}/reports_to", "reports_to cycle: " + " -> ".join(cycle)))
                    break
                seen.append(current)
                current = self.agents[current].reports_to

    def _check_teams(self, out: list[Issue]) -> None:
        index_of = {record.get("id"): i for i, record in enumerate(self.raw_agents) if isinstance(record, dict)}
        for t_index, record in enumerate(self.raw_teams):
            if not isinstance(record, dict) or not isinstance(record.get("id"), str):
                out.append(Issue("schema", f"registry/{_AGENTS_FILE}#/teams/{t_index}", "team record must be an object with a string id"))
                continue
            team = self.teams[record["id"]]
            prefix = f"registry/{_AGENTS_FILE}#/teams/{t_index}"
            expected_size = LEADERSHIP_TEAM_SIZE if team.id == LEADERSHIP_TEAM else STANDARD_TEAM_SIZE
            if len(team.members) != expected_size:
                out.append(Issue("team_size", f"{prefix}/id", f"team {team.id!r} must have {expected_size} members, found {len(team.members)}"))
            manager = team.manager
            leader = team.leader
            if manager is not None:
                if manager not in self.agents:
                    out.append(Issue("dangling_reference", f"{prefix}/manager", f"manager {manager!r} is not an agent id"))
                else:
                    manager_agent = self.agents[manager]
                    if manager_agent.type not in MANAGER_TYPES:
                        out.append(Issue("bad_manager", f"{prefix}/manager", f"manager {manager!r} has type {manager_agent.type!r}, expected one of {sorted(MANAGER_TYPES)}"))
                    if manager_agent.team != team.id:
                        out.append(Issue("manager_mismatch", f"{prefix}/manager", f"manager {manager!r} belongs to team {manager_agent.team!r}, not {team.id!r}"))
                    if leader is not None and leader in self.agents and manager_agent.reports_to != leader:
                        out.append(Issue("manager_mismatch", f"registry/{_AGENTS_FILE}#/agents/{index_of.get(manager, 0)}/reports_to", f"team manager {manager!r} reports to {manager_agent.reports_to!r}, expected team leader {leader!r}"))
                    for member in team.members:
                        if member == manager:
                            continue
                        member_agent = self.agents[member]
                        if member_agent.reports_to != manager:
                            out.append(Issue("manager_mismatch", f"registry/{_AGENTS_FILE}#/agents/{index_of.get(member, 0)}/reports_to", f"{member!r} is in team {team.id!r} but reports to {member_agent.reports_to!r}, expected manager {manager!r}"))
            if leader is not None:
                if leader not in self.agents:
                    out.append(Issue("dangling_reference", f"{prefix}/leader", f"leader {leader!r} is not an agent id"))
                elif self.agents[leader].type not in _LEADER_TYPES:
                    out.append(Issue("bad_leader", f"{prefix}/leader", f"leader {leader!r} has type {self.agents[leader].type!r}, expected 'leader'"))

    def _check_skills(self, out: list[Issue]) -> None:
        known = set(self.skill_ids)
        referenced: set[str] = set()
        for index, record in enumerate(self.raw_agents):
            if not isinstance(record, dict) or not isinstance(record.get("skill_ids"), list):
                continue
            for s_index, skill_id in enumerate(record["skill_ids"]):
                if not isinstance(skill_id, str):
                    continue
                referenced.add(skill_id)
                if skill_id not in known:
                    out.append(Issue("missing_skill", f"registry/{_AGENTS_FILE}#/agents/{index}/skill_ids/{s_index}", f"skill {skill_id!r} is not in skills.json"))
        for index, record in enumerate(self.raw_skills):
            if isinstance(record, dict) and isinstance(record.get("id"), str) and record["id"] not in referenced:
                out.append(Issue("unreferenced_skill", f"registry/{_SKILLS_FILE}#/skills/{index}/id", f"skill {record['id']!r} is referenced by no agent"))

    def _check_workflows(self, out: list[Issue]) -> None:
        workflow_ids = set(self.workflow_ids)
        for index, record in enumerate(self.raw_workflows):
            if not isinstance(record, dict):
                continue
            prefix = f"registry/{_WORKFLOWS_FILE}#/workflows/{index}"
            name = record.get("name")
            entry = record.get("entry_skill")
            if isinstance(name, str) and isinstance(entry, str) and entry != f"aipt-{name}":
                out.append(Issue("bad_entry_skill", f"{prefix}/entry_skill", f"entry_skill must be 'aipt-{name}', found {entry!r}"))
            manager = record.get("manager")
            if isinstance(manager, str):
                if manager not in self.agents:
                    out.append(Issue("dangling_reference", f"{prefix}/manager", f"manager {manager!r} is not an agent id"))
                elif self.agents[manager].type not in MANAGER_TYPES:
                    out.append(Issue("bad_manager", f"{prefix}/manager", f"manager {manager!r} has type {self.agents[manager].type!r}, expected one of {sorted(MANAGER_TYPES)}"))
            if isinstance(record.get("conditional_specialists"), list):
                for c_index, role in enumerate(record["conditional_specialists"]):
                    if isinstance(role, str) and not self.is_role(role):
                        out.append(Issue("unknown_role", f"{prefix}/conditional_specialists/{c_index}", f"conditional specialist {role!r} is not an agent id or {HUMAN_OWNER!r}"))
            if not isinstance(record.get("stages"), list):
                continue
            for s_index, stage in enumerate(record["stages"]):
                if not isinstance(stage, dict):
                    continue
                s_prefix = f"{prefix}/stages/{s_index}"
                role = stage.get("role")
                if isinstance(role, str):
                    if role == PROPOSAL_OWNER:
                        if not isinstance(stage.get("role_binding"), str) or not stage["role_binding"]:
                            out.append(Issue("unknown_role", f"{s_prefix}/role", f"{PROPOSAL_OWNER!r} requires a non-empty role_binding"))
                    elif role not in self.agents:
                        out.append(Issue("unknown_role", f"{s_prefix}/role", f"stage role {role!r} is not an agent id (or {PROPOSAL_OWNER!r} with role_binding)"))
                conditional = stage.get("conditional")
                if isinstance(conditional, str) and conditional not in self.predicates:
                    out.append(Issue("unknown_predicate", f"{s_prefix}/conditional", f"conditional {conditional!r} is not a declared predicate"))
                delegates = stage.get("delegates_to")
                if isinstance(delegates, str) and delegates not in workflow_ids:
                    out.append(Issue("dangling_reference", f"{s_prefix}/delegates_to", f"delegates_to {delegates!r} is not a workflow id"))

    def _check_authored(self, out: list[Issue]) -> None:
        for index, record in enumerate(self.raw_agents):
            if isinstance(record, dict) and isinstance(record.get("id"), str) and record["id"] in self.agents:
                path = self.root / "agents" / f"{record['id']}.md"
                if not path.is_file():
                    out.append(Issue("not_authored", f"registry/{_AGENTS_FILE}#/agents/{index}/id", f"role body {path.relative_to(self.root).as_posix()} is missing"))
        for index, record in enumerate(self.raw_skills):
            if not (isinstance(record, dict) and isinstance(record.get("id"), str) and record["id"] in self.skills):
                continue
            skill = self.skills[record["id"]]
            if not skill.name:
                continue
            directory = self.root / self.skill_dir_template.replace("<name>", skill.name)
            rel = directory.relative_to(self.root).as_posix()
            if not directory.is_dir():
                out.append(Issue("not_authored", f"registry/{_SKILLS_FILE}#/skills/{index}/id", f"skill directory {rel}/ is missing"))
            elif not (directory / self.skill_body_name).is_file():
                out.append(Issue("not_authored", f"registry/{_SKILLS_FILE}#/skills/{index}/id", f"skill body {rel}/{self.skill_body_name} is missing"))
