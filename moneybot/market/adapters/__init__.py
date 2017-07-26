# -*- coding: utf-8 -*-
from abc import ABCMeta
from abc import abstractmethod
from datetime import datetime
from logging import getLogger
from typing import Dict
from typing import List
from typing import Optional

from moneybot.market.history import MarketHistory
from moneybot.market.state import MarketState
from moneybot.strategy import ProposedTrade


logger = getLogger(__name__)


class MarketAdapter(metaclass=ABCMeta):

    def __init__(
        self,
        history: MarketHistory,
        initial_balances: Dict[str, float],
        fiat: str,
    ) -> None:
        self.market_history = history
        self.fiat = fiat
        self.market_state = MarketState(None, initial_balances, None, self.fiat)

    @abstractmethod
    def get_balances(self):
        raise NotImplementedError

    @abstractmethod
    def execute(
        self,
        proposed_trade: ProposedTrade,
    ):
        raise NotImplementedError

    def filter_and_execute(
        self,
        proposed_trades: List[ProposedTrade],
    ) -> None:
        for trade in proposed_trades:
            legal_trade = self.legalize(trade)
            if legal_trade:
                balances = self.execute(trade)
                self.market_state.balances = balances

    def get_market_state(self, time: datetime) -> MarketState:
        # Get the latest chart data from the market
        charts = self.market_history.latest(time)
        balances = self.get_balances()
        self.market_state = MarketState(charts, balances, time, self.fiat)
        return self.market_state

    def legalize(
        self,
        proposed: ProposedTrade,
    ) -> Optional[ProposedTrade]:
        # TODO This is pretty Poloniex specific, so we might move it
        #      to a PoloniexMarketAdapter if we ever add more exchanges.

        # Check that we have enough to sell
        try:
            held_amount = self.market_state.balances[proposed.from_coin]
        except KeyError:
            logger.warning(
                f"Trying to sel {proposed.from_coin}, but none is held."
            )
            return None

        if held_amount == 0:
            logger.warning(
                f"Trying to sell {proposed.from_coin}, but none is held."
            )
            return None

        if proposed.bid_amount > held_amount:
            logger.warning(
                f"Holding {held_amount} {proposed.from_coin}, but trying to sell more than is held, {proposed.bid_amount}."
                "Simply selling maximum amount."
            )
            proposed.set_bid_amount(held_amount, self.market_state)
            return proposed

        # Check that proposed bid has a price:
        if not proposed.price:
            logger.warning(
                f'Filtering out proposed trade (has no price): {proposed}.'
            )
            return None

        # Check that we are trading a positive amount for a positive amount
        if proposed.bid_amount < 0 or proposed.ask_amount < 0:
            logger.warning(
                'Filtering out proposed trade (bid or ask amount < 0): '
                f'{proposed}.'
            )
            return None

        # Check that the proposed trade exceeds minimum fiat trade amount.
        if (
            (proposed.from_coin == proposed.fiat and proposed.bid_amount < 0.0001) or
            (proposed.to_coin == proposed.fiat and proposed.ask_amount < 0.0001)
        ):
            logger.warning(
                'Filtering out proposed trade (transaction too small): '
                f'{proposed}.'
            )
            return None

        # Check that the trade is on a market that exists.
        if proposed.market_name not in self.market_state.chart_data.keys():
            logger.warning(
                f'Filtering out proposed trade (unknown market): {proposed}.'
            )
            return None

        return proposed
