from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from contextlib import contextmanager

# SQLite database stored in /app/data/memory.db (mapped to host)
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/memory.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
# Important: prevent attribute expiration on commit so ORM instances remain usable
# after the session is closed (we serialize them outside the session context).
# Without this, accessing attributes may trigger a refresh on a closed session,
# causing "Instance is not bound to a Session" errors.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)
Base = declarative_base()

def init_db():
    """Initialize database tables."""
    import models  # local module
    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations.

    Ensures commit on success and rollback on exception, and always closes
    the session. Usage:

        with session_scope() as db:
            db.add(obj)
    """
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
