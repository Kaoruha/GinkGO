# 开发/生产环境下相同的配置
DEBUG = True
REMEMBER_COOKIE_DURATION = 14  # flask_login的Cookie过期时间（天）

STOCK_URL = 'resources/market_data/'

import logging
LOGGING_LEVEL = logging.DEBUG
