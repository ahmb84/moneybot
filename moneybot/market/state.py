# -*- coding: utf-8 -*-
from datetime import datetime
from logging import getLogger
from typing import Dict
from typing import FrozenSet
from typing import Tuple


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

    def _coin_names(self, market_name: str) -> Tuple[str, str]:
        base, quote = market_name.split('_', 1)
        return (base, quote)

    def _available_markets(self) -> FrozenSet[str]:
        return frozenset(
            filter(
                lambda market: market.startswith(self.fiat),
                self.chart_data.keys(),
            )
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

    def available_coins(self) -> FrozenSet[str]:
        markets = self._available_markets()  # All of these start with fiat
        return frozenset(self._coin_names(m)[1] for m in markets) | {self.fiat}

    def held_coins_with_chart_data(self) -> FrozenSet[str]:
        return self._held_coins() & self.available_coins()

    def estimate_values(self, balances=None, **price_kwargs) -> Dict[str, float]:
        '''
        Returns a dict where keys are coin names,
        and values are the value of our holdings in fiat.
        '''
        if balances is None:
            balances = self.balances

        fiat_values = {}
        remove = []
        for coin, amount_held in balances.items():
            try:
                if coin == self.fiat:
                    fiat_values[coin] = amount_held
                else:
                    relevant_market = f'{self.fiat}_{coin}'
                    fiat_price = self.price(relevant_market, **price_kwargs)
                    fiat_values[coin] = fiat_price * amount_held
            except KeyError:
                try:
                    relevant_market = f'{coin}_{self.fiat}'
                    fiat_price = self.price(relevant_market, **price_kwargs)
                    fiat_values[coin] = amount_held / fiat_price
                except KeyError:
                    logger.warn(f'Cannot find a price for {relevant_market}. Has it been delisted? Removing from balances.')
                    fiat_values[coin] = 0
                    remove.append(coin)
        for removal in remove:
            balances.pop(removal)
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
            proposed = self.set_sell_amount(proposed)
            # TODO This makes sense as logic, but new_balances is confusing
            new_balances[proposed.sell_coin] -= proposed.sell_amount
            if proposed.buy_coin not in new_balances:
                new_balances[proposed.buy_coin] = 0
            est_trade_amt = proposed.sell_amount / proposed.price
            new_balances[proposed.buy_coin] += est_trade_amt
            return new_balances
        '''
        This method sanity-checks all proposed purchases,
        before shipping them off to the backtest / live-market.
        '''
        # TODO I hate copying this
        new_balances = self.balances.copy()
        new_proposed = proposed_trades.copy()
        for proposed in new_proposed:
            # Actually simulate purchase of the proposed trade
            # TODO I hate mutating stuff out of scope, so much
            new_balances = simulate(proposed, new_balances)

        return new_balances

    def estimate_price(self, trade):
        '''
        Sets the approximate price of the quote value, given some chart data.
        '''
        base_price = self.price(trade.market_name)
        # The price (when buying/selling)
        # should match the self.market_name.
        # So, we keep around a self.market_price to match
        # self.price is always in the quote currency.
        trade.market_price = base_price
        # Now, we find out what price matters for our trade.
        # The base price is always in the base currency,
        # So we will need to figure out if we are trading from,
        # or to, this base currency.
        if trade.buy_coin == trade.market_base_currency:
            trade.price = 1 / base_price
        else:
            trade.price = base_price
        return trade

    def set_sell_amount(
        self,
        trade,
    ):
        '''
        Sets `self.sell_amount`, `self.buy_amount`, `self.price`
        such that the proposed trade would leave us with a
        holding of `self.fiat_to_trade`.`
        '''
        trade = self.estimate_price(trade)
        if trade.sell_coin == trade.fiat:
            trade.sell_amount = trade.fiat_value_to_trade
        # If we are trying to buy fiat,
        elif trade.buy_coin == trade.fiat:
            # first we'll find the value of the coin we currently hold.
            current_value = self.balance(trade.sell_coin) * trade.price
            # To find how much coin we want to sell,
            # we'll subtract our holding's value from the ideal value
            # to produce the value of coin we must sell.
            value_to_sell = current_value - trade.fiat_value_to_trade
            # Now we find the amount of coin equal to this value.
            trade.sell_amount = value_to_sell / trade.price
            if trade.sell_amount < 0:
                trade.sell_amount = 0
        else:
            logger.warning('Proposing trade neither to nor from fiat', trade)
            raise
        # Figure out how much we will actually buy, account for fees
        inv_amt = trade.sell_amount - (trade.sell_amount * trade.fee)
        trade.buy_amount = inv_amt / trade.price
        return trade
