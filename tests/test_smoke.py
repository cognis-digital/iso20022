"""Smoke tests for the iso20022 validator. No network, runs on the demo files."""
import os

import pytest

from iso20022 import (
    TOOL_NAME,
    TOOL_VERSION,
    Severity,
    validate_file,
    validate_string,
)
from iso20022.core import iban_is_valid, bic_is_valid
from iso20022.cli import main

DEMO = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "demos",
    "01-basic",
    "pacs008-valid.xml",
)


def test_metadata():
    assert TOOL_NAME == "iso20022"
    assert TOOL_VERSION


def test_demo_file_is_clean():
    report = validate_file(DEMO)
    assert report.message_type == "pacs.008.001.08"
    assert report.namespace and report.namespace.startswith("urn:iso:std:iso:20022")
    assert not report.has_errors, [f.message for f in report.errors]
    assert report.ok
    # The success info finding is present.
    assert any(f.code == "OK000" for f in report.findings)


def test_iban_checksum_logic():
    assert iban_is_valid("DE89370400440532013000")
    assert iban_is_valid("FI2112345600000785")
    # Flip a digit -> checksum must fail.
    assert not iban_is_valid("DE89370400440532013001")
    assert not iban_is_valid("GB00NWBK")  # too short / bad checksum


def test_bic_logic():
    assert bic_is_valid("DEUTDEFF")        # 8 char
    assert bic_is_valid("DEUTDEFF500")     # 11 char
    assert not bic_is_valid("DEUT")        # too short
    assert not bic_is_valid("1234DEFF")    # bank code must be alpha


def test_malformed_xml_reports_error():
    report = validate_string("<Document><GrpHdr>")
    assert report.has_errors
    assert any(f.code == "XML001" for f in report.findings)


def test_seeded_defects_detected():
    bad = """<?xml version="1.0"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
      <FIToFICstmrCdtTrf>
        <GrpHdr>
          <MsgId>MSG-1</MsgId>
          <CreDtTm>2026-06-08T09:30:00Z</CreDtTm>
          <NbOfTxs>2</NbOfTxs>
          <CtrlSum>100.00</CtrlSum>
        </GrpHdr>
        <CdtTrfTxInf>
          <IntrBkSttlmAmt Ccy="EURO">150.00</IntrBkSttlmAmt>
          <IntrBkSttlmDt>08/06/2026</IntrBkSttlmDt>
          <DbtrAcct><Id><IBAN>DE89370400440532013001</IBAN></Id></DbtrAcct>
          <DbtrAgt><FinInstnId><BICFI>BADBIC</BICFI></FinInstnId></DbtrAgt>
        </CdtTrfTxInf>
      </FIToFICstmrCdtTrf>
    </Document>"""
    report = validate_string(bad)
    codes = {f.code for f in report.findings}
    assert "CCY001" in codes      # 'EURO' is not 3 letters
    assert "DT002" in codes       # bad date format
    assert "IBAN001" in codes     # bad checksum
    assert "BIC001" in codes      # invalid BIC
    assert "REC001" in codes      # NbOfTxs=2 but only 1 tx
    assert "REC003" in codes      # CtrlSum mismatch
    assert report.has_errors


def test_missing_namespace_warns_or_errors():
    report = validate_string("<Document><GrpHdr><MsgId>X</MsgId></GrpHdr></Document>")
    assert any(f.code == "NS001" for f in report.findings)


def test_cli_exit_codes(capsys):
    # Clean demo file -> exit 0
    rc = main(["validate", DEMO])
    assert rc == 0
    out = capsys.readouterr().out
    assert "pacs.008.001.08" in out

    # JSON format works and reports ok
    rc = main(["validate", DEMO, "--format", "json"])
    assert rc == 0
    out = capsys.readouterr().out
    assert '"ok": true' in out


def test_cli_nonzero_on_missing_file():
    rc = main(["validate", "does-not-exist-xyz.xml"])
    assert rc == 1
