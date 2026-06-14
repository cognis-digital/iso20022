"""Core engine for ISO 20022 pacs/camt message validation and linting.

Standard library only. No network calls. The validator performs real checks:

  * XML well-formedness
  * Namespace / message-type detection (urn:iso:std:iso:20022:tech:xsd:<id>)
  * Document root sanity (<Document> with a recognised business area)
  * Structural presence of the group header (GrpHdr) and transactions
  * BIC format validation (8 or 11 chars, ISO 9362)
  * IBAN validation (length + mod-97 checksum, ISO 13616)
  * Currency code shape (ISO 4217, 3 upper-case letters)
  * Amount sanity (numeric, non-negative, currency attribute present)
  * ISO date / date-time shape (ISO 8601 fragments used by ISO 20022)
  * Message-id presence and length limits (Max35Text etc.)
  * Debit/credit sum reconciliation for pacs.008 control sums
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import List, Optional
from xml.etree import ElementTree as ET

# ----------------------------------------------------------------------------
# Data model
# ----------------------------------------------------------------------------


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Finding:
    code: str
    severity: Severity
    message: str
    path: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


@dataclass
class Report:
    source: str = ""
    message_type: Optional[str] = None
    namespace: Optional[str] = None
    findings: List[Finding] = field(default_factory=list)

    def add(self, code: str, severity: Severity, message: str, path: str = "") -> None:
        self.findings.append(Finding(code, severity, message, path))

    @property
    def errors(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == Severity.ERROR]

    @property
    def warnings(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == Severity.WARNING]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    @property
    def ok(self) -> bool:
        return not self.has_errors

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "message_type": self.message_type,
            "namespace": self.namespace,
            "ok": self.ok,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "findings": [f.to_dict() for f in self.findings],
        }


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

_NS_RE = re.compile(r"urn:iso:std:iso:20022:tech:xsd:([a-z]+\.\d+\.\d+\.\d+)")
_BIC_RE = re.compile(r"^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$")
_CCY_RE = re.compile(r"^[A-Z]{3}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$"
)
_IBAN_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]+$")

# Recognised ISO 20022 business areas (prefix of the message id).
_BUSINESS_AREAS = {
    "pacs": "Payments Clearing and Settlement",
    "pain": "Payments Initiation",
    "camt": "Cash Management",
    "acmt": "Account Management",
    "reda": "Reference Data",
    "remt": "Remittance Advice",
}


def _localname(tag: str) -> str:
    """Strip the {namespace} prefix from an ElementTree tag."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _find_all(elem: ET.Element, local: str) -> List[ET.Element]:
    """Find all descendants (namespace-agnostic) with the given local name."""
    out = []
    for e in elem.iter():
        if _localname(e.tag) == local:
            out.append(e)
    return out


def _first_text(elem: ET.Element, local: str) -> Optional[str]:
    for e in elem.iter():
        if _localname(e.tag) == local and e.text is not None:
            return e.text.strip()
    return None


def iban_is_valid(iban: str) -> bool:
    """ISO 13616 IBAN validation: structure + mod-97 checksum."""
    s = iban.replace(" ", "").upper()
    if not (15 <= len(s) <= 34):
        return False
    if not _IBAN_RE.match(s):
        return False
    # Move first four chars to the end.
    rearranged = s[4:] + s[:4]
    # Convert letters to numbers (A=10 ... Z=35).
    digits = []
    for ch in rearranged:
        if ch.isdigit():
            digits.append(ch)
        elif ch.isalpha():
            digits.append(str(ord(ch) - 55))
        else:
            return False
    try:
        return int("".join(digits)) % 97 == 1
    except ValueError:
        return False


def bic_is_valid(bic: str) -> bool:
    return bool(_BIC_RE.match(bic.strip()))


def detect_message_type(root: ET.Element) -> tuple[Optional[str], Optional[str]]:
    """Return (message_id, namespace) like ('pacs.008.001.08', 'urn:...')."""
    ns = None
    tag = root.tag
    if "}" in tag:
        ns = tag[1:].split("}", 1)[0]
    if ns:
        m = _NS_RE.search(ns)
        if m:
            return m.group(1), ns
    # Fallback: scan every element's namespace for an iso 20022 xsd urn.
    for e in root.iter():
        if "}" in e.tag:
            cand = e.tag[1:].split("}", 1)[0]
            m = _NS_RE.search(cand)
            if m:
                return m.group(1), cand
    return None, ns


# ----------------------------------------------------------------------------
# Validation routines
# ----------------------------------------------------------------------------


def _check_root(root: ET.Element, report: Report) -> None:
    name = _localname(root.tag)
    if name != "Document":
        report.add(
            "ROOT001",
            Severity.ERROR,
            f"Root element is <{name}>, expected <Document> for an ISO 20022 message.",
            path="/",
        )


def _check_message_type(report: Report) -> None:
    if not report.message_type:
        report.add(
            "NS001",
            Severity.ERROR,
            "Could not detect an ISO 20022 namespace "
            "(urn:iso:std:iso:20022:tech:xsd:<id>).",
            path="/Document/@xmlns",
        )
        return
    area = report.message_type.split(".", 1)[0]
    if area not in _BUSINESS_AREAS:
        report.add(
            "NS002",
            Severity.WARNING,
            f"Unrecognised business area '{area}' in message id "
            f"'{report.message_type}'.",
            path="/Document",
        )


def _check_group_header(root: ET.Element, report: Report) -> None:
    grp = next((e for e in root.iter() if _localname(e.tag) == "GrpHdr"), None)
    if grp is None:
        report.add(
            "GRP001",
            Severity.ERROR,
            "No <GrpHdr> (group header) found.",
            path="/Document//GrpHdr",
        )
        return
    msg_id = _first_text(grp, "MsgId")
    if not msg_id:
        report.add(
            "GRP002",
            Severity.ERROR,
            "<GrpHdr> is missing <MsgId>.",
            path="//GrpHdr/MsgId",
        )
    elif len(msg_id) > 35:
        report.add(
            "GRP003",
            Severity.ERROR,
            f"<MsgId> '{msg_id}' exceeds Max35Text (35 chars).",
            path="//GrpHdr/MsgId",
        )
    cre_dt = _first_text(grp, "CreDtTm")
    if not cre_dt:
        report.add(
            "GRP004",
            Severity.WARNING,
            "<GrpHdr> is missing <CreDtTm> (creation date-time).",
            path="//GrpHdr/CreDtTm",
        )
    elif not _DATETIME_RE.match(cre_dt):
        report.add(
            "DT001",
            Severity.ERROR,
            f"<CreDtTm> '{cre_dt}' is not a valid ISO 8601 date-time.",
            path="//GrpHdr/CreDtTm",
        )


def _check_bics(root: ET.Element, report: Report) -> None:
    # Both legacy <BIC> and ISO 20022 <BICFI> are checked.
    for local in ("BIC", "BICFI"):
        for e in _find_all(root, local):
            val = (e.text or "").strip()
            if val and not bic_is_valid(val):
                report.add(
                    "BIC001",
                    Severity.ERROR,
                    f"Invalid BIC '{val}' (expected 8 or 11 chars, ISO 9362).",
                    path=f"//{local}",
                )


def _check_ibans(root: ET.Element, report: Report) -> None:
    for e in _find_all(root, "IBAN"):
        val = (e.text or "").strip()
        if val and not iban_is_valid(val):
            report.add(
                "IBAN001",
                Severity.ERROR,
                f"Invalid IBAN '{val}' (failed structure or mod-97 checksum).",
                path="//IBAN",
            )


def _check_amounts(root: ET.Element, report: Report) -> None:
    # ISO 20022 monetary amounts carry a Ccy attribute and ActiveCurrencyAndAmount.
    amount_tags = (
        "IntrBkSttlmAmt",
        "InstdAmt",
        "EqvtAmt",
        "Amt",
        "TtlIntrBkSttlmAmt",
        "CtrlSum",
    )
    for e in root.iter():
        local = _localname(e.tag)
        if local not in amount_tags:
            continue
        text = (e.text or "").strip()
        if text == "":
            continue
        try:
            value = Decimal(text)
        except InvalidOperation:
            report.add(
                "AMT001",
                Severity.ERROR,
                f"<{local}> value '{text}' is not a valid decimal amount.",
                path=f"//{local}",
            )
            continue
        if value < 0:
            report.add(
                "AMT002",
                Severity.ERROR,
                f"<{local}> amount {value} is negative; ISO 20022 amounts must be "
                "non-negative.",
                path=f"//{local}",
            )
        # CtrlSum carries no currency; everything else should.
        if local != "CtrlSum":
            ccy = e.attrib.get("Ccy")
            if ccy is None:
                report.add(
                    "AMT003",
                    Severity.ERROR,
                    f"<{local}> is missing the mandatory Ccy attribute.",
                    path=f"//{local}/@Ccy",
                )
            elif not _CCY_RE.match(ccy):
                report.add(
                    "CCY001",
                    Severity.ERROR,
                    f"Currency '{ccy}' on <{local}> is not a 3-letter ISO 4217 code.",
                    path=f"//{local}/@Ccy",
                )


def _check_dates(root: ET.Element, report: Report) -> None:
    date_tags = ("IntrBkSttlmDt", "ReqdExctnDt", "AccptncDtTm", "Dt")
    for e in root.iter():
        local = _localname(e.tag)
        if local not in date_tags:
            continue
        text = (e.text or "").strip()
        if not text:
            continue
        if _DATE_RE.match(text) or _DATETIME_RE.match(text):
            continue
        report.add(
            "DT002",
            Severity.ERROR,
            f"<{local}> value '{text}' is not a valid ISO 8601 date/date-time.",
            path=f"//{local}",
        )


def _check_txn_count_and_sum(root: ET.Element, report: Report) -> None:
    """Reconcile NbOfTxs / CtrlSum in the group header against the transactions."""
    grp = next((e for e in root.iter() if _localname(e.tag) == "GrpHdr"), None)
    txs = [
        e
        for e in root.iter()
        if _localname(e.tag) in ("CdtTrfTxInf", "TxInf", "PmtInf", "DrctDbtTxInf")
    ]
    # Settlement amounts per transaction (used for control-sum reconciliation).
    sttlm_amounts = []
    for tx in txs:
        amt_el = next(
            (c for c in tx.iter() if _localname(c.tag) == "IntrBkSttlmAmt"), None
        )
        if amt_el is not None and amt_el.text:
            try:
                sttlm_amounts.append(Decimal(amt_el.text.strip()))
            except InvalidOperation:
                pass

    if grp is None:
        return

    nb = _first_text(grp, "NbOfTxs")
    if nb is not None:
        try:
            declared = int(nb)
            if declared != len(txs):
                report.add(
                    "REC001",
                    Severity.ERROR,
                    f"<NbOfTxs> declares {declared} transactions but {len(txs)} "
                    "were found.",
                    path="//GrpHdr/NbOfTxs",
                )
        except ValueError:
            report.add(
                "REC002",
                Severity.ERROR,
                f"<NbOfTxs> value '{nb}' is not an integer.",
                path="//GrpHdr/NbOfTxs",
            )

    ctrl = _first_text(grp, "CtrlSum")
    if ctrl is not None and sttlm_amounts:
        try:
            declared_sum = Decimal(ctrl)
            actual = sum(sttlm_amounts)
            if declared_sum != actual:
                report.add(
                    "REC003",
                    Severity.ERROR,
                    f"<CtrlSum> {declared_sum} does not equal the sum of settlement "
                    f"amounts {actual}.",
                    path="//GrpHdr/CtrlSum",
                )
        except InvalidOperation:
            pass


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------


def validate_string(xml_text: str, source: str = "<string>") -> Report:
    """Validate an ISO 20022 message supplied as a string. Always returns a Report."""
    report = Report(source=source)
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        report.add(
            "XML001",
            Severity.ERROR,
            f"XML is not well-formed: {exc}",
            path="/",
        )
        return report

    msg_type, ns = detect_message_type(root)
    report.message_type = msg_type
    report.namespace = ns

    _check_root(root, report)
    _check_message_type(report)
    _check_group_header(root, report)
    _check_bics(root, report)
    _check_ibans(root, report)
    _check_amounts(root, report)
    _check_dates(root, report)
    _check_txn_count_and_sum(root, report)

    if report.ok:
        report.add(
            "OK000",
            Severity.INFO,
            f"Validated successfully as {msg_type or 'ISO 20022'} message.",
        )
    return report


def validate_file(path: str) -> Report:
    """Validate an ISO 20022 message read from a file path."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except UnicodeDecodeError:
        # File exists but is not valid UTF-8 (e.g. Latin-1 or binary).
        report = Report(source=path)
        report.add(
            "IO002",
            Severity.ERROR,
            "File is not valid UTF-8; ISO 20022 XML must be UTF-8 encoded.",
        )
        return report
    except OSError as exc:
        report = Report(source=path)
        report.add("IO001", Severity.ERROR, f"Could not read file: {exc}")
        return report
    return validate_string(text, source=path)


# ---------------------------------------------------------------------------
# Package identity (re-exported by __init__.py)
# ---------------------------------------------------------------------------

TOOL_NAME: str = "iso20022"
TOOL_VERSION: str = "0.1.0"


# ---------------------------------------------------------------------------
# Convenience aliases used by mcp_server and external integrations
# ---------------------------------------------------------------------------

def scan(target: str) -> Report:
    """Alias for validate_file; accepts a file path.

    Provides the ``scan(target)`` entry-point consumed by the MCP server and
    other integrations so they do not need to know the underlying function
    name.
    """
    return validate_file(target)


def to_json(report: Report) -> str:
    """Serialise a Report to a compact JSON string."""
    import json
    return json.dumps(report.to_dict(), indent=2)
