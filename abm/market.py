from __future__ import annotations
from typing import TYPE_CHECKING, DefaultDict, Sequence
from collections import defaultdict
from sortedcontainers import SortedList

from .metrics import calculate_median_price
from .constants import DEFAULT_BASE_PRICE, MIN_FEE, ONE_DOLLAR
from .exceptions import (
    AgentDoesNotExist,
    InsufficientBalance,
    NoOrderMatch,
    DuplicateBuyOrder
)
from .models import (
    OrderID,
    AgentID,
    MarketHashName,
    OrderType,
    ItemCategory,
    MarketItem,
    Order,
    Sale,
    AgentMarketHistory,
    AgentBuyOrderIndex,
)


if TYPE_CHECKING:
    from .agents import Agent as Agent


class Market:
    """
    Central simulation environment modeling Steam Community Market internal mechanics.

    Limitations:
        - **One Buy Order per item (per Agent)**: Agents cannot stack multiple active 
          buy orders for the same item.
        - (Optional) Max Wallet Balance cap.
        - **Max Agent Balance Cap**: Agents cannot hold more funds than ``max_balance``. 
          This restriction dynamically truncates transaction quantities during matching 
          if a sale would push the seller's balance over the limit.

    :param market_fee: Percentage 'Market' charges on any sale.
    :param steps_per_day: Number of simulation steps per simulated day.
    :param trade_lock_period: Trade hold duration (in simulation days).
    :param lock_on_purchase: If True, applies trade lock to items purchased from the market.
    :param max_balance: The maximum balance capacity allowed for any Agent.
    :param current_step: Counter of simulation steps.

    .. note:: 
        User is responsible for adding generated agents after initializing Market instance!
    """
    def __init__(
            self,
            market_fee: float = 0.15,
            steps_per_day: int = 1000,
            trade_lock_period: int = 7,
            lock_on_purchase: bool = True,
            max_balance: int = 2000,
            current_step: int = 0
    ):
        self.market_fee = market_fee
        self.steps_per_day = steps_per_day
        self.trade_lock_period = trade_lock_period
        self.lock_on_purchase = lock_on_purchase
        self.max_balance = max_balance * ONE_DOLLAR
        self.current_step = current_step

        self.agents: dict[AgentID, Agent] = {}

        self.buy_orders: DefaultDict[MarketHashName, SortedList[Order]] = defaultdict(
            lambda: SortedList(key=lambda o: (-o.price, o.step))
        )
        self.sell_orders: DefaultDict[MarketHashName, SortedList[Order]] = defaultdict(
            lambda: SortedList(key=lambda o: (o.price, o.step))
        )
        self.agent_buy_orders_idx: AgentBuyOrderIndex = defaultdict(dict)

        self.items_map: dict[MarketHashName, MarketItem] = {}
        self.sales_history: DefaultDict[MarketHashName, list[Sale]] = defaultdict(list)

        self.agent_purchases: AgentMarketHistory = defaultdict(list)
        self.agent_sales: AgentMarketHistory = defaultdict(list)

        self.item_seed_prices: dict[MarketHashName, int] = {}

    def add_agents(self, agents: list[Agent]):
        """Register agents within the market."""
        for agent in agents:
            if agent.id in self.agents:
                raise ValueError(f"Duplicate agent_id detected: {agent.id}")
            self.agents[agent.id] = agent
            agent.market = self

    def calculate_fee(self, order_total: int):
        return max(int(order_total * self.market_fee), MIN_FEE)
    
    def _max_receivable_quantity(self, seller_balance: int, price: int, desired_qty: int) -> int:
        available_capacity = self.max_balance - seller_balance
        if available_capacity <= 0:
            return 0
        if price <= 0:
            return 0

        return min(desired_qty, int(available_capacity / (price * (1 - self.market_fee))))
    
    def calculate_unlock_step(self, is_trade_lock: bool = True) -> int:
        """Calculates unlock step based on a trade lock period."""
        return self.current_step + self.trade_lock_period * self.steps_per_day if is_trade_lock else 0

    def get_base_price(self, market_hash_name: MarketHashName, number_of_sales: int = 50) -> int:
        median_price = calculate_median_price(self.sales_history, market_hash_name, number_of_sales)
        if median_price > 0:
            return median_price

        buy_orders = self.get_item_buy_orders(market_hash_name)
        if buy_orders:
            return buy_orders[0].price
        
        # Seed price registered when item first dropped from container
        seed = self.item_seed_prices.get(market_hash_name)
        if seed:
            return seed

        return DEFAULT_BASE_PRICE

    def get_item_recent_sales(self, market_hash_name: MarketHashName, number_of_sales: int = 50) -> list[Sale]:
        """Returns a list of passed number of recent sales for market_hash_name."""
        item_sales = self.sales_history.get(market_hash_name, [])
        if not item_sales:
            return []
        return item_sales[-number_of_sales:]

    def get_agent_orders(self, agent_id: AgentID, order_type: OrderType | None = None) -> dict[str, list[Order]]:
        """Returns all agent's orders filtered by type if specified."""
        if agent_id not in self.agents:
            raise AgentDoesNotExist(f"Agent {agent_id} not found")

        orders: dict[str, list[Order]] = {
            "buy_orders": [],
            "sell_orders": []
        }

        if order_type in (OrderType.BUY, None):
            for order_list in self.buy_orders.values():
                orders["buy_orders"].extend([o for o in order_list if o.agent_id == agent_id])

        if order_type in (OrderType.SELL, None):
            for order_list in self.sell_orders.values():
                orders["sell_orders"].extend([o for o in order_list if o.agent_id == agent_id])

        return orders
    
    def _get_agent_by_id(self, agent_id: AgentID):
        """Returns an Agent instance by passed agent_id"""
        return self.agents.get(agent_id)

    def _get_existing_buy_order_id(self, agent_id: AgentID, market_hash_name: MarketHashName) -> OrderID | None:
        """Checks if Agent has existing Buy Order on passed Item and returns its ID"""
        return self.agent_buy_orders_idx.get(agent_id, {}).get(market_hash_name)

    def get_agent_sales(self, agent_id: AgentID) -> list[Sale]:
        """Return list of sales made by a specific Agent."""
        return self.agent_sales.get(agent_id, [])

    def get_agent_purchases(self, agent_id: AgentID) -> list[Sale]:
        """Return list of all purchases made by a specific Agent."""
        return self.agent_purchases.get(agent_id, [])

    def get_available_items(self, category_filter: ItemCategory | None = None) -> list[MarketItem]:
        """Returns a list of all listed items on the Market filtered by category."""
        return [
            item
            for market_hash_name, order_list in self.sell_orders.items()
            if order_list
            and ((item := self.items_map.get(market_hash_name)) is not None)
            and (category_filter is None or item.category == category_filter)
        ]

    def get_item_buy_orders(self, market_hash_name: MarketHashName) -> Sequence[Order]:
        """Return a list of Buy Orders for given `Item` in descending order."""
        return self.buy_orders.get(market_hash_name, [])

    def get_item_sell_orders(self, market_hash_name: MarketHashName) -> Sequence[Order]:
        """Return a list of Sell Orders for given `Item` in ascending order."""
        return self.sell_orders.get(market_hash_name, [])

    def create_order(
            self,
            order_type: OrderType,
            item: MarketItem,
            price: int,
            quantity: int,
            agent_id: AgentID
    ):
        order = Order(
            type=order_type,
            item=item,
            price=price,
            quantity=quantity,
            agent_id=agent_id,
            step=self.current_step
        )
        market_hash_name = order.item.market_hash_name
        if order_type == OrderType.BUY:
            self.buy_orders[market_hash_name].add(order)
            self.agent_buy_orders_idx[agent_id][market_hash_name] = order.id
        else:
            self.sell_orders[market_hash_name].add(order)
            self.items_map[market_hash_name] = item

    def cancel_buy_order(self, market_hash_name: MarketHashName, order_id: OrderID) -> None:
        """Cancel Buy Order for given item"""
        orders = self.buy_orders[market_hash_name]
        for order in orders:
            if order.id == order_id:
                self._remove_buy_order(order=order)
                return
        raise NoOrderMatch("Buy Order doesn't exist.")
    
    def _remove_buy_order(self, order: Order):
        """
        Removes buy order object directly from the list and cleans up agent_buy_orders_idx.
        """
        market_hash_name = order.item.market_hash_name
        self.buy_orders[market_hash_name].remove(order)

        agent_id = order.agent_id
        self.agent_buy_orders_idx[agent_id].pop(market_hash_name, None)

        if not self.agent_buy_orders_idx[agent_id]:
            del self.agent_buy_orders_idx[agent_id]

    def cancel_sell_order(self, market_hash_name: MarketHashName, order_id: OrderID) -> None:
        """Cancel sell order and return remaining items to Agent's inventory."""
        orders = self.sell_orders[market_hash_name]
        for order in orders:
            if order.id == order_id:
                self.agents[order.agent_id].add_item(item=order.item, quantity=order.quantity)
                orders.remove(order)
                return
        raise NoOrderMatch("Sell Order doesn't exist.")

    def _get_matching_sell_orders(
            self,
            item: MarketItem,
            price: int,
            exclude_agent_id: AgentID | None = None
    ) -> list[Order]:
        """
        Fetches Sell Orders for a given Item sorted from lowest to highest price.

        Optional: Excludes orders created by a specific agent preventing self-trading.
        """
        sell_orders = self.sell_orders[item.market_hash_name]
        dummy = Order(type=OrderType.SELL, item=item, price=price, quantity=0, agent_id=AgentID(-1), step=100_000_000)
        idx = sell_orders.bisect_right(dummy)
        return [
            order for order in sell_orders[:idx]
            if exclude_agent_id is None or order.agent_id != exclude_agent_id
        ]

    def _get_matching_buy_orders(
            self,
            item: MarketItem,
            price: int,
            exclude_agent_id: int | None = None
    ) -> list[Order]:
        """
        Fetches Buy Orders for a given Item sorted from earliest to latest by current_step.

        Optional: Excludes orders created by a specific agent preventing self-trading.
        """
        buy_orders = self.buy_orders[item.market_hash_name]
        dummy = Order(type=OrderType.BUY, item=item, price=price, quantity=0, agent_id=AgentID(-1), step=100_000_000)
        idx = buy_orders.bisect_left(dummy)
        matching_orders = [
            order for order in buy_orders[:idx]
            if exclude_agent_id is None or order.agent_id != exclude_agent_id
        ]
        return sorted(matching_orders, key=lambda o: o.step)

    def add_sale(
            self,
            item: MarketItem,
            price: int,
            fee: int,
            quantity: int,
            buyer_id: AgentID,
            seller_id: AgentID
    ):
        sale = Sale(
            item=item,
            price=price,
            total_fee=fee,
            quantity=quantity,
            buyer_id=buyer_id,
            seller_id=seller_id,
            step=self.current_step
        )
        self.sales_history[item.market_hash_name].append(sale)
        self.agent_purchases[buyer_id].append(sale)
        self.agent_sales[seller_id].append(sale)

    def buy(
        self,
        buyer_id: AgentID,
        item: MarketItem,
        price: int,
        quantity: int
    ):
        """
        Places buy order and matches with existing sell orders if possible.

        :returns: bought_quantity after successful purchase

        :raise DuplicateBuyOrder: If the Agent already has an active Buy Order for the same `MarketItem`.
        :raise InsufficientBalance: If the Agent does not have enough balance to buy the `MarketItem`.
        :raise ValueError: If buy order quantity is non-positive or less than 0.
        """

        if quantity <= 0:
            raise ValueError("Buy Order quantity can't be less or equal zero.")
        
        market_hash_name = item.market_hash_name    # attr look-up optimization
        buyer = self.agents.get(buyer_id)
        if not buyer:
            raise AgentDoesNotExist(f"Buyer Agent {buyer_id} not found.")

        # Check for existing BuyOrder and return its ID
        order_id = self._get_existing_buy_order_id(agent_id=buyer_id, market_hash_name=market_hash_name)
        if order_id:
            raise DuplicateBuyOrder(f"Agent can place only one Buy Order on the item!", order_id)

        if buyer.balance < price * quantity:
            raise InsufficientBalance("Agent doesn't have enough balance for this Order!")

        matching_sell_orders = self._get_matching_sell_orders(
            item=item,
            price=price,
            exclude_agent_id=buyer_id
        )
        remaining_quantity = quantity

        for sell_order in matching_sell_orders:
            if remaining_quantity == 0:
                break

            trade_quantity = min(sell_order.quantity, remaining_quantity)

            seller = self.agents.get(sell_order.agent_id)
            if not seller:
                raise AgentDoesNotExist("Agent not found")
            
            # Ensure this sale doesn't exceed seller max allowed balance
            # if True pick maximum allowed quantity for this sale
            sell_price = sell_order.price   # attr look-up optimization
            trade_quantity = self._max_receivable_quantity(
                seller_balance=seller.balance,
                price=sell_price,
                desired_qty=trade_quantity
            )
            if trade_quantity == 0:
                continue
            
            order_total = sell_price * trade_quantity
            fee = self.calculate_fee(order_total)

            # Add up money to the seller and subtract from buyer
            seller.balance += order_total - fee
            buyer.balance -= order_total

            # Add BOUGHT ITEM to the buyer's inventory
            buyer.add_item(
                item=sell_order.item,
                quantity=trade_quantity,
                unlock_step=self.calculate_unlock_step(is_trade_lock=self.lock_on_purchase)
            )

            # Add a BOUGHT ITEM record to sales history
            self.add_sale(
                item=sell_order.item,
                price=sell_price,
                fee=fee,
                quantity=trade_quantity,
                buyer_id=buyer_id,
                seller_id=sell_order.agent_id
            )

            # Update order and remaining quantity
            sell_order.quantity -= trade_quantity
            if sell_order.quantity == 0:
                self.sell_orders[market_hash_name].remove(sell_order)
            remaining_quantity -= trade_quantity

        if remaining_quantity > 0:
            self.create_order(OrderType.BUY, item, price, remaining_quantity, buyer_id)

        return quantity - remaining_quantity

    def sell(
            self,
            seller_id: AgentID,
            item: MarketItem,
            sell_price: int,
            quantity: int
    ):
        """
        Place sell order and match it with existing buy orders if possible.

        :raise AgentDoesNotExist: If the Agent with the given ID does not exist in the system.
        :raise NotEnoughItems: If the Agent does not have enough items in its inventory to sell.
        """
        if quantity <= 0:
            raise ValueError("Quantity can't be less or equal zero, while listing items on sale.")

        market_hash_name = item.market_hash_name    # attr look-up optimization
        seller = self._get_agent_by_id(seller_id)
        if not seller:
            raise AgentDoesNotExist("Seller not found.")
        seller.remove_item(market_hash_name, quantity)

        matching_buy_orders = self._get_matching_buy_orders(
            item=item,
            price=sell_price,
            exclude_agent_id=seller_id
        )
        remaining_quantity = quantity

        for buy_order in matching_buy_orders:
            if remaining_quantity == 0:
                break

            sell_quantity = min(buy_order.quantity, remaining_quantity)
            buyer = self._get_agent_by_id(buy_order.agent_id)
            if not buyer:
                raise AgentDoesNotExist("Agent not found")

            # Check if Buyer can afford this purchase, if not buy as many as possible
            affordable_quantity = buyer.balance // sell_price
            if affordable_quantity == 0:
                self._remove_buy_order(order=buy_order)
                continue    # buyer can't afford this purchase

            # Check if Seller can sell these items and not exceed max balance
            trade_quantity = self._max_receivable_quantity(
                seller_balance=seller.balance,
                price=sell_price,
                desired_qty=min(sell_quantity, affordable_quantity)
            )
            if trade_quantity == 0:
                self._remove_buy_order(order=buy_order)
                break   # seller exceeded max balance and can't sell items anymore

            order_total = sell_price * trade_quantity
            fee = self.calculate_fee(order_total)

            seller.balance += order_total - fee
            buyer.balance -= order_total

            # Add item to the buyer inventory
            buyer.add_item(
                item=item,
                quantity=trade_quantity,
                unlock_step=self.calculate_unlock_step(is_trade_lock=self.lock_on_purchase)
            )

            # Add sale history
            self.add_sale(
                item=item,
                price=sell_price,
                fee=fee,
                quantity=trade_quantity,
                buyer_id=buyer.id,
                seller_id=seller_id
            )
            
            # Purchase as many as possible
            buy_order.quantity -= trade_quantity
            if buy_order.quantity == 0:
                self._remove_buy_order(buy_order)

            remaining_quantity -= trade_quantity

        # list unsold items, create sell order with remaining amount
        if remaining_quantity > 0:
            self.create_order(
                order_type=OrderType.SELL,
                item=item,
                price=sell_price,
                quantity=remaining_quantity,
                agent_id=seller_id
            )
