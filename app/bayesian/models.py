"""
Bayesian estimation calibration SQLAlchemy models.

Two tables: BayesianContext (the belief entity) and BayesianObservation
(append-only history of estimation vs actual pairs).
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..database import Base


class BayesianContext(Base):
    """An estimation context — a category of work with its own delay factor belief.

    Examples: "auth", "infra", "frontend". Each context has its own prior
    and observation history. The posterior is recomputed on read from
    the observation history, never stored.
    """

    __tablename__ = "bayesian_contexts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(1000), nullable=True)
    prior_mean = Column(Float, nullable=False, default=1.0)
    prior_variance = Column(Float, nullable=False, default=0.25)
    observation_noise = Column(Float, nullable=False, default=0.15)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    observations = relationship(
        "BayesianObservation",
        back_populates="context",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<BayesianContext(id={self.id}, name='{self.name}')>"


class BayesianObservation(Base):
    """A single (estimated, actual) duration pair — append-only."""

    __tablename__ = "bayesian_observations"

    id = Column(Integer, primary_key=True, index=True)
    context_id = Column(Integer, ForeignKey("bayesian_contexts.id"), nullable=False)
    estimated = Column(Float, nullable=False)
    actual = Column(Float, nullable=False)
    delay_factor = Column(Float, nullable=False)  # r = actual / estimated, computed server-side

    # Append-only: no updated_at
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    context = relationship("BayesianContext", back_populates="observations")

    def __repr__(self):
        return f"<BayesianObservation(id={self.id}, r={self.delay_factor:.3f})>"
