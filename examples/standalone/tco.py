"""
TCO Calculator - Standalone Version

A simple, dependency-light tool for Total Cost of Ownership calculations.
Perfect for scripts, notebooks, and custom integrations.

Author: lemur47
License: MIT
Version: 1.0.0

Dependencies: pandas (optional for compare_tco), matplotlib (optional for visualize_tco_comparison)
"""


def calculate_tco(
    initial_price,
    useful_life_years,
    residual_value=0,
    annual_maintenance=0,
    annual_operating_cost=0,
    discount_rate=0.03,
):
    """
    Calculate comprehensive TCO with operational costs and time value of money.

    Args:
        initial_price (float): Initial purchase price
        useful_life_years (int): Expected lifespan in years
        residual_value (float): Salvage value at end of life (default: 0)
        annual_maintenance (float): Annual maintenance/repair costs (default: 0)
        annual_operating_cost (float): Annual operational expenses (default: 0)
        discount_rate (float): Discount rate for NPV calculation (default: 0.03)

    Returns:
        dict: TCO metrics including:
            - total_cost: Total lifetime cost (undiscounted)
            - annual_cost: Average annual cost
            - monthly_cost: Average monthly cost
            - cost_per_day: Average daily cost
            - npv_tco: Net Present Value adjusted TCO
            - npv_annual: NPV-adjusted annual cost

    Example:
        >>> result = calculate_tco(
        ...     initial_price=450000,
        ...     useful_life_years=12,
        ...     residual_value=90000,
        ...     annual_maintenance=5000
        ... )
        >>> print(f"Monthly cost: ¥{result['monthly_cost']:,.0f}")
        Monthly cost: ¥2,917

    Raises:
        ValueError: If useful_life_years <= 0 or if prices are negative
    """
    # Input validation
    if useful_life_years <= 0:
        raise ValueError("useful_life_years must be positive")
    if initial_price < 0 or residual_value < 0:
        raise ValueError("Prices cannot be negative")
    if annual_maintenance < 0 or annual_operating_cost < 0:
        raise ValueError("Annual costs cannot be negative")

    # Simple TCO (no discounting)
    total_operational = (annual_maintenance + annual_operating_cost) * useful_life_years
    total_cost = initial_price + total_operational - residual_value
    annual_cost = total_cost / useful_life_years
    monthly_cost = annual_cost / 12

    # NPV-adjusted TCO (accounting for time value of money)
    npv_operational = sum(
        [
            (annual_maintenance + annual_operating_cost) / ((1 + discount_rate) ** year)
            for year in range(1, useful_life_years + 1)
        ]
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


def compare_tco(options):
    """
    Compare multiple TCO options and rank by cost efficiency.

    Args:
        options (list): List of dicts, each containing:
            - name (str): Option identifier
            - All parameters required by calculate_tco()

    Returns:
        pandas.DataFrame: Comparison results sorted by annual_cost

    Example:
        >>> options = [
        ...     {
        ...         'name': 'Premium Chair',
        ...         'initial_price': 450000,
        ...         'useful_life_years': 12,
        ...         'residual_value': 90000
        ...     },
        ...     {
        ...         'name': 'Budget Chair',
        ...         'initial_price': 50000,
        ...         'useful_life_years': 3
        ...     }
        ... ]
        >>> comparison = compare_tco(options)
        >>> print(comparison[['option', 'monthly_cost', 'annual_cost']])

    Raises:
        ImportError: If pandas is not installed
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(
            "pandas is required for compare_tco(). Install with: pip install pandas"
        )

    if not options:
        raise ValueError("options list cannot be empty")

    results = []
    for opt in options:
        # Create a copy to avoid modifying original
        opt_copy = opt.copy()
        name = opt_copy.pop("name")

        try:
            tco = calculate_tco(**opt_copy)
            tco["option"] = name
            tco["initial_investment"] = opt_copy.get("initial_price", 0)
            tco["useful_life_years"] = opt_copy.get("useful_life_years", 0)

            # Calculate cost recovery indicator (payback-like metric)
            if tco["annual_cost"] > 0:
                tco["cost_recovery_years"] = round(
                    opt_copy.get("initial_price", 0) / tco["annual_cost"], 2
                )
            else:
                tco["cost_recovery_years"] = 0

            results.append(tco)
        except Exception as e:
            print(f"Warning: Skipping option '{name}' due to error: {e}")
            continue

    if not results:
        raise ValueError("No valid options to compare")

    df = pd.DataFrame(results)

    # Reorder columns for better readability
    column_order = [
        "option",
        "initial_investment",
        "useful_life_years",
        "monthly_cost",
        "annual_cost",
        "cost_per_day",
        "total_cost",
        "npv_tco",
        "npv_annual",
        "cost_recovery_years",
    ]
    df = df[[col for col in column_order if col in df.columns]]

    return df.sort_values("annual_cost").reset_index(drop=True)


def visualize_tco_comparison(options, save_path=None):
    """
    Create visual comparison of TCO options.

    Args:
        options (list): List of option dicts (same format as compare_tco)
        save_path (str, optional): Path to save figure. If None, displays instead.

    Returns:
        matplotlib.figure.Figure: The created figure

    Example:
        >>> options = [...]  # Same as compare_tco
        >>> fig = visualize_tco_comparison(options)
        >>> # Or save to file:
        >>> fig = visualize_tco_comparison(options, save_path='tco_comparison.png')

    Raises:
        ImportError: If matplotlib is not installed
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError(
            "matplotlib is required for visualize_tco_comparison(). "
            "Install with: pip install matplotlib"
        )

    comparison = compare_tco(options)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Monthly cost comparison
    ax1.barh(comparison["option"], comparison["monthly_cost"], color="steelblue")
    ax1.set_xlabel("Monthly Cost (¥)", fontsize=10)
    ax1.set_title("Monthly TCO Comparison", fontsize=12, fontweight="bold")
    ax1.grid(axis="x", alpha=0.3)

    # Total cost breakdown
    ax2.barh(comparison["option"], comparison["total_cost"], color="coral")
    ax2.set_xlabel("Total Cost (¥)", fontsize=10)
    ax2.set_title("Total TCO over Lifetime", fontsize=12, fontweight="bold")
    ax2.grid(axis="x", alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Figure saved to: {save_path}")
    else:
        plt.show()

    return fig


def calculate_breakeven_point(option_a, option_b):
    """
    Calculate the break-even point (in years) between two TCO options.

    Useful for determining when a higher initial investment pays off
    through lower operational costs.

    Args:
        option_a (dict): First option parameters (without 'name' key)
        option_b (dict): Second option parameters (without 'name' key)

    Returns:
        float or None: Years until break-even, or None if no break-even exists

    Example:
        >>> premium = {
        ...     'initial_price': 450000,
        ...     'useful_life_years': 12,
        ...     'annual_maintenance': 5000
        ... }
        >>> budget = {
        ...     'initial_price': 50000,
        ...     'useful_life_years': 3,
        ...     'annual_maintenance': 15000
        ... }
        >>> years = calculate_breakeven_point(premium, budget)
        >>> if years:
        ...     print(f"Premium option breaks even after {years} years")
    """
    tco_a = calculate_tco(**option_a)
    tco_b = calculate_tco(**option_b)

    initial_diff = option_a.get("initial_price", 0) - option_b.get("initial_price", 0)
    annual_savings = tco_b["annual_cost"] - tco_a["annual_cost"]

    if annual_savings <= 0:
        return None  # No break-even (option A is always more expensive)

    breakeven_years = initial_diff / annual_savings
    return round(breakeven_years, 2)


# ============================================================================
# Example Usage & Tests
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("TCO Calculator - Standalone Version")
    print("=" * 70)

    # Example 1: Single TCO Calculation
    print("\n[Example 1] Herman Miller Chair - Premium Investment")
    print("-" * 70)

    hm_result = calculate_tco(
        initial_price=450000,
        useful_life_years=12,
        residual_value=90000,
        annual_maintenance=5000,
    )

    print(f"Initial Price:    ¥{450000:,}")
    print(f"Useful Life:      12 years")
    print(f"Residual Value:   ¥{90000:,}")
    print(f"\nResults:")
    print(f"  Monthly Cost:   ¥{hm_result['monthly_cost']:,.2f}")
    print(f"  Annual Cost:    ¥{hm_result['annual_cost']:,.2f}")
    print(f"  Daily Cost:     ¥{hm_result['cost_per_day']:,.2f}")
    print(f"  Total TCO:      ¥{hm_result['total_cost']:,.2f}")
    print(f"  NPV-Adjusted:   ¥{hm_result['npv_tco']:,.2f}")

    # Example 2: Comparison Analysis
    print("\n\n[Example 2] Multi-Option Comparison")
    print("-" * 70)

    options = [
        {
            "name": "Premium Chair (Herman Miller)",
            "initial_price": 450000,
            "useful_life_years": 12,
            "residual_value": 90000,
            "annual_maintenance": 5000,
        },
        {
            "name": "Mid-Range Chair",
            "initial_price": 150000,
            "useful_life_years": 6,
            "residual_value": 20000,
            "annual_maintenance": 10000,
        },
        {
            "name": "Budget Chair",
            "initial_price": 50000,
            "useful_life_years": 3,
            "residual_value": 0,
            "annual_maintenance": 8000,
        },
    ]

    try:
        comparison = compare_tco(options)
        print(comparison.to_string(index=False))
    except ImportError as e:
        print(f"⚠️  {e}")
        print("Skipping comparison example (requires pandas)")

    # Example 3: Break-even Analysis
    print("\n\n[Example 3] Break-even Analysis")
    print("-" * 70)

    premium = {
        "initial_price": 450000,
        "useful_life_years": 12,
        "residual_value": 90000,
        "annual_maintenance": 5000,
    }

    budget = {
        "initial_price": 50000,
        "useful_life_years": 3,
        "residual_value": 0,
        "annual_maintenance": 8000,
    }

    breakeven = calculate_breakeven_point(premium, budget)
    if breakeven:
        print(f"Break-even point: {breakeven} years")
        print(f"The premium option pays for itself after {breakeven} years")
    else:
        print("No break-even point found (premium option is always more expensive)")

    # Example 4: Visualization (if matplotlib available)
    print("\n\n[Example 4] Visualization")
    print("-" * 70)

    try:
        print("Generating TCO comparison chart...")
        fig = visualize_tco_comparison(options, save_path="tco_comparison.png")
        print("✓ Chart saved as 'tco_comparison.png'")
    except ImportError as e:
        print(f"⚠️  {e}")
        print("Skipping visualization (requires matplotlib)")

    print("\n" + "=" * 70)
    print("Examples Complete!")
    print("=" * 70)
    print("\n💡 Tip: Import this module to use in your own scripts:")
    print("   from tco import calculate_tco, compare_tco")
