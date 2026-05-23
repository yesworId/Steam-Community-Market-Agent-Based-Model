import random

from typing import DefaultDict
from abc import ABC, abstractmethod
from collections import defaultdict
from sortedcontainers import SortedList

from .market import Market
from .exceptions import InsufficientBalance, NotEnoughItems, DuplicateBuyOrder
from .models import (
    AgentType,
    ItemCategory,
    MarketItem,
    InventoryItem,
    Container,
    MarketHashName,
    AgentID,
    EntryPrice,
)
from .constants import (
    ONE_CENT,
    ONE_DOLLAR,
    MIN_PRICE,
    MAX_DISCOUNT,
    IMPULSIVITY_UNDERESTIMATION,
    MIN_SALES_FOR_ANALYSIS,
)


class Agent(ABC):
    """
    Base abstract Agent class with common methods and parameters to every `AgentType`.

    :param agent_id: Unique Agent identifier
    :param market: 'Market' instance, every Agent is connected to Environment
    :param agent_type: Describes type of the Agent
    :param balance: Amount of money Agent has (between 0 and 2000)
    :param impulsivity: Parameter indicating tendency of an Agent to act impulsively
    """
    __slots__ = (
        "id",
        "market",
        "type",
        "balance",
        "impulsivity",
        "inventory",
        "containers_opened",
    )

    def __init__(
            self,
            agent_id: AgentID,
            market: Market,
            agent_type: AgentType,
            balance: int = 0,
            impulsivity: float = 0.0
    ):
        self.id = agent_id
        self.market = market
        self.balance = balance
        self.type = agent_type
        self.impulsivity = impulsivity

        self.inventory: DefaultDict[MarketHashName, SortedList[InventoryItem]] = defaultdict(
            lambda: SortedList(key=lambda i: i.unlock_step)
        )

        self.containers_opened: int = 0

    @abstractmethod
    def act(self) -> None:
        raise NotImplementedError("This method is implemented in sub-classes")

    def add_balance(self, amount: int):
        if amount <= 0:
            raise ValueError("Amount to add must be positive")
        self.balance += amount

    def get_unlocked_items(self, market_hash_name: MarketHashName) -> list[InventoryItem]:
        return [
            i for i in self.inventory.get(market_hash_name, [])
            if i.quantity > 0
            and (self.market.trade_lock_period == 0 or i.unlock_step <= self.market.current_step)
        ]

    def total_unlocked_quantity(self, market_hash_name: MarketHashName) -> int:
        return sum(i.quantity for i in self.get_unlocked_items(market_hash_name))

    def has_item(self, market_hash_name: MarketHashName, quantity: int) -> bool:
        """Checks if Agent has enough number of items"""
        return self.total_unlocked_quantity(market_hash_name) >= quantity

    def add_item(self, item: MarketItem, quantity: int = 1, unlock_step: int = 0):
        self.inventory[item.market_hash_name].add(
            InventoryItem(
                item=item,
                quantity=quantity,
                unlock_step=unlock_step
            )
        )

    def remove_item(
            self,
            market_hash_name: MarketHashName,
            quantity: int,
            ignore_trade_lock: bool = False
        ):
        """Removes items from Agent's inventory."""
        if quantity <= 0:
            raise ValueError("Quantity to remove must be positive!")
        
        if not self.inventory.get(market_hash_name):
            raise NotEnoughItems("Item not found!")

        if ignore_trade_lock:
            unlocked_items = list(self.inventory[market_hash_name])
        else:
            unlocked_items = self.get_unlocked_items(market_hash_name)

        total_available = sum(i.quantity for i in unlocked_items)
        if total_available < quantity:
            raise NotEnoughItems("Not enough items in inventory!")

        remaining = quantity
        for i in unlocked_items:
            take = min(i.quantity, remaining)
            i.quantity -= take
            remaining -= take
            if remaining == 0:
                break

        to_remove = [inv_item for inv_item in self.inventory[market_hash_name] if inv_item.quantity == 0]
        for inv_item in to_remove:
            self.inventory[market_hash_name].remove(inv_item)

        if not self.inventory[market_hash_name]:
            del self.inventory[market_hash_name]

    def open_container(self, container: Container, quantity: int = 1) -> None:
        """
        Simulate CS2 containers opening.
 
        The agent will sell dropped items naturally via sell_items()
        on future simulation steps.
        """
        try:
            self.remove_item(container.market_hash_name, quantity, ignore_trade_lock=True)
        except NotEnoughItems:
            return
 
        dropped_items = container.roll_drops(quantity)
        if not dropped_items:
            return
        unlock_step = self.market.calculate_unlock_step(is_trade_lock=True)
 
        # Register seed prices on first encounter — provides get_base_price() method
        # a meaningful anchor before any real sale has occurred.
        for item in dropped_items:
            mhn = item.market_hash_name
            if mhn not in self.market.item_seed_prices:
                seed = container.get_seed_prices().get(mhn)
                if seed:
                    self.market.item_seed_prices[mhn] = seed
            self.add_item(item, quantity=1, unlock_step=unlock_step)
        
        self.containers_opened += quantity

    def is_impulsive(self) -> bool:
        return random.random() < self.impulsivity / IMPULSIVITY_UNDERESTIMATION

    def _panic_sell(self):
        """Impulsive decision, agent tries to sell all of his items"""
        for item_name, inventory_list in list(self.inventory.items()):
            if not inventory_list:
                continue
            
            unlocked_items = self.get_unlocked_items(item_name)
            if not unlocked_items:
                continue

            buy_orders = self.market.get_item_buy_orders(item_name)
            if not buy_orders:
                base_price = self.market.get_base_price(item_name)
                price = max(int(base_price * random.uniform(0.85, 1.0)), MIN_PRICE)
            else:
                highest_price = buy_orders[0].price
                price = max(int(highest_price * random.uniform(0.8, 1.0)), MIN_PRICE)

            for i in unlocked_items:
                if i.quantity == 0:
                    continue

                try:
                    self.market.sell(self.id, i.item, max(price, MIN_PRICE), i.quantity)
                except Exception as ex:
                    print(f"[Agent {self.id}] Failed to panic sell {item_name}: {ex}")


class NoviceAgent(Agent):
    """
    Simple, inexperienced-casual user, who adds noise and does act without logical strategy.
    """
    __slots__ = ()

    def __init__(
            self,
            agent_id: AgentID,
            market: Market,
            agent_type: AgentType,
            balance: int,
            impulsivity: float,
    ):
        super().__init__(agent_id, market, agent_type, balance, impulsivity)

    def act(self):
        """
        Imitates the behaviour of Novice Agent.

        He either buys or sells. There is a chance of panic sell happening based on Agent's impulsivity.
        """
        action = random.choice(['buy', 'sell'])
        if action == 'buy':
            self.buy_to_open_containers()
        else:
            self.sell_items()

    def buy_to_open_containers(self):
        """
        Imitates the process of purchasing random number of containers to open.
        """
        available_containers = [
            item for item in self.market.get_available_items(category_filter=ItemCategory.CONTAINER)
            if isinstance(item, Container)
        ]
        if not available_containers:
            return

        container = random.choice(available_containers)
        sell_orders = self.market.get_item_sell_orders(market_hash_name=container.market_hash_name)
        if not sell_orders:
            return

        max_price = 0
        total_spent = 0
        max_affordable_quantity = 0

        for sell_order in sell_orders:
            affordable_quantity = (self.balance - total_spent) // sell_order.price
            if affordable_quantity <= 0:
                break

            quantity_to_buy = min(sell_order.quantity, affordable_quantity)
            max_price = sell_order.price
            total_spent += max_price * quantity_to_buy
            max_affordable_quantity += quantity_to_buy

        if max_affordable_quantity == 0:
            return

        desired_quantity = random.randint(1, max_affordable_quantity)

        for _ in range(3):
            try:
                bought_quantity = self.market.buy(self.id, container, max_price, desired_quantity)
                if bought_quantity > 0:
                    self.open_container(container, bought_quantity)
                break
            except InsufficientBalance:
                self.sell_items()
            except DuplicateBuyOrder as ex:
                self.market.cancel_buy_order(market_hash_name=container.market_hash_name, order_id=ex.order_id)

    def sell_items(self):
        """
        Imitates a regular or impulsive sell behaviour.
        Agent either slightly undercuts the lowest sell listing or dumps items to the highest Buy Order.
        """
        if not self.inventory:
            return

        if self.is_impulsive():
            return self._panic_sell()

        # Regular strategy: Agent tries to sell items cheaper than the lowest listing
        market_hash_name = random.choice(list(self.inventory.keys()))
        inventory_list = self.inventory[market_hash_name]
        if not inventory_list:
            return
        item = inventory_list[0].item
        unlocked_quantity = self.total_unlocked_quantity(market_hash_name)
        if unlocked_quantity <= 0:
            return

        quantity = random.randint(1, unlocked_quantity)

        sell_orders = self.market.get_item_sell_orders(market_hash_name=item.market_hash_name)
        if sell_orders:
            lowest_sell_order = sell_orders[0].price
            price = lowest_sell_order - random.randint(ONE_CENT, ONE_DOLLAR)
        else:
            # Pick base price
            base_price = self.market.get_base_price(market_hash_name=item.market_hash_name)
            price = int(base_price * random.uniform(0.95, 1.05))

        self.market.sell(self.id, item, max(price, MIN_PRICE), quantity)


class TraderAgent(Agent):
    """
    More complex agent, which operates for the profits.

    TRIES TO BUY LOWER THAN THE MARKET PRICE, items that can be higher in the near future due to the past trends.
    EXAMPLE: cases are more expensive at the end of the week before the weekly drop rate re-stock / change

    :param risk_tolerance: Chance to take a risk decision
    """
    __slots__ = ("risk_tolerance", "entry_prices",)

    def __init__(
            self,
            agent_id: AgentID,
            market: Market,
            agent_type: AgentType,
            balance: int,
            impulsivity: float,
            risk_tolerance: float,
    ):
        super().__init__(agent_id, market, agent_type, balance, impulsivity)
        self.risk_tolerance = risk_tolerance

        # inconsistent with InvestorAgent
        self.entry_prices: DefaultDict[MarketHashName, list[int]] = defaultdict(list)

    def act(self):
        if self.inventory and self.is_impulsive():
            return self._panic_sell()

        # self.try_sell_for_profit()

        # self.try_buy_for_profit()

        # For each selling item analyze its trend and spread
        for item in self.market.get_available_items():
            item_name = item.market_hash_name
            recent_sales = self.market.get_item_recent_sales(item_name, MIN_SALES_FOR_ANALYSIS)
            if len(recent_sales) < 5:
                continue

            prices = [sale.price for sale in recent_sales]

            # Trend analysis
            mid = len(prices) // 2
            avg_first = sum(prices[:mid]) / mid
            avg_second = sum(prices[mid:]) / (len(prices) - mid)
            trend_up = avg_second > avg_first

            min_price = min(prices)
            max_price = max(prices)
            spread = (max_price - min_price) * (1 - self.market.market_fee)

            # Try to sell items for profit
            unlocked_quantity = self.total_unlocked_quantity(item_name)
            if item_name in self.inventory and unlocked_quantity > 0:
                buy_orders = self.market.get_item_buy_orders(item_name)
                if buy_orders:
                    highest_price = buy_orders[0].price
                    profitable = False
                    for entry_price in self.entry_prices.get(item_name, []):
                        desired_price = entry_price * (1 + self.risk_tolerance) / (1 - self.market.market_fee)
                        if highest_price >= desired_price:
                            try:
                                self.market.sell(self.id, item, highest_price, unlocked_quantity)
                                del self.entry_prices[item_name]
                                profitable = True
                            except Exception as ex:
                                print(f"Trader {self.id} failed to sell {item_name}: {ex}")
                            break
                    if profitable:
                        continue

            avg_price = sum(prices) / len(prices)
            buy_signal = False

            sell_orders = self.market.get_item_sell_orders(item_name)
            if not sell_orders:
                continue

            best_ask = sell_orders[0].price
            is_desired_price = best_ask <= min_price * (1 + self.risk_tolerance)
            buy_signal = (
                (trend_up and is_desired_price)
                or (spread >= avg_price * 0.1 and is_desired_price)
            )

            if buy_signal:
                # Determine buy quantity based on balance and risk_tolerance
                buy_quantity = int(self.balance // best_ask * self.risk_tolerance)
                if buy_quantity > 0:
                    for _ in range(3):
                        try:
                            bought_qty = self.market.buy(self.id, item, best_ask, buy_quantity)
                            if bought_qty > 0:
                                self.entry_prices[item.market_hash_name].append(best_ask)
                                break
                        except DuplicateBuyOrder as ex:
                            self.market.cancel_buy_order(
                                market_hash_name=item.market_hash_name,
                                order_id=ex.order_id
                            )


class InvestorAgent(Agent):
    """
    Determines balance for the investment, buys more as price gets lower.

    If risk_tolerance is high (0.8+) that means investor is highly risked
    and willing to buy items even after imperceptible discount.

    :param risk_tolerance: Agent's degree of making risky decisions. Determines invested amount and buy price.
    """
    __slots__ = ("risk_tolerance", "entry_prices")

    def __init__(
            self,
            agent_id: AgentID,
            market: Market,
            agent_type: AgentType,
            balance: int,
            impulsivity: float,
            risk_tolerance: float,
    ):
        super().__init__(agent_id, market, agent_type, balance, impulsivity)
        self.risk_tolerance = risk_tolerance
        self.entry_prices: dict[MarketHashName, EntryPrice] = {}

    def act(self):
        """
        Imitates behaviour of Investor Agent.

        Agent monitors his investments, sells if satisfied with returns.
        Tries to buy more if he's willing to take a risk.
        """

        if self.inventory and self.is_impulsive():
            return self._panic_sell()

        if self.try_take_profit():
            return

        self.try_buy_dip()

    def refresh_entry_prices_from_history(self):
        purchases = self.market.get_agent_purchases(self.id)
        if not purchases:
            self.entry_prices.clear()
            return

        sales = self.market.get_agent_sales(self.id)

        bought_qty: DefaultDict[MarketHashName, int] = defaultdict(int)
        bought_cost: DefaultDict[MarketHashName, int] = defaultdict(int)
        sold_qty: DefaultDict[MarketHashName, int] = defaultdict(int)

        for p in purchases:
            item_name = p.item.market_hash_name
            bought_qty[item_name] += p.quantity
            bought_cost[item_name] += p.quantity * p.price
        
        for s in sales:
            sold_qty[s.item.market_hash_name] += s.quantity

        new_entry = {}
        for mhn, total_bought in bought_qty.items():
            total_sold = sold_qty.get(mhn, 0)
            net_qty = total_bought - total_sold
            if net_qty <= 0:
                continue

            avg_buy = bought_cost[mhn] / total_bought
            remaining_cost = bought_cost[mhn] - avg_buy * total_sold

            new_entry[mhn] = EntryPrice(quantity=net_qty, avg_price=int(remaining_cost / net_qty))

        self.entry_prices = new_entry

    def try_take_profit(self):
        self.refresh_entry_prices_from_history()

        # trying to sell investments for profit, checks the price if it's already higher than desired profits
        # or just places sell order with desired price
        for market_hash_name, inventory_list in list(self.inventory.items()):
            if not inventory_list:
                continue

            entry_price = self.entry_prices.get(market_hash_name)
            if entry_price is None:
                continue

            buy_orders = self.market.get_item_buy_orders(market_hash_name)
            if not buy_orders:
                # Items have just appeared, investor hasn't invested yet
                continue

            highest_price = buy_orders[0].price
            target_price = entry_price.avg_price * (1 + self.risk_tolerance) / (1 - self.market.market_fee)

            if highest_price >= target_price:
                item = inventory_list[0].item
                unlocked_quantity = self.total_unlocked_quantity(market_hash_name)
                if unlocked_quantity <= 0:
                    continue    # waiting for items to get unlocked

                batch_quantity = max(1, random.randint(unlocked_quantity // 5, unlocked_quantity))
                try:
                    self.market.sell(self.id, item, highest_price, batch_quantity)
                except Exception as ex:
                    print(f"Investor {self.id} failed to sell his items: {ex}")
                return True
        return False

    def try_buy_dip(self):
        available_items = self.market.get_available_items()
        if not available_items:
            return

        item = random.choice(available_items)
        item_name = item.market_hash_name
        sell_orders = self.market.get_item_sell_orders(market_hash_name=item_name)
        if not sell_orders:
            return

        lowest_price = sell_orders[0].price
        discount = (1 - self.risk_tolerance) * MAX_DISCOUNT
        price = max(int(lowest_price * (1 - discount)), MIN_PRICE)
        quantity = int(self.balance * self.risk_tolerance // price)

        if quantity <= 0:
            return
        
        for _ in range(3):
            try:
                self.market.buy(self.id, item, price, quantity)
                break
            except DuplicateBuyOrder as ex:
                self.market.cancel_buy_order(market_hash_name=item_name, order_id=ex.order_id)


class FarmerAgent(Agent):
    """
    More marginal and unprincipled Market agent, which exploits in-game reward system to obtain profit.

    :param number_of_accounts: Number of accounts in a Bot Farm, affects the amount of sold items every week
    """
    __slots__ = ("number_of_accounts",)

    def __init__(
            self,
            agent_id: AgentID,
            market: Market,
            agent_type: AgentType,
            balance: int,
            impulsivity: float,
            number_of_accounts: int,
    ):
        super().__init__(agent_id, market, agent_type, balance, impulsivity)
        self.number_of_accounts = number_of_accounts

    def act(self):
        """
        He either sells farmed items each week in batches to avoid dumping the price
        or instantly sells all of them in a fear of an account ban.
        """

        if self.is_impulsive():
            self._panic_sell()
        else:
            self.sell_farmed_items()

    def sell_farmed_items(self):
        """Regular Sell, when Agent sells farmed items in batches"""
        for item_name, inventory_list in list(self.inventory.items()):
            if not inventory_list:
                continue

            item = inventory_list[0].item
            quantity = self.total_unlocked_quantity(item_name)
            if quantity <= 0:
                continue

            # Sells items in range of a median or base price
            base_price = self.market.get_base_price(market_hash_name=item_name)
            batches = random.randint(1, 10)
            batch_size = max(1, quantity // batches)

            for _ in range(batches):
                if quantity <= 0:
                    break

                price = int(base_price * random.uniform(0.9, 1.15))
                try:
                    self.market.sell(self.id, item, max(price, MIN_PRICE), batch_size)
                    quantity -= batch_size
                except NotEnoughItems:
                    break
                except Exception as ex:
                    print(f"Farmer {self.id} couldn't sell his items, happened unexpected error: {ex}")
                    break
