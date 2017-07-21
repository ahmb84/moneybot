# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Dict
from typing import List
from typing import Set
from typing import Tuple


class MarketState:
    '''
    TODO Docstring
    '''

    def __init__(
        self,
        chart_data: Dict[str, Dict[str, float]],
        balances: Dict[str, float],
        time: datetime,
        fiat: str,
    ) -> None:
        self.chart_data = chart_data
        self.balances = balances
        self.time = time
        self.fiat = fiat

    '''
    Private methods
    '''

    def _held_coins(self) -> List[str]:
        return [
            k for k
            in self.balances.keys()
            if self.balances[k] > 0
        ]

    def _coin_names(self, market_name: str) -> Tuple[str, str]:
        coins = market_name.split('_')
        return coins[0], coins[1]

    def _available_markets(self) -> Set[str]:
        return {
            k for k
            in self.chart_data.keys()
            if k.startswith(self.fiat)
        }

    '''
    Public methods
    '''

    def balance(self, coin: str) -> float:
        '''
        Returns the quantity of a coin held.
        '''
        return self.balances[coin]

    # TODO types
    def price(self, market, key='weighted_average'):
        '''
        Returns the price of a market, in terms of the base asset.
        '''
        return self.chart_data[market][key]

    def only_holding(self, coin: str) -> bool:
        '''
        Returns true if the only thing we are holding is `coin`
        '''
        return self._held_coins() == [coin]

    def available_coins(self) -> Set[str]:
        markets = self._available_markets()
        return {self._coin_names(market)[1] for market in markets} | {self.fiat}

    def held_coins_with_chart_data(self) -> Set[str]:
        avail_coins = self.available_coins()
        return set(self._held_coins()).intersection(avail_coins)

    def estimate_values(self, **kwargs) -> Dict[str, float]:
        '''
        Returns a dict where keys are coin names,
        and values are the value of our holdings in fiat.
        '''
        fiat_values = {}
        remove = []
        for coin, amount_held in self.balances.items():
            try:
                if coin == self.fiat:
                    fiat_values[coin] = amount_held
                else:
                    relevant_market = f'{self.fiat}_{coin}'
                    fiat_price = self.price(relevant_market, **kwargs)
                    fiat_values[coin] = fiat_price * amount_held
            except KeyError:
                # Remove the coin -- it has been delisted.
                remove.append(coin)
        for removal in remove:
            self.balances.pop(removal)
        return fiat_values

    def estimate_total_value(self, **kwargs) -> float:
        '''
        Returns the sum of all holding values, in fiat.
        '''
        return sum(self.estimate_values(**kwargs).values())

    def estimate_total_value_usd(self, **kwargs) -> float:
        '''
        Returns the sum of all holding values, in USD.
        '''
        est = self.estimate_total_value() * self.price('USD_BTC', **kwargs)
        return round(est, 2)

    # TODO Not sure this really belongs here
    #       maybe more the job of BacktestMarketAdapter
    def simulate_trades(self, proposed_trades):
        '''
        TODO Docstring

        TODO State assumptions going into this simulation

        We can get fancier with this later,
        observe trends in actual trades we propose vs execute,
        and use that to make more realistic simulations~!
        (after all, our proposed price will not always be achievable)
        '''
        def simulate(proposed, new_balances):
            # TODO This makes sense as logic, but new_balances is confusing
            new_balances[proposed.from_coin] -= proposed.bid_amount
            if proposed.to_coin not in new_balances:
                new_balances[proposed.to_coin] = 0
            est_trade_amt = proposed.bid_amount / proposed.price
            new_balances[proposed.to_coin] += est_trade_amt
            return new_balances
        '''
        This method sanity-checks all proposed purchases,
        before shipping them off to the backtest / live-market.
        '''
        # TODO I hate copying this
        new_balances = self.balances.copy()
        for proposed in proposed_trades:
            # Actually simulate purchase of the proposed trade
            # TODO I hate mutating stuff out of scope, so much
            new_balances = simulate(proposed, new_balances)

        return new_balances
