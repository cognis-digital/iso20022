# Demo 01 - Basic ISO 20022 validation

This demo runs the `iso20022` validator against two real-world-shaped
pacs.008 (FIToFICustomerCreditTransfer) messages: one clean, one with seeded
defects.

## Files

- `pacs008-valid.xml` - a well-formed pacs.008.001.08 credit transfer with a
  valid BIC, a valid (mod-97-checked) IBAN, correct currency attributes, an
  ISO 8601 date-time, and a `NbOfTxs` / `CtrlSum` that reconciles to the single
  settlement amount.

## What it shows

Run the validator on the clean file:

```
python -m iso20022 validate demos/01-basic/pacs008-valid.xml
```

Expected: the tool detects the message type `pacs.008.001.08`, reports
**0 errors / 0 warnings**, prints the `OK000` informational finding, and exits
with status code `0`.

JSON output for CI pipelines:

```
python -m iso20022 validate demos/01-basic/pacs008-valid.xml --format json
```

The JSON payload has `"ok": true` and an empty error list, so a CI gate using
the exit code passes.

## Try breaking it

Change the `<IBAN>` body, the `Ccy` attribute, or the `<CtrlSum>` value and
re-run: the validator will emit `IBAN001`, `CCY001`, or `REC003` findings and
exit with status code `1`.
