"""
Database configuration and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import os


def _build_engine_kwargs(database_url: str) -> dict:
    """Build SQLAlchemy engine kwargs based on the database backend."""
    kwargs = {"pool_pre_ping": True}

    if database_url.startswith("sqlite"):
        # Ensure the directory for the SQLite database exists so the engine can
        # create the file when first accessed. SQLite doesn't understand pool
        # options such as ``pool_size``/``max_overflow`` so we avoid passing
        # them entirely and instead rely on the lightweight default pooling.
        db_path = database_url.split("///", 1)[-1]
        directory = os.path.dirname(db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs.update({
            "pool_size": 10,
            "max_overflow": 20,
        })

    return kwargs

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    **_build_engine_kwargs(settings.DATABASE_URL)
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
