"""
Logic API - Main Application

A modular API for finance, productivity, privacy and more.
Each feature (tco, npv, irr, etc.) is a self-contained module.

Run with: uv run uvicorn app.main:app --reload
"""

# For CORS
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import feature routers
from .bayesian.router import router as bayesian_router
from .database import Base, engine
from .evm.router import router as evm_router
from .montecarlo.router import router as montecarlo_router
from .pert.router import router as pert_router
from .tco.router import router as tco_router


@asynccontextmanager
async def lifespan(app: FastAPI):
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
- **PERT** - Reality-adjusted project estimation
- **EVM** - Earned Value Management performance tracking
- **Bayesian** - Estimation calibration via Bayesian updating
- **Monte Carlo** - Schedule simulation with probability distributions
        """,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # allow_origins=["*"],
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:4321").split(","),
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
        "features": ["tco", "pert", "evm", "bayesian", "montecarlo"],
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
app.include_router(pert_router, prefix="/pert", tags=["PERT"])
app.include_router(evm_router, prefix="/evm", tags=["EVM"])
app.include_router(bayesian_router, prefix="/bayesian", tags=["Bayesian"])
app.include_router(montecarlo_router, prefix="/montecarlo", tags=["Monte Carlo"])
