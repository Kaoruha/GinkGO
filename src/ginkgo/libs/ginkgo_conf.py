import yaml
import shutil
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
        pass

    @property
    def setting_path(self) -> str:
        path = os.path.join(
            os.environ.get("GINKGO_DIR", self.get_conf_dir()), "config.yml"
        )
        return path

    @property
    def secure_path(self) -> str:
        path = os.path.join(
            os.environ.get("GINKGO_DIR", self.get_conf_dir()), "secure.yml"
        )
        return path

    def get_conf_dir(self) -> str:
        root = os.environ.get("GINKGO_DIR", None)
        if root is None:
            root = os.path.expanduser("~/.ginkgo")
            os.environ["GINKGO_DIR"] = root
        return root

    def ensure_dir(self, path: str) -> None:
        if os.path.exists(path) and os.path.isdir(path):
            return
        os.makedirs(path)

    def generate_config_file(self, path=None) -> None:
        if path is None:
            path = self.get_conf_dir()

        self.ensure_dir(path)
        current_path = os.path.abspath(__file__)

        if not os.path.exists(os.path.join(path, "config.yml")):
            origin_path = os.path.join(
                os.path.dirname(current_path), "../config/config.yml"
            )
            target_path = os.path.join(path, "config.yml")
            shutil.copy(origin_path, target_path)
            print(f"Copy config.yml from {origin_path} to {target_path}")

        if not os.path.exists(os.path.join(path, "secure.yml")):
            origin_path = os.path.join(
                os.path.dirname(current_path), "../config/secure.yml"
            )
            target_path = os.path.join(path, "secure.yml")
            print(f"Copy secure.yml from {origin_path} to {target_path}")
            shutil.copy(origin_path, target_path)

    def _read_config(self) -> dict:
        self.generate_config_file()
        try:
            with open(self.setting_path, "r") as file:
                r = yaml.safe_load(file)
            return r
        except Exception as e:
            print(e)
            return {}

    def _read_secure(self) -> dict:
        self.generate_config_file()
        try:
            with open(self.secure_path, "r") as file:
                r = yaml.safe_load(file)
            return r
        except Exception as e:
            print(e)
            return {}

    def _write_config(self, key: str, value: any) -> None:
        try:
            with open(self.setting_path, "r") as file:
                data = yaml.safe_load(file)
            data[key] = value
            with open(self.setting_path, "w") as file:
                yaml.safe_dump(data, file)
        except Exception as e:
            print(e)
            return {}

    @property
    def Telegram_Token(self) -> str:
        return self._read_secure()["telegram"]["token"]

    @property
    def EPSILON(self) -> float:
        return float(self._read_config()["epsilon"])

    @property
    def LOGGING_PATH(self) -> str:
        # Where to store the log files
        return self._read_config()["log_path"]

    def set_logging_path(self, path: str) -> None:
        self._write_config("log_path", path)

    @property
    def WORKING_PATH(self) -> str:
        # Where to store the log files
        return self._read_config()["working_directory"]

    def set_work_path(self, path: str) -> None:
        self._write_config("working_directory", path)

    @property
    def UNITTEST_PATH(self) -> str:
        # Where to store the log files
        return self._read_config()["unittest_path"]

    def set_unittest_path(self, path: str) -> None:
        self._write_config("unittest_path", path)

    @property
    def LOGGING_FILE_ON(self) -> str:
        # Turn on/off the logging
        return self._read_config()["log_file_on"]

    @property
    def LOGGING_DEFAULT_FILE(self) -> str:
        # Turn on/off the logging
        return self._read_config()["log_default_file"]

    @property
    def LOGGING_LEVEL_CONSOLE(self) -> str:
        # Turn on/off the logging
        return self._read_config()["log_level_console"]

    @property
    def LOGGING_LEVEL_FILE(self) -> str:
        # Turn on/off the logging
        return self._read_config()["log_level_file"]

    @property
    def LOGGING_COLOR(self) -> dict:
        # Turn on/off the logging
        return self._read_config()["log_color"]

    @property
    def CLICKDB(self) -> str:
        r = ""
        try:
            r = self._read_secure()["database"]["clickhouse"]["database"]
        except Exception as e:
            r = "default"
        return r

    @property
    def MYSQLDB(self) -> str:
        r = ""
        try:
            r = self._read_secure()["database"]["mysql"]["database"]
        except Exception as e:
            r = "default"
        return r

    @property
    def MONGODB(self) -> str:
        r = ""
        try:
            r = self._read_secure()["database"]["mongodb"]["database"]
        except Exception as e:
            r = "default"
        return r

    @property
    def CLICKUSER(self) -> str:
        r = ""
        try:
            r = self._read_secure()["database"]["clickhouse"]["username"]
        except Exception as e:
            r = "default"
        return r

    @property
    def MYSQLUSER(self) -> str:
        r = ""
        try:
            r = self._read_secure()["database"]["mysql"]["username"]
        except Exception as e:
            r = "default"
        return r

    @property
    def MONGOUSER(self) -> str:
        r = ""
        try:
            r = self._read_secure()["database"]["mongodb"]["username"]
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
            r = self._read_secure()["database"]["clickhouse"]["password"]
            r = base64.b64decode(r)
            r = str(r, "utf-8")
            r = r.replace("\n", "")
        except Exception as e:
            r = "default"
        return r

    @property
    def MYSQLPWD(self) -> str:
        """
        Password for clickhouse
        """
        r = ""
        try:
            r = self._read_secure()["database"]["mysql"]["password"]
            r = base64.b64decode(r)
            r = str(r, "utf-8")
            r = r.replace("\n", "")
        except Exception as e:
            r = "default"
        return r

    @property
    def MONGOPWD(self) -> str:
        r = ""
        try:
            r = self._read_secure()["database"]["mongodb"]["password"]
            r = base64.b64decode(r)
            r = str(r, "utf-8")
        except Exception as e:
            r = "default"
        return r

    @property
    def CLICKHOST(self) -> int:
        r = ""
        r = self._read_secure()["database"]["clickhouse"]["host"]
        return r

    @property
    def MYSQLHOST(self) -> int:
        r = ""
        r = self._read_secure()["database"]["mysql"]["host"]
        return r

    @property
    def MONGOHOST(self) -> int:
        r = ""
        r = self._read_secure()["database"]["mongo"]["host"]
        return r

    @property
    def CLICKPORT(self) -> int:
        on_dev = self.DEBUGMODE

        r = self._read_secure()["database"]["clickhouse"]["port"]
        if not on_dev:
            return r
        else:
            return f"1{r}"

    @property
    def MYSQLPORT(self) -> int:
        on_dev = self.DEBUGMODE

        r = self._read_secure()["database"]["mysql"]["port"]
        if not on_dev:
            return r
        else:
            return f"1{r}"

    @property
    def MONGOPORT(self) -> int:
        on_dev = self.DEBUGMODE

        r = self._read_secure()["database"]["mongo"]["port"]
        if not on_dev:
            return r
        else:
            return f"1{r}"

    @property
    def REDISHOST(self) -> str:
        r = self._read_secure()["database"]["redis"]["host"]
        return r

    @property
    def REDISPORT(self) -> str:
        r = self._read_secure()["database"]["redis"]["port"]
        return r

    @property
    def HEARTBEAT(self) -> float:
        r = 0
        try:
            r = self._read_config()["heart_beat"]
        except Exception as e:
            r = 0
        return r

    @property
    def TUSHARETOKEN(self) -> str:
        r = ""
        try:
            r = self._read_secure()["tushare"]["token"]
        except Exception as e:
            pass
        return r

    @property
    def DEFAULTSTART(self) -> str:
        r = ""
        try:
            r = self._read_config()["default_start"]
        except Exception as e:
            pass
        return r

    @property
    def DEFAULTEND(self) -> str:
        r = ""
        try:
            r = self._read_config()["default_end"]
        except Exception as e:
            pass
        return r

    @property
    def DBDRIVER(self) -> str:
        r = ""
        try:
            r = self._read_config()["db_driver"]
        except Exception as e:
            pass
        return r

    @property
    def DEBUGMODE(self) -> bool:
        r = True
        try:
            r = self._read_config()["debug"]
        except Exception as e:
            pass
        return r

    def set_debug(self, value: bool) -> None:
        if isinstance(value, bool):
            self._write_config("debug", value)

    @property
    def CPURATIO(self) -> float:
        r = 0.4
        try:
            r = self._read_config()["cpu_ratio"]
        except Exception as e:
            pass
        return r

    def set_cpu_ratio(self, value) -> None:
        if isinstance(value, float):
            self._write_config("cpu_ratio", value)


GCONF = GinkgoConfig()
