# app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database path (Render uses a persistent disk)
DB_PATH = '/opt/render/project/src/data/receipts.db'

# Ensure the directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# SQLAlchemy setup
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    # Dependency for FastAPI endpoints
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
