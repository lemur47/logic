"""TCO (Total Cost of Ownership) calculator module."""

from .core import calculate_breakeven, calculate_tco, compare_options
from .router import router

__all__ = ["router", "calculate_tco", "compare_options", "calculate_breakeven"]
