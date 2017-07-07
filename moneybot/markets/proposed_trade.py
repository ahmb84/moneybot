# -*- coding: utf-8 -*-
from logging import getLogger

from moneybot.markets.state import MarketState


logger = getLogger(__name__)


class ProposedTrade:

    def __init__(
        self,
        from_coin: str,
        to_coin: str,
        fiat: str = 'BTC',
        fee: float = 0.0025,
    ) -> None:
        self.from_coin = from_coin
        self.to_coin = to_coin
        self.fiat = fiat
        self.price = 0.0
        self.ask_amount = 0.0
        self.bid_amount = 0.0
        self.fee = fee

        # get the Poloniex market name
        # Poloniex markets are named `{fiatSymol}_{quoteSymbol}`
        # By seeing whether from_ or to_ are the fiat,
        # we will construct the proper market name.
        # (yes, we can only trade directly fiat to/from fiat for now. sorry!)
        if from_coin == fiat:
            self.market_name = self._get_market_name(fiat, to_coin)
        elif to_coin == fiat:
            self.market_name = self._get_market_name(fiat, from_coin)

    def __str__(self) -> str:
        return '{!s} {!s} for {!s} {!s} (price of {!s} {!s}/{!s} on market {!s})'.format(
            self.bid_amount, self.from_coin,
            self.ask_amount, self.to_coin,
            self.price, self.from_coin, self.to_coin,
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
        if self.to_coin == self.fiat:
            self.price = 1 / base_price
        else:
            self.price = base_price

    def set_bid_amount(
        self,
        amount: float,
        market_state: MarketState,
    ):
        '''
        Set how much `from_coin` we are putting on sale, by value.

        For convenience: we can estimate the price of the asset
        to set the `ask_amount` as well.
        When `self.estimate_price_with` is passed a `chart` object,
        it will pass this down to `estimate_price()`.
        '''
        if amount > market_state.balance(self.from_coin):
            self.bid_amount = market_state.balance(self.from_coin)
        else:
            self.bid_amount = amount

        self.estimate_price(market_state)
        self.ask_amount = self._purchase_amount(amount, self.price)

    def sell_to_achieve_value_of(
        self,
        desired_value: float,
        market_state: MarketState,
    ) -> None:
        '''
        Sets `self.bid_amount`, `self.ask_amount`, `self.price`
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
        current_value = market_state.balance(self.from_coin) * self.price
        # To find how much coin we want to sell,
        # we'll subtract our holding's value from the ideal value
        # to produce the value of coin we must sell
        value_to_sell = current_value - desired_value
        # Now we find the amount of coin equal to this value
        amount_to_sell = value_to_sell / self.price
        self.set_bid_amount(amount_to_sell, market_state)