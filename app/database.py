import os
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

db_url = settings.DATABASE_URL

# Fix postgres:// dialect for SQLAlchemy 2.0 (e.g. Supabase, Neon, Render)
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# On Vercel Serverless environment, root filesystem is read-only (except /tmp)
if os.getenv("VERCEL") and db_url.startswith("sqlite"):
    tmp_db_path = "/tmp/office_management.db"
    orig_db_path = db_url.replace("sqlite:///", "")
    if not os.path.exists(tmp_db_path) and os.path.exists(orig_db_path):
        try:
            shutil.copy2(orig_db_path, tmp_db_path)
        except Exception as e:
            print(f"[Vercel DB Setup] Warning copying SQLite db to /tmp: {e}")
    db_url = f"sqlite:///{tmp_db_path}"

connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
