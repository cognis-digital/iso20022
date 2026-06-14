"""Hardening tests: error paths, edge cases, and new validation guards.

All tests use only the public API (validate_string, validate_file, main).
No network access, no external files beyond the existing demo.
"""
from __future__ import annotations

import json
import os
import tempfile

from iso20022.core import (
    validate_string, validate_file, scan, to_json, TOOL_NAME, TOOL_VERSION
)
from iso20022.cli import main


# ---------------------------------------------------------------------------
# Package identity
# ---------------------------------------------------------------------------

def test_core_exports_tool_name_and_version():
    assert TOOL_NAME == "iso20022"
    assert TOOL_VERSION  # non-empty


# ---------------------------------------------------------------------------
# scan() / to_json() aliases (used by MCP server)
# ---------------------------------------------------------------------------

def test_scan_alias_accepts_file():
    demo = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "demos", "01-basic", "pacs008-valid.xml",
    )
    report = scan(demo)
    assert report.ok


def test_scan_alias_missing_file():
    report = scan("definitely-does-not-exist-xyz.xml")
    assert report.has_errors
    assert any(f.code == "IO001" for f in report.findings)


def test_to_json_produces_valid_json():
    report = validate_string("<bad>")
    blob = to_json(report)
    obj = json.loads(blob)  # must not raise
    assert "ok" in obj
    assert obj["ok"] is False


# ---------------------------------------------------------------------------
# validate_file: non-UTF-8 input
# ---------------------------------------------------------------------------

def test_validate_file_non_utf8():
    """A file with invalid UTF-8 bytes must return IO002, not crash."""
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as fh:
        # Write bytes that are not valid UTF-8 (latin-1 encoded ö)
        fh.write(b"<?xml version='1.0'?><Document>\x96</Document>")
        name = fh.name
    try:
        report = validate_file(name)
        assert report.has_errors
        assert any(f.code == "IO002" for f in report.findings)
    finally:
        os.unlink(name)


# ---------------------------------------------------------------------------
# NbOfTxs vs actual transaction count
# ---------------------------------------------------------------------------

_PACS_TPL = """\
<?xml version="1.0"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
  <FIToFICstmrCdtTrf>
    <GrpHdr>
      <MsgId>T001</MsgId>
      <CreDtTm>2026-06-08T09:30:00Z</CreDtTm>
      <NbOfTxs>{nb}</NbOfTxs>
    </GrpHdr>{txns}
  </FIToFICstmrCdtTrf>
</Document>"""

_ONE_TXN = """
    <CdtTrfTxInf>
      <IntrBkSttlmAmt Ccy="EUR">100.00</IntrBkSttlmAmt>
    </CdtTrfTxInf>"""


def test_nbooftxs_declared_but_zero_transactions():
    """NbOfTxs=3 with no actual transactions must raise REC001."""
    xml = _PACS_TPL.format(nb=3, txns="")
    report = validate_string(xml)
    codes = {f.code for f in report.findings}
    assert "REC001" in codes, f"Expected REC001 in {codes}"


def test_nbooftxs_mismatch_one_vs_two():
    """NbOfTxs=1 but 2 transactions present must raise REC001."""
    xml = _PACS_TPL.format(nb=1, txns=_ONE_TXN + _ONE_TXN)
    report = validate_string(xml)
    codes = {f.code for f in report.findings}
    assert "REC001" in codes


def test_nbooftxs_matches_does_not_raise_rec001():
    """NbOfTxs=1 with exactly 1 transaction must NOT raise REC001."""
    xml = _PACS_TPL.format(nb=1, txns=_ONE_TXN)
    report = validate_string(xml)
    codes = {f.code for f in report.findings}
    assert "REC001" not in codes


# ---------------------------------------------------------------------------
# CLI hardening
# ---------------------------------------------------------------------------

def test_cli_validate_utf8_error(tmp_path, capsys):
    """A non-UTF-8 file must exit 1 with a clean IO002 error, not a traceback."""
    bad_file = tmp_path / "bad.xml"
    bad_file.write_bytes(b"<?xml?><Data>\x96</Data>")
    rc = main(["validate", str(bad_file)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "IO002" in out


def test_cli_no_subcommand_exits_2(capsys):
    """Calling main() with no subcommand must return exit code 2."""
    rc = main([])
    assert rc == 2


def test_cli_json_format_includes_tool_name(capsys):
    demo = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "demos", "01-basic", "pacs008-valid.xml",
    )
    rc = main(["validate", demo, "--format", "json"])
    assert rc == 0
    out = capsys.readouterr().out
    obj = json.loads(out)
    assert obj["tool"] == TOOL_NAME
