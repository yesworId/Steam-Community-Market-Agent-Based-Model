import random
import statistics
from abc import ABC, abstractmethod

from .market import Market
from .models import AgentType
from .exceptions import InsufficientBalance, NotEnoughItems, DuplicateBuyOrder
from .constants import ONE_CENT, ONE_DOLLAR, MIN_PRICE, MAX_DISCOUNT, IMPULSIVITY_UNDERESTIMATION


class Agent(ABC):
    """
    Base abstract Agent class, which methods and parameters are common to every Agent.

    :param agent_id: Unique Agent identifier
    :param market: 'Market' instance, every Agent is connected to Environment
    :param agent_type: Describes type of the Agent
    :param balance: Amount of money Agent has (between 0 and 2000)
    :param impulsivity: Parameter indicating tendency of an Agent to act impulsively
    """
    __slots__ = ("id", "market", "type", "balance", "impulsivity", "inventory")
    # TODO: ADD BASE PARAMETER FOR EACH AGENT ('is_play_game') with values True/False

    def __init__(
            self,
            agent_id: int,
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
        self.inventory: dict[str, int] = {}

    @abstractmethod
    def act(self):
        raise NotImplementedError("This method is implemented in sub-classes")

    def add_balance(self, amount: int = 0):
        if amount > 0:
            self.balance += amount

    def add_item(self, item_name: str, quantity: int = 1):
        self.inventory[item_name] = self.inventory.get(item_name, 0) + quantity

    def remove_item(self, item_name: str, quantity: int):
        if self.inventory.get(item_name, 0) < quantity:
            raise NotEnoughItems("Not enough items in inventory")

        self.inventory[item_name] -= quantity
        if self.inventory[item_name] == 0:
            del self.inventory[item_name]

    def _panic_sell(self):
        """Impulsive decision, agent tries to sell all of his items"""
        for item_name, quantity in list(self.inventory.items()):
            buy_orders = self.market.get_item_buy_orders(item_name)
            if not buy_orders:
                # Pick fair price to sell items, how to do it?
                continue

            highest_price = buy_orders[0].price
            price = int(random.uniform(highest_price * 0.7, highest_price))
            self.market.sell(self.id, item_name, max(price, MIN_PRICE), quantity)

    def open_container(self, item_name, quantity=1):
        """
        Simulates opening a container.
        Removes container from the Agent's inventory.
        (Optional) Rewards Agent with an Item Drop added to his balance based on the rarity probability
        """
        try:
            self.remove_item(item_name, quantity)
            # TODO: Add-up reward value to Agent Balance based on Item rarity
            # reward = calculate_container_reward(item_name, quantity)
            # self.add_balance(reward)
        except NotEnoughItems:
            print(f"Agent {self.id} doesn't have enough '{item_name}' containers to open!")

    def is_impulsive(self) -> bool:
        return random.random() < self.impulsivity / IMPULSIVITY_UNDERESTIMATION


class NoviceAgent(Agent):
    """
    Simple, inexperienced-casual user, who adds noise and does act without logical strategy.
    """
    __slots__ = ()

    def __init__(self, agent_id, market, agent_type, balance, impulsivity):
        super().__init__(agent_id, market, agent_type, balance, impulsivity)

    def act(self):
        """
        Imitates the behaviour of Novice Agent.

        He either buys or sells. There is a chance of panic sell happening based on Agent's impulsivity.
        """
        action = random.choice(['buy', 'sell'])
        if action == 'buy':
            self.buy_container()
        else:
            self.sell_items()

    def buy_container(self):
        """
        Imitates the process of purchasing random number of containers he can afford, then to open.
        """

        # Maybe change to weighted choice based on popularity of items?
        available_items = self.market.get_available_items()
        if not available_items:
            return

        item_name = random.choice(available_items)
        sell_orders = self.market.get_item_sell_orders(item_name)
        if not sell_orders:
            # Place Buy Order then?
            return

        price = 0
        total_spent = 0
        max_affordable_quantity = 0

        # I could try to refactor this loop to buy each listing individually
        # Yet for optimization purposes I pick max price to buy items in a single call of 'buy()' method
        for sell_order in sell_orders:
            affordable_quantity = int((self.balance - total_spent) // sell_order.price)
            if affordable_quantity <= 0:
                break

            quantity_to_buy = min(sell_order.quantity, affordable_quantity)
            price = sell_order.price
            total_spent += price * quantity_to_buy
            max_affordable_quantity += quantity_to_buy

        if max_affordable_quantity == 0:
            return

        desired_quantity = random.randint(1, max_affordable_quantity)

        # TODO: REFACTOR!
        for attempt in range(3):
            try:
                result = self.market.buy(self.id, item_name, price, desired_quantity)
                bought_quantity = result['bought_quantity']
                # Possible unnatural behaviour, when buyer couldn't buy the item, so market placed buy order
                # but still he wanted to open a container.
                # Afterward buy order fulfilled and items are delivered to the buyer's inventory.
                # Then he calls sell method and just sells items he wanted to open.
                if bought_quantity > 0:
                    self.open_container(item_name, bought_quantity)
                break
            except InsufficientBalance:
                # self.add_balance(amount=)
                self.sell_items()
            except DuplicateBuyOrder as ex:
                self.market.cancel_buy_order(item_name=item_name, order_id=ex.order_id)

    def sell_items(self):
        """
        Imitates a regular or impulsive sell behaviour.
        Agent either slightly undercuts the lowest sell listing or dumps items to the highest Buy Order.
        """
        if not self.inventory:
            return

        if self.is_impulsive():
            return self._panic_sell()

        # Regular strategy: Agent tries to sell items little cheaper than the lowest listing
        item_name = random.choice(list(self.inventory.keys()))
        quantity = random.randint(1, self.inventory[item_name])

        sell_orders = self.market.get_item_sell_orders(item_name)
        if sell_orders:
            lowest_sell_order = sell_orders[0].price
            price = lowest_sell_order - random.randint(ONE_CENT, ONE_DOLLAR)
        else:
            # Pick base price
            base_price = self.market.get_base_price(item_name)
            price = int(base_price * random.uniform(0.95, 1.05))

        self.market.sell(self.id, item_name, max(price, MIN_PRICE), quantity)


class TraderAgent(Agent):
    """
    More complex agent, which operates for the profits.

    TRIES TO BUY LOWER THAN THE MARKET PRICE, items that can be higher in the near future due to the past trends.
    EXAMPLE: cases are more expensive at the end of the week before the weekly drop rate re-stock / change

    :param risk_tolerance: Chance to take a risk decision
    """
    __slots__ = ("risk_tolerance", "entry_prices")

    def __init__(self, agent_id, market, agent_type, balance, impulsivity, risk_tolerance):
        super().__init__(agent_id, market, agent_type, balance, impulsivity)
        self.risk_tolerance = risk_tolerance
        # TODO: Add params such as: min_profit_margin, spread_threshold etc!

        self.entry_prices = {}

    def act(self):
        if self.inventory and self.is_impulsive():
            return self._panic_sell()

        # self.try_sell_for_profit()

        # self.try_buy_for_profit()

        # For each selling item analyze its trend and spread
        for item_name in self.market.get_available_items():
            recent_sales = self.market.get_item_recent_sales(item_name, number_of_sales=250)
            if len(recent_sales) < 5:
                continue

            prices = [sale.price for sale in recent_sales]

            # Trend analysis
            mid = len(prices) // 2
            avg_first = statistics.mean(prices[:mid])
            avg_second = statistics.mean(prices[mid:])
            trend_up = avg_second > avg_first

            min_price = min(prices)
            max_price = max(prices)
            spread = (max_price - min_price) * (1 - self.market.market_fee)

            # Try to sell items for profit
            if item_name in self.inventory and self.inventory[item_name] > 0:
                buy_orders = self.market.get_item_buy_orders(item_name)
                if buy_orders:
                    highest_price = buy_orders[0].price
                    profitable = False
                    for entry_price in self.entry_prices.get(item_name, []):
                        desired_price = entry_price * (1 + self.risk_tolerance) / (1 - self.market.market_fee)
                        if highest_price >= desired_price:
                            quantity = self.inventory[item_name]
                            try:
                                self.market.sell(self.id, item_name, highest_price, quantity)
                                self.entry_prices[item_name] = []
                                profitable = True
                            except Exception as ex:
                                print(f"Trader {self.id} failed to sell {item_name}: {ex}")
                            break
                    if profitable:
                        continue

            avg_price = statistics.mean(prices)
            buy_signal = False
            sell_orders = self.market.get_item_sell_orders(item_name)
            if sell_orders:
                best_ask = sell_orders[0].price
                # In case of bullish trend and lowest listing price is in range of historical minimum price
                # for observed data, multiplied by an eager of a risk decision
                is_desired_price = best_ask <= min_price * (1 + self.risk_tolerance)
                if trend_up and is_desired_price:
                    buy_signal = True

                elif spread >= avg_price * 0.1 and is_desired_price:
                    buy_signal = True

                if buy_signal:
                    # Determine buy quantity based on balance and risk_tolerance
                    quantity = int(self.balance // best_ask * self.risk_tolerance)
                    if quantity > 0:
                        for attempt in range(3):
                            try:
                                r = self.market.buy(self.id, item_name, best_ask, quantity)
                                bought_qty = r['bought_quantity']
                                if bought_qty > 0:
                                    self.entry_prices.setdefault(item_name, []).append(best_ask)
                                    break
                            except DuplicateBuyOrder as ex:
                                self.market.cancel_buy_order(item_name=item_name, order_id=ex.order_id)


class InvestorAgent(Agent):
    """
    Determines balance for the investment, buys more as price gets lower.

    If risk_tolerance is high (0.8+) that means investor is highly risked
    and willing to buy items even after imperceptible discount.

    :param risk_tolerance: Agent's degree of making risky decisions. Determines invested amount and buy price.
    """
    __slots__ = ("risk_tolerance", "entry_prices")

    def __init__(self, agent_id, market, agent_type, balance, impulsivity, risk_tolerance):
        super().__init__(agent_id, market, agent_type, balance, impulsivity)
        self.risk_tolerance = risk_tolerance
        self.entry_prices: dict[str, dict[str, int]] = {}

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
        # TODO: REFACTOR
        # Possible unnatural logic is when agent sold his weekly drop and it still calculated in the new entry_prices
        # although he got it for free
        purchases = self.market.get_agent_purchases(self.id)
        if not purchases:
            self.entry_prices.clear()
            return

        sales = self.market.get_agent_sales(self.id)

        by_item = {}
        for p in purchases:
            info = by_item.setdefault(p.item_name, {'bought_qty': 0, 'bought_cost': 0, 'sold_qty': 0})
            info['bought_qty'] += p.quantity
            info['bought_cost'] += p.quantity * p.price
        for s in sales:
            info = by_item.setdefault(s.item_name, {'bought_qty': 0, 'bought_cost': 0, 'sold_qty': 0})
            info['sold_qty'] += s.quantity

        new_entry = {}
        for item, info in by_item.items():
            bq = info['bought_qty']
            if bq == 0:
                continue
            sq = info['sold_qty']
            net_qty = bq - sq
            if net_qty <= 0:
                continue

            total_cost = info['bought_cost']
            if sq > 0:
                avg_buy = info['bought_cost'] / bq
                total_cost -= avg_buy * sq

            new_entry[item] = {
                'qty': net_qty,
                'avg_price': int(total_cost / net_qty)
            }

        self.entry_prices = new_entry

    def try_take_profit(self):
        self.refresh_entry_prices_from_history()

        # trying to sell investments for profit, checks the price if it's already higher than desired profits
        # or just places sell order with desired price
        for item_name, quantity in list(self.inventory.items()):
            entry_price = self.entry_prices.get(item_name)
            if entry_price is None:
                continue

            buy_orders = self.market.get_item_buy_orders(item_name)
            if not buy_orders:
                # Handles initial situation, when items are just appeared, most likely investor hasn't invested yet
                continue

            highest_price = buy_orders[0].price
            target_price = entry_price['avg_price'] * (1 + self.risk_tolerance)

            if highest_price >= target_price / (1 - self.market.market_fee):
                batch_quantity = random.randint(quantity // 5, quantity)
                try:
                    self.market.sell(self.id, item_name, highest_price, batch_quantity)
                except Exception as ex:
                    print(f"Investor {self.id} failed to sell his items: {ex}")
                return True
        return False

    def try_buy_dip(self):
        available_items = self.market.get_available_items()
        if not available_items:
            return

        item_name = random.choice(available_items)
        sell_orders = self.market.get_item_sell_orders(item_name)
        if not sell_orders:
            return

        # DO I NEED TO ADD IMPULSIVE PURCHASE HERE? OR I CAN JUST LEAVE WITH RISKY DECISION BASED ON RISK_TOLERANCE
        # TODO: Pick a price!
        # Check sales for last week and pick price lower than the cheapest from the history
        lowest_price = sell_orders[0].price
        discount = (1 - self.risk_tolerance) * MAX_DISCOUNT
        price = int(lowest_price * (1 - discount))
        quantity = int(self.balance * self.risk_tolerance // price)

        if quantity > 0:
            try:
                self.market.buy(self.id, item_name, max(price, MIN_PRICE), quantity)
            except DuplicateBuyOrder:
                pass


class FarmerAgent(Agent):
    """
    More marginal and unprincipled Market agent, which exploits in-game reward system to obtain profit.

    :param number_of_accounts: Number of accounts in a Bot Farm, affects the amount of sold items every week
    """
    __slots__ = ("number_of_accounts",)

    def __init__(self, agent_id, market, agent_type, balance, impulsivity, number_of_accounts):
        super().__init__(agent_id, market, agent_type, balance, impulsivity)
        self.number_of_accounts = number_of_accounts

    def act(self):
        """
        He either sells his farmed items each week in batches to avoid dumping the price
        or insta sells all of his items in fear of account ban.
        """

        if self.is_impulsive():
            self._panic_sell()
        else:
            self.sell_farmed_items()

    def sell_farmed_items(self):
        """Regular Sell, when Agent sells farmed items in batches"""
        for item_name, initial_quantity in list(self.inventory.items()):
            remaining_quantity = initial_quantity
            # Sells items in range of a median or base price
            base_price = self.market.get_base_price(item_name)
            batches = random.randint(1, 10)
            batch_size = max(1, initial_quantity // batches)

            for i in range(batches):
                if remaining_quantity <= 0:
                    break

                # Multiply based on popularity?
                price = int(base_price * random.uniform(0.9, 1.1))
                try:
                    self.market.sell(self.id, item_name, max(price, MIN_PRICE), batch_size)
                    remaining_quantity -= batch_size
                except NotEnoughItems:
                    break
                except Exception as ex:
                    print(f"Farmer {self.id} couldn't sell his items, happened unexpected error: {ex}")
                    break
