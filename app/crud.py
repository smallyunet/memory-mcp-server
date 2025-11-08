import models, database
from sqlalchemy.orm import Session
from typing import List, Dict

def create_command(command_text: str, tags: List[str]):
    """Insert a raw user command into the commands table (single-user mode)."""
    with database.session_scope() as db:
        entry = models.Command(
            command_text=command_text,
            tags=",".join(tags) if tags else "",
        )
        db.add(entry)

def _serialize_commands(rows: List[models.Command]) -> List[Dict]:
    """Convert ORM rows to plain serializable dicts without relying on lazy loads."""
    serialized = []
    for r in rows:
        serialized.append({
            "command_text": r.command_text,
            "tags": r.tags.split(",") if r.tags else [],
            "timestamp": r.timestamp.isoformat() + "Z",
        })
    return serialized


def list_commands() -> List[Dict]:
    """Return all commands ordered by newest first (single-user).

    Note: We immediately serialize inside the session context so that no
    attribute access is attempted after the session is closed, avoiding
    detached instance refresh errors.
    """
    with database.session_scope() as db:
        rows = (
            db.query(models.Command)
            .order_by(models.Command.timestamp.desc())
            .all()
        )
        return _serialize_commands(rows)

def compute_stats() -> Dict:
    """Compute basic statistics across commands (single-user)."""
    with database.session_scope() as db:
        rows = db.query(models.Command).all()
        # Work with a fully serialized snapshot to avoid detached issues.
        snap = list(rows)
    total = len(snap)
    tag_counter: Dict[str, int] = {}
    hour_counter: Dict[int, int] = {}
    for r in snap:
        # tags
        for t in (r.tags.split(",") if r.tags else []):
            if not t:
                continue
            tag_counter[t] = tag_counter.get(t, 0) + 1
        # active hours (UTC hour bucket)
        hour = r.timestamp.hour
        hour_counter[hour] = hour_counter.get(hour, 0) + 1

    # top keywords derived from tags for MVP (could expand to NLP of command_text later)
    top_keywords = sorted(tag_counter.items(), key=lambda x: x[1], reverse=True)[:5]
    # Convert active hours into simple ranges (coarse heuristic)
    active_hours_sorted = sorted(hour_counter.items(), key=lambda x: x[1], reverse=True)[:3]
    # Format hours: e.g., 10 -> "10:00-11:00"
    active_hour_ranges = [f"{h:02d}:00-{(h+1)%24:02d}:00" for h, _ in active_hours_sorted]

    return {
        "total_commands": total,
        "top_keywords": [k for k, _ in top_keywords],
        "active_hours": active_hour_ranges,
    }

def analyze_preferences() -> Dict:
    """Heuristic preference analysis from commands.

    Signals considered:
    - preferred_language: inferred from tags and command_text heuristics
    - common_tasks: tags/keywords like test, refactor, optimize, deploy, debug
    - style: keywords like async, clean, OOP, functional, TDD
    - frameworks/tools (additional, non-breaking fields)
    """
    # Take a lightweight snapshot of just the fields we need while the session is open
    with database.session_scope() as db:
        rows = db.query(models.Command).all()
        snap = [
            {
                "command_text": (r.command_text or ""),
                "tags": (r.tags.split(",") if r.tags else []),
            }
            for r in rows
        ]

    # Counters
    tag_counts: Dict[str, int] = {}
    task_counts: Dict[str, int] = {}
    style_counts: Dict[str, int] = {}
    framework_counts: Dict[str, int] = {}
    tool_counts: Dict[str, int] = {}
    language_counts: Dict[str, int] = {}

    # Heuristic dictionaries
    lang_markers = {
        "python": ["python", ".py", "pip", "pytest", "uv ", "conda", "poetry", "ruff", "mypy"],
        "typescript": ["typescript", "ts ", ".ts", "tsc", "pnpm", "vite", "nextjs", "next.js"],
        "javascript": ["javascript", "js ", ".js", "npm", "yarn", "node"],
        "go": ["golang", " go ", ".go", "go build", "go test"],
        "java": [" java ", ".java", "maven", "mvn ", "gradle"],
        "rust": ["rust", ".rs", "cargo"],
        "bash": ["bash", "zsh", ".sh", "shell"],
    }
    task_markers = [
        "refactor", "test", "optimize", "document", "deploy", "debug",
        "fix", "lint", "typecheck", "benchmark", "profile", "migrate",
    ]
    style_markers = ["async", "clean", "performance", "oop", "functional", "tdd", "cli", "script"]
    framework_markers = [
        "fastapi", "flask", "django", "react", "nextjs", "vue", "svelte",
        "spring", "springboot", "express", "nestjs",
    ]
    tool_markers = [
        "docker", "kubernetes", "k8s", "git", "curl", "jq", "pytest", "pip", "conda", "poetry", "uv ",
        "alembic", "black", "ruff", "flake8", "mypy", "pre-commit", "eslint", "prettier", "jest", "vitest",
        "playwright", "cypress",
    ]

    def count_if_present(text: str, markers: List[str], counter: Dict[str, int], key_map: Dict[str, str] | None = None):
        for m in markers:
            if m.lower() in text:
                name = key_map.get(m, m) if key_map else m
                counter[name] = counter.get(name, 0) + 1

    # Aggregate
    for item in snap:
        tags = [t.lower() for t in item["tags"] if t]
        lower = item["command_text"].lower()

        # Tags as-is
        for t in tags:
            tag_counts[t] = tag_counts.get(t, 0) + 1

        # Language from tags
        for lang in lang_markers.keys():
            if lang in tags:
                language_counts[lang] = language_counts.get(lang, 0) + 1

        # Language heuristics from text
        for lang, markers in lang_markers.items():
            count_before = language_counts.get(lang, 0)
            count_if_present(lower, markers, language_counts)
            # reduce accidental double counting if both tag and marker matched strongly
            if language_counts.get(lang, 0) > count_before:
                pass

        # Tasks / style / frameworks / tools
        count_if_present(lower, task_markers, task_counts)
        count_if_present(lower, style_markers, style_counts)
        count_if_present(lower, framework_markers, framework_counts)
        count_if_present(lower, tool_markers, tool_counts)

    # Preferred language selection
    preferred_language = None
    preferred_language_confidence = None
    if language_counts:
        lang_sorted = sorted(language_counts.items(), key=lambda x: x[1], reverse=True)
        top_lang, top_count = lang_sorted[0]
        total = sum(language_counts.values())
        confidence = (top_count / total) if total else 1.0
        preferred_language = top_lang.capitalize() if top_lang == "python" else top_lang
        preferred_language_confidence = round(confidence, 3)

    # Top tasks and style summary
    common_tasks = [
        k.replace("document", "documentation")
        for k, _ in sorted(task_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    style_summary = ", ".join([k.upper() if k in ("oop", "tdd") else k for k, _ in sorted(style_counts.items(), key=lambda x: x[1], reverse=True)[:5]]) or None

    # Additional informative fields (non-breaking): frameworks and tools
    frameworks = [k for k, _ in sorted(framework_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
    tools = [k for k, _ in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:8]]

    return {
        "preferred_language": preferred_language,
        "preferred_language_confidence": preferred_language_confidence,
        "common_tasks": common_tasks,
        "style": style_summary,
        "frameworks": frameworks,
        "tools": tools,
        # Raw signals (optional for transparency; consumers may ignore)
        "signals": {
            "languages": language_counts,
            "tasks": task_counts,
            "styles": style_counts,
            "frameworks": framework_counts,
            "tools": tool_counts,
        },
    }


def analyze_preferences_contextual(context: str, limit: int = 50) -> Dict:
    """Derive task-focused preferences given a prompt/context string.

    Steps:
      1. Pull recent commands (up to limit) and reuse core signals logic.
      2. Score relevance: which stored signals overlap with context words.
      3. Return only the subset likely useful for this context (e.g. 'update docs' -> doc tools & style).

    This does not train a model; it is heuristic filtering layered on base signals.
    """
    base = analyze_preferences()
    lowered = context.lower()

    # Keyword groups for contextual mapping
    context_groups = {
        "documentation": ["doc", "docs", "documentation", "readme", "comment", "write", "update"],
        "testing": ["test", "pytest", "coverage", "unit", "integration"],
        "performance": ["perf", "optimize", "benchmark", "profile"],
        "deployment": ["deploy", "docker", "k8s", "kubernetes", "release"],
        "refactor": ["refactor", "clean", "restructure"],
        "debug": ["debug", "trace", "error", "fail"],
    }

    matched_groups = [g for g, kws in context_groups.items() if any(k in lowered for k in kws)]

    # Filter tasks/styles/tools/frameworks based on matched groups heuristics
    def filter_list(values: List[str], relevance_words: List[str]) -> List[str]:
        if not relevance_words:
            return []
        lv = lowered
        return [v for v in values if any(w in lv or w in v for w in relevance_words)]

    relevance_words = []
    for g in matched_groups:
        relevance_words.extend(context_groups[g])

    contextual = {
        "matched_groups": matched_groups,
        "preferred_language": base.get("preferred_language"),
        "style_subset": filter_list(base.get("style", "").split(", "), relevance_words),
        "tasks_subset": filter_list(base.get("common_tasks", []), relevance_words),
        "frameworks_subset": filter_list(base.get("frameworks", []), relevance_words),
        "tools_subset": filter_list(base.get("tools", []), relevance_words),
        "signals_overlap": {
            "tasks": {k: v for k, v in base.get("signals", {}).get("tasks", {}).items() if k in relevance_words},
            "styles": {k: v for k, v in base.get("signals", {}).get("styles", {}).items() if k in relevance_words},
            "tools": {k: v for k, v in base.get("signals", {}).get("tools", {}).items() if k in relevance_words},
        },
        "context": context,
    }

    # Fallback: if no groups matched, surface a minimal neutral preference set
    if not matched_groups:
        contextual["tasks_subset"] = base.get("common_tasks", [])[:3]
        contextual["style_subset"] = base.get("style", "").split(", ") if base.get("style") else []
        contextual["frameworks_subset"] = base.get("frameworks", [])[:3]
        contextual["tools_subset"] = base.get("tools", [])[:5]
        contextual["note"] = "No specific contextual group matched; returned neutral top signals." 

    return contextual

def get_recent_context(limit: int = 5):
    """Return the most recent user commands up to the given limit.

    Provides a simplified context of recent raw instructions (command_text)
    and associated tags. We serialize while the session is active.
    """
    with database.session_scope() as db:
        recents = (
            db.query(models.Command)
            .order_by(models.Command.timestamp.desc())
            .limit(limit)
            .all()
        )
        items = [
            {
                "command_text": r.command_text,
                "tags": r.tags.split(",") if r.tags else [],
                "timestamp": r.timestamp.isoformat() + "Z",
            }
            for r in recents
        ]
        return {
            "recent_commands": [i["command_text"] for i in items],
            "items": items,
        }
