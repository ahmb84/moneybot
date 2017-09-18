# -*- coding: utf-8 -*-
from abc import ABCMeta
from abc import abstractmethod
from logging import getLogger
from typing import FrozenSet
from typing import List

from moneybot.market.history import MarketHistory
from moneybot.market.state import MarketState
from moneybot.trade import AbstractTrade
from moneybot.utils import simulate_trades


logger = getLogger(__name__)


class Strategy(metaclass=ABCMeta):
    '''
    A Fund uses a Strategy to propose trades,
    executed by the MarketAdapter.

    Specifically, Strategies have a method `propose_trade()`,
    which takes a MarketState and a MarketHistory,
    returning a list of ProposedTrades for the MarketAdapter
    to process at every training step.

    The way in which trades are proposed at specific steps
    is mostly up to callers of this library. In other words,
    we imagine callers will subclass `Strategy` to create
    their own Strategies.

    This class also includes a few convenience methods for
    common trade proposals.
    '''

    def __init__(self, fiat: str, trade_interval: int) -> None:
        self.fiat = fiat
        self.trade_interval = trade_interval  # Time between trades, in seconds

    @abstractmethod
    def propose_trades(
        self,
        market_state: MarketState,
        market_history: MarketHistory,
    ) -> List[AbstractTrade]:
        raise NotImplementedError

    '''
    Trade proposal utilities
    '''

    def _ideal_fiat_value_per_coin(self, market_state: MarketState) -> float:
        """We define "ideal" value as total value (in fiat) / # of available
        coins (including fiat).
        """
        total_value = market_state.estimate_total_value(market_state.balances, self.fiat)
        num_coins = len(market_state.available_coins())
        return total_value / num_coins

    def _possible_investments(self, market_state: MarketState) -> FrozenSet[str]:
        '''
        Returns a set of all coins that the strategy might invest in, excluding
        `self.fiat`.
        '''
        return market_state.available_coins() - {self.fiat}

    def propose_trades_for_total_rebalancing(
        self,
        market_state: MarketState,
    ) -> List[AbstractTrade]:
        """A total rebalancing should get us as close as possible to an equal
        distribution of value (w/r/t `self.fiat`) across all "reachable"
        markets (those in which the base currency is `self.fiat`).
        """
        ideal_fiat_value_per_coin = self._ideal_fiat_value_per_coin(market_state)

        est_values = market_state.estimate_values(market_state.balances, self.fiat)

        coins_to_sell = {}
        coins_to_buy = {}
        for coin in self._possible_investments(market_state):
            value = est_values.get(coin, 0)
            delta = value - ideal_fiat_value_per_coin
            if delta > 0:
                coins_to_sell[coin] = delta
            elif delta < 0:
                coins_to_buy[coin] = abs(delta)

        trades_to_fiat = [
            AbstractTrade(sell_coin, self.fiat, self.fiat, fiat_value)
            for sell_coin, fiat_value
            in coins_to_sell.items()
        ]

        trades_from_fiat = [
            AbstractTrade(self.fiat, buy_coin, self.fiat, fiat_value)
            for buy_coin, fiat_value
            in coins_to_buy.items()
        ]

        return trades_to_fiat + trades_from_fiat

    def propose_trades_for_partial_rebalancing(
        self,
        market_state: MarketState,
        coins_to_rebalance: FrozenSet[str],
    ) -> List[AbstractTrade]:
        """TODO: Trade directly from X to Y without going through fiat.
        """
        ideal_fiat_value_per_coin = self._ideal_fiat_value_per_coin(market_state)

        est_values = market_state.estimate_values(market_state.balances, self.fiat)

        # 1) Fan in to fiat, selling excess value in coins we want to rebalance
        trades_to_fiat = []
        for sell_coin in coins_to_rebalance:
            if sell_coin == self.fiat:
                continue
            value = est_values.get(sell_coin, 0)
            delta = value - ideal_fiat_value_per_coin
            if delta > 0:
                trades_to_fiat.append(
                    AbstractTrade(sell_coin, self.fiat, self.fiat, delta),
                )

        # 2) Simulate trades and estimate portfolio state afterwards
        est_balances_after_trades = simulate_trades(
            trades_to_fiat,
            market_state,
        )
        est_values_after_trades = market_state.estimate_values(
            est_balances_after_trades,
            self.fiat,
        )

        fiat_after_trades = est_balances_after_trades[self.fiat]
        fiat_to_redistribute = fiat_after_trades - ideal_fiat_value_per_coin
        if fiat_to_redistribute <= 0:
            return trades_to_fiat

        # 3) Find coins in which we don't hold enough value
        possible_buys = set()
        for buy_coin in self._possible_investments(market_state):
            value = est_values_after_trades.get(buy_coin, 0)
            if ideal_fiat_value_per_coin > value:
                possible_buys.add(buy_coin)

        fiat_to_redistribute_per_coin = fiat_to_redistribute / len(possible_buys)

        # 4) Plan trades, fanning back out from fiat to others
        trades_from_fiat = []
        for buy_coin in possible_buys:
            value = est_values_after_trades.get(buy_coin, 0)
            delta = ideal_fiat_value_per_coin - value
            if delta > 0:
                available_fiat = min(fiat_to_redistribute_per_coin, delta)
                trades_from_fiat.append(
                    AbstractTrade(self.fiat, buy_coin, self.fiat, available_fiat),
                )

        return trades_to_fiat + trades_from_fiat
