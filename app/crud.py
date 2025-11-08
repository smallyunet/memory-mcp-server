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

    - preferred_language: inferred from tags (python, js, go, java, rust etc.)
    - common_tasks: tags like test, refactor, optimize
    - style: look for substrings in command_text (async, clean, OOP, functional)
    """
    with database.session_scope() as db:
        rows = db.query(models.Command).all()
        snap = list(rows)  # snapshot before session closes

    # Language inference
    lang_tags_priority = ["python", "typescript", "javascript", "go", "java", "rust"]
    tag_counts: Dict[str, int] = {}
    common_task_markers = ["refactor", "test", "optimize", "document", "deploy"]
    task_counts: Dict[str, int] = {}
    style_markers = ["async", "clean", "performance", "OOP", "functional"]
    style_hits: List[str] = []

    for r in snap:
        tags = r.tags.split(",") if r.tags else []
        for t in tags:
            if not t:
                continue
            tag_counts[t] = tag_counts.get(t, 0) + 1
        lower = r.command_text.lower() if r.command_text else ""
        for marker in common_task_markers:
            if marker in lower:
                task_counts[marker] = task_counts.get(marker, 0) + 1
        for style in style_markers:
            if style.lower() in lower:
                style_hits.append(style)

    preferred_language = None
    for lang in lang_tags_priority:
        if lang in tag_counts:
            preferred_language = lang.capitalize() if lang == "python" else lang
            break

    common_tasks = [k.replace("document", "documentation") for k, _ in sorted(task_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
    style_summary = ", ".join(sorted(set(style_hits))) if style_hits else None

    return {
        "preferred_language": preferred_language,
        "common_tasks": common_tasks,
        "style": style_summary,
    }

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
