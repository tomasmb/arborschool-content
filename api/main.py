"""FastAPI application entry point.

Run with:
    uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import get_settings
from api.routers import course_sync, overview, pipelines, questions, subjects, sync, tests

settings = get_settings()

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Admin dashboard API for managing the PAES M1 content pipeline.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Configure CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(overview.router, prefix="/api", tags=["Overview"])
app.include_router(subjects.router, prefix="/api/subjects", tags=["Subjects"])
app.include_router(questions.router, prefix="/api/subjects", tags=["Questions"])
app.include_router(course_sync.router, prefix="/api/subjects", tags=["Course Sync"])
app.include_router(pipelines.router, prefix="/api/pipelines", tags=["Pipelines"])
app.include_router(sync.router, prefix="/api/sync", tags=["Sync"])
app.include_router(tests.router, prefix="/api/subjects", tags=["Tests"])


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": settings.api_version}
