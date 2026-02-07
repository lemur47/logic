"""Root test fixtures: in-memory database, async client."""

import sys
from pathlib import Path

# Ensure app/ is on sys.path before any app imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import pytest
from database import Base, get_db
from httpx import ASGITransport, AsyncClient
from main import app
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

# In-memory SQLite with StaticPool so every connection shares the same database
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
async def client():
    """Async HTTP client wired to the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
