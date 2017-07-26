# -*- coding: utf-8 -*-
from typing import Dict

from moneybot.market.adapters import MarketAdapter
from moneybot.strategy import ProposedTrade


class BacktestMarketAdapter(MarketAdapter):

    def get_balances(self):
        return self.market_state.balances

    def execute(
        self,
        proposed_trade: ProposedTrade,
    ) -> Dict[str, float]:
        balances = self.market_state.simulate_trades([proposed_trade])
        return balances
