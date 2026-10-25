"""
backend/main.py - Main Application Entry Point for SIH26261 (Person 4).
Initializes FastAPI, mounts CORS middleware, registers API routes,
and serves the static reviewer dashboard frontend.
"""

import os
import sys
from pathlib import Path

# Ensure repo root and dataset root are on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = REPO_ROOT / "dataset"
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"

for p in [str(REPO_ROOT), str(DATASET_PATH)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router as api_v1_router


def create_application() -> FastAPI:
    """Factory creating and configuring the primary FastAPI application instance."""
    app = FastAPI(
        title="AICTE Application Verification System",
        description=(
            "AI-Powered Application Validation, Document Authentication, and "
            "Regulatory Compliance Verification (SIH26261)."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS Configuration
    origins_env = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
    )
    origins = [o.strip() for o in origins_env.split(",") if o.strip()]
    if "*" not in origins:
        origins.append("*")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Primary API v1 Router
    app.include_router(api_v1_router, prefix="/api/v1", tags=["Verification Pipeline"])

    # Root Health Check
    @app.get("/health", tags=["System"])
    def root_health():
        return {"status": "healthy", "service": "AICTE Application Verification System", "version": "1.0.0"}

    # Serve compiled frontend from frontend/dist if present
    if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
    else:
        # Fallback friendly landing page directing users to API docs or dev server
        @app.get("/", response_class=HTMLResponse, tags=["System"])
        def root_landing():
            return """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>AICTE Application Verification System - API Online</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 40px; text-align: center; }
                    .card { max-width: 600px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 32px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); border: 1px solid #334155; }
                    h1 { color: #38bdf8; margin-top: 0; }
                    .btn { display: inline-block; background: #0284c7; color: white; padding: 10px 24px; border-radius: 8px; text-decoration: none; font-weight: bold; margin: 10px; }
                    .badge { display: inline-block; background: #10b981; color: #064e3b; padding: 4px 12px; border-radius: 999px; font-weight: bold; font-size: 14px; margin-bottom: 20px; }
                </style>
            </head>
            <body>
                <div class="card">
                    <span class="badge">API v1 ONLINE</span>
                    <h1>AICTE Document Verification System</h1>
                    <p>Regulatory Compliance, Document Authentication, and Anomaly Detection Gateway</p>
                    <p style="color: #94a3b8;">The backend orchestration pipeline is ready. Interactive API documentation is available below:</p>
                    <div>
                        <a href="/docs" class="btn">Swagger OpenAPI Docs</a>
                        <a href="/api/v1/health" class="btn" style="background: #334155;">Health Check JSON</a>
                    </div>
                </div>
            </body>
            </html>
            """

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("APP_PORT", "8000"))
    host = os.getenv("APP_HOST", "0.0.0.0")
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
