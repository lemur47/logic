"""EVM (Earned Value Management) performance tracking module."""

from .core import create_baseline, evaluate_progress, evm_metrics, health_signal
from .router import router

__all__ = ["router", "evm_metrics", "health_signal", "create_baseline", "evaluate_progress"]
