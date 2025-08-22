from collections import defaultdict
from sortedcontainers import SortedList

from .models import MarketHashName, OrderType, ItemCategory, MarketItem, Order, Sale
from .metrics import calculate_median_price
from .constants import DEFAULT_BASE_PRICE
from .exceptions import (
    NotEnoughItems,
    AgentDoesNotExist,
    InsufficientBalance,
    NoOrderMatch,
    DuplicateBuyOrder
)


class Market:
    """
    Simulation environment with its parameters and methods for Agents to interact with.

    :param market_fee: Percentage 'Market' charges on any sale.
    :param steps_per_day: Number of simulation steps per simulated day.
    :param trade_lock_period: Duration of trade restriction for newly acquired items (in simulation days).
    :param current_step: Counter of simulation steps.
    """
    def __init__(
            self,
            agents: list = None,
            market_fee: float = 0.15,
            steps_per_day: int = 1000,
            trade_lock_period: int = 7,
            current_step: int = 0
    ):
        from .agents import Agent as Agent

        self.market_fee = market_fee
        self.steps_per_day = steps_per_day
        self.trade_lock_period = trade_lock_period
        self.current_step = current_step

        self.agents: dict[int, Agent] = {}
        self.buy_orders: defaultdict[MarketHashName, SortedList[Order]] = defaultdict(
            lambda: SortedList(key=lambda o: (-o.price, o.step))
        )
        self.sell_orders: defaultdict[MarketHashName, SortedList[Order]] = defaultdict(
            lambda: SortedList(key=lambda o: (o.price, o.step))
        )

        self.items_map: dict[MarketHashName, MarketItem] = {}
        self.sales_history: defaultdict[MarketHashName, list[Sale]] = defaultdict(list)

        if agents:
            self.add_agents(agents)

    def add_agents(self, agents: list):
        for agent in agents:
            if agent.id in self.agents:
                raise ValueError(f"Duplicate agent_id detected: {agent.id}")
            self.agents[agent.id] = agent
            agent.market = self

    def calculate_unlock_step(self) -> int:
        """Calculates unlock step based on a trade lock period."""
        return self.current_step + self.trade_lock_period * self.steps_per_day

    def get_median_price(self, market_hash_name: str | MarketHashName, number_of_sales: int = 50) -> int:
        return calculate_median_price(self.sales_history, market_hash_name, number_of_sales)

    def get_base_price(self, market_hash_name: str | MarketHashName, number_of_sales: int = 50) -> int:
        median_price = calculate_median_price(self.sales_history, market_hash_name, number_of_sales)
        if median_price > 0:
            return median_price

        buy_orders = self.get_item_buy_orders(market_hash_name)
        if buy_orders:
            return buy_orders[0].price

        return DEFAULT_BASE_PRICE

    def get_item_recent_sales(self, market_hash_name: str | MarketHashName, number_of_sales: int = 50) -> list[Sale]:
        """Returns a list of passed number of recent sales for market_hash_name."""
        item_sales = self.sales_history.get(market_hash_name, [])
        if not item_sales:
            return []
        return item_sales[-number_of_sales:]

    def get_agent_orders(self, agent_id: int, order_type: OrderType = None):
        """Returns all agent's orders filtered by type if specified."""
        if agent_id not in self.agents:
            raise AgentDoesNotExist(f"Agent {agent_id} not found")

        orders = {
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

    def _get_existing_buy_order_id(self, agent_id: int, market_hash_name: str | MarketHashName):
        """Checks if Agent has existing Buy Order on passed Item and returns its ID"""
        orders = self.buy_orders.get(market_hash_name, [])
        for order in orders:
            if order.agent_id == agent_id:
                return order.id
        return None

    def get_agent_sales(self, agent_id: int):
        """Returns a list of Agent's sales history."""
        if agent_id not in self.agents:
            raise AgentDoesNotExist(f"Agent {agent_id} not found")

        return [
            sale
            for item_sales in self.sales_history.values()
            for sale in item_sales
            if sale.seller_id == agent_id
        ]

    def get_agent_purchases(self, agent_id: int):
        """Return a list of all purchases made by the Agent."""
        if agent_id not in self.agents:
            raise AgentDoesNotExist(f"Agent {agent_id} not found")

        return [
            sale
            for item_sales in self.sales_history.values()
            for sale in item_sales
            if sale.buyer_id == agent_id
        ]

    def get_available_items(self, category_filter: ItemCategory = None) -> list[MarketItem]:
        """Returns a list of all listed items on the Market filtered by category."""
        return [
            item
            for market_hash_name in self.sell_orders
            if ((item := self.items_map.get(market_hash_name)) is not None)
            and (category_filter is None or item.category == category_filter)
        ]

    def get_item_buy_orders(self, market_hash_name: str | MarketHashName):
        """Return a list of Buy Orders for given `Item` in descending order."""
        return self.buy_orders.get(market_hash_name, [])

    def get_item_sell_orders(self, market_hash_name: str | MarketHashName):
        """Return a list of Sell Orders for given `Item` in ascending order."""
        return self.sell_orders.get(market_hash_name, [])

    def create_order(
            self,
            order_type: OrderType,
            item: MarketItem,
            price: int,
            quantity: int,
            agent_id: int
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
        else:
            self.sell_orders[market_hash_name].add(order)
            self.items_map[market_hash_name] = item

    def cancel_buy_order(self, market_hash_name: str | MarketHashName, order_id: int):
        """Cancel Buy Order for given item"""
        orders = self.buy_orders[market_hash_name]
        for order in orders:
            if order.id == order_id:
                orders.remove(order)
                return
        raise NoOrderMatch("Buy Order doesn't exist.")

    def cancel_sell_order(self, market_hash_name: str | MarketHashName, order_id: int):
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
            exclude_agent_id: int | None = None
    ) -> list[Order]:
        """
        Fetches Sell Orders for a given Item sorted from lowest to highest price.

        Optional: Excludes orders created by a specific agent preventing self-trading.
        """

        sell_orders = self.sell_orders.get(item.market_hash_name, ())
        dummy = Order(type=OrderType.SELL, item=item, price=price, quantity=0, agent_id=-1, step=100_000_000)
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
        dummy = Order(type=OrderType.BUY, item=item, price=price, quantity=0, agent_id=-1, step=100_000_000)
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
            buyer_id: int,
            seller_id: int
    ):
        sale = Sale(
            item=item,
            price=price,
            fee=fee,
            quantity=quantity,
            buyer_id=buyer_id,
            seller_id=seller_id,
            step=self.current_step
        )
        self.sales_history[item.market_hash_name].append(sale)

    def _get_agent_by_id(self, agent_id: int):
        """Returns an Agent instance by passed agent_id"""
        return self.agents.get(agent_id)

    def get_agent_balance(self, agent_id: int) -> int:
        """Returns balance of an Agent by passed agent_id"""
        agent = self._get_agent_by_id(agent_id)
        if not agent:
            raise AgentDoesNotExist("Agent not found")
        return agent.balance

    def get_agent_inventory(self, agent_id: int):
        """Returns an instance of the Agent's Inventory"""
        agent = self._get_agent_by_id(agent_id)
        if not agent:
            raise AgentDoesNotExist("Agent not found")
        return dict(agent.inventory)

    def has_item(self, agent_id: int, item: MarketItem, quantity: int) -> bool:
        """Checks if Agent has enough number of items"""
        agent = self._get_agent_by_id(agent_id)
        if not agent:
            raise AgentDoesNotExist("Agent not found")
        return sum(i.quantity for i in agent.get_unlocked_items(item)) >= quantity

    def add_item_to_inventory(self, agent_id: int, item: MarketItem, quantity: int):
        """Adds item to inventory of an Agent, updates quantity if item already exists."""
        agent = self._get_agent_by_id(agent_id)
        if not agent:
            raise AgentDoesNotExist("Agent not found")

        agent.add_item(
            item=item,
            quantity=quantity,
            unlock_step=self.calculate_unlock_step()
        )

    def remove_item_from_inventory(self, agent_id: int, item: MarketItem, quantity: int):
        """Removes item from Agent's inventory"""
        agent = self._get_agent_by_id(agent_id)
        if not agent:
            raise AgentDoesNotExist("Agent not found")
        agent.remove_item(item, quantity)

    def buy(
        self,
        buyer_id: int,
        item: MarketItem,
        price: int,
        quantity: int
    ):
        """
        Places buy order and matches with existing sell orders if possible.

        :returns: remaining_balance and bought_quantity after successful purchase

        :raise DuplicateBuyOrder: If the Agent already has an active Buy Order for the same Item.
        :raise InsufficientBalance: If the Agent does not have enough balance to buy the Item.
        """

        buyer = self.agents.get(buyer_id)
        if not buyer:
            raise AgentDoesNotExist(f"Buyer Agent {buyer_id} not found.")

        # Return order_id of existing order
        order_id = self._get_existing_buy_order_id(agent_id=buyer_id, market_hash_name=item.market_hash_name)
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
            order_total = sell_order.price * trade_quantity
            fee = int(order_total * self.market_fee)

            # Add up money to the seller and subtract from buyer
            seller = self.agents.get(sell_order.agent_id)
            seller.balance += order_total - fee
            buyer.balance -= order_total

            # Add BOUGHT ITEM to the buyer's inventory
            self.add_item_to_inventory(buyer_id, sell_order.item, trade_quantity)

            # Add a BOUGHT ITEM record to sales history
            self.add_sale(
                item=sell_order.item,
                price=sell_order.price,
                fee=fee,
                quantity=trade_quantity,
                buyer_id=buyer_id,
                seller_id=sell_order.agent_id
            )

            # Update order and remaining quantity
            sell_order.quantity -= trade_quantity
            if sell_order.quantity == 0:
                self.sell_orders[item.market_hash_name].remove(sell_order)
            remaining_quantity -= trade_quantity

        if remaining_quantity > 0:
            self.create_order(OrderType.BUY, item, price, remaining_quantity, buyer_id)

        return {
            "remaining_balance": buyer.balance,
            "bought_quantity": quantity - remaining_quantity,
        }

    def sell(
            self,
            seller_id: int,
            item: MarketItem,
            order_price: int,
            quantity: int
    ):
        """
        Place sell order and match it with existing buy orders if possible.

        :raise AgentDoesNotExist: If the Agent with the given ID does not exist in the system.
        :raise NotEnoughItems: If the Agent does not have enough items in its inventory to sell.
        """

        seller = self._get_agent_by_id(seller_id)
        if not seller:
            raise AgentDoesNotExist("Seller not found.")

        if not self.has_item(seller_id, item, quantity):
            raise NotEnoughItems("Agent doesn't have enough items in his inventory.")
        self.remove_item_from_inventory(seller_id, item, quantity)

        matching_buy_orders = self._get_matching_buy_orders(
            item=item,
            price=order_price,
            exclude_agent_id=seller_id
        )
        remaining_quantity = quantity

        for buy_order in matching_buy_orders:
            if remaining_quantity == 0:
                break

            trade_quantity = min(buy_order.quantity, remaining_quantity)
            order_total = order_price * trade_quantity
            fee = int(order_total * self.market_fee)

            buyer = self._get_agent_by_id(buy_order.agent_id)

            # Check if Buyer can afford this purchase, if not buy as many as possible
            if buyer.balance < order_total:
                max_affordable_quantity = int(buyer.balance // buy_order.price)
                if max_affordable_quantity == 0:
                    self.cancel_buy_order(market_hash_name=item.market_hash_name, order_id=buy_order.id)
                    continue

                # Purchase as many as possible
                order_total = buy_order.price * max_affordable_quantity
                fee = int(order_total * self.market_fee)

            seller.balance += order_total - fee
            buyer.balance -= order_total

            # Add item to the buyer inventory
            self.add_item_to_inventory(buyer.id, item, trade_quantity)

            # Add sale history
            self.add_sale(
                item=item,
                price=buy_order.price,
                fee=fee,
                quantity=trade_quantity,
                buyer_id=buyer.id,
                seller_id=seller_id
            )

            buy_order.quantity -= trade_quantity
            if buy_order.quantity == 0:
                self.buy_orders[item.market_hash_name].remove(buy_order)

            remaining_quantity -= trade_quantity

        if remaining_quantity > 0:
            self.create_order(
                order_type=OrderType.SELL,
                item=item,
                price=order_price,
                quantity=remaining_quantity,
                agent_id=seller_id
            )
