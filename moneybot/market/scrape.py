# -*- coding: utf-8 -*-
import time
import requests
from datetime import datetime
from logging import getLogger
from typing import Optional
from typing import Dict
from typing import Iterable

from funcy import compose
from funcy import partial
from pandas import DataFrame
from pandas import to_datetime
from pandas import Series
from pyloniex import PoloniexPublicAPI

from moneybot.clients import Postgres
from moneybot.clients import Poloniex


YEAR_IN_SECS = 60 * 60 * 24 * 365

logger = getLogger(__name__)


def format_time(ts: datetime) -> str:
    return ts.strftime('%Y-%m-%d %H:%M:%S')


def historical(ticker: str) -> Dict:
    url = f'https://graphs.coinmarketcap.com/currencies/{ticker}'
    return requests.get(url).json()


def market_cap(hist_ticker: Dict) -> Series:
    r = {}
    ts = None
    for key, vals in hist_ticker.items():
        if ts is None:
            ts = [to_datetime(t[0] * 1000000) for t in vals]
        r[key] = [t[1] for t in vals]
    return DataFrame(r, index=ts)


coin_history = compose(market_cap, historical)


def marshall(hist_df):
    btc_to_usd = hist_df['price_usd'] / hist_df['price_btc']
    # volume in BTC
    # TODO is this correct? or is `'volume'` the quote volume?
    hist_df['volume'] = hist_df['volume_usd'] / btc_to_usd
    hist_df = hist_df.drop([
        'market_cap_by_available_supply',
        'volume_usd'
    ], axis=1)
    hist_df['weighted_average'] = hist_df['price_usd']
    hist_df['time'] = hist_df.index
    hist_df['currency_pair'] = hist_df.apply(lambda x: 'USD_BTC', axis=1)

    def nothing_burger():
        return hist_df.apply(lambda x: None, axis=1)

    hist_df['open'] = nothing_burger()
    hist_df['high'] = nothing_burger()
    hist_df['low'] = nothing_burger()
    hist_df['close'] = nothing_burger()
    hist_df['quote_volume'] = nothing_burger()
    return hist_df


def historical_prices_of(
        polo: PoloniexPublicAPI,
        btc_price_history: Series,
        pair: str,
        period: int = 900,
        start: Optional[float] = None,
        end: Optional[float] = None
) -> Iterable[Series]:
    '''
    Returns a series of time-indexed prices.
    `pair` is of the form e.g. 'BTC_ETH',
    `period` is an integer number of seconds,
    either 300, 900, 1800, 7200, 14400, or 86400.

    We do some data marshalling in this method as well,
    to turn API results into stuff amenable for our Postgres DB.
    '''
    def contemporary_usd_price(row: Series) -> float:
        contemporary_btc_price = btc_price_history['price_usd'].asof(row.name)
        return row['weightedAverage'] * contemporary_btc_price
    # Scraping
    now = time.time()
    start = start or now - YEAR_IN_SECS
    end = end or now
    ex_trades = polo.return_chart_data(
        currency_pair=pair,
        period=period,
        start=start,
        end=end,
    )
    # Data marshalling
    ts_df = DataFrame(ex_trades, dtype=float)
    ts_df['time'] = [datetime.fromtimestamp(t) for t in ts_df['date']]
    ts_df.index = ts_df['time']
    ts_df['price_usd'] = ts_df.apply(contemporary_usd_price, axis=1)
    ts_df['currency_pair'] = ts_df.apply(lambda x: pair, axis=1)
    ts_df = ts_df.rename(index=str, columns={
        'quoteVolume': 'quote_volume',
        'weightedAverage': 'weighted_average',
    })
    for _, row in ts_df.iterrows():
        # chart = scraped_chart(pair, row)
        # for some reason, when there's no chart data to report,
        # the API will give us some reading with all 0s.
        if row['volume'] == 0 and row['weighted_average'] == 0:
            # we will just ignore these
            pass
        else:
            yield row


def insert(cursor, row):
    return cursor.execute("""
    INSERT INTO scraped_chart (time, currency_pair, high, low, price_usd, quote_volume, volume, weighted_average)
    VALUES (%(time)s, %(currency_pair)s, %(high)s, %(low)s, %(price_usd)s, %(quote_volume)s, %(volume)s, %(weighted_average)s);""",
                          row.to_dict())


def scrape_since_last_reading():

    # postgres client
    client = Postgres.get_client()
    cursor = client.cursor()
    inserter = partial(insert, cursor)
    # get the last time we fetched some data,
    # looking at the most recent result in the db
    query = ' '.join([
        'select time from scraped_chart',
        'order by time desc',
        'limit 1',
    ])
    cursor.execute(query)
    latest_fetch_time = cursor.fetchone()[0]
    latest_fetch_unix = time.mktime(latest_fetch_time.timetuple())

    # now get USD_BTC history
    btc_price_hist = coin_history('bitcoin')
    # and write that history to DB,
    btc_rows = marshall(btc_price_hist)
    # NOTE since latest fetch time?
    # recent_btc = btc_rows[btc_rows['time'] > latest_fetch_time]
    # [inserter(row) for _, row in recent_btc.iterrows()]
    [inserter(row) for _, row in btc_rows.iterrows()]
    client.commit()
    logger.debug('Scraped USD_BTC')

    # now, a poloniex client
    polo = Poloniex.get_public()
    # and a method for grabbing historical prices
    grab_historical_prices = partial(historical_prices_of, polo, btc_price_hist)
    # for each market,
    for market in polo.return_ticker():
        # fetch all the chart data since last fetch
        generator = grab_historical_prices(
            market,
            start=latest_fetch_unix,
            end=time.time(),
        )
        list(map(inserter, generator))
        client.commit()
        logger.debug(f'Scraped {market}')

    cursor.close()
