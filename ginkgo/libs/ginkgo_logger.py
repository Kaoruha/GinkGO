import os
import logging
import colorlog
import threading
from ginkgo.libs.ginkgo_conf import GCONF

# Read Configure
LOGGING_LEVEL_CONSOLE = GCONF.LOGGING_LEVEL_CONSOLE
LOGGING_LEVEL_FILE = GCONF.LOGGING_LEVEL_FILE
LOGGING_COLOR = GCONF.LOGGING_COLOR
LOGGING_PATH = GCONF.LOGGING_PATH
LOGGIN_DEFAULT_FILE = GCONF.LOGGING_DEFAULT_FILE
LOGGING_FILE_ON = GCONF.LOGGING_FILE_ON


class GinkgoLogger(object):
    # singleton
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> object:
        if not hasattr(GinkgoLogger, "_instance"):
            with GinkgoLogger._instance_lock:
                if not hasattr(GinkgoLogger, "_instance"):
                    GinkgoLogger._instance = object.__new__(cls)
        return GinkgoLogger._instance

    def __init__(self, logger_name, file_name=None) -> None:
        super().__init__()

        if not os.path.exists(LOGGING_PATH):
            os.mkdir(LOGGING_PATH)
            print(f"Create folder {LOGGING_PATH}")

        if file_name:
            self.file_name = file_name
        else:
            self.file_name = LOGGIN_DEFAULT_FILE

        self.logger = logging.getLogger(logger_name)
        console_handler = logging.StreamHandler()
        self.file_handler = logging.FileHandler(
            filename=LOGGING_PATH + self.file_name, encoding="utf-8", mode="a"
        )

        # 设置日志级别，会以最高级别为准
        self.logger.setLevel(logging.DEBUG)
        console_handler.setLevel(self.get_log_level(LOGGING_LEVEL_CONSOLE))
        self.file_handler.setLevel(self.get_log_level(LOGGING_LEVEL_FILE))

        # 日志输出格式
        file_formatter = logging.Formatter(
            fmt="[%(asctime)s.%(msecs)03d][%(levelname)s]:%(message)s  %(filename)s -> %(funcName)s line:%(lineno)d ",
            datefmt="%Y-%m-%d  %H:%M:%S",
        )
        console_formatter = colorlog.ColoredFormatter(
            # fmt="%(log_color)s%(asctime) s[%(levelname)s] %(message)s [%(filename)s->%(funcName)s L:%(lineno)d]",
            fmt="%(log_color)s%(asctime) s PID:%(process)d [%(levelname)s] %(message)s  [%(filename)s --> %(funcName)s L:%(lineno)d]",
            # datefmt="%Y-%m-%d %H:%M:%S",
            datefmt="%H:%M:%S",
            log_colors=LOGGING_COLOR,
        )
        console_handler.setFormatter(console_formatter)
        self.file_handler.setFormatter(file_formatter)

        # 添加日志处理
        self.logger.addHandler(console_handler)
        if LOGGING_FILE_ON:
            self.logger.addHandler(self.file_handler)

    def reset_logfile(self, file_name: str) -> None:
        if not LOGGING_FILE_ON:
            return
        self.logger.removeHandler(self.file_handler)
        self.file_handler = logging.FileHandler(
            filename=LOGGING_PATH + file_name, encoding="utf-8", mode="a"
        )
        file_formatter = logging.Formatter(
            fmt="[%(asctime)s.%(msecs)03d][%(levelname)s]:%(message)s  %(filename)s -> %(funcName)s line:%(lineno)d ",
            datefmt="%Y-%m-%d  %H:%M:%S",
        )
        self.file_handler.setFormatter(file_formatter)
        self.logger.addHandler(self.file_handler)

    def get_log_level(self, level) -> int:
        r = 10
        if level == "DEBUG":
            r = 10
        elif level == "INFO":
            r = 20
        elif level == "WARNING":
            r = 30
        elif level == "ERROR":
            r = 40
        elif level == "CRITICAL":
            r = 50
        return r

    def INFO(self, msg: str):
        self.logger.info(msg)

    def DEBUG(self, msg: str):
        self.logger.debug(msg)

    def WARN(self, msg: str):
        self.logger.warn(msg)

    def CRITICAL(self, msg: str):
        self.logger.critical(msg)


GLOG = GinkgoLogger("ginkgo_log")
