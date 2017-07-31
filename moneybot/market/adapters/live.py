# -*- coding: utf-8 -*-
import operator
from functools import partial
from logging import getLogger
from typing import Callable
from typing import Dict
from moneybot.clients import Poloniex
from moneybot.market.adapters import MarketAdapter
from moneybot.market.history import MarketHistory
from moneybot.market.state import MarketState
from moneybot.strategy import ProposedTrade


logger = getLogger(__name__)


class LiveMarketAdapter(MarketAdapter):

    def __init__(
        self,
        market_history: MarketHistory,
        fiat: str,
    ) -> None:
        self.polo = Poloniex.get_client()
        self.market_history = market_history
        self.balances = self.get_balances()
        self.fiat = fiat

    def get_balances(self) -> Dict[str, float]:
        bals = self.polo.returnCompleteBalances()
        all_balances = {}
        for coin, bal, in bals.items():
            avail = float(bal['available'])
            if avail > 0:
                all_balances[coin] = avail
        return all_balances

    def execute(
        self,
        proposed_trade: ProposedTrade,
    ) -> Dict[str, float]:
        self._place_order(proposed_trade, self.market_state)
        return self.get_balances()

    '''
    Private methods
    '''

    def _adjust(
        self,
        val: float,
        operator: Callable,
        tweak: float = 0.001,
    ) -> float:
        '''
        Pass in `operator.__add__`
        or `operator.__sub__`
        to move `val` up or down by `tweak`.
        '''
        return operator(val, (val * tweak))

    def _adjust_up(self, val: float, **kwargs) -> float:
        return self._adjust(val, operator.__add__, **kwargs)

    def _adjust_down(self, val: float, **kwargs) -> float:
        return self._adjust(val, operator.__sub__, **kwargs)

    def _proposed_trade_measurement(
        self,
        direction: str,
        market: str,
        price: float,
        amount: float,
        order_status: str,
    ) -> Dict:
        return {
            'measurement': 'proposedTrade',
            'tags': {
                'order_status': order_status,
            },
            'fields': {
                'direction': direction,
                'market': market,
                'price': price,
                'amount': amount,
            }
        }

    def _purchase_helper(
        self,
        direction: str,
        market: str,
        price: float,
        amount: float,
        purchase_fn: Callable,
        adjust_fn: Callable,
    ) -> Dict:
        make_measurement = partial(self._proposed_trade_measurement,
                                   direction, market, price, amount)
        try:
            res = purchase_fn(
                market,
                price,
                amount,
                # Cancel order if not fulfilled in entirity at this price
                orderType='fillOrKill',
            )
            measurement = make_measurement('filled')
            logger.debug(str(measurement))
        # If we can't fill the order at this price,
        except:
            measurement = make_measurement('killed')
            logger.debug(str(measurement))
            # recursively again at a (higher / lower) price
            adjusted_price = adjust_fn(price)
            return self._purchase_helper(
                direction,
                market,
                adjusted_price,
                amount,
                purchase_fn,
                adjust_fn
            )
        return res

    def _place_order(
        self,
        proposed_trade: ProposedTrade,
        market_state: MarketState,
    ) -> Dict:

        # in the language of poloniex,
        # buying a market's quote currency is a "buy"
        if proposed_trade.buy_coin == proposed_trade.market_quote_currency():
            return self._purchase_helper(
                'buy',
                proposed_trade.market_name,
                proposed_trade.market_price,
                proposed_trade.buy_amount,
                self.polo.buy,
                # We try to buy low,
                # But don't always get to,
                # so we adjust up if we must.
                self._adjust_up,
            )

        # in the language of poloniex,
        # buying a market's base currency is a "sell"
        elif proposed_trade.buy_coin == proposed_trade.market_base_currency():
            return self._purchase_helper(
                'sell',
                proposed_trade.market_name,
                proposed_trade.market_price,
                proposed_trade.sell_amount,
                self.polo.sell,
                # We try to sell high,
                # But don't always get to,
                # so we adjust down if we must.
                self._adjust_down,
            )

        return {}
