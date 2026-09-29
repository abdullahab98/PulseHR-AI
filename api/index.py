import sys
import os
import traceback
from pathlib import Path

# Add project root to sys.path so 'app' can be imported anywhere on Vercel
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from app.main import app
    handler = app
except Exception as e:
    tb = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI(title="Error Handler")

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
    def catch_all(full_path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "FastAPI Startup Failed",
                "detail": str(e),
                "traceback": tb.splitlines()
            }
        )
    handler = app
