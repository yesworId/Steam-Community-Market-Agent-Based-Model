# Steam Community Market Agent-Based Model
```
Agent-Based Model used for CS2 Economy Research and Simulations
```


## Limitations
* **I DO NOT** take into consideration 7-day Trade Ban, due to the time-consuming;
* **I DO NOT** take into account market-manipulations, those are short-term and do not lead to the major changes;
* **I DO NOT** take into account unnatural spikes in prices, such those when rare item was sold expensive on Community Market;
* **I DO NOT** take into consideration the volatility of different currencies; 
  - Steam uses USD as main currency and then re-evaluates/recalculates prices in other 
  currencies with a new-updated currency-rate;
  - Charts/plots are updating history prices as well;
* Balance of an Agent **should** be non-negative in range of allowed Steam Balance from 0 to 2000;
* Agent can place **ONLY ONE** Buy Order per Item;
* Self-Trading is not possible;
