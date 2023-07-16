import yaml
import base64
import threading
import os


class GinkgoConfig(object):
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> object:
        if not hasattr(GinkgoConfig, "_instance"):
            with GinkgoConfig._instance_lock:
                if not hasattr(GinkgoConfig, "_instance"):
                    GinkgoConfig._instance = object.__new__(cls)
        return GinkgoConfig._instance

    def __init__(self) -> None:
        current_path = os.path.abspath(__file__)
        self.setting_path = os.path.join(
            os.path.dirname(current_path), "../config/config.yml"
        )
        self.secure_path = os.path.join(
            os.path.dirname(current_path), "../config/secure.yml"
        )
        # self.setting_path = "./ginkgo/config/config.yml"
        # self.secure_path = "./ginkgo/config/secure.yml"

    def __read_config(self) -> dict:
        os.system("pwd")
        with open(self.setting_path, "r") as file:
            r = yaml.safe_load(file)
        return r

    def __read_secure(self) -> dict:
        with open(self.secure_path, "r") as file:
            r = yaml.safe_load(file)
        return r

    @property
    def LOGGING_PATH(self) -> str:
        # Where to store the log files
        return self.__read_config()["log_path"]

    @property
    def LOGGING_FILE_ON(self) -> str:
        # Turn on/off the logging
        return self.__read_config()["log_file_on"]

    @property
    def LOGGING_DEFAULT_FILE(self) -> str:
        # Turn on/off the logging
        return self.__read_config()["log_default_file"]

    @property
    def LOGGING_LEVEL_CONSOLE(self) -> str:
        # Turn on/off the logging
        return self.__read_config()["log_level_console"]

    @property
    def LOGGING_LEVEL_FILE(self) -> str:
        # Turn on/off the logging
        return self.__read_config()["log_level_file"]

    @property
    def LOGGING_COLOR(self) -> dict:
        # Turn on/off the logging
        return self.__read_config()["log_color"]

    @property
    def CLICKDB(self) -> str:
        on_dev = self.__read_config()["debug"]
        if not on_dev:
            r = ""
            try:
                r = self.__read_secure()["database"]["clickhouse"]["database"]
            except Exception as e:
                r = "default"
            return r
        else:
            return "testdb"

    @property
    def CLICKUSER(self) -> str:
        r = ""
        try:
            r = self.__read_secure()["database"]["clickhouse"]["username"]
        except Exception as e:
            r = "default"
        return r

    @property
    def CLICKPWD(self) -> str:
        """
        Password for clickhouse
        """
        r = ""
        try:
            r = self.__read_secure()["database"]["clickhouse"]["password"]
            r = base64.b64decode(r)
            r = str(r, "utf-8")
        except Exception as e:
            r = "default"
        return r

    @property
    def CLICKHOST(self) -> int:
        r = ""
        r = self.__read_secure()["database"]["clickhouse"]["host"]
        return r

    @property
    def CLICKPORT(self) -> int:
        r = ""
        r = self.__read_secure()["database"]["clickhouse"]["port"]
        return r

    @property
    def MONGODB(self) -> str:
        r = ""
        try:
            r = self.__read_secure()["database"]["mongodb"]["database"]
        except Exception as e:
            r = "default"
        return r

    @property
    def MONGOUSER(self) -> str:
        r = ""
        try:
            r = self.__read_secure()["database"]["mongodb"]["username"]
        except Exception as e:
            r = "default"
        return r

    @property
    def MONGOPWD(self) -> str:
        r = ""
        try:
            r = self.__read_secure()["database"]["mongodb"]["password"]
            r = base64.b64decode(r)
            r = str(r, "utf-8")
        except Exception as e:
            r = "default"
        return r

    @property
    def DBDRIVER(self) -> str:
        r = ""
        try:
            r = self.__read_config()["db_driver"]
        except Exception as e:
            r = "default"
        return r

    @property
    def HEARTBEAT(self) -> float:
        r = 0
        try:
            r = self.__read_config()["heart_beat"]
        except Exception as e:
            r = 0
        return r

    @property
    def TUSHARETOKEN(self) -> str:
        r = ""
        try:
            r = self.__read_secure()["tushare"]["token"]
        except Exception as e:
            pass
        return r

    @property
    def DEFAULTSTART(self) -> str:
        r = ""
        try:
            r = self.__read_config()["default_start"]
        except Exception as e:
            pass
        return r

    @property
    def DEFAULTEND(self) -> str:
        r = ""
        try:
            r = self.__read_config()["default_end"]
        except Exception as e:
            pass
        return r


GCONF = GinkgoConfig()
