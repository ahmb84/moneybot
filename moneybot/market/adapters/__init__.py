# -*- coding: utf-8 -*-
from abc import ABCMeta
from abc import abstractmethod
from datetime import datetime
from logging import getLogger
from typing import Dict
from typing import List
from typing import Optional

from moneybot.market import Order
from moneybot.market.history import MarketHistory
from moneybot.market.state import MarketState
from moneybot.trade import AbstractTrade


logger = getLogger(__name__)


class MarketAdapter(metaclass=ABCMeta):

    @classmethod
    @abstractmethod
    def reify_trades(
        cls,
        trades: List[AbstractTrade],
        market_state: MarketState,
    ) -> List[Order]:
        raise NotImplementedError

    def __init__(
        self,
        fiat: str,
        history: MarketHistory,
        initial_balances: Dict[str, float],
    ) -> None:
        self._fiat = fiat
        self._market_history = history
        self._market_state = MarketState(
            None,
            initial_balances,
            None,
            self.fiat,
        )

    @property
    def fiat(self):
        return self._fiat

    @property
    def market_history(self) -> MarketHistory:
        return self._market_history

    @property
    def market_state(self) -> MarketState:
        return self._market_state

    def update_market_state(self, time: datetime):
        # Get the latest chart data from the market
        charts = self.market_history.latest(time)
        balances = self.get_balances()
        self._market_state = MarketState(charts, balances, time, self.fiat)

    @abstractmethod
    def get_balances(self) -> Dict[str, float]:
        raise NotImplementedError

    @abstractmethod
    def execute_order(self, order: Order, attempts: int = 8) -> Optional[int]:
        """Execute an order, returning an order identifier.
        """
        raise NotImplementedError
