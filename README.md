# Steam Community Market Agent-Based Model
```
Agent-Based Model used for Simulation and Research of CS2 Market Economy
```

The goal is to analyze how different factors such as market fee percentage, agent behaviour impact whole Market overall.  


## Limitations:
* Balance of each Agent **should** be non-negative, for example in range of allowed Steam Balance from 0 to 2000;
* Agent can place **ONLY ONE** Buy Order per Item;
* Self-Trading is **Prohibited** and not possible;
* Price of an Item is non-negative and **CANNOT** be less than a minimum price, which equal to One Cent;

**NOTE:** All limitations are based on Steam Community Market Rules and mechanisms.


## Features:
* Run single or multiple simulations with various parameters;
* Results visualization;
* Metrics and statistics gathering;
* Trade Lock **On/Off** on newly obtained Items;