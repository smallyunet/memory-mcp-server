from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

import crud
import database
from starlette.responses import JSONResponse

# Initialize DB tables
database.init_db()

# Create FastMCP server for MCP traffic
# Provide concise server instructions to guide LLMs on when to use memory tools.
mcp = FastMCP(
    "memory-mcp",
    instructions=(
        "Command Memory Layer:"
        " Use 'record_command(command_text, tags?)' (MCP Tool) to persist raw user instructions."
        " Use 'memory_context(token, limit?)' (MCP Tool) to retrieve recent user commands for grounding."
        " Use 'commands()' (MCP Tool) to list all stored commands."
        " Use 'stats()' (MCP Tool) to get simple usage statistics."
        " Use 'preferences()' (MCP Tool) to get heuristic preference analysis."
        " Tip: some clients cache tool lists — disconnect/reconnect to refresh after updates."
        " Streamable HTTP is also available at /mcp; legacy record/search tools are removed."
    ),
)

# Configure networking and mount path for standalone Streamable HTTP
mcp.settings.host = "0.0.0.0"
mcp.settings.port = 8000
# Use default streamable HTTP endpoint path (client URL should include /mcp)
mcp.settings.streamable_http_path = "/mcp"


@mcp.resource("memory://user/{token}/recent")
def user_recent_resource(token: str) -> str:
    """Return recent command context as JSON string (token ignored in single-user mode)."""
    data = crud.get_recent_context(limit=10)
    return json.dumps(data)


# Tools
## Removed legacy memory_record and memory_search tools (record feature deprecated)


@mcp.tool(name="memory_context")
def tool_context(token: str, limit: int = 10) -> dict:
    """Return recent command context (single-user; token is ignored). Limit is advisory."""
    context = crud.get_recent_context(limit=limit)
    return context


# Additional MCP tools mirroring existing HTTP routes

@mcp.tool(name="record_command")
def tool_record_command(command_text: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """Save a raw user command (single-user).

    Inputs:
    - command_text: required instruction text
    - tags: optional list of tag strings

    Returns: { "status": "ok" } on success, or { "error": str } on validation failure.
    """
    if not command_text or not isinstance(command_text, str):
        return {"error": "command_text_required"}
    if tags is None:
        tags = []
    if not isinstance(tags, list):
        return {"error": "tags_must_be_list"}
    # Coerce non-string items to strings defensively
    safe_tags = [str(t) for t in tags if t is not None]
    crud.create_command(command_text=command_text, tags=safe_tags)
    return {"status": "ok"}


@mcp.tool(name="commands")
def tool_list_commands() -> list[dict]:
    """Return all historical commands for the authenticated user (newest first)."""
    return crud.list_commands()


@mcp.tool(name="stats")
def tool_stats() -> dict:
    """Return basic statistics across commands (single-user)."""
    return crud.compute_stats()


@mcp.tool(name="preferences")
def tool_preferences() -> dict:
    """Return heuristic preference analysis inferred from commands (single-user)."""
    return crud.analyze_preferences()


@mcp.tool(name="help")
def tool_help() -> dict:
    """List available tools and their usage signatures for this server."""
    # Static descriptor to avoid relying on private internals of FastMCP
    return {
        "tools": [
            {
                "name": "memory_context",
                "args": {"token": "string (ignored)", "limit": "int=10"},
                "description": "Return recent command context (single-user).",
            },
            {
                "name": "record_command",
                "args": {"command_text": "string", "tags": "list[string]=[]"},
                "description": "Persist a raw user instruction with optional tags.",
            },
            {"name": "commands", "args": {}, "description": "List all stored commands (newest first)."},
            {"name": "stats", "args": {}, "description": "Basic usage statistics across commands."},
            {"name": "preferences", "args": {}, "description": "Heuristic preference analysis."},
        ]
    }


# Optional: Prompts to guide clients/LLMs
## Removed legacy prompts related to record storage and search.


# Lightweight health endpoint for quick readiness checks
@mcp.custom_route("/healthz", methods=["GET"])
async def health_check(request):
    return JSONResponse({"status": "ok", "transport": "streamable-http", "path": mcp.settings.streamable_http_path})


# ------------------------------
# REST API: Command Memory Layer
# ------------------------------

@mcp.custom_route("/record_command", methods=["POST"])
async def record_command(request):
    """Save a raw user command.

    Body: { "command_text": str, "tags": [str, ...] }
    """
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid_json"}, status_code=400)

    command_text = (data or {}).get("command_text")
    tags = (data or {}).get("tags", []) or []
    if not command_text or not isinstance(command_text, str):
        return JSONResponse({"error": "command_text_required"}, status_code=400)
    if not isinstance(tags, list):
        return JSONResponse({"error": "tags_must_be_list"}, status_code=400)

    crud.create_command(command_text=command_text, tags=tags)
    return JSONResponse({"status": "ok"})


@mcp.custom_route("/commands", methods=["GET"])
async def list_commands(request):
    """Return all historical commands for the authenticated user."""
    items = crud.list_commands()
    return JSONResponse(items)


@mcp.custom_route("/stats", methods=["GET"])
async def stats(request):
    data = crud.compute_stats()
    return JSONResponse(data)


@mcp.custom_route("/preferences", methods=["GET"])
async def preferences(request):
    data = crud.analyze_preferences()
    return JSONResponse(data)


if __name__ == "__main__":
    # Run as a standalone Streamable HTTP MCP server on 0.0.0.0:8000
    # Note: Run AFTER registering prompts and custom routes so they are available.
    mcp.run(transport="streamable-http")
