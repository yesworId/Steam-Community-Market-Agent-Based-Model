# Market:

The **Market** class simulates real-life trading environment - [Steam Community Market](https://steamcommunity.com/market/). It executes proper order matching based on price and "FCFS" method, records sales history, and charges a fee on each transaction.

```python
class Market:
    """
    Simulation environment with its parameters and methods for Agents to interact with.

    :param market_fee: Percentage 'Market' charges on any sale.
    """
    def __init__(self, agents: list = None, market_fee=0.15):
        from .agents import Agent as Agent

        self.market_fee: float = market_fee
        self.current_step: int = 0

        self.agents: dict[int, Agent] = {}
        self.buy_orders: dict[str, list[Order]] = {}
        self.sell_orders: dict[str, list[Order]] = {}

        self.sales_history: defaultdict[str, list[Sale]] = defaultdict(list)

        if agents:
            self.add_agents(agents)
```
