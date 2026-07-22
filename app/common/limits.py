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

# Maximum length of any single free-text identifier: task and work-package names,
# tag names, risk-class names, dependency references. 255 matches the cap already
# applied to the name fields these must line up with — a dependency reference
# longer than a task name could never match one anyway.
#
# Note these schemas are imported directly by the shipped pmorun-mcp server, so
# a cap here is a product-facing input constraint, not just an API one. 255 sits
# far above any real PMO identifier while still bounding per-item memory.
MAX_NAME_LENGTH = 255

# Maximum length of a `search` query parameter. Search strings reach a SQL LIKE
# via the crud layer; an unbounded one is wasted scan work per request.
MAX_SEARCH_LENGTH = 255
