"""
EVM SQLAlchemy models.

Three tables with relationships — first module in this repo with ForeignKey.
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from ..database import Base


class EvmBaseline(Base):
    """An approved project baseline — the reference for all EVM calculations."""

    __tablename__ = "evm_baselines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(String(1000), nullable=True)
    bac = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    work_packages = relationship(
        "EvmWorkPackage",
        back_populates="baseline",
        cascade="all, delete-orphan",
    )
    snapshots = relationship(
        "EvmSnapshot",
        back_populates="baseline",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<EvmBaseline(id={self.id}, name='{self.name}')>"


class EvmWorkPackage(Base):
    """A work package belonging to a baseline."""

    __tablename__ = "evm_baseline_work_packages"

    id = Column(Integer, primary_key=True, index=True)
    baseline_id = Column(Integer, ForeignKey("evm_baselines.id"), nullable=False)
    name = Column(String(255), nullable=False)
    planned_value = Column(Float, nullable=False)
    weight = Column(Float, nullable=False)

    baseline = relationship("EvmBaseline", back_populates="work_packages")

    def __repr__(self):
        return f"<EvmWorkPackage(id={self.id}, name='{self.name}')>"


class EvmSnapshot(Base):
    """An evaluation snapshot — append-only history of EVM measurements."""

    __tablename__ = "evm_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    baseline_id = Column(Integer, ForeignKey("evm_baselines.id"), nullable=False)

    # Inputs
    percent_planned = Column(Float, nullable=False)
    actual_cost = Column(Float, nullable=False)

    # Computed (from evm_metrics)
    pv = Column(Float, nullable=False)
    ev = Column(Float, nullable=False)
    sv = Column(Float, nullable=False)
    spi = Column(Float, nullable=False)
    cv = Column(Float, nullable=False)
    cpi = Column(Float, nullable=False)
    eac = Column(Float, nullable=False)
    etc = Column(Float, nullable=False)
    vac = Column(Float, nullable=False)
    tcpi = Column(Float, nullable=False)
    percent_complete = Column(Float, nullable=False)
    percent_spent = Column(Float, nullable=False)

    # Health
    health_status = Column(String(20), nullable=False)
    health_summary = Column(String(500), nullable=False)

    # Append-only: no updated_at
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    baseline = relationship("EvmBaseline", back_populates="snapshots")

    def __repr__(self):
        return f"<EvmSnapshot(id={self.id}, baseline_id={self.baseline_id})>"
