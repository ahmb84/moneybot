# -*- coding: utf-8 -*-
from typing import Dict
from typing import Tuple

from numpy import median
from pandas import DataFrame
from pandas import Series

from moneybot.strategy import Strategy


class BuyHoldStrategy(Strategy):

    def propose_trades(self, market_state, market_history):
        # If we only have BTC,
        if market_state.only_holding(self.fiat):
            # buy some stuff
            return self.propose_trades_for_total_rebalancing(market_state)

        # if we hold things other than BTC, hold.
        return


class BuffedCoinStrategy(Strategy):

    # HACK HACK HACK HACK HACK
    magic_number = 1.5  # HACK
    # HACK HACK HACK HACK HACK

    def median(self, est_values: Dict[str, float]) -> float:
        return median(list(est_values.values()))

    def is_buffed(
        self,
        coin: str,
        coin_values: Dict[str, float]
    ) -> bool:
        median_value = self.median(coin_values)
        return coin_values[coin] > (median_value * type(self).magic_number)

    def find_buffed_coins(self, market_state):
        est_values = market_state.estimate_values()
        buffed_coins = [
            coin for coin
            in market_state.held_coins_with_chart_data()
            if self.is_buffed(coin, est_values)
        ]
        return buffed_coins

    def propose_trades(self, market_state, market_history):
        # If there are coins we don't own, perform a total rebalancing
        if len(market_state.available_coins_not_held()) > 0:
            return self.propose_trades_for_total_rebalancing(market_state)

        # Otherwise, see if any of our holdings are buffed
        buffed_coins = self.find_buffed_coins(market_state)
        # if any of them are,
        if len(buffed_coins):
            # sell them so as to reallocate their value eqaully
            return self.propose_trades_for_partial_rebalancing(market_state, buffed_coins)

        return


class PeakRiderStrategy(BuffedCoinStrategy):

    def emas(
        self,
        price_series: Series,
        shortw=96,
        longw=2400,
        **kwargs,
    ) -> Tuple[Series, Series]:
        long_ema = price_series.ewm(com=longw).mean()
        short_ema = price_series.ewm(com=shortw).mean()
        return long_ema, short_ema

    def percentage_price_oscillator(
        self,
        price_series: Series,
        **kwargs,
    ) -> Series:
        longe, shorte = self.emas(price_series, **kwargs)
        ppo = (shorte - longe) / longe
        return ppo

    def ppo_histogram(
        self,
        price_series: Series,
        **kwargs,
    ) -> DataFrame:
        ppo = self.percentage_price_oscillator(price_series)
        ppo_ema = ppo.ewm(com=9).mean()
        ppo_hist = DataFrame(ppo - ppo_ema)
        return ppo_hist

    def latest_ppo_hist(self, price_series: Series) -> float:
        ppo_hist = self.ppo_histogram(price_series)
        latest = ppo_hist.iloc[-1].values[0]
        return latest

    def is_buffed(self, coin: str, coin_values: Dict[str, float]) -> bool:
        # HACK HACK HACK HACK HACK
        # HACK magic number HACK
        # HACK HACK HACK HACK HACK
        POWER_OF = 1.2
        median_value = self.median(coin_values)
        if median_value > 1:
            median_to_power = pow(median_value, POWER_OF)
        else:
            median_to_power = pow(median_value, 1 / POWER_OF)
            val = coin_values[coin]
            if val > median_to_power:
                return True
        return False

    def is_crashing(self, coin, time, market_history):
        if coin == self.fiat:
            prices = market_history.asset_history(time, 'USD', self.fiat)
        else:
            prices = market_history.asset_history(time, self.fiat, coin)
            latest = self.latest_ppo_hist(prices)
            if latest > 0:
                return True
            return False

    def propose_trades(self, market_state, market_history):
        # First of all, if we only hold fiat,
        if market_state.only_holding(self.fiat):
            # Make initial trades
            return self.propose_trades_for_total_rebalancing(market_state)

        # If we do have stuff other than fiat,
        # see if any of those holdings are buffed
        buffed_coins = self.find_buffed_coins(market_state)
        buffed_and_crashing = [
            coin
            for coin
            in buffed_coins
            if self.is_crashing(coin, market_state.time, market_history)
        ]
        # if any of them are,
        if len(buffed_and_crashing):
            # sell them so as to reallocate their value eqaully
            return self.propose_trades_for_partial_rebalancing(
                market_state,
                buffed_and_crashing,
            )

        return
