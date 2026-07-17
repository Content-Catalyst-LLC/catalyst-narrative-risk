#!/usr/bin/env python3
"""Manage persistent Catalyst Narrative Risk cases from the command line."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from narrative_risk.workspaces import SQLiteCaseRepository


def read_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(value, path: str | None = None):
    content = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if path:
        Path(path).write_text(content, encoding="utf-8")
    else:
        print(content, end="")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--database", default="data/catalyst-narrative-risk.sqlite3")
    commands = root.add_subparsers(dest="command", required=True)

    commands.add_parser("init")
    create = commands.add_parser("create")
    create.add_argument("--title", required=True)
    create.add_argument("--summary", default="")
    create.add_argument("--organization-id")
    create.add_argument("--project-id")
    create.add_argument("--status", default="draft")
    create.add_argument("--priority", default="normal")
    create.add_argument("--tag", action="append", default=[])
    create.add_argument("--input")
    create.add_argument("--created-by")

    listing = commands.add_parser("list")
    listing.add_argument("--query", default="")
    listing.add_argument("--status")
    listing.add_argument("--priority")
    listing.add_argument("--tag", action="append", default=[])
    listing.add_argument("--archived", action="store_true")

    show = commands.add_parser("show")
    show.add_argument("case_id")
    show.add_argument("--details", action="store_true")

    revise = commands.add_parser("add-revision")
    revise.add_argument("case_id")
    revise.add_argument("--input", required=True)
    revise.add_argument("--record", action="store_true", help="Input is a canonical record rather than analytical input.")
    revise.add_argument("--created-by")
    revise.add_argument("--change-note", default="")

    review = commands.add_parser("add-review")
    review.add_argument("case_id")
    review.add_argument("--event-type", default="comment")
    review.add_argument("--revision-id")
    review.add_argument("--author-id")
    review.add_argument("--author-name")
    review.add_argument("--body", default="")

    archive = commands.add_parser("archive")
    archive.add_argument("case_id")
    restore = commands.add_parser("restore")
    restore.add_argument("case_id")

    export = commands.add_parser("export")
    export.add_argument("case_id")
    export.add_argument("--output", required=True)
    export.add_argument("--exported-at")

    import_cmd = commands.add_parser("import")
    import_cmd.add_argument("--input", required=True)

    verify = commands.add_parser("verify-bundle")
    verify.add_argument("--input", required=True)

    view = commands.add_parser("save-view")
    view.add_argument("--name", required=True)
    view.add_argument("--owner-id")
    view.add_argument("--filters", required=True, help="Path to a JSON filters object.")
    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "verify-bundle":
        write_json(SQLiteCaseRepository.verify_bundle(read_json(args.input)))
        return 0

    repository = SQLiteCaseRepository(args.database)
    try:
        if args.command == "init":
            write_json(repository.health())
        elif args.command == "create":
            write_json(repository.create_case(
                title=args.title, summary=args.summary, organization_id=args.organization_id,
                project_id=args.project_id, status=args.status, priority=args.priority, tags=args.tag,
                initial_payload=read_json(args.input) if args.input else None, created_by=args.created_by,
            ))
        elif args.command == "list":
            cases = repository.list_cases(query=args.query, status=args.status, priority=args.priority, tags=args.tag, archived=args.archived)
            write_json({"cases": cases, "count": len(cases)})
        elif args.command == "show":
            write_json(repository.get_case(args.case_id, include_details=args.details))
        elif args.command == "add-revision":
            data = read_json(args.input)
            kwargs = {"record": data} if args.record else {"payload": data}
            write_json(repository.add_revision(args.case_id, created_by=args.created_by, change_note=args.change_note, **kwargs))
        elif args.command == "add-review":
            write_json(repository.add_review_event(
                args.case_id, event_type=args.event_type, revision_id=args.revision_id,
                author_id=args.author_id, author_name=args.author_name, body=args.body,
            ))
        elif args.command == "archive":
            write_json(repository.archive_case(args.case_id))
        elif args.command == "restore":
            write_json(repository.restore_case(args.case_id))
        elif args.command == "export":
            bundle = repository.export_case_bundle(args.case_id, exported_at=args.exported_at)
            write_json(bundle, args.output)
            print(f"Wrote {args.output}", file=sys.stderr)
        elif args.command == "import":
            write_json(repository.import_case_bundle(read_json(args.input)))
        elif args.command == "save-view":
            write_json(repository.save_view(name=args.name, owner_id=args.owner_id, filters=read_json(args.filters)))
        else:  # pragma: no cover
            raise AssertionError(args.command)
    finally:
        repository.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
