#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup


setup(
    name='moneybot',
    version='0.0.4',

    packages=find_packages(),

    install_requires=[
        'funcy',
        'numpy',
        'pandas',
        'psycopg2',
        'pyloniex>=0.0.4',
        'PyStaticConfiguration[yaml]',
        'requests',
    ],

    author='Nick Merrill',
    author_email='yes@cosmopol.is',
    description='backtest (and deploy) cryptocurrency trading strategies',
    url='https://github.com/elsehow/moneybot',
)
