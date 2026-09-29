import sqlite3
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routers import (
    auth, employees, departments, attendance, leaves, 
    projects, tasks, meetings, audit_logs, ai, permissions,
    qa, finance, it_support, inventory, documents, sales,
    offices, ranks, designations, payroll, health
)

# Create database tables if they do not exist
Base.metadata.create_all(bind=engine)

# --- SQLite column migration (handles existing DBs missing new columns) ---
def _run_sqlite_migrations():
    """Adds columns that SQLAlchemy create_all cannot add to existing tables."""
    db_url = str(engine.url)
    if not db_url.startswith("sqlite"):
        return  # Only needed for SQLite

    db_path = db_url.replace("sqlite:///", "")
    if not os.path.exists(db_path):
        return

    migrations = [
        ("employees", "office_id", "INTEGER REFERENCES offices(id)"),
        ("employees", "rank_id",   "INTEGER REFERENCES ranks(id)"),
        ("employees", "designation_id", "INTEGER REFERENCES designations(id)"),
        ("employees", "phone", "VARCHAR(50)"),
        ("employees", "personal_email", "VARCHAR(150)"),
        ("employees", "address_info", "JSON"),
        ("employees", "family_info", "JSON"),
        ("employees", "bio", "TEXT"),
    ]

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        for table, column, definition in migrations:
            cur.execute(f"PRAGMA table_info({table})")
            existing = [r[1] for r in cur.fetchall()]
            if column not in existing:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Migration] Warning: {e}")

_run_sqlite_migrations()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs"
)

# Enable CORS for Angular frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(employees.router, prefix=settings.API_V1_STR)
app.include_router(departments.router, prefix=settings.API_V1_STR)
app.include_router(attendance.router, prefix=settings.API_V1_STR)
app.include_router(leaves.router, prefix=settings.API_V1_STR)
app.include_router(projects.router, prefix=settings.API_V1_STR)
app.include_router(tasks.router, prefix=settings.API_V1_STR)
app.include_router(meetings.router, prefix=settings.API_V1_STR)
app.include_router(audit_logs.router, prefix=settings.API_V1_STR)
app.include_router(ai.router, prefix=settings.API_V1_STR)

# New 12-Panel Enterprise Routers
app.include_router(permissions.router, prefix=settings.API_V1_STR)
app.include_router(qa.router, prefix=settings.API_V1_STR)
app.include_router(finance.router, prefix=settings.API_V1_STR)
app.include_router(it_support.router, prefix=settings.API_V1_STR)
app.include_router(inventory.router, prefix=settings.API_V1_STR)
app.include_router(documents.router, prefix=settings.API_V1_STR)
app.include_router(sales.router, prefix=settings.API_V1_STR)
app.include_router(offices.router, prefix=settings.API_V1_STR)
app.include_router(ranks.router, prefix=settings.API_V1_STR)
app.include_router(designations.router, prefix=settings.API_V1_STR)
app.include_router(payroll.router, prefix=settings.API_V1_STR)
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(health.router)

@app.get("/")
def root():
    return {
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "health": f"{settings.API_V1_STR}/health",
        "docs": f"{settings.API_V1_STR}/docs"
    }
