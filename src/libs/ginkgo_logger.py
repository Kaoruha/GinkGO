import logging
import colorlog
from src.config.setting import (
    LOGGING_LEVEL_CONSOLE,
    LOGGING_LEVEL_FILE,
    LOGGING_COLOR,
    LOGGING_PATH,
    LOGGING_FILE_ON
    )


class GinkgoLogging(object):
    def __init__(self, logger_name) -> None:
        super().__init__()
        self.logger = logging.getLogger(logger_name)
        console_handler = logging.StreamHandler()
        file_handler = logging.FileHandler(filename=LOGGING_PATH, mode='a')

        # 设置日志级别，会以最高级别为准
        self.logger.setLevel(logging.DEBUG)
        console_handler.setLevel(LOGGING_LEVEL_CONSOLE)
        file_handler.setLevel(LOGGING_LEVEL_FILE)

        # 日志输出格式
        file_formatter = logging.Formatter(
            fmt='[%(asctime)s.%(msecs)03d][%(levelname)s]:%(message)s  %(filename)s -> %(funcName)s line:%(lineno)d ',
            datefmt='%Y-%m-%d  %H:%M:%S'
            )
        console_formatter = colorlog.ColoredFormatter(
            fmt='%(log_color)s%(asctime) s[%(levelname)s] %(message)s [%(filename)s->%(funcName)s L:%(lineno)d]',
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors=LOGGING_COLOR
        )
        console_handler.setFormatter(console_formatter)
        file_handler.setFormatter(file_formatter)
        
        # 添加日志处理
        self.logger.addHandler(console_handler)
        if LOGGING_FILE_ON:
            self.logger.addHandler(file_handler)


ginkgo_logger = GinkgoLogging('GinkgoLogger').logger
