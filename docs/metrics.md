# Metrics

This module contains utility functions to gather various statistics within the simulation such as price trend,
fee revenue or volume of sales for a given period.


### Median price:

```python
def calculate_median_price(sales_history, item_name: str, number_of_sales: int) -> int:
    """Returns median price of the most recent `number_of_sales` sales for a specific item"""
    if number_of_sales <= 0:
        raise ValueError("Number of sales must be positive")

    item_sales = sales_history.get(item_name, [])
    if not item_sales:
        return 0

    return int(median([sale.price for sale in item_sales[-number_of_sales:]]))
```


### Total Earned Fee:

```python
def calculate_total_fee(sales_history) -> float:
    """Returns total fee earned for all sales."""
    return sum(sale.fee for history in sales_history.values() for sale in history) / ONE_DOLLAR
```


### Sales volume:

```python
def calculate_sales_volume(sales_history, item_name: str, steps_per_day: int = 1000, period: str = "day") -> int:
    """
    Return the total quantity of items sold over a specified time period.

    :param sales_history: List with records of all past sales
    :param item_name: Name of the Item
    :param steps_per_day: Number of simulation steps that correspond to one Day
    :param period: Chosen period of recent sales ("day", "week", or "month")

    :returns: Total number of units sold within the specified period

    :raises ValueError: if period is not one of "day", "week", or "month"
    """
    item_sales = sales_history.get(item_name, [])
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