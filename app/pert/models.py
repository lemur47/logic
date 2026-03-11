"""
PERT SQLAlchemy models.
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String

from ..database import Base


class PertScenario(Base):
    """A saved PERT estimation scenario."""

    __tablename__ = "pert_scenarios"

    id = Column(Integer, primary_key=True, index=True)

    # Metadata
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Tasks input & computed (stored as JSON)
    tasks = Column(JSON, nullable=False)

    # Project-level computed results
    total_expected = Column(Float, nullable=True)
    total_std_dev = Column(Float, nullable=True)
    total_variance = Column(Float, nullable=True)
    range_68 = Column(JSON, nullable=True)
    range_95 = Column(JSON, nullable=True)
    range_99 = Column(JSON, nullable=True)

    # Tags for organization
    tags = Column(JSON, default=list)

    def __repr__(self):
        return f"<PertScenario(id={self.id}, name='{self.name}')>"
