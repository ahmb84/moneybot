# -*- coding: utf-8 -*-
from logging import getLogger
from typing import Dict
from typing import Optional

from moneybot.errors import OrderValidationError
from moneybot.market import Order
from moneybot.market.adapters.poloniex import PoloniexMarketAdapter
from moneybot.utils import simulate_order


logger = getLogger(__name__)


class BacktestMarketAdapter(PoloniexMarketAdapter):

    def get_balances(self) -> Dict[str, float]:
        return self.market_state.balances.copy()

    def execute_order(self, order: Order, attempts: int = 8) -> Optional[int]:
        try:
            type(self).validate_order(order, self.market_state.balances)
        except OrderValidationError as e:
            logger.warning(f'Order failed validation: {e}')
            return None

        logger.debug(f'Simulating order: {order}')
        updated_balances = simulate_order(order, self.market_state.balances)
        # We're mutating the MarketState's balances directly here, which... ¯\_(ツ)_/¯
        self.market_state.balances.update(updated_balances)
        return 0
