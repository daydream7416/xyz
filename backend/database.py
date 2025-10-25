from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# DATABASE_URL = os.environ.get("DATABASE_URL")
# This is a placeholder, we will get the real URL from Railway later
DATABASE_URL = "postgresql://user:password@host:port/database"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()