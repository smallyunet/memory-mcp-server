# User Command Memory MCP Server

A lightweight local server that exposes a REST “Command Memory Layer”, plus a Streamable HTTP MCP interface for fetching recent command context and related analytics.

- Stores user commands (not AI replies) in a local SQLite database
- Exposes 4 REST APIs: `/record_command`, `/commands`, `/stats`, `/preferences`
- Provides MCP resources and tools (see below for full list)
- Ships with Docker Compose and persists data at `./data/memory.db`

## Run with Docker Compose

```bash
docker compose up --build
```

Services:
- memory-mcp: MCP + REST on http://localhost:8000
- sqlite-web: SQLite browser on http://localhost:8080 (reads ./data/memory.db)

Data persists to `./data/memory.db` on the host.

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
	-d '{"command_text":"Write unit tests for FastAPI endpoints","tags":["testing","python"]}'
```

### 2) List commands

GET /commands

Response:

```json
[
	{
		"command_text": "Write unit tests for FastAPI endpoints",
		"tags": ["testing", "python"],
		"timestamp": "2025-11-08T11:10:00Z"
	}
]
```

```bash
curl http://localhost:8000/commands
```

### 3) Stats

GET /stats

Response (MVP heuristic):

```json
{
	"total_commands": 124,
	"top_keywords": ["refactor", "test", "optimize"],
	"active_hours": ["10:00-11:00", "20:00-21:00", "22:00-23:00"]
}
```

```bash
curl http://localhost:8000/stats
```

### 4) Preferences

GET /preferences

Response (MVP heuristic):

```json
{
	"preferred_language": "Python",
	"common_tasks": ["refactor", "test"],
	"style": "async, clean"
}
```

```bash
curl http://localhost:8000/preferences
```

## MCP interface (optional)

The same process also exposes a Streamable HTTP MCP server at `http://localhost:8000/mcp`.

### Tools

| Tool | Args | Description |
|------|------|-------------|
| `memory_context` | `token: string (ignored)`, `limit: int=10` | Return recent command context (list of stored raw commands). |
| `record_command` | `command_text: string`, `tags: list[string]=[]` | Persist a raw user instruction with optional tags. Returns `{"status": "ok"}`. |
| `commands` | *(none)* | List all stored commands (newest first). |
| `stats` | *(none)* | Basic heuristic statistics across commands. |
| `preferences` | *(none)* | Heuristic preference analysis inferred from commands. |
| `help` | *(none)* | Returns this list (for clients that want to introspect). |

### Resource

- `memory://user/{token}/recent` — recent commands as JSON (token ignored in single-user mode)

### Health check

```bash
curl http://localhost:8000/healthz
```

## Storage

- SQLite file: `./data/memory.db` (mapped to `/app/data/memory.db` in the container)
- Tables:
	- `commands` (raw user commands)

## Notes

- This is an MVP: analyses are heuristic and lightweight. You can extend with search, weekly digests, embeddings, or a web UI in the future.
