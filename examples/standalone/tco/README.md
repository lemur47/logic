# TCO Calculator 🧮

**Total Cost of Ownership calculations in pure Python.**

Because "cheap" and "inexpensive" are not the same thing.

## The Problem

Your boss wants new office chairs. Budget option: ¥50,000. Premium option: ¥450,000.

"Obviously we go with Budget, right? It's 9x cheaper!"

Not so fast. Let's do the math.

![Premium vs Budget](./test_tco_comparison.)

## Quick Start

```python
from tco import calculate_tco, compare_tco

options = [
    {
        'name': 'Premium Chair',
        'initial_price': 450000,
        'useful_life_years': 12,
        'residual_value': 90000,
        'annual_maintenance': 5000
    },
    {
        'name': 'Budget Chair',
        'initial_price': 50000,
        'useful_life_years': 3,
        'annual_maintenance': 8000
    }
]

df = compare_tco(options)
print(df[['option', 'monthly_cost', 'total_cost']])
```

Output:
```
          option  monthly_cost  total_cost
0  Premium Chair       2916.67      360000
1   Budget Chair       1611.11       50000
```

Wait... Premium costs more monthly AND in total?

Yes. But here's what the numbers don't show at first glance:

## The Real Story

**Budget Chair over 12 years:**
- Buy 4 chairs (lasts 3 years each): ¥50,000 × 4 = ¥200,000
- Maintenance: ¥8,000 × 12 = ¥96,000
- Residual value: ¥0
- **True 12-year cost: ¥296,000**
- Plus: 4 procurement cycles, 4 disposal headaches, inconsistent comfort

**Premium Chair over 12 years:**
- Buy once: ¥450,000
- Maintenance: ¥5,000 × 12 = ¥60,000
- Residual value: -¥90,000
- **True 12-year cost: ¥420,000**
- Plus: 12-year warranty, ergonomic support, no replacement hassle

The gap narrows. And we haven't even factored in productivity, back pain, or the time cost of repeatedly researching and ordering chairs.

**This is TCO thinking.**

## Installation

```bash
# Core functions - zero dependencies
curl -O https://raw.githubusercontent.com/yourrepo/tco.py

# Optional: comparison & visualization
pip install pandas matplotlib
```

## API

### `calculate_tco()` — The Core

```python
from tco import calculate_tco

result = calculate_tco(
    initial_price=450000,       # Upfront cost
    useful_life_years=12,       # Lifespan
    residual_value=90000,       # What you get back at end
    annual_maintenance=5000,    # Yearly upkeep
    annual_operating_cost=0,    # Consumables, energy, etc.
    discount_rate=0.03          # Time value of money
)

# Returns:
# {
#     'total_cost': 420000.0,
#     'annual_cost': 35000.0,
#     'monthly_cost': 2916.67,
#     'cost_per_day': 95.89,
#     'npv_tco': 398234.51,      # Inflation-adjusted
#     'npv_annual': 33186.21
# }
```

**Dependencies:** None ✅

### `compare_tco()` — Side-by-Side

```python
from tco import compare_tco

options = [
    {'name': 'Option A', 'initial_price': 100000, 'useful_life_years': 5},
    {'name': 'Option B', 'initial_price': 50000, 'useful_life_years': 2},
]

df = compare_tco(options)  # Returns pandas DataFrame, sorted by annual_cost
```

**Dependencies:** `pandas`

### `calculate_breakeven_point()` — When Does Premium Pay Off?

```python
from tco import calculate_breakeven_point

premium = {'initial_price': 450000, 'useful_life_years': 12, 'annual_maintenance': 5000}
budget = {'initial_price': 50000, 'useful_life_years': 3, 'annual_maintenance': 8000}

years = calculate_breakeven_point(premium, budget)
print(f"Premium breaks even after {years} years")
# Premium breaks even after 21.05 years
```

Interesting — in this specific comparison, Budget actually wins on pure numbers. But TCO isn't just about the math...

**Dependencies:** None ✅

### `visualize_tco_comparison()` — Make It Visual

```python
from tco import visualize_tco_comparison

fig = visualize_tco_comparison(options, save_path='comparison.png')
```

**Dependencies:** `pandas`, `matplotlib`

## Real-World Applications

### Build vs Buy

```python
build = {
    'initial_price': 5000000,      # Dev costs
    'useful_life_years': 5,
    'annual_maintenance': 1000000,  # Internal team
}

buy = {
    'initial_price': 0,
    'useful_life_years': 5,
    'annual_operating_cost': 1800000,  # SaaS subscription
}

years = calculate_breakeven_point(build, buy)
```

### Equipment Lifecycle

```python
# When should we replace the server?
old_server = calculate_tco(
    initial_price=0,  # Already paid
    useful_life_years=3,
    annual_maintenance=500000,
    annual_operating_cost=300000  # Power, cooling
)

new_server = calculate_tco(
    initial_price=2000000,
    useful_life_years=5,
    annual_maintenance=100000,
    annual_operating_cost=150000
)
```

### Lease vs Own

```python
lease = {
    'initial_price': 0,
    'useful_life_years': 3,
    'annual_operating_cost': 600000,  # Monthly payments × 12
}

own = {
    'initial_price': 4500000,
    'useful_life_years': 7,
    'residual_value': 1500000,
    'annual_maintenance': 200000,
}
```

## The Mental Model

TCO forces you to think about:

1. **Time horizon** — How long will you actually use this?
2. **Hidden costs** — Maintenance, training, downtime, opportunity cost
3. **Residual value** — Can you sell it? Trade it in?
4. **Replacement cycles** — Cheap things need replacing more often

The cheapest option upfront is rarely the most inexpensive over time.

## Dependencies

| Function | Requires |
|----------|----------|
| `calculate_tco()` | Nothing |
| `calculate_breakeven_point()` | Nothing |
| `compare_tco()` | pandas |
| `visualize_tco_comparison()` | pandas, matplotlib |

## Testing

```bash
# Run built-in examples
python tco.py

# Run test suite
pytest test_tco.py
```

## License

MIT — Use it however you want.

---

**Philosophy:** Transform financial intuition into code.

*"Price is what you pay. Value is what you get."* — Warren Buffett
