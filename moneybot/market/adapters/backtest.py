# -*- coding: utf-8 -*-
from logging import getLogger
from typing import Dict

from moneybot.market.adapters import MarketAdapter
from moneybot.strategy import ProposedTrade


logger = getLogger(__name__)


class BacktestMarketAdapter(MarketAdapter):

    def get_balances(self):
        return self.market_state.balances

    def execute(
        self,
        proposed_trade: ProposedTrade,
    ) -> Dict[str, float]:
        logger.debug(f'Simulating trade: {proposed_trade}')
        balances = self.market_state.simulate_trades([proposed_trade])
        return balances
