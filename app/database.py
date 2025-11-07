from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite database stored in /app/data/memory.db (mapped to host)
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/memory.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def init_db():
    """Initialize database tables."""
    import models  # local module
    Base.metadata.create_all(bind=engine)
