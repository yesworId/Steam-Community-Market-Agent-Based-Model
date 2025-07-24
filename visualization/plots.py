import numpy as np
import matplotlib.pyplot as plt

from abm.constants import ONE_DOLLAR


def agent_balance_histogram(agents: list, bin_width: int = 100):
    """
    Plot a histogram of agent balances.

    :param agents: List of Agent instances.
    :param bin_width: Width of each bin, by default in hundreds.
    """
    balances = [agent.balance / ONE_DOLLAR for agent in agents]
    bin_edges = np.arange(0, int(max(balances) // bin_width + 2) * bin_width, bin_width)

    plt.figure(figsize=(8, 4))
    plt.hist(balances, bins=bin_edges, color="tab:blue", edgecolor="black", alpha=0.7)
    plt.xlabel("Agent Balances")
    plt.ylabel("Number of Agents")
    plt.title("Distribution of Agent Balances")
    plt.tight_layout()
    plt.show()


def plot_sales_history(sales_history, item_name: str, show_volume: bool = False, steps_per_day: int = 1000):
    """
    Plots sales history. If show_volume equal True, adds vertical bars of daily sold volume.

    :param sales_history: List with records of all past sales
    :param item_name: Name of the Item
    :param show_volume: If True, add histogram with sold quantity per day
    :param steps_per_day: Number of simulation steps that correspond to one Day
    """
    item_sales = sales_history.get(item_name, [])
    if not item_sales:
        return

    steps = np.array([sale.step for sale in item_sales])
    prices = np.array([sale.price for sale in item_sales]) / ONE_DOLLAR
    quantities = np.array([sale.quantity for sale in item_sales])

    sort_indices = np.argsort(steps)
    steps = steps[sort_indices]
    prices = prices[sort_indices]
    quantities = quantities[sort_indices]

    grid_kwargs = {"color": "#dddddd", "linestyle": "--", "linewidth": 0.5, "alpha": 0.7}

    if not show_volume:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(steps, prices, color="tab:blue", linewidth=1.0)
        ax.set_xlabel("Simulation Step")
        ax.set_ylabel("Price")
        ax.set_title("Sales History")
        ax.grid(**grid_kwargs)
        plt.tight_layout()
        plt.show()
        return

    days = steps // steps_per_day
    unique_days, day_indices = np.unique(days, return_inverse=True)
    volume_by_day = np.bincount(day_indices, weights=quantities)

    fig, ax_price = plt.subplots(figsize=(10, 5))

    ax_price.plot(steps, prices, color="tab:blue", linewidth=1.0, label="Price")
    ax_price.set_xlabel("Simulation Step")
    ax_price.set_ylabel("Price", color="tab:blue")
    ax_price.tick_params(axis="y", labelcolor="tab:blue")
    ax_price.set_title("Sales History (with Daily Volume)")
    ax_price.grid(**grid_kwargs)

    ax_vol = ax_price.twinx()
    x_positions = unique_days * steps_per_day
    bar_width = steps_per_day * 0.9

    ax_vol.bar(
        x_positions,
        volume_by_day,
        width=bar_width,
        color="tab:green",
        alpha=0.4,
        edgecolor="black",
        label="Units Sold per Day"
    )
    ax_vol.set_ylabel("Units Sold per Day", color="tab:green")
    ax_vol.tick_params(axis="y", labelcolor="tab:green")

    lines_price, labels_price = ax_price.get_legend_handles_labels()
    lines_vol, labels_vol = ax_vol.get_legend_handles_labels()
    ax_price.legend(lines_price + lines_vol, labels_price + labels_vol, loc="upper right")

    plt.tight_layout()
    plt.show()


def plot_order_book(market, item_name: str):
    """
    Plot cumulative Order Book for passed item_name.

    :param market: 'Market' instance, where Buy/Sell orders are stored.
    :param item_name: Item name.
    """
    buy_list = market.buy_orders.get(item_name, [])
    sell_list = market.sell_orders.get(item_name, [])

    if (not buy_list) and (not sell_list):
        print(f"No buy or sell orders found for item '{item_name}'.")
        return

    if buy_list:
        buy_prices = np.array([o.price for o in buy_list]) / ONE_DOLLAR
        buy_qtys = np.array([o.quantity for o in buy_list])

        idx_buy = np.argsort(-buy_prices)
        buy_prices_sorted = buy_prices[idx_buy]
        buy_qtys_sorted = buy_qtys[idx_buy]
        buy_cumulative = np.cumsum(buy_qtys_sorted)
    else:
        buy_prices_sorted = np.array([])
        buy_cumulative = np.array([])

    if sell_list:
        sell_prices = np.array([o.price for o in sell_list]) / ONE_DOLLAR
        sell_qtys = np.array([o.quantity for o in sell_list])
        idx_sell = np.argsort(sell_prices)
        sell_prices_sorted = sell_prices[idx_sell]
        sell_qtys_sorted = sell_qtys[idx_sell]
        sell_cumulative = np.cumsum(sell_qtys_sorted)
    else:
        sell_prices_sorted = np.array([])
        sell_cumulative = np.array([])

    fig, ax = plt.subplots(figsize=(8, 5))

    if buy_prices_sorted.size > 0:
        ax.step(
            buy_prices_sorted,
            buy_cumulative,
            where="post",
            color="tab:blue",
            linewidth=1.5,
            label="Cumulative Buy Volume"
        )

    if sell_prices_sorted.size > 0:
        ax.step(
            sell_prices_sorted,
            sell_cumulative,
            where="post",
            color="tab:green",
            linewidth=1.5,
            label="Cumulative Sell Volume"
        )

    ax.set_xlabel("Price")
    ax.set_ylabel("Cumulative Quantity")
    ax.set_title(f"Order Book Depth for '{item_name}'")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="upper left")
    plt.tight_layout()
    plt.show()
