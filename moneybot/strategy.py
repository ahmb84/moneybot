# -*- coding: utf-8 -*-
from abc import ABCMeta
from abc import abstractmethod
from logging import getLogger
from typing import FrozenSet
from typing import Generator
from typing import Iterable
from typing import List

from moneybot.market.history import MarketHistory
from moneybot.market.state import MarketState


logger = getLogger(__name__)


class ProposedTrade:
    '''
    ProposedTrades represent possible trades
    that have not yet been executed by a `MarketAdapter`.
    They parlay data between the Strategy and the MarketAdapter.

    Specifically, Strategies use a method `propose_trades()` to
    return a list of ProposedTrades on each trading step. Using a
    high-level API, a Strategy can propose a plausible trade.
    The MarketAdapter then decides if this ProposedTrade trade is legal
    and, if it is, attempts to execute it at the best possible price.
    '''

    def __init__(
        self,
        sell_coin: str,
        buy_coin: str,
        fiat_value_to_trade: float,
        fiat: str = 'BTC',
        fee: float = 0.0025,
    ) -> None:
        self.sell_coin = sell_coin
        self.buy_coin = buy_coin
        self.fiat_value_to_trade = fiat_value_to_trade
        self.fiat = fiat
        self.market_price = 0.0
        self.price = 0.0
        self.buy_amount = 0.0
        self.sell_amount = 0.0
        self.fee = fee

        # get the Poloniex market name
        # Poloniex markets are named `{fiatSymol}_{quoteSymbol}`
        # By seeing whether from_ or to_ are the fiat,
        # we will construct the proper market name.
        # (yes, we can only trade directly fiat to/from fiat for now. sorry!)
        if sell_coin == fiat:
            self.market_name = self._get_market_name(fiat, buy_coin)
        elif buy_coin == fiat:
            self.market_name = self._get_market_name(fiat, sell_coin)
        else:
            logger.warning('Proposing a trade neither to nor from fiat.')
            raise

        if self.market_name:
            # Set the "base" and "quote" currency (strings)
            self.market_base_currency, self.market_quote_currency = self.market_name.split('_')

    def __str__(self) -> str:
        return '{!s} {!s} for {!s} {!s} (price of {!s} {!s}/{!s} on market {!s})'.format(
            self.sell_amount, self.sell_coin,
            self.buy_amount, self.buy_coin,
            self.price, self.sell_coin, self.buy_coin,
            self.market_name)

    '''
    Private methods
    '''

    def _get_market_name(
        self,
        base: str,
        quote: str,
    ) -> str:
        ''' Return Poloniex market name'''
        return f'{base}_{quote}'


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
        self.has_proposed_initial_trades = False

    @abstractmethod
    def propose_trades(
        self,
        market_state: MarketState,
        market_history: MarketHistory,
    ) -> List[ProposedTrade]:
        raise NotImplementedError

    '''
    Trade proposal utilities
    '''

    def _possible_investments(self, market_state: MarketState) -> FrozenSet[str]:
        '''
        Returns a set of all coins that the strategy might invest in,
        not including the fiat.
        '''
        return market_state.available_coins() - {self.fiat}

    '''
    wow stuff to cut/move
    '''

    def _propose_trades_to_fiat(
        self,
        coins: Iterable[str],
        fiat_value_per_coin: float,
        market_state: MarketState,
    ) -> Generator[ProposedTrade, None, None]:
        for coin in coins:
            if coin != self.fiat:
                # Sell `coin` for `fiat`,
                # estimating how much `fiat` we should bid
                # (and how much `coin` we should ask for)
                # given the fiat value we want that coin to have after the trade
                proposed = ProposedTrade(coin, self.fiat, fiat_value_per_coin)
                yield proposed

    def _propose_trades_from_fiat(
        self,
        coins: Iterable[str],
        fiat_investment_per_coin: float,
        market_state: MarketState,
    ) -> Generator[ProposedTrade, None, None]:
        for coin in coins:
            proposed = ProposedTrade(self.fiat, coin, fiat_investment_per_coin)
            yield proposed

    def initial_proposed_trades(
        self,
        market_state: MarketState,
    ) -> Generator[ProposedTrade, None, None]:
        """Initial trades should get us as close as possible to an equal
        distribution of value (w/r/t fiat) across all "reachable" markets
        (those in which the base currency is our "fiat").
        """
        total_value = market_state.estimate_total_value()
        target_coins = self._possible_investments(market_state)
        ideal_fiat_value_per_coin = total_value / (len(target_coins) + 1.0)  # Including fiat

        est_values = market_state.estimate_values()

        # 1) Propose trades that would have us buy fiat
        for coin in target_coins:
            value = est_values.get(coin, 0)
            delta = value - ideal_fiat_value_per_coin
            if delta > 0:
                yield ProposedTrade(coin, self.fiat, delta)

        # 2) Propose trades that would have us sell fiat
        for coin in target_coins:
            value = est_values.get(coin, 0)
            delta = value - ideal_fiat_value_per_coin
            if delta < 0:
                yield ProposedTrade(self.fiat, coin, abs(delta))

    # TODO Trade directly from X to Y!
    def rebalancing_proposed_trades(
        self,
        coins_to_rebalance: List[str],
        market_state: MarketState,
    ) -> List[ProposedTrade]:

        # First, we will "fan in,"
        # selling all of our coins_to_rebalance to fiat
        possible_investments = self._possible_investments(market_state)
        total_value = market_state.estimate_total_value()
        ideal_fiat_value_per_coin = total_value / len(possible_investments)
        coins_to_invest_in = possible_investments - set(coins_to_rebalance) - {self.fiat}

        proposed_trades_to_fiat = list(self._propose_trades_to_fiat(coins_to_rebalance,
                                                                    ideal_fiat_value_per_coin,
                                                                    market_state))
        # If we have proposed to do anything,
        if self.fiat in coins_to_rebalance and len(proposed_trades_to_fiat) > 0:
            # we will "fan out,"
            # selling fiat to the coins we wish to buy.
            # First we'll simulate executing trades to fiat
            est_bals_after_fiat_trades = market_state.simulate_trades(proposed_trades_to_fiat)
            # We'll then use these simulated amounts to plan ahead trades
            # from fiat to our target investment coins.
            fiat_after_trades = est_bals_after_fiat_trades[self.fiat]
            to_redistribute = fiat_after_trades - ideal_fiat_value_per_coin
            to_redistribute_per_coin = to_redistribute / len(coins_to_invest_in)
            proposed_trades_from_fiat = self._propose_trades_from_fiat(coins_to_invest_in,
                                                                       to_redistribute_per_coin,
                                                                       market_state)
            trades = proposed_trades_to_fiat + list(proposed_trades_from_fiat)

            return trades

        return proposed_trades_to_fiat
