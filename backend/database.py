from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Local test uses SQLite, production uses Railway PostgreSQL
def get_database_url():
    if os.environ.get("USE_SQLITE", "").lower() in {"1", "true", "yes", "on"}:
        return "sqlite:///./test.db"
    # Use Railway DATABASE_URL when set
    if os.environ.get("DATABASE_URL"):
        return os.environ.get("DATABASE_URL")
    # Default to SQLite for local testing
    else:
        return "sqlite:///./test.db"

DATABASE_URL = get_database_url()

# SQLite connection arguments
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
