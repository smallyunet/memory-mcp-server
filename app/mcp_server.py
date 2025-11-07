from __future__ import annotations

import json
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

import crud
import database

# Initialize DB tables
database.init_db()

# Create FastMCP server for MCP traffic
# Provide concise server instructions to guide LLMs on when to use memory tools.
mcp = FastMCP(
    "memory-mcp",
    instructions=(
        "Memory usage policy: 1) At conversation start, on a new task, or roughly every 3–5 turns, call 'memory_context(token, limit=15)' to refresh recent preferences. "
        "2) When you infer a stable user preference, profile detail, project-wide decision, or reusable fact, call 'memory_record(token, summary, category?, tags?, detail?)'. "
        "Keep summaries concise (<=160 chars) and avoid secrets or one-time data. 3) For targeted recall, use 'memory_search(token, query)'. "
        "Avoid calling tools every turn; refresh when it benefits future turns."
    ),
)

# Configure networking and mount path for standalone Streamable HTTP
mcp.settings.host = "0.0.0.0"
mcp.settings.port = 8000
# Use default streamable HTTP endpoint path (client URL should include /mcp)
mcp.settings.streamable_http_path = "/mcp"


# Resources
@mcp.resource("memory://help")
def help_resource() -> str:
    """Public help content describing endpoints and MCP methods."""
    return (
        "# Memory MCP\n\n"
        "Tools:\n\n"
        "- memory_record(token, summary, category?, tags?, detail?)\n"
        "- memory_search(token, query)\n"
        "- memory_context(token, limit?)\n\n"
        "Resources:\n\n"
        "- memory://help (this page)\n"
        "- memory://user/{token}/recent (recent summaries for user token)\n"
    )


@mcp.resource("memory://user/{token}/recent")
def user_recent_resource(token: str) -> str:
    """Return recent memory context for a given token as JSON string."""
    # Default to a slightly larger window for human-readable resource
    data = crud.get_recent_context(token, limit=10)
    return json.dumps(data)


# Tools
@mcp.tool(name="memory_record")
def tool_record(token: str, summary: str, category: str = "general", tags: Optional[List[str]] = None, detail: Optional[dict] = None) -> str:
    """Store a memory record for a user token."""
    payload = {
        "summary": summary,
        "category": category,
        "tags": tags or [],
        "detail": detail,
    }
    crud.create_record(token, payload)
    return "ok"


@mcp.tool(name="memory_search")
def tool_search(token: str, query: str) -> dict:
    """Search memory records for a user token by query in summary."""
    results = crud.search_records(token, query)
    return {"results": results}


@mcp.tool(name="memory_context")
def tool_context(token: str, limit: int = 10) -> dict:
    """Return recent memory context for a user token. Limit is advisory."""
    context = crud.get_recent_context(token, limit=limit)
    return context


# Optional: Prompts to guide clients/LLMs
@mcp.prompt(title="Add Memory")
def prompt_add_memory(summary: str, category: str = "general", tags: str = "") -> str:
    """Prompt template for adding a memory."""
    return (
        "You are a helpful assistant that records user memories.\n"
        f"Category: {category}\n"
        f"Tags: {tags}\n"
        f"Summary: {summary}\n"
    )


@mcp.prompt(title="Search Memory")
def prompt_search_memory(query: str) -> str:
    """Prompt template for searching memories."""
    return (
        "Search the stored memories for relevant items.\n"
        f"Query: {query}\n"
    )


# Lightweight health endpoint for quick readiness checks
@mcp.custom_route("/healthz", methods=["GET"])
async def health_check(request):
    from starlette.responses import JSONResponse

    return JSONResponse({"status": "ok", "transport": "streamable-http", "path": mcp.settings.streamable_http_path})


if __name__ == "__main__":
    # Run as a standalone Streamable HTTP MCP server on 0.0.0.0:8000
    # Note: Run AFTER registering prompts and custom routes so they are available.
    mcp.run(transport="streamable-http")
