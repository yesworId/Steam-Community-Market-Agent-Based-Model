# Metrics

This module contains utility functions to gather various statistics within the simulation such as price trend,
fee revenue or volume of sales for a given period.


### Median price:

```python
def calculate_median_price(
        sales_history: SalesHistory,
        market_hash_name: MarketHashName,
        number_of_sales: int
) -> int:
    """Returns median price of the most recent number of sales for a specific item in cents."""
    if number_of_sales <= 0:
        raise ValueError("Number of sales must be positive")

    item_sales = sales_history.get(market_hash_name, [])
    if not item_sales:
        return 0

    return round(median([sale.price for sale in item_sales[-number_of_sales:]]))
```


### Total Earned Fee:

```python
def calculate_total_fee(sales_history: SalesHistory) -> float:
    """Returns total fee earned for all sales (in monetary units)."""
    return sum(sale.total_fee for history in sales_history.values() for sale in history) / ONE_DOLLAR
```


### Sales volume:

```python
def calculate_sales_volume(
        sales_history: SalesHistory,
        market_hash_name: MarketHashName,
        steps_per_day: int = 1000,
        period: str = "day"
) -> int:
    """
    Return the total quantity of items sold over a specified time period.

    :param sales_history: List with records of all past sales
    :param market_hash_name: Market name of the `Item`
    :param steps_per_day: Number of simulation steps that correspond to one Day
    :param period: Chosen period of recent sales ("day", "week", or "month")

    :returns: Total number of units sold within the specified period

    :raises ValueError: if period is not one of "day", "week", or "month"
    """
    item_sales = sales_history.get(market_hash_name, [])
    if not item_sales:
        return 0

    latest_step = max(sale.step for sale in item_sales)

    if period == "day":
        time_threshold = latest_step - steps_per_day
    elif period == "week":
        time_threshold = latest_step - steps_per_day * 7
    elif period == "month":
        time_threshold = latest_step - steps_per_day * 30
    else:
        raise ValueError("Wrong time period! Please use 'day', 'week' or 'month'.")

    return sum(
        sale.quantity
        for sale in item_sales
        if sale.step >= time_threshold
    )
```

### List of all sales:

```python
def get_all_sales(sales_history: SalesHistory):
    """Return a list of all Sales."""
    return [sale for item_sale in sales_history.values() for sale in item_sale]
```
