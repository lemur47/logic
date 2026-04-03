"""
Monte Carlo schedule simulation SQLAlchemy models.

Single table: MonteCarloScenario stores task inputs and cached simulation
results as JSON. Results are recomputed when task data changes.
"""

from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String

from ..database import Base


class MonteCarloScenario(Base):
    """A saved Monte Carlo simulation scenario with cached results.

    Tasks and simulation outputs are stored as JSON. The simulation is
    re-run whenever calculation-affecting fields change (tasks,
    num_simulations, seed).
    """

    __tablename__ = "montecarlo_scenarios"

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

    # Input parameters
    tasks = Column(JSON, nullable=False)  # list of task dicts
    num_simulations = Column(Integer, nullable=False, default=10_000)
    seed = Column(Integer, nullable=True)

    # Cached simulation results
    percentiles = Column(JSON, nullable=True)  # {"P50": ..., "P75": ..., ...}
    histogram = Column(JSON, nullable=True)  # {"bin_edges": [...], "counts": [...]}
    critical_path_frequency = Column(JSON, nullable=True)  # {"task_name": freq, ...}
    mean_duration = Column(Float, nullable=True)
    std_dev_duration = Column(Float, nullable=True)
    min_duration = Column(Float, nullable=True)
    max_duration = Column(Float, nullable=True)

    def __repr__(self):
        return f"<MonteCarloScenario(id={self.id}, name='{self.name}')>"
