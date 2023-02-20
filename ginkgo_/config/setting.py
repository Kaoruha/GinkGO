import logging

PACKAGE_NAME = "ginkgo"
VERSION = "0.1.30"
AUTHOR = "suny"
EMAIL = "sun159753@gmai.com"
DESCRIPTION = "my quant lib"
PACKAGE_URL = "url://"

# 开发/生产环境下相同的配置
DEBUG = True
TOKEN_EXPIRATION = 14  # Token过期时间（天）

# 日志设置
LOGGING_PATH = "./logs/"
LOGGIN_DEFAULT_FILE = "test.log"
LOGGING_FILE_ON = True
LOGGING_LEVEL_CONSOLE = logging.DEBUG
LOGGING_LEVEL_FILE = logging.DEBUG
LOGGING_COLOR = {
    "DEBUG": "white",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold_red",
}
