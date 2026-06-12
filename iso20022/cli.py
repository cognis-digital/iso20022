"""Command-line interface for the iso20022 validator.

Examples:

    # Validate a single message, human-readable table
    iso20022 validate payment.xml

    # Validate several files and emit JSON for CI / piping
    iso20022 validate *.xml --format json

    # Exit code is non-zero when any file has errors -> use it as a CI gate
    iso20022 validate payment.xml && echo CLEAN

    # Show the tool version
    iso20022 --version
"""
from __future__ import annotations

import argparse
import json
from typing import List, Optional

from . import TOOL_NAME, TOOL_VERSION
from .core import Report, Severity, validate_file

_SEV_LABEL = {
    Severity.ERROR: "ERROR",
    Severity.WARNING: "WARN",
    Severity.INFO: "INFO",
}


def _render_table(reports: List[Report]) -> str:
    lines: List[str] = []
    total_err = total_warn = 0
    for rep in reports:
        header = f"{rep.source}  [{rep.message_type or 'unknown'}]"
        lines.append(header)
        lines.append("-" * len(header))
        if not rep.findings:
            lines.append("  (no findings)")
        for f in rep.findings:
            label = _SEV_LABEL[f.severity]
            loc = f"  {f.path}" if f.path else ""
            lines.append(f"  {label:5} {f.code}: {f.message}{loc}")
        total_err += len(rep.errors)
        total_warn += len(rep.warnings)
        status = "OK" if rep.ok else "FAILED"
        lines.append(
            f"  => {status} ({len(rep.errors)} error(s), {len(rep.warnings)} warning(s))"
        )
        lines.append("")
    lines.append(
        f"Summary: {len(reports)} file(s), {total_err} error(s), "
        f"{total_warn} warning(s)."
    )
    return "\n".join(lines)


def _render_json(reports: List[Report]) -> str:
    payload = {
        "tool": TOOL_NAME,
        "version": TOOL_VERSION,
        "file_count": len(reports),
        "ok": all(r.ok for r in reports),
        "reports": [r.to_dict() for r in reports],
    }
    return json.dumps(payload, indent=2)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="Validate and lint ISO 20022 pacs/camt XML payment messages "
        "(SWIFT MX). Zero dependencies, standard library only.",
        epilog="Example: iso20022 validate payment.xml --format json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{TOOL_NAME} {TOOL_VERSION}",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Output format (default: table). Use json for CI / piping.",
    )

    sub = parser.add_subparsers(dest="command")
    val = sub.add_parser(
        "validate",
        help="Validate one or more ISO 20022 XML message files.",
        description="Validate one or more ISO 20022 XML message files. "
        "Exits non-zero if any file contains errors.",
    )
    val.add_argument(
        "files",
        nargs="+",
        metavar="FILE",
        help="Path(s) to ISO 20022 XML message file(s).",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command != "validate":
        parser.print_help()
        return 2

    reports = [validate_file(path) for path in args.files]

    if args.format == "json":
        print(_render_json(reports))
    else:
        print(_render_table(reports))

    # Non-zero exit when any file has errors so CI gates can rely on it.
    return 1 if any(r.has_errors for r in reports) else 0
