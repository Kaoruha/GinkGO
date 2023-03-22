import yaml
import base64
import threading


class GinkgoConfig(object):
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> object:
        if not hasattr(GinkgoConfig, "_instance"):
            with GinkgoConfig._instance_lock:
                if not hasattr(GinkgoConfig, "_instance"):
                    GinkgoConfig._instance = object.__new__(cls)
        return GinkgoConfig._instance

    def __init__(self) -> None:
        self.setting_path = "./ginkgo/config/config.yml"
        self.secure_path = "./ginkgo/config/secure.yml"

    def __read_config(self) -> dict:
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
        return self.__read_config()["LOGGING_PATH"]

    @property
    def LOGGING_FILE_ON(self) -> str:
        # Turn on/off the logging
        return self.__read_config()["LOGGING_FILE_ON"]

    @property
    def LOGGING_DEFAULT_FILE(self) -> str:
        # Turn on/off the logging
        # return self.__read_config()["LOGGING_DEFAULT_FILE"]
        return self.__read_config()["LOGGIN_DEFAULT_FILE"]

    @property
    def LOGGING_LEVEL_CONSOLE(self) -> str:
        # Turn on/off the logging
        return self.__read_config()["LOGGING_LEVEL_CONSOLE"]

    @property
    def LOGGING_LEVEL_FILE(self) -> str:
        # Turn on/off the logging
        return self.__read_config()["LOGGING_LEVEL_CONSOLE"]

    @property
    def LOGGING_COLOR(self) -> dict:
        # Turn on/off the logging
        return self.__read_config()["LOGGING_COLOR"]

    @property
    def CLICKDB(self) -> str:
        r = ""
        try:
            r = self.__read_secure()["database"]["clickhouse"]["database"]
        except Exception as e:
            r = "default"
        return r

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


GINKGOCONF = GinkgoConfig()