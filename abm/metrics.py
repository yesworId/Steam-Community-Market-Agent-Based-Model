from statistics import median

from .constants import ONE_DOLLAR


# TODO: Calculate agent profits, number of active agents, volatility, ...
# Number of Active agents - Agents that had at least one active market action in past N days.
# Volatility - average? difference between lowest and the highest price a day?
# Rate of sales sold to LOWEST Sell Order or HIGHEST Buy Order
# Liquidity
# Demand - Total number of all Buy Orders.
# Supply - Total number of all Sell Orders.
# Demand / Supply ratio = (Demand / Supply - 1) * 100
# Popularity

def calculate_median_price(sales_history, item_name: str, number_of_sales: int) -> int:
    """Calculates median price for given item on number of sales."""
    if number_of_sales <= 0:
        raise ValueError("Number of sales must be positive")

    item_sales = sales_history.get(item_name, [])
    if not item_sales:
        return 0

    prices = [sale.price for sale in item_sales[-number_of_sales:]]
    if not prices:
        return 0

    return int(median(prices))


def calculate_weighted_mean_price(sales_history, item_name: str, number_of_sales: int) -> int:
    item_sales = sales_history.get(item_name, [])
    if not item_sales:
        return 0
    item_sales = item_sales[-number_of_sales:]

    total_qty = sum(sale.quantity for sale in item_sales)
    if total_qty == 0:
        return 0

    weighted_sum = sum(sale.price * sale.quantity for sale in item_sales)
    return int(weighted_sum / total_qty)


def calculate_total_fee(sales_history) -> float:
    """Calculates the total fee earned for all sales."""
    return sum(sale.fee for history in sales_history.values() for sale in history) / ONE_DOLLAR


def calculate_sales_volume(sales_history, item_name: str, steps_per_day: int = 1000, period: str = "day") -> int:
    """
    Calculate the total quantity of items sold over a specified time period.

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
        raise ValueError("Wrong period! Please use 'day', 'week' or 'month'.")

    return sum(
        sale.quantity
        for sale in item_sales
        if sale.step >= time_threshold
    )


def get_all_sales(sales_history):
    """Return a list of all Sales."""
    return [sale for item_sale in sales_history.values() for sale in item_sale]
