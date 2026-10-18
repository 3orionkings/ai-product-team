#!/usr/bin/env python3
"""Generate the offline agent directory (docs/directory/index.html and README.md) from the registry.

Single responsibility: render one searchable, keyboard-operable HTML page and one Markdown table from
registry/agents.json, registry/skills.json and evals/roles/*/readiness.json. No external assets.
Standard library only.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    reg = json.loads((ROOT / "registry/agents.json").read_text())
    skills = {s["id"]: "aipt-method-" + s["name"] for s in json.loads((ROOT / "registry/skills.json").read_text())["skills"]}
    agents = []
    for a in reg["agents"]:
        ready = json.loads((ROOT / f"evals/roles/{a['id']}/readiness.json").read_text())
        b = dict(a)
        b["methods"] = [skills[s] for s in a["skill_ids"]]
        b["status"] = ready["state"].replace("_", " ")
        agents.append(b)
    data = {"agents": agents, "teams": reg["teams"]}
    html = (ROOT / "tools/templates/directory.html").read_text().replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    out = ROOT / "docs/directory"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html, encoding="utf-8")
    md = ["# AI Product Team — agent directory", "",
          "Generated from `registry/agents.json`. Open `index.html` in this folder for a searchable version that works offline.", ""]
    for t in reg["teams"]:
        lead = next((x["name"] for x in reg["agents"] if x["id"] == t["leader"]), None)
        md += [f"## {t['name']}", "", f"Director: {lead}." if lead else "Accountable to the human owner.", "",
               "| # | Agent | Type | What it does | Installed as |", "|---|---|---|---|---|"]
        for a in [x for x in agents if x["team"] == t["id"]]:
            md.append(f"| {a['number']:02d} | **{a['name']}** | {a['type'].replace('_', ' ')} | {a['description']} | `{a['native_name']}` |")
        md.append("")
    (out / "README.md").write_text("\n".join(md), encoding="utf-8")
    print(f"directory: {len(agents)} agents, {len(reg['teams'])} teams")
    return 0


if __name__ == "__main__":
    sys.exit(main())
