"""Generate golden fixtures pinning simulation output across the pipeline refactor.

Run BEFORE refactoring to capture the baseline, then re-run the test suite after
to prove nothing moved:

    uv run python tests/montecarlo/generate_pipeline_fixtures.py

The fixtures exist so the "identical seeds produce identical outputs" guarantee
outlives the refactor that motivated it — a scratch capture would prove it once
and leave no regression net behind.

DELIBERATELY EXCLUDES degenerate (O==M==P) schedules. The plain path mishandles
those today, inventing a +/-0.5 histogram spread for zero-variance data, and the
refactor FIXES that by extending the drift path's guard to both paths. Freezing
the current degenerate output would pin the bug in place. Degenerate behaviour is
asserted directly in test_pipeline_parity.py instead.
"""

import hashlib
import json
from pathlib import Path

import numpy as np

from app.montecarlo.core import (
    DriftConfig,
    DriftTask,
    Posterior,
    RiskClass,
    Task,
    simulate_schedule,
    simulate_with_drift,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "pipeline-golden.json"
N_SIMS = 2000
SEED = 42


def _digest(durations: np.ndarray) -> str:
    """Stable hash of the duration samples, rounded to absorb float noise."""
    return hashlib.sha256(np.round(durations, 6).tobytes()).hexdigest()[:32]


def _capture(result) -> dict:
    return {
        "n_simulations": result.n_simulations,
        "percentiles": result.percentiles,
        "histogram": result.histogram,
        "critical_path_frequency": result.critical_path_frequency,
        "durations_digest": _digest(result.durations),
        "mean": round(float(np.mean(result.durations)), 6),
        "std_dev": round(float(np.std(result.durations)), 6),
    }


def _plain_independent():
    return [
        Task("A", 2.0, 5.0, 10.0),
        Task("B", 3.0, 6.0, 12.0),
        Task("C", 1.0, 2.0, 8.0),
    ]


def _plain_dependent():
    return [
        Task("Design", 2.0, 5.0, 10.0),
        Task("Build", 4.0, 8.0, 16.0, depends_on=("Design",)),
        Task("Docs", 1.0, 3.0, 6.0, depends_on=("Design",)),
        Task("Ship", 1.0, 2.0, 4.0, depends_on=("Build", "Docs")),
    ]


def _drift_config():
    return DriftConfig(
        risk_classes=(
            RiskClass(name="auth", posterior=Posterior(mu=1.4, sigma=0.2)),
            RiskClass(name="ui", posterior=Posterior(mu=1.0, sigma=0.1)),
        ),
        seed=SEED,
    )


def _drift_independent():
    return [
        DriftTask("A", 2.0, 5.0, 10.0, risk_class="auth"),
        DriftTask("B", 3.0, 6.0, 12.0, risk_class="ui"),
        DriftTask("C", 1.0, 2.0, 8.0),  # unclassified -> blends across classes
    ]


def _drift_dependent():
    return [
        DriftTask("Design", 2.0, 5.0, 10.0, risk_class="ui"),
        DriftTask("Build", 4.0, 8.0, 16.0, risk_class="auth", depends_on=("Design",)),
        DriftTask("Ship", 1.0, 2.0, 4.0, depends_on=("Build",)),
    ]


def build() -> dict:
    return {
        "_meta": {
            "n_simulations": N_SIMS,
            "seed": SEED,
            "note": "Golden values captured pre-refactor. Any diff is a regression "
            "unless deliberately re-generated with a recorded reason.",
        },
        "plain_independent": _capture(
            simulate_schedule(_plain_independent(), n_simulations=N_SIMS, seed=SEED)
        ),
        "plain_dependent": _capture(
            simulate_schedule(_plain_dependent(), n_simulations=N_SIMS, seed=SEED)
        ),
        "drift_independent": _capture(
            simulate_with_drift(_drift_independent(), _drift_config(), n_simulations=N_SIMS)
        ),
        "drift_dependent": _capture(
            simulate_with_drift(_drift_dependent(), _drift_config(), n_simulations=N_SIMS)
        ),
    }


if __name__ == "__main__":
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(build(), indent=2, sort_keys=True) + "\n")
    print(f"wrote {FIXTURE_PATH}")
