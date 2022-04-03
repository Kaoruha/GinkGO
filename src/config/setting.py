# coding=utf-8
"""
Author: Kaoru
Date: 2021-12-24 23:46:54
LastEditTime: 2022-03-22 04:13:35
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/src/config/setting.py
What goes around comes around.
"""
import logging

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
