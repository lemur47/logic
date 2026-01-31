"""
TCO SQLAlchemy models.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, JSON

from ..database import Base


class Scenario(Base):
    """A saved TCO calculation scenario."""

    __tablename__ = "tco_scenarios"

    id = Column(Integer, primary_key=True, index=True)

    # Metadata
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Input parameters
    initial_price = Column(Float, nullable=False)
    useful_life_years = Column(Integer, nullable=False)
    residual_value = Column(Float, default=0)
    annual_maintenance = Column(Float, default=0)
    annual_operating_cost = Column(Float, default=0)
    discount_rate = Column(Float, default=0.03)

    # Computed results
    total_cost = Column(Float, nullable=True)
    annual_cost = Column(Float, nullable=True)
    monthly_cost = Column(Float, nullable=True)
    cost_per_day = Column(Float, nullable=True)
    npv_tco = Column(Float, nullable=True)
    npv_annual = Column(Float, nullable=True)

    # Tags for organization
    tags = Column(JSON, default=list)

    def __repr__(self):
        return f"<TCOScenario(id={self.id}, name='{self.name}')>"
