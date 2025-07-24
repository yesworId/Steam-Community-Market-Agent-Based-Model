# DropGenerator

This class imitates **Weekly Drop System** similar to how it works in **Counter-Strike 2 (CS2)**. 
It rewards active `Agents` with a random item from the Drop Pool. Drops are limited by the User and its distribution is
performed once per each simulation day.

Parameters:
- `agents`: List of all Agents.
- `market`: Instance of a `Market`.
- `items_drop_pool`: Pool of items actively dropping with its probabilities. 
- `base_drop_chance`: Fixed chance in range of (0-1) to get an item reward.
- `reset_day`: Index of a day when drop eligibility resets (0=Monday, 1=Tuesday, ..., 6=Sunday).
- `max_drops_per_week`: Maximum number of Drops each week per `Agent`.
- `trade_lock_on`: Determines if received items are going to be trade locked for some period.

`_eligible` is a set of eligible `Agents`, who are likely to get an Item Drop this week.
`items_drop_pool` is read once after initialization to unpack list of `items` and its `weights`.
`total_drops_count` is a counter of all items dropped throughout the simulation.

Main method `tick()` should be called every simulation step. Method checks if it's an end of a day to give Item Drops.
In case, when it's also `reset_day`, it updates set of eligible `Agents` so they can obtain rewards once again. 
Randomly selects `Agents` from `_eligible`. At the end, finalizes it by distributing items to Agents respectively. 

```python
    def tick(self, step: int):
        """
        Performs Drop once per simulated day. Each week at the set day resets limit of a given drop for all Agents.
        """
        # Check if it's an end of a day
        if step % self.market.steps_per_day != 0:
            return

        if self._is_reset_day(step):
            self._reset_eligibility()

        winners_count = self._calculate_winners_count()
        if winners_count <= 0:
            return

        winners = self._select_winners(winners_count)
        self._distribute_items_to_winners(winners)
```

Basically `Agent` gets a certain number of Item drops each week.
These items are selected randomly based on their weights (probabilities).
And the total amount of all the Drops is calculated by multiplying `max_drops_per_week` by `number_of_accounts`.

```python
    def select_random_item(self) -> str:
        """Selects random item from the Active Pool with given probabilities."""
        return random.choices(self._items_list, weights=self._weights_list, k=1)[0]

    def calculate_drop_quantity(self, agent) -> int:
        """Calculates drop quantity based on number of accounts Agent has."""
        return self.max_drops_per_week * getattr(agent, 'number_of_accounts', DEFAULT_NUMBER_OF_ACCOUNTS)
```

**NOTE:** 
`DEFAULT_NUMBER_OF_ACCOUNTS` - default or a minimum number of accounts that every `Agent` has, can be changed in 
[constants.py](https://github.com/yesworId/Steam-Community-Market-Agent-Based-Model/blob/master/abm/constants.py#L11) if desired.
