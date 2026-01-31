"""
TCO core calculation logic.
Pure functions - no dependencies on FastAPI or SQLAlchemy.
"""


def calculate_tco(
    initial_price: float,
    useful_life_years: int,
    residual_value: float = 0,
    annual_maintenance: float = 0,
    annual_operating_cost: float = 0,
    discount_rate: float = 0.03,
) -> dict:
    """
    Calculate comprehensive TCO with operational costs and time value of money.

    Returns:
        dict with total_cost, annual_cost, monthly_cost, cost_per_day, npv_tco, npv_annual
    """
    if useful_life_years <= 0:
        raise ValueError("useful_life_years must be positive")
    if initial_price < 0 or residual_value < 0:
        raise ValueError("Prices cannot be negative")
    if annual_maintenance < 0 or annual_operating_cost < 0:
        raise ValueError("Annual costs cannot be negative")

    # Simple TCO
    total_operational = (annual_maintenance + annual_operating_cost) * useful_life_years
    total_cost = initial_price + total_operational - residual_value
    annual_cost = total_cost / useful_life_years
    monthly_cost = annual_cost / 12

    # NPV-adjusted TCO
    npv_operational = sum(
        (annual_maintenance + annual_operating_cost) / ((1 + discount_rate) ** year)
        for year in range(1, useful_life_years + 1)
    )
    npv_residual = residual_value / ((1 + discount_rate) ** useful_life_years)
    npv_tco = initial_price + npv_operational - npv_residual
    npv_annual = npv_tco / useful_life_years

    return {
        "total_cost": round(total_cost, 2),
        "annual_cost": round(annual_cost, 2),
        "monthly_cost": round(monthly_cost, 2),
        "cost_per_day": round(annual_cost / 365, 2),
        "npv_tco": round(npv_tco, 2),
        "npv_annual": round(npv_annual, 2),
    }


def calculate_breakeven(option_a: dict, option_b: dict) -> float | None:
    """Calculate break-even point (years) between two options."""
    tco_a = calculate_tco(**option_a)
    tco_b = calculate_tco(**option_b)

    initial_diff = option_a.get("initial_price", 0) - option_b.get("initial_price", 0)
    annual_savings = tco_b["annual_cost"] - tco_a["annual_cost"]

    if annual_savings <= 0:
        return None

    return round(initial_diff / annual_savings, 2)


def compare_options(options: list[dict]) -> list[dict]:
    """Compare multiple TCO options, sorted by annual cost."""
    results = []

    for opt in options:
        opt_copy = opt.copy()
        name = opt_copy.pop("name")
        tco = calculate_tco(**opt_copy)

        results.append(
            {
                "name": name,
                "initial_price": opt_copy.get("initial_price", 0),
                "useful_life_years": opt_copy.get("useful_life_years", 0),
                **tco,
            }
        )

    results.sort(key=lambda x: x["annual_cost"])
    for i, r in enumerate(results):
        r["rank"] = i + 1

    return results
