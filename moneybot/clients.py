# -*- coding: utf-8 -*-
import psycopg2
from poloniex import Poloniex as _Poloniex

from moneybot import config


class Postgres:

    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            host = config.read_string('postgres.host')
            port = config.read_int('postgres.port')
            user = config.read_string('postgres.username')
            pswd = config.read_string('postgres.password')
            dbname = config.read_string('postgres.dbname')
            cls._client = psycopg2.connect(
                host=host,
                port=port,
                dbname=dbname,
                user=user,
                password=pswd,
            )
        return cls._client


class Poloniex:

    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls._client = _Poloniex(
                config.read_string('poloniex.key', default=None),
                config.read_string('poloniex.secret', default=None),
            )
        return cls._client
