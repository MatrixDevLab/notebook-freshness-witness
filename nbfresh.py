#!/usr/bin/env python3
"""Static source/output freshness witness for Jupyter notebooks."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA = "nbfresh-1"


def read_notebook(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict) or not isinstance(value.get("cells"), list):
        raise ValueError(f"not a notebook-shaped JSON document: {path}")
    return value


def cell_key(cell: dict[str, Any], index: int) -> str:
    value = cell.get("id")
    return f"id:{value}" if isinstance(value, str) and value else f"index:{index}"


def source_text(cell: dict[str, Any]) -> str:
    source = cell.get("source", "")
    return "".join(source) if isinstance(source, list) else str(source)


def digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def entries(notebook: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for index, raw_cell in enumerate(notebook["cells"]):
        if not isinstance(raw_cell, dict):
            continue
        cell_type = raw_cell.get("cell_type")
        if cell_type != "code":
            continue
        outputs = raw_cell.get("outputs", [])
        result.append(
            {
                "key": cell_key(raw_cell, index),
                "index": index,
                "source_hash": digest(source_text(raw_cell)),
                "output_hash": digest(outputs),
                "has_output": bool(outputs),
                "execution_count": raw_cell.get("execution_count"),
            }
        )
    return result


def make_manifest(notebook: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "notebook_format": [notebook.get("nbformat"), notebook.get("nbformat_minor")],
        "cells": entries(notebook),
        "limits": [
            "Matches only recorded source and output hashes.",
            "Does not prove dependency, filesystem, network, kernel, or nondeterminism stability.",
        ],
    }


def check(notebook: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    expected = {item["key"]: item for item in manifest.get("cells", []) if isinstance(item, dict) and "key" in item}
    actual = {item["key"]: item for item in entries(notebook)}
    reports = []
    for key in sorted(set(expected) | set(actual)):
        old, current = expected.get(key), actual.get(key)
        if old is None:
            status = "missing_manifest"
        elif current is None:
            status = "missing_current_cell"
        elif not current["has_output"]:
            status = "missing_output"
        elif old.get("source_hash") != current["source_hash"]:
            status = "source_changed"
        elif old.get("output_hash") != current["output_hash"]:
            status = "output_changed"
        else:
            status = "fresh_under_manifest"
        reports.append({"key": key, "status": status})
    failures = [item for item in reports if item["status"] != "fresh_under_manifest"]
    return {"schema": SCHEMA, "ok": not failures, "cells": reports, "limits": manifest.get("limits", [])}


def command_record(args: argparse.Namespace) -> int:
    manifest = make_manifest(read_notebook(Path(args.notebook)))
    Path(args.manifest).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "manifest": args.manifest, "cell_count": len(manifest["cells"])}, sort_keys=True))
    return 0


def command_check(args: argparse.Namespace) -> int:
    notebook = read_notebook(Path(args.notebook))
    try:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(json.dumps({"schema": SCHEMA, "ok": False, "status": "missing_manifest"}, sort_keys=True))
        return 2
    report = check(notebook, manifest)
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if report["ok"] else 1


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    record = sub.add_parser("record", help="record source/output hashes")
    record.add_argument("notebook")
    record.add_argument("--manifest", required=True)
    record.set_defaults(run=command_record)
    verify = sub.add_parser("check", help="check a notebook against a manifest")
    verify.add_argument("notebook")
    verify.add_argument("--manifest", required=True)
    verify.set_defaults(run=command_check)
    return root


if __name__ == "__main__":
    try:
        arguments = parser().parse_args()
        raise SystemExit(arguments.run(arguments))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2)
