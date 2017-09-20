# -*- coding: utf-8 -*-
from logging import getLogger
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pyloniex.constants import OrderType
from pyloniex.errors import PoloniexRequestError

from moneybot.clients import Poloniex
from moneybot.errors import InsufficientBalanceError
from moneybot.errors import NoMarketAvailableError
from moneybot.errors import OrderTooSmallError
from moneybot.errors import OrderValidationError
from moneybot.market import format_currency_pair
from moneybot.market import Order
from moneybot.market import split_currency_pair
from moneybot.market.adapters import MarketAdapter
from moneybot.market.history import MarketHistory
from moneybot.market.state import MarketState
from moneybot.trade import AbstractTrade


logger = getLogger(__name__)


class PoloniexMarketAdapter(MarketAdapter):

    MINIMUM_ORDER_AMOUNT = 0.0001
    ORDER_ADJUSTMENT = 0.001

    # Class methods

    @classmethod
    def reify_trade(
        cls,
        trade: AbstractTrade,
        market_state: MarketState,
    ) -> List[Order]:
        """Given an abstract trade, return a list of concrete orders that will
        accomplish the higher-level transaction described.
        """
        markets = market_state.available_markets()

        market = format_currency_pair(trade.sell_coin, trade.buy_coin)
        if market not in markets:
            market = format_currency_pair(trade.buy_coin, trade.sell_coin)
        if market not in markets:
            raise NoMarketAvailableError(
                f'No market available between {trade.sell_coin} and '
                f'{trade.buy_coin} and indirect trades are not yet supported'
            )
        base, quote = split_currency_pair(market)

        # Price is given as base currency / quote currency
        price = market_state.price(market)

        # Order amount is given with respect to the quote currency
        quote_amount = market_state.estimate_value(
            trade.reference_coin,
            trade.reference_value,
            quote,
        )

        # Order direction is given with respect to the quote currency
        if trade.sell_coin == base:
            # Buy quote currency; sell base currency
            direction = Order.Direction.BUY
        elif trade.sell_coin == quote:
            # Sell quote currency; buy quote currency
            direction = Order.Direction.SELL
        else:
            raise

        return [
            Order(
                market,
                price,
                quote_amount,
                direction,
                OrderType.fill_or_kill,
            )
        ]

    @classmethod
    def reify_trades(
        cls,
        trades: List[AbstractTrade],
        market_state: MarketState,
    ) -> List[Order]:
        """Given a list of abstract trades, produce a list of concrete orders
        that will get us into the desired state.
        """
        orders = []
        for trade in trades:
            try:
                _orders = cls.reify_trade(trade, market_state)
            except NoMarketAvailableError:
                logger.exception(
                    f'Cannot reify trade {trade}; no market available'
                )
                continue
            orders.extend(_orders)
        return orders

    @classmethod
    def validate_order(cls, order: Order, balances: Dict[str, float]):
        """Ensure that the given order is actually valid according to the
        constraints imposed by our balances and Poloniex's rules.
        """
        # Check that we exceed Poloniex's minimum order amount
        if order.amount < cls.MINIMUM_ORDER_AMOUNT:
            raise OrderTooSmallError(
                f'[{order}] is below minimum amount of {cls.MINIMUM_ORDER_AMOUNT}'
            )

        # Check that we have enough of the currency being sold
        if order.direction == Order.Direction.BUY:
            # Buying quote currency in exchange for base currency
            base_balance = balances.get(order.base_currency, 0)
            if order.base_amount > base_balance:
                raise InsufficientBalanceError(
                    f'[{order}] requires {order.base_amount} '
                    f'{order.base_currency}, which exceeds held balance of '
                    f'{base_balance}'
                )
        elif order.direction == Order.Direction.SELL:
            # Selling quote currency in exchange for base currency
            quote_balance = balances.get(order.quote_currency, 0)
            if order.quote_amount > quote_balance:
                raise InsufficientBalanceError(
                    f'[{order}] requires {order.quote_amount} '
                    f'{order.quote_currency}, which exceeds held balance of '
                    f'{quote_balance}'
                )

    # Instance methods

    def __init__(
        self,
        fiat: str,
        history: MarketHistory,
        initial_balances: Dict[str, float],
    ) -> None:
        super().__init__(fiat, history, initial_balances)
        self.private_api = Poloniex.get_private()

    def get_balances(self) -> Dict[str, float]:
        response = self.private_api.return_complete_balances()
        return {
            coin: float(balances['available'])
            for coin, balances
            in response.items()
        }

    def execute_order(self, order: Order, attempts: int = 8) -> Optional[int]:
        """Submit an order, returning the order number if the order is filled
        successfully or None otherwise.
        """
        if attempts <= 0:
            logger.warning(f'Attempts exhausted; not executing order [{order}]')
            return None

        balances = self.get_balances()
        try:
            type(self).validate_order(order, balances)
        except OrderValidationError as e:
            logger.warning(f'Order failed validation: {e}')
            return None

        if order.direction == Order.Direction.BUY:
            method = self.private_api.buy
        else:
            method = self.private_api.sell

        response: Dict[Any, Any] = {}
        error = None

        try:
            response = method(
                currency_pair=order.market,
                rate=order.price,
                amount=order.amount,
                order_type=order.type,
            )
        except PoloniexRequestError as e:
            logger.exception(
                f'Received {e.status_code} error from Poloniex API'
            )
            error = e.message
        else:
            error = response.get('error')

        if 'orderNumber' in response:
            # Order filled successfully
            for resulting_trade in response['resultingTrades']:
                logger.info(resulting_trade)
            return response['orderNumber']

        # TODO: Magic strings suck; find a better way to do this
        if error == 'Unable to fill order completely.':
            adjustment = type(self).ORDER_ADJUSTMENT

            if order.direction == Order.Direction.BUY:
                # Adjust price up a little
                new_price = order.price + adjustment
            else:
                # Adjust price down a little
                new_price = order.price - adjustment
            # Recurse and try again
            new_order = Order(
                order.market,
                new_price,
                order.amount,
                order.direction,
                order.type,
            )
            return self.execute_order(new_order, attempts - 1)

        return None
