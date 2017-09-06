# -*- coding: utf-8 -*-
import psycopg2
from pyloniex import PoloniexPrivateAPI
from pyloniex import PoloniexPublicAPI

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

    _private = None

    @classmethod
    def get_private(cls) -> PoloniexPrivateAPI:
        if cls._private is None:
            cls._private = PoloniexPrivateAPI(
                key=config.read_string('poloniex.key'),
                secret=config.read_string('poloniex.secret'),
            )
        return cls._private

    _public = None

    @classmethod
    def get_public(cls) -> PoloniexPublicAPI:
        if cls._public is None:
            cls._public = PoloniexPublicAPI()
        return cls._public
