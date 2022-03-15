import logging
from ..config.setting import LOGGING_LEVEL


class GinkgoLogger(object):
    def __init__(self):
        logging.basicConfig(
            level=LOGGING_LEVEL,
            format=
            '%(asctime)s [%(levelname)s] %(message)s (%(filename)s:L%(lineno)d)',
            datefmt='%Y-%m-%d %H:%M:%S')

    def debug(self, message):
        logging.debug(message)

    def info(self, message):
        logging.info(message)

    def warning(self, message):
        logging.warning(message)

    def error(self, message):
        logging.error(message)

    def critical(self, message):
        logging.critical(message)


ginkgo_logger = GinkgoLogger()