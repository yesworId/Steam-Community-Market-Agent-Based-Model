# Visualization

This module is created to visualize calculated results for better understanding and analysis.


## `agent_balance_histogram()`

Use to display the distribution of `Agent` balances at any moment in simulation.

### Parameters:
* `agents` - list of `Agent` instances.
* `bin_width` - Width of each bin, interval in which you want balances to be split.

**NOTE:** By default this will group balances in range of hundreds, like: (0-100, 100-200, ....).

```python
from visualization import plots

plots.agent_balance_histogram(agents)
```

## `plot_sales_history()`

Used to display price chart. You can also visualize daily sales volume by passing `show_volume` parameter as **True**:

```python
from visualization import plots

# Simple sales price chart
plots.plot_sales_history(sales_history=market.sales_history, item_name='Item A')

# Price history chart with daily sales volume
plots.plot_sales_history(sales_history=market.sales_history, item_name='Item A', show_volume=True)
```


## `plot_order_book`

Used to visualize Buy and Sell orders in any moment in simulation:

```python
from visualization import plots

plots.plot_order_book(market=market, item_name='Item A')
```
