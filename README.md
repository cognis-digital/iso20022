<a name="top"></a>
<div align="center">

<img src="https://capsule-render.vercel.app/api?type=rect&color=0:6b46c1,100:2b6cb0&height=120&section=header&text=ISO20022&fontSize=48&fontColor=ffffff&fontAlignY=58" width="100%" alt="ISO20022"/>

# ISO20022

### Validates, lints, and diffs ISO 20022 / pacs / camt payment messages and translates legacy MT into MX with schema-aware errors.

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=18&duration=3500&pause=1000&color=6B46C1&center=true&vCenter=true&width=720&lines=Validates+lints+and+diffs+ISO+20022++pacs++camt+payment+mess;Self-hostable+%C2%B7+MCP-native+%C2%B7+CI-ready+%C2%B7+polyglot" width="720"/>

[![PyPI](https://img.shields.io/pypi/v/cognis-iso20022.svg?color=6b46c1)](https://pypi.org/project/cognis-iso20022/) [![CI](https://github.com/cognis-digital/iso20022/actions/workflows/ci.yml/badge.svg)](https://github.com/cognis-digital/iso20022/actions) [![License: COCL 1.0](https://img.shields.io/badge/License-COCL%201.0-2b6cb0.svg)](LICENSE) [![Suite](https://img.shields.io/badge/Cognis-Neural%20Suite-6b46c1.svg)](https://github.com/cognis-digital)

*Fintech & Payments Security — PCI, fraud, AML, and payment rails.*

</div>

```bash
pip install cognis-iso20022
iso20022 scan .            # → prioritized findings in seconds
```

## Usage — step by step

1. **Install** (zero runtime dependencies, standard library only):

   ```bash
   pip install iso20022
   ```

2. **Validate a message** — point the `validate` subcommand at one or more ISO 20022 XML files (pacs/camt SWIFT MX):

   ```bash
   iso20022 validate payment.xml
   ```

   You get a per-file table of findings (ERROR / WARN / INFO) plus a summary line.

3. **Validate a batch** — globs and multiple paths are accepted:

   ```bash
   iso20022 validate inbound/*.xml
   ```

4. **Read the output in CI** — emit JSON for piping, and rely on the exit code (non-zero when any file has errors):

   ```bash
   iso20022 validate payment.xml --format json | jq '.ok'
   iso20022 validate payment.xml && echo CLEAN
   ```

5. **Automation / CI gate** — fail the pipeline when any message is invalid:

   ```bash
   iso20022 validate messages/*.xml --format json > iso20022-report.json
   ```

## Contents

- [Why iso20022?](#why) · [Features](#features) · [Quick start](#quick-start) · [Example](#example) · [Architecture](#architecture) · [AI stack](#ai-stack) · [How it compares](#how-it-compares) · [Integrations](#integrations) · [Install anywhere](#install-anywhere) · [Related](#related) · [Contributing](#contributing)

<a name="why"></a>
## Why iso20022?

The 2025 SWIFT MT-to-MX migration left teams without a free CLI validator; schema-aware lint + MT->MX diff in CI is exactly what payment ops need and Googles constantly.

`iso20022` is single-purpose, scriptable, and self-hostable: point it at a target, get prioritized results in the format your workflow already speaks (table · JSON · SARIF), gate CI on it, and let agents drive it over MCP.

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="features"></a>
## Features

- ✅ Iban Is Valid
- ✅ Bic Is Valid
- ✅ Detect Message Type
- ✅ Validate String
- ✅ Validate File
- ✅ Runs on Linux/macOS/Windows · Docker · devcontainer
- ✅ Ports in Python, JavaScript, Go, and Rust (`ports/`)

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="quick-start"></a>
## Quick start

```bash
pip install cognis-iso20022
iso20022 --version
iso20022 scan .                       # scan current project
iso20022 scan . --format json         # machine-readable
iso20022 scan . --fail-on high        # CI gate (non-zero exit)
```

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="example"></a>
## Example

```text
$ iso20022 scan .
  [HIGH    ] ISO-001  example finding             (./src/app.py)
  [MEDIUM  ] ISO-002  another signal              (./config.yaml)

  2 findings · risk score 5 · 38ms
```

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="architecture"></a>
## Architecture

```mermaid
flowchart LR
  IN[target / manifest] --> P[iso20022<br/>checks + rules]
  P --> OUT[findings (JSON / SARIF)]
```

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="ai-stack"></a>
## Use it from any AI stack

`iso20022` is interoperable with every popular way of using AI:

- **MCP server** — `iso20022 mcp` (Claude Desktop, Cursor, Cognis.Studio, [uncensored-fleet](https://github.com/cognis-digital/uncensored-fleet))
- **OpenAI-compatible / JSON** — pipe `iso20022 scan . --format json` into any agent or LLM
- **LangChain · CrewAI · AutoGen · LlamaIndex** — wrap the CLI/JSON as a tool in one line
- **CI / scripts** — exit codes + SARIF for non-AI pipelines

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="how-it-compares"></a>
## How it compares

| | **Cognis iso20022** | Prowide ISO 20022 |
|---|:---:|:---:|
| Self-hostable, no account | ✅ | varies |
| Single command, zero config | ✅ | ⚠️ |
| JSON + SARIF for CI | ✅ | varies |
| MCP-native (AI agents) | ✅ | ❌ |
| Polyglot ports (JS/Go/Rust) | ✅ | ❌ |
| Open license | ✅ COCL | varies |

*Built in the spirit of **Prowide ISO 20022 / py-iso20022**, re-framed the Cognis way. Missing a credit? Open a PR.*

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="integrations"></a>
## Integrations

Pipes into your stack: **SARIF** for code-scanning, **JSON** for anything, an **MCP server** (`iso20022 mcp`) for AI agents, and a webhook forwarder for SIEM/Slack/Jira. See [`docs/INTEGRATIONS.md`](docs/INTEGRATIONS.md).

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="install-anywhere"></a>
## Install — every way, every platform

```bash
pip install "git+https://github.com/cognis-digital/iso20022.git"    # pip (works today)
pipx install "git+https://github.com/cognis-digital/iso20022.git"   # isolated CLI
uv tool install "git+https://github.com/cognis-digital/iso20022.git" # uv
pip install cognis-iso20022                                          # PyPI (when published)
docker run --rm ghcr.io/cognis-digital/iso20022:latest --help        # Docker
brew install cognis-digital/tap/iso20022                             # Homebrew tap
curl -fsSL https://raw.githubusercontent.com/cognis-digital/iso20022/main/install.sh | sh
```

| Linux | macOS | Windows | Docker | Cloud |
|---|---|---|---|---|
| `scripts/setup-linux.sh` | `scripts/setup-macos.sh` | `scripts/setup-windows.ps1` | `docker run ghcr.io/cognis-digital/iso20022` | [DEPLOY.md](docs/DEPLOY.md) (AWS/Azure/GCP/k8s) |

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="related"></a>
## Related Cognis tools

- [`panhound`](https://github.com/cognis-digital/panhound) — Scans code, logs, fixtures, and S3 buckets for leaked PANs (Luhn-validated card numbers) and CVVs before they hit prod.
- [`fraudlens`](https://github.com/cognis-digital/fraudlens) — Replays a stream of transactions against pluggable fraud rules and ML scorers, emitting precision/recall and alert volume from the terminal.
- [`obscan`](https://github.com/cognis-digital/obscan) — Conformance and security linter for Open Banking / FAPI APIs: validates OAuth flows, consent scopes, and PSD2 endpoints against the spec.
- [`ledgerproof`](https://github.com/cognis-digital/ledgerproof) — Verifies double-entry ledger integrity and tamper-evidence by checking balance invariants and hash-chained journal entries.
- [`tokenvault`](https://github.com/cognis-digital/tokenvault) — Self-hostable PCI tokenization microservice and CLI that swaps PANs for format-preserving tokens and proves no raw card data persists.
- [`sanctscan`](https://github.com/cognis-digital/sanctscan) — Screens counterparties and transactions against OFAC/EU/UN sanctions lists with fuzzy name matching and explainable hit scoring.

**Explore the suite →** [🗂️ all 170+ tools](https://github.com/cognis-digital/cognis-neural-suite) · [⭐ awesome-cognis](https://github.com/cognis-digital/awesome-cognis) · [🔗 cognis-sources](https://github.com/cognis-digital/cognis-sources) · [🤖 uncensored-fleet](https://github.com/cognis-digital/uncensored-fleet) · [🧠 engram](https://github.com/cognis-digital/engram)

<div align="right"><a href="#top">↑ back to top</a></div>

<a name="contributing"></a>
## Contributing

PRs, new rules, and demo scenarios are welcome under the collaboration-pull model — see [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

> ### ⭐ If `iso20022` saved you time, **star it** — it genuinely helps others find it.

## License

Source-available under the **Cognis Open Collaboration License (COCL) v1.0** — free for personal, internal-evaluation, research, and educational use; **commercial / production use requires a license** (licensing@cognis.digital). See [LICENSE](LICENSE).

---

<div align="center"><sub><b><a href="https://cognis.digital">Cognis Digital</a></b> · one of 170+ tools in the <a href="https://github.com/cognis-digital/cognis-neural-suite">Cognis Neural Suite</a> · <i>Making Tomorrow Better Today</i></sub></div>
