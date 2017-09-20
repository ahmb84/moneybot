# -*- coding: utf-8 -*-
from enum import Enum
from typing import Any
from typing import Tuple

from pyloniex.constants import OrderType


def format_currency_pair(base: str, quote: str) -> str:
    return f'{base}_{quote}'


def split_currency_pair(market: str) -> Tuple[str, str]:
    currencies = market.split('_')
    if len(currencies) != 2:
        raise ValueError(
            f'Unable to extract 2 currencies from market string {market}'
        )
    base, quote = currencies
    return (base, quote)


class Order:
    """TODO: This implementation is still somewhat Poloniex-specific; we should
    maybe figure out how to make it more general.
    """

    class Direction(str, Enum):
        BUY = 'buy'
        SELL = 'sell'

    def __init__(
        self,
        market: str,
        price: float,
        amount: float,
        direction: Direction,
        type_: OrderType,
    ) -> None:
        self._market = market
        self._price = price
        self._amount = amount
        self._direction = direction
        self._type = type_

        self._base_currency, self._quote_currency = split_currency_pair(market)

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, type(self)) and
            other.market == self.market and
            other.price == self.price and
            other.amount == self.amount and
            other.direction == self.direction and
            other.type == self.type
        )

    def __str__(self) -> str:
        return f'{self.direction.value.upper()} {self.type.value} {self.market} {self.amount}@{self.price}'

    # Intrinsic properties

    @property
    def market(self) -> str:
        """A string like "BTC_ETH", in which the first currency is referred to
        as the "base" currency, and the second currency the "quote" currency.
        """
        return self._market

    @property
    def price(self) -> float:
        """The price at which to buy or sell the quote currency, e.g.
        base / quote.
        """
        return self._price

    @property
    def amount(self) -> float:
        """The quantity of the quote currency being bought or sold.
        """
        return self._amount

    @property
    def direction(self) -> Direction:
        """Whether the order is a "buy" (buy quote currency with base currency)
        or a "sell" (buy base currency with quote currency).
        """
        return self._direction

    @property
    def type(self) -> OrderType:
        return self._type

    # Convenience properties

    @property
    def base_currency(self):
        return self._base_currency

    @property
    def base_amount(self) -> float:
        return self.price * self.amount

    @property
    def quote_currency(self):
        return self._quote_currency

    @property
    def quote_amount(self) -> float:
        return self.amount
