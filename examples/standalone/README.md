# TCO Calculator - Standalone Version 🧮

**Simple, powerful Total Cost of Ownership calculations in pure Python.**

Perfect for scripts, Jupyter notebooks, and quick financial analysis.

## 🚀 Quick Start

### Installation

```bash
# Core functionality (no dependencies!)
# Just download tco.py and use it!

# For comparison features (pandas):
pip install pandas
# OR with uv (recommended):
uv pip install pandas

# For visualization (matplotlib):
pip install matplotlib
# OR with uv (recommended):
uv pip install matplotlib

# Install both at once:
pip install pandas matplotlib
# OR with uv:
uv pip install pandas matplotlib
```

### Using UV (Modern Python Package Manager)

If you're using [uv](https://github.com/astral-sh/uv) - the fast, modern Python package installer:

```bash
# Install uv (if you haven't already)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create a virtual environment
uv venv

# Activate it
source .venv/bin/activate  # On macOS/Linux
.venv\Scripts\activate     # On Windows

# Install dependencies
uv pip install pandas matplotlib
```

### Basic Usage

```python
from tco import calculate_tco

# Calculate TCO for a premium office chair
result = calculate_tco(
    initial_price=450000,      # ¥450,000
    useful_life_years=12,      # 12-year warranty
    residual_value=90000,      # Estimated resale value
    annual_maintenance=5000    # Annual upkeep
)

print(f"Monthly cost: ¥{result['monthly_cost']:,.0f}")
# Output: Monthly cost: ¥2,917
```

## 📊 Features

### ✅ Core Calculation (`calculate_tco`)
- Simple TCO calculation
- NPV-adjusted TCO (time value of money)
- Daily, monthly, and annual costs
- **Zero dependencies** - works with just Python!

### ✅ Comparison (`compare_tco`)
- Compare multiple options
- Automatic ranking by cost
- Payback period calculation
- Returns pandas DataFrame
- Requires: `pandas`

### ✅ Visualization (`visualize_tco_comparison`)
- Side-by-side cost comparison
- Monthly and total cost charts
- Save to file or display
- Professional styling
- Requires: `pandas`, `matplotlib`

### ✅ Break-Even Analysis (`calculate_breakeven_point`)
- When does higher upfront pay off?
- Useful for build vs. buy decisions
- **Zero dependencies**

## 💡 Use Cases

### 1. Quick Analysis (No Dependencies)

```python
from tco import calculate_tco

# Evaluate an investment
cost = calculate_tco(initial_price=100000, useful_life_years=5)
print(cost)
```

### 2. Compare Options (Requires pandas)

```python
from tco import compare_tco

options = [
    {
        'name': 'Premium',
        'initial_price': 450000,
        'useful_life_years': 12,
        'residual_value': 90000
    },
    {
        'name': 'Budget',
        'initial_price': 50000,
        'useful_life_years': 3
    }
]

df = compare_tco(options)
print(df[['option', 'monthly_cost', 'total_cost']])
```

### 3. Visual Comparison (Requires matplotlib)

```python
from tco import visualize_tco_comparison

options = [...]  # Same as above
fig = visualize_tco_comparison(options, save_path='comparison.png')
```

### 4. Break-Even Analysis

```python
from tco import calculate_breakeven_point

premium = {'initial_price': 450000, 'useful_life_years': 12}
budget = {'initial_price': 50000, 'useful_life_years': 3}

years = calculate_breakeven_point(premium, budget)
print(f"Breaks even in {years} years")
```

## 🎓 Examples

### Jupyter Notebook

```python
import pandas as pd
from tco import calculate_tco

# Analyze price sensitivity
scenarios = []
for price in range(300000, 600000, 50000):
    result = calculate_tco(initial_price=price, useful_life_years=10)
    scenarios.append({
        'price': price,
        'monthly': result['monthly_cost']
    })

df = pd.DataFrame(scenarios)
df.plot(x='price', y='monthly', kind='line',
        title='Price Sensitivity Analysis')
```

### Custom Decision Logic

```python
from tco import calculate_tco

def should_invest(price, life_years, max_monthly_budget):
    """Decide if investment fits budget."""
    result = calculate_tco(
        initial_price=price,
        useful_life_years=life_years
    )
    return result['monthly_cost'] <= max_monthly_budget

if should_invest(450000, 12, 3000):
    print("✅ Investment approved!")
```

### Batch Processing

```python
from tco import compare_tco
import json

# Load data
with open('options.json') as f:
    options = json.load(f)

# Analyze
results = compare_tco(options)

# Export
results.to_csv('tco_analysis.csv')
results.to_excel('tco_analysis.xlsx')
```

## 📖 API Reference

### `calculate_tco()`

Calculate Total Cost of Ownership.

**Parameters:**
- `initial_price` (float): Initial purchase price
- `useful_life_years` (int): Expected lifespan in years
- `residual_value` (float): Salvage value at end of life (default: 0)
- `annual_maintenance` (float): Annual maintenance costs (default: 0)
- `annual_operating_cost` (float): Annual operational expenses (default: 0)
- `discount_rate` (float): Discount rate for NPV (default: 0.03)

**Returns:** dict with keys:
- `total_cost`: Total lifetime cost (undiscounted)
- `annual_cost`: Average annual cost
- `monthly_cost`: Average monthly cost
- `cost_per_day`: Average daily cost
- `npv_tco`: NPV-adjusted total cost
- `npv_annual`: NPV-adjusted annual cost

**Dependencies:** None ✅

### `compare_tco(options)`

Compare multiple options.

**Parameters:**
- `options` (list): List of dicts, each with 'name' and TCO parameters

**Returns:** pandas.DataFrame sorted by annual_cost

**Dependencies:** `pandas`

### `visualize_tco_comparison(options, save_path=None)`

Create comparison charts.

**Parameters:**
- `options` (list): Same as compare_tco()
- `save_path` (str, optional): Path to save figure

**Returns:** matplotlib Figure object

**Dependencies:** `pandas`, `matplotlib`

### `calculate_breakeven_point(option_a, option_b)`

Calculate when option A pays for itself vs option B.

**Parameters:**
- `option_a` (dict): First option parameters
- `option_b` (dict): Second option parameters

**Returns:** float (years) or None if no break-even

**Dependencies:** None ✅

## 🧪 Testing

Run the built-in examples:

```bash
python tco.py
```

This will:
- Calculate single TCO
- Compare multiple options
- Perform break-even analysis
- Generate visualization (if matplotlib installed)

## 🤔 FAQ

**Q: What if I don't have pandas/matplotlib?**
A: The core `calculate_tco()` and `calculate_breakeven_point()` work without any dependencies! Comparison and visualization features are optional.

**Q: Should I use pip or uv?**
A: Both work! UV is faster and more modern, but pip is more widely available. Choose what you prefer.

**Q: Can I use this in commercial projects?**
A: Yes! MIT License allows commercial use.

**Q: How accurate is the NPV calculation?**
A: Uses standard NPV formula with configurable discount rate. Suitable for business analysis and decision-making.

**Q: What about inflation?**
A: The discount rate can account for inflation. Adjust it based on your economic context (e.g., use 5-7% for high-inflation environments).

**Q: Can I modify the code?**
A: Absolutely! It's open source. Fork it, extend it, adapt it to your needs.

## 📦 Dependency Overview

| Feature | Dependencies | Install Command |
|---------|-------------|-----------------|
| Core TCO calculation | **None** | Just download tco.py |
| Break-even analysis | **None** | Just download tco.py |
| Comparison | `pandas` | `uv pip install pandas` |
| Visualization | `pandas`, `matplotlib` | `uv pip install pandas matplotlib` |

## 🛠️ Development Setup (for contributors)

```bash
# Clone or download the file
wget https://raw.githubusercontent.com/yourusername/tco-calculator/main/tco.py

# Install dev dependencies with UV
uv pip install pandas matplotlib pytest

# Run tests (if test file exists)
pytest test_tco.py

# Or just run the examples
python tco.py
```

## 📄 License

MIT License - See LICENSE file

## 🤝 Contributing

Found a bug? Have a feature request? Open an issue or PR!

Contributions welcome:
- Bug fixes
- New calculation methods
- Performance improvements
- Documentation enhancements
- Example use cases

## 🌟 Credits

**Built by:** Everyday Magic for Wise Investors
**Philosophy:** Transform mental models into practical code

---

## 💡 Pro Tips

### Tip 1: Explore the API
```python
from tco import *
help(calculate_tco)
```

### Tip 2: Use in Scripts
```python
#!/usr/bin/env python3
from tco import calculate_tco
import sys

price = float(sys.argv[1])
years = int(sys.argv[2])

result = calculate_tco(initial_price=price, useful_life_years=years)
print(f"Monthly: ¥{result['monthly_cost']:,.0f}")
```

Usage: `python script.py 450000 12`

### Tip 3: Integration with Other Tools
The standalone version is designed to be embedded in larger projects. Just copy `tco.py` into your project and import it!

---

**Quick Command Reference:**

```bash
# With pip
pip install pandas matplotlib

# With uv (faster!)
uv pip install pandas matplotlib

# Run examples
python tco.py

# In Python REPL
>>> from tco import calculate_tco
>>> calculate_tco(100000, 5)
```
