import models, database
from sqlalchemy.orm import Session
import json

def create_record(user_id: str, data: dict):
    """Insert a new record into the database."""
    db: Session = database.SessionLocal()
    record = models.Record(
        user_id=user_id,
        category=data.get("category", "general"),
        summary=data.get("summary"),
        detail=json.dumps(data),
        tags=",".join(data.get("tags", []))
    )
    db.add(record)
    db.commit()
    db.close()

def search_records(user_id: str, query: str):
    """Return records that match the query across summary, tags, or category.

    Note: This broadens matching beyond summary to improve recall for
    technical preferences/decisions that are often captured via tags
    (e.g., "docker", "postgres") or category (e.g., "technical decision").
    """
    from sqlalchemy import or_

    db: Session = database.SessionLocal()
    q = f"%{query}%"
    results = (
        db.query(models.Record)
        .filter(models.Record.user_id == user_id)
        .filter(
            or_(
                models.Record.summary.ilike(q),
                models.Record.tags.ilike(q),
                models.Record.category.ilike(q),
            )
        )
        .order_by(models.Record.timestamp.desc())
        .limit(10)
        .all()
    )
    db.close()
    return [
        {
            "summary": r.summary,
            "category": r.category,
            "tags": r.tags,
            "timestamp": r.timestamp.isoformat(),
        }
        for r in results
    ]

def get_recent_context(user_id: str, limit: int = 5):
    """Return the most recent user records up to the given limit.

    Returns both a list of summaries and an 'items' array with richer metadata
    to support clients that need categories/tags without additional queries.
    """
    db: Session = database.SessionLocal()
    recents = (
        db.query(models.Record)
        .filter(models.Record.user_id == user_id)
        .order_by(models.Record.timestamp.desc())
        .limit(limit)
        .all()
    )
    db.close()
    return {
        "recent_summaries": [r.summary for r in recents],
        "items": [
            {
                "summary": r.summary,
                "category": r.category,
                "tags": r.tags,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in recents
        ],
    }
