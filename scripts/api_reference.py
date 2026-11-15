"""Write the API reference from the running app, so it can never drift from the code.

    python scripts/api_reference.py

Starts the app in memory on the demo morning (no network, no database file), lists every route
under /api, calls each GET route once with sample ids, and writes:
  docs/tech/api.md               one row per route, then an example answer for each GET
  docs/diagrams/data-model.mmd   the tables and their columns, as a Mermaid ER diagram
"""
import json
import pathlib
import sys

import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app        # noqa: E402
from common import dsn, lighttime, models  # noqa: E402

SAMPLE = {"ref": "C1", "alert_id": "A1", "case_id": "A1", "message_id": "1"}


def offline(*args):
    raise requests.ConnectionError("the reference is written offline")


def shorten(value, depth=0):
    """Keep the shape of an answer, not all of it: first item of each list, nested two levels."""
    if isinstance(value, list):
        return [shorten(value[0], depth + 1), f"... {len(value) - 1} more"] if len(value) > 1 else \
            [shorten(v, depth + 1) for v in value]
    if isinstance(value, dict):
        if depth >= 3:
            return "{...}"
        return {k: shorten(v, depth + 1) for k, v in value.items()}
    return value


def main():
    lighttime.fetch = dsn.fetch = offline
    app = create_app("sqlite:///:memory:", morning=True)
    client = app.test_client()
    rows, examples = [], []
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        if not rule.rule.startswith("/api/"):
            continue
        methods = sorted(m for m in rule.methods if m in ("GET", "POST", "PUT", "DELETE"))
        doc = (app.view_functions[rule.endpoint].__doc__ or "").strip().splitlines()
        rows.append(f"| {', '.join(methods)} | `{rule.rule}` | {doc[0] if doc else ''} |")
        if "GET" in methods:
            path = rule.rule
            for name in rule.arguments:
                path = path.replace(f"<{name}>", SAMPLE.get(name, "1"))
            if "history" in path:
                path += "?metric=hr_rest"
            answer = client.get(path)
            body = json.dumps(shorten(answer.get_json()), indent=2) if answer.is_json else answer.data[:200].decode()
            examples.append(f"### GET `{path}`\n\nStatus {answer.status_code}\n\n```json\n{body}\n```\n")
    models.set_clock(None)
    head = ["# API reference", "",
            "Written by `scripts/api_reference.py` from the running app on the demo morning. Do not edit by hand:",
            "run the script again after a route changes. The contract the console builds against is the API table",
            "in `docs/specs/2026-11-14-backend-design.md`; this page shows what the code answers today.", "",
            "| Methods | Route | What it does |", "|---|---|---|"]
    out = ROOT / "docs" / "tech"
    out.mkdir(parents=True, exist_ok=True)
    (out / "api.md").write_text("\n".join(head + rows) + "\n\n## Example answers\n\n" + "\n".join(examples),
                                encoding="utf-8")
    er = ["erDiagram"]
    for table in models.db.metadata.sorted_tables:
        er.append(f"    {table.name} {{")
        er += [f"        {str(col.type).split('(')[0].replace(' ', '_')} {col.name}" for col in table.columns]
        er.append("    }")
        for fk in table.foreign_keys:
            er.append(f"    {fk.column.table.name} ||--o{{ {table.name} : has")
    (ROOT / "docs" / "diagrams").mkdir(parents=True, exist_ok=True)
    (ROOT / "docs" / "diagrams" / "data-model.mmd").write_text("\n".join(er) + "\n", encoding="utf-8")
    print(f"{len(rows)} routes, {len(examples)} examples")


if __name__ == "__main__":
    main()
