# User Command Memory MCP Server

A lightweight, local-first server that provides a REST “Command Memory Layer” and a Streamable HTTP MCP interface to persist user commands and derive preferences for AI agents.

- Local-first and privacy-friendly: single-user, no auth, data stored in SQLite
- REST + MCP: easy to integrate with agents and tools
- Contextual preferences: return task-focused signals based on the current goal
- Dockerized: one command to run; data persisted at `./data/memory.db`

## Features

- Persist raw user instructions (not assistant output)
- Retrieve recent command context and full history
- Heuristic analytics: stats, holistic preferences, and contextual preferences
- MCP tools for direct agent usage, plus plain REST for fallback

## Quick Start (Docker Compose)

```bash
docker compose up --build
```

Services
- memory-mcp: MCP + REST on http://localhost:8000
- sqlite-web: SQLite browser on http://localhost:8080 (reads ./data/memory.db)

Data persists to `./data/memory.db` on the host.

Restart script (rebuild after code changes):
```bash
./restart.sh
```

> Note (Apple Silicon): `sqlite-web` runs as amd64 via emulation and may print a platform warning; this is expected.

## Run Locally (without Docker)

Requirements: Python 3.10+

```bash
# from the repo root
python -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt

# run the server (works best from repo root so data path resolves to ./data)
python app/mcp_server.py
```

Server will listen on http://localhost:8000. Data will be stored at `./data/memory.db`.

## REST API

Single-user mode: No Authorization header required.

### 1) Record command

POST /record_command

Body:

```json
{
	"command_text": "Refactor this function using async/await",
	"tags": ["refactor", "python"]
}
```

Response:

```json
{ "status": "ok" }
```

Example:

```bash
curl -X POST \
	-H 'Content-Type: application/json' \
	http://localhost:8000/record_command \
	-d '{"command_text":"Write unit tests for FastAPI endpoints","tags":["test","python"]}'
```

### 2) List commands

GET /commands

Response:

```json
[
	{
		"command_text": "Write unit tests for FastAPI endpoints",
		"tags": ["test", "python"],
		"timestamp": "2025-11-08T11:10:00Z"
	}
]
```

```bash
curl -s http://localhost:8000/commands | jq
```

### 3) Stats

GET /stats

Response (heuristic):

```json
{
	"total_commands": 124,
	"top_keywords": ["refactor", "test", "optimize"],
	"active_hours": ["10:00-11:00", "20:00-21:00", "22:00-23:00"]
}
```

```bash
curl -s http://localhost:8000/stats | jq
```

### 4) Preferences (holistic)

GET /preferences

Response (heuristic):

```json
{
	"preferred_language": "Python",
	"preferred_language_confidence": 0.8,
	"common_tasks": ["test", "refactor"],
	"style": "async, OOP",
	"frameworks": ["fastapi"],
	"tools": ["docker", "pytest", "git"],
	"signals": {
		"languages": {"python": 8, "javascript": 2},
		"tasks": {"test": 5, "refactor": 3},
		"styles": {"async": 3, "oop": 2},
		"frameworks": {"fastapi": 3},
		"tools": {"docker": 3, "pytest": 3, "git": 2}
	}
}
```

```bash
curl -s http://localhost:8000/preferences | jq
```

### 5) Preferences (contextual)

POST /preferences/contextual

Body:

```json
{ "context": "Update README and improve docs clarity", "limit": 50 }
```

Response (task-focused subset):

```json
{
	"matched_groups": ["documentation"],
	"preferred_language": "Python",
	"style_subset": [],
	"tasks_subset": ["documentation"],
	"frameworks_subset": [],
	"tools_subset": ["git"],
	"signals_overlap": {
		"tasks": {"documentation": 3},
		"styles": {},
		"tools": {"git": 2}
	},
	"context": "Update README and improve docs clarity"
}
```

```bash
curl -s -X POST http://localhost:8000/preferences/contextual \
	-H 'Content-Type: application/json' \
	-d '{"context":"Update README and improve docs clarity"}' | jq
```

## MCP interface (optional)

This server also exposes a Streamable HTTP MCP endpoint at `http://localhost:8000/mcp`.

### Tools

| Tool | Args | Description |
|------|------|-------------|
| `memory_context` | `token: string (ignored)`, `limit: int=10` | Return recent command context (list of stored raw commands). |
| `record_command` | `command_text: string`, `tags: list[string]=[]` | Persist a raw user instruction with optional tags. |
| `commands` | *(none)* | List all stored commands (newest first). |
| `stats` | *(none)* | Basic heuristic statistics across commands. |
| `preferences` | *(none)* | Holistic heuristic preference analysis (language/tasks/style/frameworks/tools + confidence + raw signals). |
| `contextual_preferences` | `context: string`, `limit: int=50` | Task-focused subset of preferences filtered by the provided context string. |
| `help` | *(none)* | Returns this list (for clients that want to introspect). |

### Resource

- `memory://user/{token}/recent` — recent commands as JSON (token ignored in single-user mode)

### Health check

```bash
curl -s http://localhost:8000/healthz | jq
```

## Data & Storage

- SQLite file: `./data/memory.db` (mapped to `/app/data/memory.db` in the container)
- Table(s):
	- `commands` — raw user commands with tags and timestamps

## Design Principles

- Local-first: designed to run on your machine by default.
- Minimal coupling: both MCP tools and plain REST are available.
- Heuristic, transparent signals: expose raw counts alongside summaries.

## Troubleshooting

- “Instance <...> is not bound to a Session”
	- The server has been fixed to avoid detached-instance issues; if you see this after updating code, restart the service:
		```bash
		./restart.sh
		```
- Apple Silicon platform warning for `sqlite-web`
	- The image runs under amd64 emulation; it’s safe to ignore. You can also replace it with a Python-based container installing `sqlite-web` via pip.

## Next Ideas

- Recency weighting and trend detection
- Negation handling (e.g., “avoid docker”)
- Confidence thresholds and insufficient-data flag
- Relevance scoring beyond keyword overlap
