# -*- coding: utf-8 -*-
from abc import ABCMeta
from abc import abstractmethod
from logging import getLogger
from typing import Generator
from typing import List
from typing import Set

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
        fiat: str = 'BTC',
        fee: float = 0.0025,
    ) -> None:
        self.sell_coin = sell_coin
        self.buy_coin = buy_coin
        self.fiat = fiat
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

    def _purchase_amount(
        self,
        investment: float,
        price: float,
    ) -> float:
        '''
        Private method.
        Get the amount of some coin purchased,
        given an investment (in quote), and a price (in quote),
        accounting for trading fees.
        '''
        in_amt = investment - (investment * self.fee)
        return in_amt / price

    '''
    Utility methods
    '''

    def estimate_price(self, market_state: MarketState):
        '''
        Sets the approximate price of the quote value, given some chart data.
        '''
        base_price = market_state.price(self.market_name)
        # The price (when buying/selling)
        # should match the self.market_name.
        # So, we keep around a self.market_price to match
        # self.price is always in the quote currency.
        self.market_price = base_price
        # Now, we find out what price matters for our trade.
        # The base price is always in the base currency,
        # So we will need to figure out if we are trading from,
        # or to, this base currency.
        if self.buy_coin == self.market_base_currency:
            self.price = 1 / base_price
        else:
            self.price = base_price

    def set_sell_amount(
        self,
        amount: float,
        market_state: MarketState,
    ):
        '''
        Set how much `sell_coin` we are putting on sale, by value.

        For convenience: we can estimate the price of the asset
        to set the `buy_amount` as well.
        When `self.estimate_price_with` is passed a `chart` object,
        it will pass this down to `estimate_price()`.
        '''
        # if amount > market_state.balance(self.sell_coin):
        #     self.sell_amount = market_state.balance(self.sell_coin)
        # else:
        self.sell_amount = amount
        self.estimate_price(market_state)
        self.buy_amount = self._purchase_amount(amount, self.price)

    def sell_to_achieve_value_of(
        self,
        desired_value: float,
        market_state: MarketState,
    ) -> None:
        '''
        Sets `self.sell_amount`, `self.buy_amount`, `self.price`
        such that the proposed trade would leave us with a
        holding of `desired_value`.
        '''
        self.estimate_price(market_state)
        if not self.price:
            logger.error(
                'Must set a price for ProposedTrade, or pass a chart object '
                'into estimate_price_with'
            )
            raise
        # After rebalance, we want the value of the coin we're trading to
        # to be equal to the ideal value (in fiat).
        # First we'll find the value of the coin we currently hold.
        current_value = market_state.balance(self.sell_coin) * self.price
        # To find how much coin we want to sell,
        # we'll subtract our holding's value from the ideal value
        # to produce the value of coin we must sell
        value_to_sell = current_value - desired_value
        # Now we find the amount of coin equal to this value
        amount_to_sell = value_to_sell / self.price
        self.set_sell_amount(amount_to_sell, market_state)


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
    ) -> List[ProposedTrade]:
        raise NotImplementedError

    '''
    Trade proposal utilities
    '''

    def _possible_investments(self, market_state: MarketState) -> Set[str]:
        '''
        Returns a set of all coins that the strategy might invest in,
        not including the fiat.
        '''
        return market_state.available_coins() - {self.fiat}

    def _propose_trades_to_fiat(
        self,
        coins: List[str],
        fiat_value_per_coin: float,
        market_state: MarketState,
    ) -> Generator[ProposedTrade, None, None]:
        for coin in coins:
            if coin != self.fiat:
                # Sell `coin` for `fiat`,
                # estimating how much `fiat` we should bid
                # (and how much `coin` we should ask for)
                # given the fiat value we want that coin to have after the trade
                proposed = ProposedTrade(coin, self.fiat)
                proposed.sell_to_achieve_value_of(fiat_value_per_coin, market_state)
                if proposed.sell_amount > 0:
                    yield proposed

    def _propose_trades_from_fiat(
        self,
        coins: Set[str],
        fiat_investment_per_coin: float,
        market_state: MarketState,
    ) -> Generator[ProposedTrade, None, None]:
        for coin in coins:
            proposed = ProposedTrade(self.fiat, coin)
            proposed.set_sell_amount(fiat_investment_per_coin, market_state)
            yield proposed

    def initial_proposed_trades(
        self,
        market_state: MarketState,
    ) -> Generator[ProposedTrade, None, None]:
        '''
        "Initial" purchases are from fiat.
        (We assume funds start with only a fiat balance.)
        The resulting proposed trades should result in an equal allocation (of value, in fiat)
        across all "reachable" markets (markets in which the base currency is fiat).
        '''
        possible_investments = self._possible_investments(market_state)
        fiat_investment_per_coin = market_state.balances[self.fiat] / (len(possible_investments) + 1.0)
        trades = self._propose_trades_from_fiat(possible_investments,
                                                fiat_investment_per_coin,
                                                market_state)
        return trades

    def rebalancing_proposed_trades(
        self,
        coins_to_rebalance: List[str],
        market_state: MarketState,
    ) -> List[ProposedTrade]:
        possible_investments = self._possible_investments(market_state)
        total_value = market_state.estimate_total_value()
        ideal_fiat_value_per_coin = total_value / len(possible_investments)

        proposed_trades_to_fiat = list(self._propose_trades_to_fiat(coins_to_rebalance,
                                                                    ideal_fiat_value_per_coin,
                                                                    market_state))

        # Next, we will simulate actually executing all of these trades
        # Afterward, we'll get some simulated balances
        est_bals_after_fiat_trades = market_state.simulate_trades(proposed_trades_to_fiat)

        if self.fiat in coins_to_rebalance and len(proposed_trades_to_fiat) > 0:
            fiat_after_trades = est_bals_after_fiat_trades[self.fiat]
            to_redistribute = fiat_after_trades - ideal_fiat_value_per_coin
            coins_divested_from = [proposed.sell_coin for proposed in proposed_trades_to_fiat]
            coins_to_buy = possible_investments - set(coins_divested_from) - {self.fiat}
            to_redistribute_per_coin = to_redistribute / len(coins_to_buy)
            proposed_trades_from_fiat = self._propose_trades_from_fiat(coins_to_buy,
                                                                       to_redistribute_per_coin,
                                                                       market_state)
            trades = proposed_trades_to_fiat + list(proposed_trades_from_fiat)

            return trades

        return proposed_trades_to_fiat
