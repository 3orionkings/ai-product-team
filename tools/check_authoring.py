#!/usr/bin/env python3
"""Authoring gates for role bodies and shared skills.

This is the automated half of ``docs/architecture/authoring-contract.md`` section 5: gate 1 (structure),
gate 2 (prohibitions), gate 3 (non-duplication) and gate 4 (registry agreement). Gate 5, the reviewer
pass, is a human reading and is not attempted here.

Usage::

    python3 tools/check_authoring.py skills [--root DIR] [--json]
    python3 tools/check_authoring.py agents [--root DIR] [--json]

``skills`` checks every ``skills/<name>/SKILL.md`` (sections 3 and 5 of the contract). ``agents`` checks
every ``agents/<id>.md`` (sections 2 and 5) against ``registry/agents.json``; ``registry/skills.json``
supplies the skill name/id pairs for both commands when it exists. A registry entry with no body yet is
listed as ``not_authored``, which is a state and never a failure, so the tool works on an empty or partial
``agents/`` directory.

Exit status: 0 when every checked file passes, 1 when at least one file fails, 2 when the run itself
could not be performed (missing root, unreadable registry).

Severities: ``blocking`` and ``major`` fail a file; ``warning`` and ``info`` do not.

``--json`` prints ``{"files": [{"path", "ok", "status", "findings": [{"gate", "severity", "message",
"line"?}]}], "summary": {"checked", "passed", "failed", "warnings", "not_authored"}}``.

Standard library only; Python 3.11 or newer.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "Finding",
    "FileResult",
    "Frontmatter",
    "GateError",
    "Section",
    "build_report",
    "check_agent",
    "check_headings",
    "check_length",
    "check_skill",
    "jaccard",
    "main",
    "near_duplicate_findings",
    "outline",
    "parse_frontmatter",
    "run_agents",
    "run_skills",
    "scan_prohibited",
    "shingles",
]

# --------------------------------------------------------------------------------------------------
# Contract constants
# --------------------------------------------------------------------------------------------------

SKILL_NAME_RE = re.compile(r"^aipt-method-[a-z0-9]+(-[a-z0-9]+)*$")
SKILL_NAME_MAX = 64
SKILL_ID_RE = re.compile(r"^S(0[1-9]|1[0-9]|2[0-8])$")
PROVENANCE_VALUES = frozenset({"adapt", "newly_authored"})
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
METADATA_KEYS: tuple[str, ...] = ("aipt_skill_id", "aipt_provenance", "aipt_version")
FRONTMATTER_KEYS: frozenset[str] = frozenset({"name", "description", "license", "metadata"})
DESCRIPTION_MAX = 1024
DESCRIPTION_WARN = 600

SKILL_HEADINGS: tuple[str, ...] = (
    "Purpose",
    "Use when",
    "Do not use when",
    "Required inputs",
    "Method",
    "Output contract",
    "Evidence and uncertainty rules",
    "Guardrails",
    "Success criteria",
    "Example",
)
AGENT_HEADINGS: tuple[str, ...] = (
    "Position",
    "Use when",
    "Do not use when",
    "Inputs",
    "Method",
    "Output",
    "Evidence rules",
    "Distinctive rule",
    "Status and escalation",
    "Worked example",
    "Negative case",
    "Review rubric",
)

#: (target low, target high, fail below, fail above) in lines of the whole file.
SKILL_LENGTH: tuple[int, int, int, int] = (120, 300, 90, 360)
AGENT_LENGTH: tuple[int, int, int, int] = (120, 240, 90, 300)

SHINGLE_SIZE = 5
DUPLICATE_MAJOR = 0.35
DUPLICATE_BLOCKING = 0.60

FAILING_SEVERITIES: frozenset[str] = frozenset({"blocking", "major"})

_NAME_WORDS = r"openai|anthropic|claude|gpt|codex|gemini|llama|mistral|sonnet|opus|haiku"
#: The short reasoning-model names are matched lowercase only: upper-case ``O1`` is how the worked
#: examples label options (``O0 do nothing``, ``O1 shared template library``), not a model.
_SHORT_MODEL_WORDS = r"o1|o3|o4"

#: Ordered (category, pattern). Earlier categories win when matches overlap on a line.
PROHIBITED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "model_id",
        re.compile(r"\b(?:gpt|claude|gemini|llama|mistral|codex)-[a-z0-9]+(?:[.\-][a-z0-9]+)*", re.IGNORECASE),
    ),
    ("model_id", re.compile(rf"\b(?:{_SHORT_MODEL_WORDS})-[a-z0-9]+(?:[.\-][a-z0-9]+)*")),
    ("provider_or_model_name", re.compile(rf"\b(?:{_NAME_WORDS})\b", re.IGNORECASE)),
    ("provider_or_model_name", re.compile(rf"\b(?:{_SHORT_MODEL_WORDS})\b")),
    ("currency_amount", re.compile(r"[$€£]\s?\d")),
    ("token_rate", re.compile(r"\bper\s+(?:token|1k|million)\b", re.IGNORECASE)),
    ("persona_opener", re.compile(r"\byou are an?\b|\bworld-class\b|\bexpert at\b", re.IGNORECASE)),
    ("filler", re.compile(r"\bit is important to note\b|\bbe sure to\b|\bas an ai\b", re.IGNORECASE)),
    (
        "emoji",
        re.compile(
            "[\U0001F000-\U0001FAFF☀-➿⭐⭕⌚⌛⏩-⏺◽◾️]"
        ),
    ),
)

SKILL_REF_RE = re.compile(r"`(aipt-method-[a-z0-9-]+)`\s*\((S\d{2})\)")
SKILL_PREFIX = "aipt-method-"

_WORD_RE = re.compile(r"[a-z0-9]+")
_WS_RE = re.compile(r"\s+")

# --------------------------------------------------------------------------------------------------
# Result model
# --------------------------------------------------------------------------------------------------


class GateError(Exception):
    """The run cannot be performed at all (bad root, unreadable registry)."""


@dataclass
class Finding:
    gate: str
    severity: str  # blocking | major | warning | info
    message: str
    line: int | None = None

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {"gate": self.gate, "severity": self.severity, "message": self.message}
        if self.line is not None:
            out["line"] = self.line
        return out


@dataclass
class FileResult:
    path: str
    findings: list[Finding] = field(default_factory=list)
    authored: bool = True

    @property
    def ok(self) -> bool:
        return not any(f.severity in FAILING_SEVERITIES for f in self.findings)

    @property
    def status(self) -> str:
        if not self.authored:
            return "not_authored"
        return "passed" if self.ok else "failed"

    def to_json(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "ok": self.ok,
            "status": self.status,
            "findings": [f.to_json() for f in self.findings],
        }


@dataclass
class Section:
    title: str
    line: int  # 1-based line number of the heading
    start: int  # 0-based index of the first line after the heading
    end: int  # 0-based exclusive end index


@dataclass
class Frontmatter:
    data: dict[str, Any]
    key_lines: dict[str, int]  # "name" or "metadata.aipt_skill_id" -> 1-based line
    body_start: int  # 0-based index of the first line after the closing ---


def _normalize_ws(text: str) -> str:
    return _WS_RE.sub(" ", text).strip()


# --------------------------------------------------------------------------------------------------
# Frontmatter: a deliberately tiny YAML subset
# --------------------------------------------------------------------------------------------------

_TOP_KEY_RE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_-]*):(?P<rest>.*)$")
_NESTED_KEY_RE = re.compile(r"^(?P<indent> +)(?P<key>[A-Za-z_][A-Za-z0-9_-]*):(?P<rest>.*)$")
_REJECTED_VALUE_START = ("[", "{", "|", ">", "&", "*", "!", "%", "@", "- ")


def _parse_scalar(raw: str, lineno: int) -> tuple[str | None, Finding | None]:
    value = raw.strip()
    if value == "-" or value.startswith(_REJECTED_VALUE_START):
        return None, Finding(
            "frontmatter",
            "major",
            f"value {value[:20]!r} uses YAML syntax outside the supported subset (plain or quoted scalars only)",
            lineno,
        )
    for quote in ('"', "'"):
        if value.startswith(quote):
            if len(value) < 2 or not value.endswith(quote):
                return None, Finding("frontmatter", "major", "unterminated quoted value", lineno)
            inner = value[1:-1]
            if "\\" in inner or quote in inner:
                return None, Finding(
                    "frontmatter", "major", "escape sequences inside quoted values are not supported", lineno
                )
            return inner, None
    return value, None


def parse_frontmatter(lines: list[str]) -> tuple[Frontmatter | None, int, list[Finding]]:
    """Parse the leading ``---`` block.

    Supported: ``key: scalar`` at column 0 and one nested map under ``metadata:`` whose entries are
    ``  key: scalar`` with a consistent indent. Scalars are plain or single-/double-quoted without escapes.
    Anything else (lists, other nested maps, block scalars, comments, blank lines, duplicate keys) is
    rejected with one finding. Returns ``(frontmatter or None, body_start, findings)``; ``body_start`` is
    the index after the closing ``---`` when one exists, else 0.
    """
    if not lines or lines[0].lstrip("﻿").strip() != "---":
        return None, 0, [Finding("frontmatter", "major", "file does not start with a '---' frontmatter block", 1)]

    closing = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    fallback_body = closing + 1 if closing is not None else 0

    def fail(message: str, lineno: int) -> tuple[None, int, list[Finding]]:
        return None, fallback_body, [Finding("frontmatter", "major", message, lineno)]

    if closing is None:
        return fail("frontmatter block is never closed with '---'", 1)

    data: dict[str, Any] = {}
    key_lines: dict[str, int] = {}
    nested_key: str | None = None
    nested_indent: str | None = None

    for idx in range(1, closing):
        line = lines[idx].rstrip("\r")
        lineno = idx + 1
        if not line.strip():
            return fail("blank line inside frontmatter is not allowed", lineno)
        if line.lstrip().startswith("#"):
            return fail("comments inside frontmatter are not allowed", lineno)
        if line.lstrip().startswith("- "):
            return fail("lists are not allowed in frontmatter", lineno)

        nested = _NESTED_KEY_RE.match(line)
        if nested:
            if nested_key is None:
                return fail("indented line outside the metadata map", lineno)
            if nested_indent is None:
                nested_indent = nested.group("indent")
            elif nested.group("indent") != nested_indent:
                return fail("inconsistent indentation inside the metadata map", lineno)
            key = nested.group("key")
            if key in data[nested_key]:
                return fail(f"duplicate key {key!r} in metadata", lineno)
            value, problem = _parse_scalar(nested.group("rest"), lineno)
            if problem is not None:
                return None, fallback_body, [problem]
            if value == "":
                return fail(f"metadata key {key!r} has no value", lineno)
            data[nested_key][key] = value
            key_lines[f"{nested_key}.{key}"] = lineno
            continue

        top = _TOP_KEY_RE.match(line)
        if not top:
            return fail("line is not 'key: value'", lineno)
        key = top.group("key")
        if key in data:
            return fail(f"duplicate key {key!r}", lineno)
        rest = top.group("rest")
        key_lines[key] = lineno
        if rest.strip() == "":
            if key == "metadata":
                data[key] = {}
                nested_key = key
                nested_indent = None
            else:
                # An empty scalar; the gate for that key reports it as missing or empty.
                nested_key = None
                data[key] = ""
            continue
        if rest and not rest[0].isspace():
            return fail("a space is required after the colon", lineno)
        nested_key = None
        value, problem = _parse_scalar(rest, lineno)
        if problem is not None:
            return None, fallback_body, [problem]
        data[key] = value

    if nested_key is not None and not data[nested_key]:
        return fail("metadata map is empty", key_lines[nested_key])

    return Frontmatter(data, key_lines, closing + 1), closing + 1, []


# --------------------------------------------------------------------------------------------------
# Markdown outline (headings outside code fences)
# --------------------------------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_H1_RE = re.compile(r"^ {0,3}#(?!#)\s+(?P<title>.+?)\s*$")
_H2_RE = re.compile(r"^ {0,3}##(?!#)\s+(?P<title>.+?)\s*$")


def outline(lines: list[str], start: int = 0) -> tuple[list[tuple[str, int]], list[Section], list[Finding]]:
    """Return ``(h1 headings, h2 sections, findings)``; headings inside fenced code are ignored."""
    h1s: list[tuple[str, int]] = []
    sections: list[Section] = []
    findings: list[Finding] = []
    fence: str | None = None
    fence_line = 0
    for idx in range(start, len(lines)):
        line = lines[idx]
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                fence, fence_line = marker, idx + 1
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is not None:
            continue
        h2 = _H2_RE.match(line)
        if h2:
            if sections:
                sections[-1].end = idx
            sections.append(Section(h2.group("title").strip(), idx + 1, idx + 1, len(lines)))
            continue
        h1 = _H1_RE.match(line)
        if h1:
            h1s.append((h1.group("title").strip(), idx + 1))
    if fence is not None:
        findings.append(
            Finding("structure", "major", "code fence opened here is never closed; headings after it are hidden", fence_line)
        )
    return h1s, sections, findings


def _find_section(sections: list[Section], title: str) -> Section | None:
    return next((s for s in sections if s.title == title), None)


def _section_text(lines: list[str], section: Section) -> str:
    return "\n".join(lines[section.start : section.end])


def _first_paragraph(lines: list[str], section: Section) -> tuple[str, int | None]:
    idx = section.start
    while idx < section.end and not lines[idx].strip():
        idx += 1
    if idx >= section.end:
        return "", None
    first = idx
    parts: list[str] = []
    while idx < section.end and lines[idx].strip():
        parts.append(lines[idx].strip())
        idx += 1
    return _normalize_ws(" ".join(parts)), first + 1


# --------------------------------------------------------------------------------------------------
# Shared gates
# --------------------------------------------------------------------------------------------------


def check_title(h1s: list[tuple[str, int]]) -> list[Finding]:
    if not h1s:
        return [Finding("structure", "major", "missing the '# <Title>' heading")]
    if len(h1s) > 1:
        return [Finding("structure", "major", f"more than one H1 heading ('# {h1s[1][0]}')", h1s[1][1])]
    return []


def check_headings(sections: list[Section], expected: tuple[str, ...], label: str) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[str] = set()
    found_order: list[str] = []
    for section in sections:
        if section.title not in expected:
            findings.append(
                Finding(
                    "structure",
                    "major",
                    f"unexpected H2 heading '## {section.title}'; the {label} template allows only: "
                    + ", ".join(expected),
                    section.line,
                )
            )
            continue
        if section.title in seen:
            findings.append(Finding("structure", "major", f"duplicate H2 heading '## {section.title}'", section.line))
            continue
        seen.add(section.title)
        found_order.append(section.title)
    for heading in expected:
        if heading not in seen:
            findings.append(Finding("structure", "major", f"missing H2 heading '## {heading}'"))
    expected_order = [h for h in expected if h in seen]
    if found_order != expected_order:
        for got, want in zip(found_order, expected_order):
            if got != want:
                line = next(s.line for s in sections if s.title == got)
                findings.append(
                    Finding("structure", "major", f"heading '## {got}' is out of order; expected '## {want}' here", line)
                )
                break
    return findings


def check_length(line_count: int, bounds: tuple[int, int, int, int], label: str) -> list[Finding]:
    low, high, fail_low, fail_high = bounds
    if line_count < fail_low or line_count > fail_high:
        return [
            Finding(
                "length",
                "major",
                f"{label} is {line_count} lines; it must stay within {fail_low}-{fail_high} (target {low}-{high})",
            )
        ]
    if line_count < low or line_count > high:
        return [Finding("length", "warning", f"{label} is {line_count} lines; the target is {low}-{high}")]
    return []


def scan_prohibited(lines: list[str], start: int = 0) -> list[Finding]:
    """Case-insensitive scan for provider/model names, prices, persona openers, filler and emoji."""
    findings: list[Finding] = []
    for idx in range(start, len(lines)):
        line = lines[idx]
        taken: list[tuple[int, int]] = []
        for category, pattern in PROHIBITED_PATTERNS:
            for match in pattern.finditer(line):
                begin, end = match.span()
                if any(begin < t_end and t_begin < end for t_begin, t_end in taken):
                    continue
                taken.append((begin, end))
                findings.append(
                    Finding("prohibited_content", "major", f"{category}: {match.group(0)!r}", idx + 1)
                )
    return findings


def shingles(text: str, size: int = SHINGLE_SIZE) -> set[tuple[str, ...]]:
    words = _WORD_RE.findall(text.lower())
    return {tuple(words[i : i + size]) for i in range(len(words) - size + 1)}


def jaccard(a: set[Any], b: set[Any]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def near_duplicate_findings(methods: dict[str, tuple[str, int | None]]) -> dict[str, list[Finding]]:
    """Compare Method sections pairwise; each flagged pair is reported once, on the first path in sort order."""
    paths = sorted(methods)
    sets = {path: shingles(methods[path][0]) for path in paths}
    out: dict[str, list[Finding]] = {}
    for i, first in enumerate(paths):
        for second in paths[i + 1 :]:
            score = jaccard(sets[first], sets[second])
            if score < DUPLICATE_MAJOR:
                continue
            severity = "blocking" if score >= DUPLICATE_BLOCKING else "major"
            out.setdefault(first, []).append(
                Finding(
                    "near_duplicate",
                    severity,
                    f"Method section is {score:.2f} Jaccard-similar ({SHINGLE_SIZE}-word shingles) to {second}; "
                    "move the shared text into a skill and reference it",
                    methods[first][1],
                )
            )
    return out


def _read_lines(path: Path, result: FileResult) -> list[str] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        result.findings.append(Finding("structure", "major", "file is not valid UTF-8"))
        return None
    except OSError as exc:
        result.findings.append(Finding("structure", "major", f"file could not be read: {exc.strerror}"))
        return None
    return text.splitlines()


# --------------------------------------------------------------------------------------------------
# Registries
# --------------------------------------------------------------------------------------------------


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise GateError(f"cannot read {path}: {exc.strerror}") from exc
    except json.JSONDecodeError as exc:
        raise GateError(f"{path} is not valid JSON: {exc}") from exc


def load_skill_registry(root: Path) -> dict[str, dict[str, str]] | None:
    """Return ``{installed name: {"id", "provenance"}}`` from registry/skills.json, or None when absent."""
    path = root / "registry" / "skills.json"
    if not path.is_file():
        return None
    data = _load_json(path)
    entries = data.get("skills") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise GateError(f"{path} has no 'skills' list")
    registry: dict[str, dict[str, str]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not isinstance(entry.get("name"), str):
            raise GateError(f"{path}: every skill needs string 'id' and 'name'")
        name = entry["name"]
        installed = name if name.startswith(SKILL_PREFIX) else SKILL_PREFIX + name
        provenance = entry.get("provenance")
        status = provenance.get("status", "") if isinstance(provenance, dict) else str(provenance or "")
        registry[installed] = {"id": entry["id"], "provenance": status}
    return registry


def load_agent_registry(root: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Return ``(agent entries, {team id: team name})`` from registry/agents.json."""
    path = root / "registry" / "agents.json"
    if not path.is_file():
        raise GateError(f"{path} does not exist; the agents gate needs the registry")
    data = _load_json(path)
    entries = data.get("agents") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        raise GateError(f"{path} has no 'agents' list")
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            raise GateError(f"{path}: every agent needs a string 'id'")
    teams: dict[str, str] = {}
    if isinstance(data, dict):
        for team in data.get("teams", []) or []:
            if isinstance(team, dict) and isinstance(team.get("id"), str):
                teams[team["id"]] = str(team.get("name") or team["id"])
    return entries, teams


# --------------------------------------------------------------------------------------------------
# Skills
# --------------------------------------------------------------------------------------------------


def check_skill_frontmatter(
    fm: Frontmatter, dir_name: str, registry: dict[str, dict[str, str]] | None
) -> list[Finding]:
    findings: list[Finding] = []
    data, at = fm.data, fm.key_lines

    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        findings.append(Finding("name", "major", "frontmatter 'name' is missing or empty", at.get("name")))
        name = None
    else:
        if name != dir_name:
            findings.append(
                Finding("name", "major", f"name {name!r} does not equal the directory name {dir_name!r}", at["name"])
            )
        if not SKILL_NAME_RE.match(name):
            findings.append(
                Finding("name", "major", f"name {name!r} does not match ^aipt-method-[a-z0-9]+(-[a-z0-9]+)*$", at["name"])
            )
        if len(name) > SKILL_NAME_MAX:
            findings.append(
                Finding("name", "major", f"name is {len(name)} characters; the maximum is {SKILL_NAME_MAX}", at["name"])
            )

    description = data.get("description")
    if not isinstance(description, str) or not description.strip():
        findings.append(Finding("description", "major", "description is missing or empty", at.get("description")))
    elif len(description) > DESCRIPTION_MAX:
        findings.append(
            Finding(
                "description",
                "major",
                f"description is {len(description)} characters; the hard limit is {DESCRIPTION_MAX}",
                at["description"],
            )
        )
    elif len(description) > DESCRIPTION_WARN:
        findings.append(
            Finding(
                "description",
                "warning",
                f"description is {len(description)} characters; aim for {DESCRIPTION_WARN} or fewer",
                at["description"],
            )
        )

    license_value = data.get("license")
    if not isinstance(license_value, str) or not license_value.strip():
        findings.append(Finding("license", "major", "license line is missing or empty", at.get("license")))

    metadata = data.get("metadata")
    skill_id: str | None = None
    provenance: str | None = None
    if not isinstance(metadata, dict):
        findings.append(Finding("metadata", "major", "metadata map is missing", at.get("metadata")))
    else:
        missing = [k for k in METADATA_KEYS if k not in metadata]
        extra = sorted(set(metadata) - set(METADATA_KEYS))
        if missing:
            findings.append(Finding("metadata", "major", "metadata is missing " + ", ".join(missing), at.get("metadata")))
        if extra:
            findings.append(
                Finding(
                    "metadata",
                    "major",
                    "metadata has unexpected keys " + ", ".join(extra) + "; exactly " + ", ".join(METADATA_KEYS) + " are allowed",
                    at.get(f"metadata.{extra[0]}"),
                )
            )
        skill_id = metadata.get("aipt_skill_id")
        if skill_id is not None and not SKILL_ID_RE.match(skill_id):
            findings.append(
                Finding("metadata", "major", f"aipt_skill_id {skill_id!r} is not in S01-S28", at.get("metadata.aipt_skill_id"))
            )
            skill_id = None
        provenance = metadata.get("aipt_provenance")
        if provenance is not None and provenance not in PROVENANCE_VALUES:
            findings.append(
                Finding(
                    "metadata",
                    "major",
                    f"aipt_provenance {provenance!r} must be adapt or newly_authored",
                    at.get("metadata.aipt_provenance"),
                )
            )
            provenance = None
        version = metadata.get("aipt_version")
        if version is not None and not VERSION_RE.match(version):
            findings.append(
                Finding("metadata", "major", f"aipt_version {version!r} must look like 0.1.0", at.get("metadata.aipt_version"))
            )

    unknown = sorted(set(data) - FRONTMATTER_KEYS)
    if unknown:
        findings.append(
            Finding("frontmatter", "warning", "frontmatter has keys outside the template: " + ", ".join(unknown), at.get(unknown[0]))
        )

    if registry is not None and name is not None:
        entry = registry.get(name)
        if entry is None:
            findings.append(Finding("registry_agreement", "major", f"{name!r} is not listed in registry/skills.json", at["name"]))
        else:
            if skill_id is not None and skill_id != entry["id"]:
                findings.append(
                    Finding(
                        "registry_agreement",
                        "major",
                        f"aipt_skill_id is {skill_id!r}; registry/skills.json gives {entry['id']!r} for {name}",
                        at.get("metadata.aipt_skill_id"),
                    )
                )
            registry_provenance = entry.get("provenance", "")
            if provenance is not None and registry_provenance in PROVENANCE_VALUES and provenance != registry_provenance:
                findings.append(
                    Finding(
                        "registry_agreement",
                        "major",
                        f"aipt_provenance is {provenance!r}; registry/skills.json gives {registry_provenance!r}",
                        at.get("metadata.aipt_provenance"),
                    )
                )
    return findings


def check_skill(
    path: Path, root: Path, registry: dict[str, dict[str, str]] | None
) -> tuple[FileResult, tuple[str, int | None] | None]:
    """Run every single-file skill gate. Returns the result and the Method text for duplicate detection."""
    result = FileResult(path.relative_to(root).as_posix())
    lines = _read_lines(path, result)
    if lines is None:
        return result, None

    fm, body_start, fm_findings = parse_frontmatter(lines)
    result.findings.extend(fm_findings)
    if fm is not None:
        result.findings.extend(check_skill_frontmatter(fm, path.parent.name, registry))

    h1s, sections, outline_findings = outline(lines, body_start)
    result.findings.extend(outline_findings)
    result.findings.extend(check_title(h1s))
    result.findings.extend(check_headings(sections, SKILL_HEADINGS, "skill"))
    result.findings.extend(check_length(len(lines), SKILL_LENGTH, "SKILL.md"))
    result.findings.extend(scan_prohibited(lines))

    method = _find_section(sections, "Method")
    method_info = (_section_text(lines, method), method.line) if method else None
    return result, method_info


def run_skills(root: Path) -> list[FileResult]:
    registry = load_skill_registry(root)
    skills_dir = root / "skills"
    results: list[FileResult] = []
    methods: dict[str, tuple[str, int | None]] = {}
    seen: set[str] = set()

    if skills_dir.is_dir():
        for directory in sorted(p for p in skills_dir.iterdir() if p.is_dir() and not p.name.startswith((".", "_"))):
            skill_file = directory / "SKILL.md"
            seen.add(directory.name)
            if not skill_file.is_file():
                results.append(
                    FileResult(skill_file.relative_to(root).as_posix(), [Finding("structure", "major", "skill directory has no SKILL.md")])
                )
                continue
            result, method = check_skill(skill_file, root, registry)
            results.append(result)
            if method is not None:
                methods[result.path] = method

    if registry is not None:
        for name, entry in registry.items():
            if name in seen:
                continue
            rel = (Path("skills") / name / "SKILL.md").as_posix()
            results.append(
                FileResult(rel, [Finding("not_authored", "info", f"{entry['id']} ({name}) has no SKILL.md yet")], authored=False)
            )

    for result in results:
        result.findings.extend(near_duplicate_findings(methods).get(result.path, []))
    return sorted(results, key=lambda r: r.path)


# --------------------------------------------------------------------------------------------------
# Agents
# --------------------------------------------------------------------------------------------------

_POSITION_SPLIT_RE = re.compile(r"\s*·\s*")


def _parse_position(lines: list[str], section: Section) -> dict[str, tuple[str, int]]:
    fields: dict[str, tuple[str, int]] = {}
    for idx in range(section.start, section.end):
        stripped = lines[idx].strip()
        if not stripped.startswith(("- ", "* ")):
            continue
        for part in _POSITION_SPLIT_RE.split(stripped[2:].strip()):
            key, sep, value = part.partition(":")
            if not sep:
                continue
            fields.setdefault(key.strip().lower(), (value.strip(), idx + 1))
    return fields


def check_position(
    lines: list[str],
    section: Section,
    entry: dict[str, Any],
    team_names: dict[str, str],
    skill_registry: dict[str, dict[str, str]] | None,
) -> list[Finding]:
    findings: list[Finding] = []
    fields = _parse_position(lines, section)

    def mismatch(label: str, found: str, expected: str, line: int) -> None:
        findings.append(
            Finding("registry_agreement", "major", f"Position '{label}' is {found!r}; registry/agents.json says {expected!r}", line)
        )

    def field_value(key: str, label: str) -> tuple[str, int] | None:
        got = fields.get(key)
        if got is None:
            findings.append(Finding("registry_agreement", "major", f"Position block has no '{label}' field", section.line))
            return None
        return got[0].strip("`").strip(), got[1]

    def expect(key: str, label: str, registry_key: str, expected: str | None = None) -> None:
        if expected is None:
            if registry_key not in entry:
                return
            expected = str(entry[registry_key])
        got = field_value(key, label)
        if got is not None and got[0] != expected:
            mismatch(label, got[0], expected, got[1])

    expect("role id", "Role id", "id")
    expect("type", "Type", "type")
    if "team" in entry:
        got = field_value("team", "Team")
        if got is not None:
            accepted = {str(entry["team"]), team_names.get(str(entry["team"]), str(entry["team"]))}
            if got[0] not in accepted:
                mismatch("Team", got[0], team_names.get(str(entry["team"]), str(entry["team"])), got[1])
    expect("reports to", "Reports to", "reports_to")
    expect("reviewed by", "Reviewed by", "reviewed_by")
    expect("write scope", "Write scope", "write_scope")
    if "may_dispatch" in entry:
        expect("may dispatch", "May dispatch", "may_dispatch", "yes" if entry["may_dispatch"] else "no")
    expect("acceptance authority", "Acceptance authority", "acceptance_authority")

    if "dispatch_condition" in entry:
        got = field_value("dispatch condition", "Dispatch condition")
        if got is not None and _normalize_ws(got[0]) != _normalize_ws(str(entry["dispatch_condition"])):
            mismatch("Dispatch condition", got[0], str(entry["dispatch_condition"]), got[1])

    if "skill_ids" in entry:
        got = fields.get("shared skills")
        if got is None:
            findings.append(Finding("registry_agreement", "major", "Position block has no 'Shared skills' field", section.line))
        else:
            value, line = got
            pairs = SKILL_REF_RE.findall(value)
            expected_ids = [str(s) for s in entry["skill_ids"]]
            if not pairs and value.strip().lower() not in ("", "none"):
                findings.append(
                    Finding(
                        "registry_agreement",
                        "major",
                        "Shared skills could not be parsed; use `aipt-method-<name>` (S0x), ... with one pair per skill",
                        line,
                    )
                )
            listed = [sid for _, sid in pairs]
            duplicates = sorted({sid for sid in listed if listed.count(sid) > 1})
            if duplicates:
                findings.append(Finding("registry_agreement", "major", "Shared skills lists " + ", ".join(duplicates) + " more than once", line))
            if sorted(set(listed)) != sorted(set(expected_ids)):
                findings.append(
                    Finding(
                        "registry_agreement",
                        "major",
                        f"Shared skills ids {sorted(set(listed))} do not equal registry skill_ids {sorted(set(expected_ids))}",
                        line,
                    )
                )
            if skill_registry is not None:
                for name, sid in pairs:
                    reg = skill_registry.get(name)
                    if reg is None:
                        findings.append(Finding("registry_agreement", "major", f"shared skill {name!r} is not in registry/skills.json", line))
                    elif reg["id"] != sid:
                        findings.append(
                            Finding(
                                "registry_agreement",
                                "major",
                                f"shared skill {name!r} is labelled {sid}; registry/skills.json gives {reg['id']}",
                                line,
                            )
                        )
    return findings


def check_distinctive_rule(lines: list[str], section: Section, entry: dict[str, Any]) -> list[Finding]:
    if "distinctive_rule" not in entry:
        return []
    paragraph, line = _first_paragraph(lines, section)
    expected = _normalize_ws(str(entry["distinctive_rule"]))
    if paragraph != expected:
        return [
            Finding(
                "registry_agreement",
                "major",
                f"first paragraph of '## Distinctive rule' is {paragraph[:80]!r}; registry distinctive_rule is {expected!r}",
                line or section.line,
            )
        ]
    return []


def check_negative_case(lines: list[str], section: Section, entry: dict[str, Any]) -> list[Finding]:
    if "negative_test" not in entry:
        return []
    text = _normalize_ws(_section_text(lines, section))
    expected = _normalize_ws(str(entry["negative_test"]))
    if not text.startswith(expected):
        _, line = _first_paragraph(lines, section)
        return [
            Finding(
                "registry_agreement",
                "major",
                f"'## Negative case' begins {text[:80]!r}; it must begin with the registry negative_test {expected!r}",
                line or section.line,
            )
        ]
    return []


def check_agent(
    path: Path,
    root: Path,
    entry: dict[str, Any],
    team_names: dict[str, str],
    skill_registry: dict[str, dict[str, str]] | None,
) -> tuple[FileResult, tuple[str, int | None] | None]:
    """Run every single-file role-body gate. Returns the result and the Method text for duplicate detection."""
    result = FileResult(path.relative_to(root).as_posix())
    lines = _read_lines(path, result)
    if lines is None:
        return result, None

    h1s, sections, outline_findings = outline(lines)
    result.findings.extend(outline_findings)
    result.findings.extend(check_title(h1s))
    if len(h1s) == 1 and isinstance(entry.get("name"), str) and h1s[0][0] != entry["name"]:
        result.findings.append(
            Finding("registry_agreement", "warning", f"title is '# {h1s[0][0]}'; registry name is {entry['name']!r}", h1s[0][1])
        )
    result.findings.extend(check_headings(sections, AGENT_HEADINGS, "role body"))
    result.findings.extend(check_length(len(lines), AGENT_LENGTH, "role body"))
    result.findings.extend(scan_prohibited(lines))

    position = _find_section(sections, "Position")
    if position is not None:
        result.findings.extend(check_position(lines, position, entry, team_names, skill_registry))
    distinctive = _find_section(sections, "Distinctive rule")
    if distinctive is not None:
        result.findings.extend(check_distinctive_rule(lines, distinctive, entry))
    negative = _find_section(sections, "Negative case")
    if negative is not None:
        result.findings.extend(check_negative_case(lines, negative, entry))

    method = _find_section(sections, "Method")
    method_info = (_section_text(lines, method), method.line) if method else None
    return result, method_info


def run_agents(root: Path) -> list[FileResult]:
    entries, team_names = load_agent_registry(root)
    skill_registry = load_skill_registry(root)
    by_id = {entry["id"]: entry for entry in entries}
    agents_dir = root / "agents"
    results: list[FileResult] = []
    methods: dict[str, tuple[str, int | None]] = {}
    seen: set[str] = set()

    if agents_dir.is_dir():
        for path in sorted(agents_dir.glob("*.md")):
            if path.name.lower() == "readme.md" or path.name.startswith((".", "_")):
                continue
            role_id = path.stem
            seen.add(role_id)
            entry = by_id.get(role_id)
            if entry is None:
                results.append(
                    FileResult(
                        path.relative_to(root).as_posix(),
                        [Finding("registry_agreement", "major", f"{role_id!r} is not a role id in registry/agents.json")],
                    )
                )
                continue
            result, method = check_agent(path, root, entry, team_names, skill_registry)
            results.append(result)
            if method is not None:
                methods[result.path] = method

    for role_id in by_id:
        if role_id not in seen:
            results.append(
                FileResult(
                    (Path("agents") / f"{role_id}.md").as_posix(),
                    [Finding("not_authored", "info", f"{role_id} has no role body yet")],
                    authored=False,
                )
            )

    for result in results:
        result.findings.extend(near_duplicate_findings(methods).get(result.path, []))
    return sorted(results, key=lambda r: r.path)


# --------------------------------------------------------------------------------------------------
# Reporting and CLI
# --------------------------------------------------------------------------------------------------


def build_report(results: list[FileResult]) -> dict[str, Any]:
    ordered = sorted(results, key=lambda r: r.path)
    checked = [r for r in ordered if r.authored]
    summary = {
        "checked": len(checked),
        "passed": sum(1 for r in checked if r.ok),
        "failed": sum(1 for r in checked if not r.ok),
        "warnings": sum(1 for r in checked for f in r.findings if f.severity == "warning"),
        "not_authored": len(ordered) - len(checked),
    }
    return {"files": [r.to_json() for r in ordered], "summary": summary}


def render_text(report: dict[str, Any], target: str) -> str:
    out: list[str] = []
    not_authored: list[str] = []
    for entry in report["files"]:
        if entry["status"] == "not_authored":
            path = Path(entry["path"])
            not_authored.append(path.stem if target == "agents" else path.parent.name)
            continue
        out.append(f"{'PASS' if entry['ok'] else 'FAIL'}  {entry['path']}")
        for finding in entry["findings"]:
            location = f" (line {finding['line']})" if "line" in finding else ""
            out.append(f"    {finding['severity']:<8} {finding['gate']}: {finding['message']}{location}")
    if not_authored:
        out.append(f"not authored ({len(not_authored)}): " + ", ".join(not_authored))
    s = report["summary"]
    out.append(
        f"{target}: {s['checked']} checked, {s['passed']} passed, {s['failed']} failed, "
        f"{s['warnings']} warnings, {s['not_authored']} not authored"
    )
    return "\n".join(out)


def _default_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_authoring.py",
        description="Authoring gates for shared skills and role bodies (authoring-contract.md section 5).",
    )
    parser.add_argument("target", choices=("skills", "agents"), help="which bodies to check")
    parser.add_argument("--root", type=Path, default=None, help="repository root (default: the parent of tools/)")
    parser.add_argument("--json", action="store_true", dest="as_json", help="print the machine-readable report")
    args = parser.parse_args(argv)

    root = (args.root or _default_root()).resolve()
    try:
        if not root.is_dir():
            raise GateError(f"root {root} is not a directory")
        results = run_skills(root) if args.target == "skills" else run_agents(root)
    except GateError as exc:
        if args.as_json:
            print(json.dumps({"error": str(exc)}, indent=2))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 2

    report = build_report(results)
    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(render_text(report, args.target))
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
