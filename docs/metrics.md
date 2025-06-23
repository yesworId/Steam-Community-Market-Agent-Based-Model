# Metrics - !unfinished!

**Median price**

```python
def calculate_median_price(sales_history, item_name: str, number_of_sales: int) -> float:
    """Calculates median price for given item on number of sales."""
    prices = [sale.price for sale in sales_history if sale.item_name == item_name]
    if not prices:
        return 0.0

    return float(median(prices[-number_of_sales:]))
```


**Total Earned Fee**

```python
def calculate_total_fee(sales_history) -> float:
    """Calculates the total fee earned for all sales."""
    return sum(sale.fee for sale in sales_history)
```


**Sales volume**

```python
def calculate_sales_volume(sales_history, steps_per_day: int = 1000, period: str = "day") -> int:
    """
    Calculate the total quantity of items sold over a specified time period.

    :param sales_history: List with records of all past sales
    :param steps_per_day: Number of simulation steps that correspond to one Day
    :param period: Chosen period of recent sales ("day", "week", or "month")

    :returns: Total number of units sold within the specified period

    :raises ValueError: if period is not one of "day", "week", or "month"
    """
    if not sales_history:
        return 0

    latest_step = max(sale.step for sale in sales_history)

    if period == "day":
        time_threshold = latest_step - steps_per_day
    elif period == "week":
        time_threshold = latest_step - steps_per_day * 7
    elif period == "month":
        time_threshold = latest_step - steps_per_day * 30
    else:
        raise ValueError("Wrong period! Please use 'day', 'week' or 'month'.")

    return sum(
        sale.quantity
        for sale in sales_history
        if sale.step >= time_threshold
    )
```