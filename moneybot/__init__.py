# -*- coding: utf-8 -*-
import logging

import staticconf


CONFIG_NS = 'moneybot'


logging.basicConfig(
    format='[%(asctime)s %(levelname)s %(name)s] %(message)s',
)
config = staticconf.NamespaceReaders(CONFIG_NS)


def load_config(path):
    staticconf.YamlConfiguration(path, namespace=CONFIG_NS)
