import random
from typing import List


class DropGenerator:
    """
    Drop Generator imitates CS2 Weekly Drop System. Rewards Agents that play the game with an item.
    """
    __slots__ = (
        "agents",
        "base_drop_chance",
        "steps_per_day",
        "reset_day",
        "max_drops_per_week",
        "_eligible",
        "_items_list",
        "_weights_list",
        "total_drops_count"
    )

    def __init__(
            self,
            agents: List,
            items_drop_pool: dict[str, float],
            base_drop_chance: float,
            steps_per_day: int,
            reset_day: int = 2,
            max_drops_per_week: int = 1
    ):
        """
        :param agents: List of all Agents
        :param items_drop_pool: Pool of items actively dropping with its probabilities
        :param base_drop_chance: Fixed chance in range of (0-1) to get an item reward
        :param steps_per_day: Amount of simulation steps per day
        :param reset_day: Index of a day of reset (0-Monday, 1-Tuesday, ..., 6-Sunday)
        :param max_drops_per_week: Maximum Drops each week per Agent
        """
        self.agents = {agent.id: agent for agent in agents}
        self.base_drop_chance = base_drop_chance
        self.steps_per_day = steps_per_day
        self.reset_day = reset_day
        self.max_drops_per_week = max_drops_per_week

        self._eligible = set(agent.id for agent in agents)

        self._items_list = list(items_drop_pool.keys()) if items_drop_pool else ["Default Item"]
        self._weights_list = list(items_drop_pool.values()) if items_drop_pool else [1.0]

        self.total_drops_count = 0

    def _is_reset_day(self, step: int) -> bool:
        """Checks if it's a day of a Weekly Drop reset."""
        return (step // self.steps_per_day % 7) == self.reset_day

    def _reset_eligibility(self):
        """Reset eligibility for all agents. Used for weekly reset."""
        self._eligible = set(self.agents.keys())

    def _calculate_winners_count(self) -> int:
        """Calculates number of Agents that will receive a Drop."""
        eligible_count = len(self._eligible)
        if eligible_count == 0:
            return 0

        winners_count = int(eligible_count * self.base_drop_chance)
        return min(winners_count, eligible_count)

    def _select_winners(self, count: int) -> List:
        """Selects random Agents that received a Weekly Drop."""
        # TODO: GIVE DROP ONLY TO ELIGIBLE AGENTS, WHO ALSO ARE PLAYED THE GAME
        if count <= 0 or not self._eligible:
            return []

        winners_ids = set(random.sample(list(self._eligible), k=count))
        self._eligible -= winners_ids

        return [self.agents[agent_id] for agent_id in winners_ids]

    def _distribute_items_to_winners(self, winners: List):
        for agent in winners:
            drop_quantity = self.calculate_drop_quantity(agent)
            self.total_drops_count += drop_quantity

            if len(self._items_list) == 1:
                agent.add_item(self._items_list[0], drop_quantity)
                continue

            for _ in range(drop_quantity):
                item = self.select_random_item()
                agent.add_item(item)

    def select_random_item(self) -> str:
        """Selects random item from the Active Pool with given probabilities."""
        return random.choices(self._items_list, weights=self._weights_list, k=1)[0]

    def calculate_drop_quantity(self, agent) -> int:
        """Calculates drop quantity based on number of accounts Agent has."""
        return self.max_drops_per_week * getattr(agent, 'number_of_accounts', 1)

    def tick(self, step: int):
        """
        Performs Drop once per simulated day. Each week at the set day resets limit of a given drop for all Agents.
        """
        # Check if it's an end of a day
        if step % self.steps_per_day != 0:
            return

        if self._is_reset_day(step):
            self._reset_eligibility()

        winners_count = self._calculate_winners_count()
        if winners_count <= 0:
            return

        winners = self._select_winners(winners_count)
        self._distribute_items_to_winners(winners)
