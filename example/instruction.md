# Memory MCP Server — Usage Instructions

This document provides a practical instruction set for assistants and tools that interact with the Memory MCP Server in this repository. It aims to maximize signal (useful, reusable memory) while minimizing noise (ephemeral or redundant data).

The server exposes three tools and one help resource:
- `memory_context(token, limit?)` — Load recent core memories (default limit: 15)
- `memory_search(token, query)` — Search stored memories across summary, tags, and category
- `memory_record(token, summary, category?, tags?, detail?)` — Persist a new memory
- Resource: `memory://help`

The HTTP transport (for MCP-aware clients) listens on `0.0.0.0:8000` with path `/mcp`.

---

## When to Load, Search, and Record

### Load Context (memory_context)
Call when:
- Conversation start (first turn)
- A clearly new task/topic begins
- Roughly every 3–5 turns to refresh context and reduce drift
- Before major code generation or design recommendations
- You’re missing a known preference required to proceed

Use `limit=15` by default. Adjust up/down (10–20) based on latency and usefulness.

### Search (memory_search)
Call when you need to:
- Verify if a preference/decision already exists before saving a new one (de‑duplication)
- Retrieve prior decisions’ rationale/scope to inform current work
- Fill a reasoning gap (e.g., “What DB strategy did we adopt previously?”)

Avoid searching every turn—justify by need.

### Record (memory_record)
Record ONLY high-value, reusable items:
- Stable user preferences (style, tool, workflow)
- Concrete technical/infra decisions
- Cross-session constraints that reduce ambiguity in future turns

Do NOT record:
- Ephemeral states (short-lived errors, temporary hacks)
- Secrets, credentials, tokens, PII
- One-off steps unlikely to recur
- Speculative ideas not yet adopted

Before recording, run a quick `memory_search` with 1–3 key terms to avoid duplicates.

---

## Categories (Taxonomy)

Use one of the following categories to improve retrieval and aggregation:

- `profile` — User profile and long-term preferences
- `tech.preference` — Technology/tooling preferences
- `tech.decision` — Concrete technical decisions
- `infra.incident` — Infra issues/incidents and concise root causes
- `infra.decision` — Infra-level decisions (deploy/monitoring/architecture)
- `workflow.preference` — Collaboration/review/branching preferences
- `deprecated` — Deprecated preferences/decisions (avoid relying on these)

If uncertain: for stack/tool bias use `tech.preference`; for finalized design changes use `tech.decision`.

---

## Decision Detail Schema (Recommended)

For decisions, include a structured `detail` object to strengthen future reuse:

```json
{
  "type": "decision",
  "scope": "service:auth | project:memory-mcp | global",
  "rationale": "Unify permission audit and decouple bot from DB",
  "status": "approved",
  "source": "issue:#42 | manual | copilot",
  "date": "2025-11-07"
}
```

Status options: `proposed | approved | deprecated | rejected`.

---

## Summary Style Guide

- ≤ 160 characters
- Atomic, declarative, no filler (avoid “User says that…”) 
- Present tense for preferences, past tense for finalized decisions
- No sensitive data; use placeholders like `<API_KEY>` if needed

Examples:
- Preference: `Prefers concise diff output; avoid verbose stack traces.`
- Decision: `Auth service now uses REST permission endpoints; direct DB writes removed.`

---

## Duplication Guard (Client-side Heuristic)

1. Extract 1–3 key tokens from the intended summary.
2. Call `memory_search(token, token_i)` for each.
3. If a near-identical summary already exists (high textual overlap), skip or update instead of adding a new record.

---

## Privacy & Safety

Never store:
- Secrets (API keys, passwords, tokens)
- Personal identifiable information (PII)
- Full stack traces; summarize root cause succinctly instead

The backend generates `timestamp` automatically; clients should not set it.

---

## Quick Usage Examples

> The examples below are conceptual invocations. Actual usage depends on your MCP client integration.

- Load context at conversation start:
  - `memory_context(token="smallyu", limit=5)`

- Targeted recall before making a decision:
  - `memory_search(token="smallyu", query="permission api decision")`

- Persist a new decision with structure:
  - `memory_record(
        token="smallyu",
        summary="Auth service uses REST /permissions; direct DB writes removed.",
        category="tech.decision",
        tags=["permissions","api","refactor","service:auth"],
        detail={
          "type":"decision",
          "scope":"service:auth",
          "rationale":"Centralize auditing and reduce coupling",
          "status":"approved",
          "source":"manual",
          "date":"2025-11-07"
        }
     )`

---

## Token Consistency

Use a single, consistent user token (e.g., `smallyu`) across all calls. Mixed tokens degrade recall and context quality.

---

## Resource Index

- `memory://help` — Overview and usage hints
- `memory://user/{token}/recent` — Recent summaries for a given token

---

## Notes

- Server search matches across `summary`, `tags`, and `category` (not just `summary`).
- Default `memory_context` limit is small by design; expand only when needed.
- Prefer fewer, higher-quality records over frequent, low-signal entries.
