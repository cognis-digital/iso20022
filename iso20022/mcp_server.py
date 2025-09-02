"""ISO20022 MCP server — exposes scan() as an MCP tool for Cognis.Studio."""
from __future__ import annotations
from iso20022.core import scan, to_json

def serve() -> int:
    """Start an MCP stdio server. Requires the optional 'mcp' extra:
        pip install "cognis-iso20022[mcp]"
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print("Install the MCP extra: pip install 'cognis-iso20022[mcp]'")
        return 1
    app = FastMCP("iso20022")

    @app.tool()
    def iso20022_scan(target: str) -> str:
        """Validates, lints, and diffs ISO 20022 / pacs / camt payment messages and translates legacy MT into MX with schema-aware errors.. Returns JSON findings."""
        return to_json(scan(target))

    app.run()
    return 0
