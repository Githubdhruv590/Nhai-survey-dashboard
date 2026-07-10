from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config.config import settings

# If no DATABASE_URL is set, raise an error or use a local dev default
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in environment or .env file.")

# Handle PostgreSQL vs SQLite specific connection args
connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args, pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
