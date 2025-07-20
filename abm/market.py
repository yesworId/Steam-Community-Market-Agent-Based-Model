import math
from collections import defaultdict

from .models import *
from .exceptions import *
from .metrics import calculate_median_price
from .constants import DEFAULT_BASE_PRICE


class Market:
    """
    Simulation environment with its parameters and methods for Agents to interact with.

    :param market_fee: Percentage 'Market' charges on any sale.
    :param steps_per_day: Number of simulation steps per day
    :param trade_lock_period: Duration of trade restriction for newly acquired items (in simulation days).
    """
    def __init__(
            self,
            agents: list = None,
            market_fee: float = 0.15,
            steps_per_day: int = 1000,
            trade_lock_period: int = 0,
            current_step: int = 0
    ):
        from .agents import Agent as Agent

        self.market_fee: float = market_fee
        self.steps_per_day = steps_per_day
        # TODO: Implement trade lock feature in simulation
        self.trade_lock_period = trade_lock_period
        self.current_step = current_step

        self.agents: dict[int, Agent] = {}
        self.buy_orders: dict[str, list[Order]] = {}
        self.sell_orders: dict[str, list[Order]] = {}

        self.sales_history: defaultdict[str, list[Sale]] = defaultdict(list)

        if agents:
            self.add_agents(agents)

    def add_agents(self, agents: list):
        for agent in agents:
            if agent.id in self.agents:
                raise ValueError(f"Duplicate agent_id detected: {agent.id}")
            self.agents[agent.id] = agent
            agent.market = self

    def get_median_price(self, item_name, number_of_sales: int = 30):
        return calculate_median_price(self.sales_history, item_name, number_of_sales)

    def get_base_price(self, item_name, number_of_sales: int = 30):
        median_price = calculate_median_price(self.sales_history, item_name, number_of_sales)
        if median_price > 0:
            return median_price

        buy_orders = self.get_item_buy_orders(item_name)
        if buy_orders:
            return buy_orders[0].price

        return DEFAULT_BASE_PRICE

    def get_item_recent_sales(self, item_name: str, number_of_sales: int = 50) -> list[Sale]:
        """Returns list of passed number of recent sales for item_name"""
        item_sales = self.sales_history.get(item_name, [])
        if not item_sales:
            return []
        return item_sales[-number_of_sales:]

    def get_agent_orders(self, agent_id: int, order_type: OrderType = None):
        """Returns agent's orders filtered by type if specified"""
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

    def _get_existing_buy_order_id(self, agent_id: int, item_name: str):
        """Checks if Agent has existing Buy Order on passed item and returns its ID"""
        orders = self.buy_orders.get(item_name, [])
        for order in orders:
            if order.agent_id == agent_id:
                return order.id
        return None

    def get_agent_sales(self, agent_id: int):
        """Returns list of Agent sales history"""
        if agent_id not in self.agents:
            raise AgentDoesNotExist(f"Agent {agent_id} not found")

        agent_sales = []
        for item_sales in self.sales_history.values():
            for sale in item_sales:
                if sale.seller_id == agent_id:
                    agent_sales.append(sale)
        return agent_sales

    def get_agent_purchases(self, agent_id: int):
        """Returns list of all Agent purchases"""
        if agent_id not in self.agents:
            raise AgentDoesNotExist(f"Agent {agent_id} not found")

        agent_purchases = []
        for item_sales in self.sales_history.values():
            for sale in item_sales:
                if sale.buyer_id == agent_id:
                    agent_purchases.append(sale)
        return agent_purchases

    def get_available_items(self):
        """Returns all items currently being sold on the Market."""
        return list(self.sell_orders.keys())

    def get_item_buy_orders(self, item_name: str):
        """Get Buy Orders for an item sorted by price from the highest and current_step"""
        return sorted(
            self.buy_orders.get(item_name, []),
            key=lambda order: (-order.price, order.step)
        )

    def get_item_sell_orders(self, item_name: str):
        """Get Sell Orders for an item sorted by price from the lowest and current_step"""
        return sorted(
            self.sell_orders.get(item_name, []),
            key=lambda order: (order.price, order.step)
        )

    def create_order(
            self,
            order_type: OrderType,
            item_name: str,
            price: float,
            quantity: int,
            agent_id: int
    ):
        order = Order(
            type=order_type,
            item_name=item_name,
            price=price,
            quantity=quantity,
            agent_id=agent_id,
            step=self.current_step
        )
        if order_type == OrderType.BUY:
            self.buy_orders.setdefault(item_name, []).append(order)
        else:
            self.sell_orders.setdefault(item_name, []).append(order)

    def cancel_buy_order(self, item_name: str, order_id: int):
        """Cancel Buy Order for given item"""
        orders = self.buy_orders[item_name]
        for order in orders:
            if order.id == order_id:
                orders.remove(order)
                return
        raise NoOrderMatch("Buy Order doesn't exist.")

    def cancel_sell_order(self, item_name: str, order_id: int):
        """Cancel sell order and return remaining items to Agent's inventory."""
        orders = self.sell_orders[item_name]
        for order in orders:
            if order.id == order_id:
                orders.remove(order)
                self.agents[order.agent_id].add_item(order.item_name, order.quantity)
                return
        raise NoOrderMatch("Sell Order doesn't exist.")

    def _get_matching_sell_orders(
            self,
            item_name: str,
            price: float,
            exclude_agent_id: int | None = None
    ):
        """
        Fetches Sell Orders for a given Item sorted from lowest to highest price.

        Optional: Excludes orders created by a specific agent preventing self-trading.
        """

        return sorted(
            [
                order for order in self.sell_orders.get(item_name, [])
                if order.price <= price and (exclude_agent_id is None or order.agent_id != exclude_agent_id)
            ], key=lambda order: (order.price, order.step)
        )

    def _get_matching_buy_orders(
            self,
            item_name: str,
            price: float,
            exclude_agent_id: int | None = None
    ):
        """
        Fetches Buy Orders for a given Item sorted from earliest to latest by current_step.

        Optional: Excludes orders created by a specific agent preventing self-trading.
        """

        return sorted(
            [
                order for order in self.buy_orders.get(item_name, [])
                if order.price >= price and (exclude_agent_id is None or order.agent_id != exclude_agent_id)
            ], key=lambda order: (order.step, -order.price)
        )

    def add_sale(
            self,
            item_name: str,
            price: float,
            fee: float,
            quantity: int,
            buyer_id: int,
            seller_id: int
    ):
        sale = Sale(
            item_name=item_name,
            price=price,
            fee=fee,
            quantity=quantity,
            buyer_id=buyer_id,
            seller_id=seller_id,
            step=self.current_step
        )
        self.sales_history[item_name].append(sale)

    def _get_agent_by_id(self, agent_id: int):
        """Returns an Agent instance by passed agent_id"""
        return self.agents.get(agent_id)

    def get_agent_balance(self, agent_id: int) -> float:
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

    def has_item(self, agent_id: int, item_name: str, quantity: int) -> bool:
        """Checks if Agent has enough number of items"""
        agent = self._get_agent_by_id(agent_id)
        return agent and agent.inventory.get(item_name, 0) >= quantity

    def add_item_to_inventory(self, agent_id: int, item_name: str, quantity: int):
        """Adds item to inventory of an Agent, updates quantity if item already exists."""
        agent = self._get_agent_by_id(agent_id)
        if not agent:
            raise AgentDoesNotExist("Agent not found")
        agent.add_item(item_name, quantity)

    def remove_item_from_inventory(self, agent_id: int, item_name: str, quantity: int):
        """Removes item from Agent's inventory"""
        agent = self._get_agent_by_id(agent_id)
        if not agent:
            raise AgentDoesNotExist("Agent not found")
        agent.remove_item(item_name, quantity)

    def buy(
        self,
        buyer_id: int,
        item_name: str,
        order_price: float,
        quantity: int
    ):
        """
        Places buy order and matches with existing sell orders if possible.

        :returns: remaining_balance and bought_quantity after successful purchase

        :raise DuplicateBuyOrder: If the Agent already has an active Buy Order for the same Item.
        :raise InsufficientBalance: If the Agent does not have enough balance to buy the Item.
        """
        order_price = math.floor(order_price * 100) / 100.0

        buyer = self.agents.get(buyer_id)
        if not buyer:
            raise AgentDoesNotExist(f"Buyer Agent {buyer_id} not found.")

        # Return order_id of existing order
        order_id = self._get_existing_buy_order_id(buyer_id, item_name)
        if order_id:
            raise DuplicateBuyOrder(f"Agent can place only one Buy Order on the item!", order_id)

        if buyer.balance < order_price * quantity:
            raise InsufficientBalance("Agent doesn't have enough balance for this Order!")

        sell_orders = self._get_matching_sell_orders(
            item_name,
            order_price,
            exclude_agent_id=buyer_id
        )
        remaining_quantity = quantity

        for sell_order in sell_orders:
            if remaining_quantity == 0:
                break

            trade_quantity = min(sell_order.quantity, remaining_quantity)
            order_total = sell_order.price * trade_quantity
            fee = round(order_total * self.market_fee, 2)

            # Add up money to the seller and subtract from buyer
            seller = self.agents.get(sell_order.agent_id)
            seller.balance += order_total - fee
            buyer.balance -= order_total

            # Add item to the buyer inventory
            self.add_item_to_inventory(buyer_id, item_name, trade_quantity)

            # Add sale history
            self.add_sale(item_name, sell_order.price, fee, trade_quantity, buyer_id, sell_order.agent_id)

            # Update order and remaining quantity
            sell_order.quantity -= trade_quantity
            if sell_order.quantity == 0:
                self.sell_orders[item_name].remove(sell_order)
            remaining_quantity -= trade_quantity

        if remaining_quantity > 0:
            self.create_order(OrderType.BUY, item_name, order_price, remaining_quantity, buyer_id)

        return {
            "remaining_balance": buyer.balance,
            "bought_quantity": quantity - remaining_quantity,
        }

    def sell(
            self,
            seller_id: int,
            item_name: str,
            order_price: float,
            quantity: int
    ):
        """
        Place sell order and match it with existing buy orders if possible.

        :raise AgentDoesNotExist: If the Agent with the given ID does not exist in the system.
        :raise NotEnoughItems: If the Agent does not have enough items in its inventory to sell.
        """
        order_price = math.floor(order_price * 100) / 100.0

        seller = self._get_agent_by_id(seller_id)
        if not seller:
            raise AgentDoesNotExist("Seller not found.")

        if not self.has_item(seller_id, item_name, quantity):
            raise NotEnoughItems("Agent doesn't have enough items in his inventory.")
        self.remove_item_from_inventory(seller_id, item_name, quantity)

        matching_buy_orders = self._get_matching_buy_orders(item_name, order_price, seller_id)
        remaining_quantity = quantity

        for buy_order in matching_buy_orders:
            if remaining_quantity == 0:
                break

            trade_quantity = min(buy_order.quantity, remaining_quantity)
            order_total = order_price * trade_quantity
            fee = round(order_price * self.market_fee, 2)

            buyer = self._get_agent_by_id(buy_order.agent_id)

            # Check if Buyer can afford this purchase, if not buy as many as possible
            if buyer.balance < order_total:
                max_affordable_quantity = int(buyer.balance // buy_order.price)
                if max_affordable_quantity == 0:
                    self.cancel_buy_order(item_name=item_name, order_id=buy_order.id)
                    continue

                # Purchase as many as possible
                order_total = buy_order.price * max_affordable_quantity
                fee = round(order_total * self.market_fee, 2)

            seller.balance += order_total - fee
            buyer.balance -= order_total

            # Add item to the buyer inventory
            self.add_item_to_inventory(buyer.id, item_name, trade_quantity)

            # Add sale history
            self.add_sale(item_name, buy_order.price, fee, trade_quantity, buyer.id, seller_id)

            buy_order.quantity -= trade_quantity
            if buy_order.quantity == 0:
                self.buy_orders[item_name].remove(buy_order)

            remaining_quantity -= trade_quantity

        if remaining_quantity > 0:
            self.create_order(OrderType.SELL, item_name, order_price, remaining_quantity, seller_id)
