"""Shared input-size ceilings — defence against unbounded-allocation DoS.

These are safety limits, not domain constraints: real PMO inputs sit far below
them. They exist so that a single (unauthenticated) request cannot force the
server to allocate unbounded memory or CPU.
"""

# Maximum number of items accepted in any request-body list (tasks, observations,
# work packages, comparison options, risk classes). A network or comparison set
# larger than this is already pathological; the cap bounds per-request memory.
#
# The Monte Carlo product ceiling (n_tasks × num_simulations) is a core-allocation
# concern and lives beside the arrays it guards: app.montecarlo.core.MAX_SIMULATION_CELLS.
MAX_LIST_ITEMS = 1000
