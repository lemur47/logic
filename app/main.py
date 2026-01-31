"""
Logic API - Main Application

A modular API for finance, productivity, privacy and more.
Each feature (tco, npv, irr, etc.) is a self-contained module.

Run with: uv run uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base

# Import feature routers
from .tco.router import router as tco_router


@asynccontextmanager
async def lifespan(app: FASTAPI):
    """Create database tables on startup."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Logic API",
    description="""
A modular API for finance, productivity, privacy and more.

Small tools for real problems, direct contribution to the world.

## Features

- **TCO** - Total Cost of Ownership calculator
- *More coming soon...*
        """,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Health Endpoints
# =============================================================================


@app.get("/", tags=["Health"])
async def root():
    """API info and available features."""
    return {
        "name": "Logic API",
        "version": "0.1.0",
        "features": ["tco"],
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    """Health check."""
    return {"status": "ok"}


# =============================================================================
# Mount Feature Routers
# =============================================================================

app.include_router(tco_router, prefix="/tco", tags=["TCO"])
