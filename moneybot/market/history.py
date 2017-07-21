# -*- coding: utf-8 -*-
from datetime import datetime
from datetime import timedelta
from logging import getLogger
from typing import Dict
from typing import List

from pandas import Series

from moneybot.clients import Postgres
from moneybot.market.scrape import scrape_since_last_reading


logger = getLogger(__name__)


class MarketHistory:
    '''
    TODO Docstring
    '''

    def __init__(self) -> None:
        self.client = Postgres.get_client()

    def scrape_latest(self) -> None:
        return scrape_since_last_reading()

    # String -> { 'BTC_ETH': { weighted_average, ...} ...}
    # TODO One issue here is that we are *only* getting the latest (15-minute) candlestic
    # So, if we are only trading once per day, certain values (like volume) will be misleading,
    # as they won't cover teh whole 24-hour period.
    # We could, in the future, address this by taking all the candlesticks since we last checked
    # and pass them through to the strategy together, sorted ny time.
    # Then, the strategy can then decide how to combine them.
    def latest(self, time: datetime) -> Dict[str, Dict[str, float]]:
        cursor = self.client.cursor()
        prior_date = time - timedelta(days=1)
        query = cursor.mogrify(
            (
                'SELECT DISTINCT ON (currency_pair) * FROM scraped_chart '
                'WHERE time <= %s AND time > %s '
                'ORDER BY currency_pair, time DESC'
            ),
            (time, prior_date),
        )
        logger.debug(query)
        cursor.execute(query)
        rows = cursor.fetchall()
        col_names = [column.name for column in cursor.description]
        row_dicts = [dict(zip(col_names, row)) for row in rows]
        result = {
            row_dict['currency_pair']: row_dict
            for row_dict
            in row_dicts
        }
        cursor.close()
        return result

    def asset_history(
        self,
        time: datetime,
        base: str,
        quote: str,
        days_back: int=30
    ) -> List[float]:
        cursor = self.client.cursor()
        currency_pair = f'{base}_{quote}'
        prior_date = time - timedelta(days=days_back)
        query = cursor.mogrify(
            (
                'SELECT time, price_usd FROM scraped_chart '
                'WHERE currency_pair = %s AND time <= %s AND time > %s '
                'ORDER BY time DESC'
            ),
            (currency_pair, time, prior_date),
        )
        logger.debug(query)
        cursor.execute(query)
        rows = cursor.fetchall()
        df = Series([p[1] for p in rows])
        df.index = [p[0] for p in rows]
        cursor.close()
        return df
