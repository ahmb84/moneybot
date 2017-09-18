# -*- coding: utf-8 -*-
from datetime import datetime
from logging import getLogger
from typing import Dict
from typing import FrozenSet
from typing import Optional

from moneybot.market import format_currency_pair
from moneybot.market import split_currency_pair


logger = getLogger(__name__)


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

    def _held_coins(self) -> FrozenSet[str]:
        return frozenset(
            coin for (coin, balance)
            in self.balances.items()
            if balance > 0
        )

    '''
    Public methods
    '''

    def balance(self, coin: str) -> float:
        '''
        Returns the quantity of a coin held.
        '''
        return self.balances[coin]

    def price(self, market: str, key='weighted_average') -> float:
        '''
        Returns the price of a market, in terms of the base asset.
        '''
        return self.chart_data[market][key]

    def only_holding(self, coin: str) -> bool:
        '''
        Returns true if the only thing we are holding is `coin`
        '''
        return self._held_coins() == {coin}

    def available_markets(self) -> FrozenSet[str]:
        """Return a frozenset containing all available markets, e.g. 'BTC_ETH'.
        """
        return frozenset(
            filter(
                lambda market: market.startswith(self.fiat),
                self.chart_data.keys(),
            )
        )

    def available_coins(self) -> FrozenSet[str]:
        markets = self.available_markets()  # All of these start with fiat
        return frozenset(split_currency_pair(m)[1] for m in markets) | {self.fiat}

    def available_coins_not_held(self) -> FrozenSet[str]:
        return self.available_coins() - self._held_coins()

    def held_coins_with_chart_data(self) -> FrozenSet[str]:
        return self._held_coins() & self.available_coins()

    def estimate_value(
        self,
        coin: str,
        amount: float,
        reference_coin: str,
    ) -> Optional[float]:
        """Given `amount` of `coin`, estimate its value in terms of
        `reference_coin`.

        TODO: It would be super awesome if we could calculate this value across
        multiple hops, e.g. be able to tell the value of x ETH in BCH if we
        only have access to the markets BTC_ETH and BTC_BCH.
        """
        if coin == reference_coin:
            return amount

        chart_key = 'weighted_average'

        market = format_currency_pair(reference_coin, coin)
        if market in self.chart_data:
            reference_per_coin = self.chart_data[market][chart_key]
            return amount * reference_per_coin

        # We may have to flip the coins around to find the market
        market = format_currency_pair(coin, reference_coin)
        if market in self.chart_data:
            coin_per_reference = self.chart_data[market][chart_key]
            return amount / coin_per_reference

        logger.warning(
            f"Couldn't find a market for {reference_coin}:{coin}; has it been delisted?",
        )
        return None

    def estimate_values(
        self,
        balances: Dict[str, float],
        reference_coin: str,
    ) -> Dict[str, float]:
        """Return a dict mapping coin names to value in terms of the reference
        coin.

        NOTE: If no market exists between a coin and the reference coin, we
        can't estimate a value for said coin (see docstring for
        `MarketState::estimate_value`). If this happens, the un-valuable coin
        will be omitted from the returned dict.
        """
        estimated_values = {}
        for coin, amount in balances.items():
            value = self.estimate_value(coin, amount, reference_coin)
            if value is not None:
                estimated_values[coin] = value
        return estimated_values

    def estimate_total_value(
        self,
        balances: Dict[str, float],
        reference_coin: str,
    ) -> float:
        """Calculate the total value of all holdings in terms of the reference
        coin.
        """
        return sum(self.estimate_values(balances, reference_coin).values())

    def estimate_total_value_usd(self, balances: Dict[str, float]) -> float:
        '''
        Returns the sum of all holding values, in USD.
        '''
        btc_val = self.estimate_total_value(balances, 'BTC')
        usd_val = btc_val * self.price('USD_BTC')
        return round(usd_val, 2)
