import os
import yaml
import shutil
import base64
import threading
from pathlib import Path

import traceback


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
        path = os.path.join(os.environ.get("GINKGO_DIR", self.get_conf_dir()), "config.yml")
        return path

    @property
    def secure_path(self) -> str:
        path = os.path.join(os.environ.get("GINKGO_DIR", self.get_conf_dir()), "secure.yml")
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
        Path(path).makedirs(parents=True, exist_ok=True)

    def generate_config_file(self, path=None) -> None:
        if path is None:
            path = self.get_conf_dir()

        current_path = os.getcwd()

        if not os.path.exists(os.path.join(path, "config.yml")):
            origin_path = os.path.join(current_path, "src/ginkgo/config/config.yml")
            target_path = os.path.join(path, "config.yml")
            shutil.copy(origin_path, target_path)
            print(f"Copy config.yml from {origin_path} to {target_path}")

        if not os.path.exists(os.path.join(path, "secure.yml")):
            origin_path = os.path.join(current_path, "src/ginkgo/config/secure.backup")
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
        key = "TELEGRAM_TOKEN"
        token = os.environ.get(key, None)
        if token is None:
            token = self._read_secure()["telegram"]["token"]
            token = str(token)
            os.environ[key] = token
        return token

    @property
    def TELEGRAM_PWD(self) -> str:
        key = "TELEGRAM_PWD"
        pwd = os.environ.get(key, None)
        if pwd is None:
            pwd = self._read_secure()["telegram"]["password"]
            pwd = str(pwd)
            os.environ[key] = pwd
        return pwd

    @property
    def Telegram_ChatIDs(self) -> list:
        return self._read_secure()["telegram"]["chatids"]

    @property
    def EPSILON(self) -> float:
        return float(self._read_config()["epsilon"])

    @property
    def LOGGING_PATH(self) -> str:
        key = "GINKGO_LOGGING_PATH"
        path = os.environ.get(key, None)
        if path is None:
            path = self._read_config()["log_path"]
            path = str(path)
            os.environ[key] = path
        return path

    def set_logging_path(self, path: str) -> None:
        self._write_config("log_path", path)

    @property
    def WORKING_PATH(self) -> str:
        key = "GINKGO_WORKING_PATH"
        path = os.environ.get(key, None)
        if path is None:
            path = self._read_config()["working_directory"]
            path = str(path)
            os.environ[key] = path
        return path

    def set_work_path(self, path: str) -> None:
        self._write_config("working_directory", path)

    @property
    def UNITTEST_PATH(self) -> str:
        key = "GINKGO_UNITTEST_PATH"
        path = os.environ.get(key, None)
        if path is None:
            path = self._read_config()["unittest_path"]
            path = str(path)
            os.environ[key] = path
        return path

    def set_unittest_path(self, path: str) -> None:
        self._write_config("unittest_path", path)

    @property
    def LOGGING_FILE_ON(self) -> str:
        key = "GINKGO_LOGGING_FILE_ON"
        on = os.environ.get(key, None)
        if on is None:
            on = self._read_config()["log_file_on"]
            on = str(on)
            os.environ[key] = on
        return bool(on)

    @property
    def LOGGING_DEFAULT_FILE(self) -> str:
        key = "GINKGO_LOGGING_DEFAULT_FILE"
        file = os.environ.get(key, None)
        if file is None:
            file = self._read_config()["log_default_file"]
            file = str(file)
            os.environ[key] = file
        return file

    @property
    def LOGGING_LEVEL_CONSOLE(self) -> str:
        key = "GINKGO_LOGGING_LEVEL_CONSOLE"
        level = os.environ.get(key, None)
        if level is None:
            level = self._read_config()["log_level_console"]
            level = str(level)
            os.environ[key] = level
        return level

    @property
    def LOGGING_LEVEL_FILE(self) -> str:
        key = "GINKGO_LOGGING_LEVEL_FILE"
        level = os.environ.get(key, None)
        if level is None:
            level = self._read_config()["log_level_file"]
            level = str(level)
            os.environ[key] = level
        return level

    @property
    def LOGGING_COLOR(self) -> dict:
        # Turn on/off the logging
        return self._read_config()["log_color"]

    @property
    def CLICKDB(self) -> str:
        key = "GINKGO_CLICK_DB"
        db = os.environ.get(key, None)
        if db is None:
            db = self._read_secure()["database"]["clickhouse"]["database"]
            db = str(db)
            os.environ[key] = db
        return db

    @property
    def MYSQLDB(self) -> str:
        key = "GINKGO_MYSQL_DB"
        db = os.environ.get(key, None)
        if db is None:
            db = self._read_secure()["database"]["mysql"]["database"]
            db = str(db)
            os.environ[key] = db
        return db

    @property
    def MONGODB(self) -> str:
        key = "GINKGO_MONGO_DB"
        db = os.environ.get(key, None)
        if db is None:
            db = self._read_secure()["database"]["mongodb"]["database"]
            db = str(db)
            os.environ[key] = db
        return db

    @property
    def CLICKUSER(self) -> str:
        key = "GINKGO_CLICK_USER"
        user = os.environ.get(key, None)
        if user is None:
            user = self._read_secure()["database"]["clickhouse"]["username"]
            user = str(user)
            os.environ[key] = user
        return user

    @property
    def MYSQLUSER(self) -> str:
        key = "GINKGO_MYSQL_USER"
        user = os.environ.get(key, None)
        if user is None:
            user = self._read_secure()["database"]["mysql"]["username"]
            user = str(user)
            os.environ[key] = user
        return user

    @property
    def MONGOUSER(self) -> str:
        key = "GINKGO_MONGO_USER"
        user = os.environ.get(key, None)
        if user is None:
            user = self._read_secure()["database"]["mongodb"]["username"]
            user = str(user)
            os.environ[key] = user
        return user

    @property
    def CLICKPWD(self) -> str:
        """
        Password for clickhouse
        """
        key = "GINKGO_CLICK_PWD"
        pwd = os.environ.get(key, None)
        if pwd is None:
            pwd = self._read_secure()["database"]["clickhouse"]["password"]
            pwd = str(pwd)
            os.environ[key] = pwd
        pwd = base64.b64decode(pwd)
        pwd = str(pwd, "utf-8")
        pwd = pwd.replace("\n", "")
        return pwd

    @property
    def MYSQLPWD(self) -> str:
        """
        Password for clickhouse
        """
        key = "GINKGO_MYSQL_PWD"
        pwd = os.environ.get(key, None)
        if pwd is None:
            pwd = self._read_secure()["database"]["mysql"]["password"]
            pwd = str(pwd)
            os.environ[key] = pwd
        pwd = base64.b64decode(pwd)
        pwd = str(pwd, "utf-8")
        pwd = pwd.replace("\n", "")
        return pwd

    @property
    def MONGOPWD(self) -> str:
        key = "GINKGO_MONGO_PWD"
        pwd = os.environ.get(key, None)
        if pwd is None:
            pwd = self._read_secure()["database"]["mongodb"]["password"]
            pwd = str(pwd)
            os.environ[key] = pwd
        pwd = base64.b64decode(pwd)
        pwd = str(pwd, "utf-8")
        pwd = pwd.replace("\n", "")
        return pwd

    @property
    def CLICKHOST(self) -> int:
        key = "GINKGO_CLICK_HOST"
        host = os.environ.get(key, None)
        if host is None:
            host = self._read_secure()["database"]["clickhouse"]["host"]
            host = str(host)
            os.environ[key] = host
        return host

    @property
    def MYSQLHOST(self) -> int:
        key = "GINKGO_MYSQL_HOST"
        host = os.environ.get(key, None)
        if host is None:
            host = self._read_secure()["database"]["mysql"]["host"]
            host = str(host)
            os.environ[key] = host
        return host

    @property
    def MONGOHOST(self) -> int:
        key = "GINKGO_MONGO_HOST"
        host = os.environ.get(key, None)
        if host is None:
            host = self._read_secure()["database"]["mongodb"]["host"]
            host = str(host)
            os.environ[key] = host
        return host

    @property
    def CLICKPORT(self) -> int:
        on_dev = self.DEBUGMODE
        key = "GINKGO_CLICK_PORT"
        port = os.environ.get(key, None)
        if port is None:
            port = self._read_secure()["database"]["clickhouse"]["port"]
            port = str(port)
            os.environ[key] = port

        if on_dev:
            return f"1{port}"
        else:
            return port

    @property
    def MYSQLPORT(self) -> int:
        on_dev = self.DEBUGMODE
        key = "GINKGO_MYSQL_PORT"
        port = os.environ.get(key, None)
        if port is None:
            port = self._read_secure()["database"]["mysql"]["port"]
            port = str(port)
            os.environ[key] = port

        if on_dev:
            return f"1{port}"
        else:
            return port

    @property
    def MONGOPORT(self) -> int:
        on_dev = self.DEBUGMODE
        key = "GINKGO_MONGO_PORT"
        port = os.environ.get(key, None)
        if port is None:
            port = self._read_secure()["database"]["mongodb"]["port"]
            port = str(port)
            os.environ[key] = port

        if not on_dev:
            return f"1{port}"
        else:
            return port

    @property
    def KAFKAHOST(self) -> str:
        key = "GINKGO_KAFKA_HOST"
        host = os.environ.get(key, None)
        if host is None:
            host = self._read_secure()["database"]["kafka"]["host"]
            host = str(host)
            os.environ[key] = host
        return host

    @property
    def KAFKAPORT(self) -> str:
        key = "GINKGO_KAFKA_PORT"
        port = os.environ.get(key, None)
        if port is None:
            port = self._read_secure()["database"]["kafka"]["port"]
            port = str(port)
            os.environ[key] = port
        return port

    @property
    def REDISHOST(self) -> str:
        key = "GINKGO_REDIS_HOST"
        host = os.environ.get(key, None)
        if host is None:
            host = self._read_secure()["database"]["redis"]["host"]
            host = str(host)
            os.environ[key] = host
        return host

    @property
    def REDISPORT(self) -> str:
        key = "GINKGO_REDIS_PORT"
        port = os.environ.get(key, None)
        if port is None:
            port = self._read_secure()["database"]["redis"]["port"]
            port = str(port)
            os.environ[key] = port
        return port

    @property
    def HEARTBEAT(self) -> float:
        key = "GINKGO_HEARTBEAT"
        hb = os.environ.get(key, None)
        if hb is None:
            hb = self._read_config()["heart_beat"]
            hb = str(hb)
            os.environ[key] = hb
        return float(hb)

    @property
    def TUSHARETOKEN(self) -> str:
        key = "TUSHARE_TOKEN"
        token = os.environ.get(key, None)
        if token is None:
            token = self._read_secure()["tushare"]["token"]
            token = str(token)
            os.environ[key] = token
        return token

    @property
    def DEFAULTSTART(self) -> str:
        key = "GINKGO_DEFAULT_STARTDATE"
        date = os.environ.get(key, None)
        if date is None:
            date = self._read_config()["default_start"]
            date = str(date)
            os.environ[key] = date
        return date

    @property
    def DEFAULTEND(self) -> str:
        key = "GINKGO_DEFAULT_ENDDATE"
        date = os.environ.get(key, None)
        if date is None:
            date = self._read_config()["default_end"]
            date = str(date)
            os.environ[key] = date
        return date

    @property
    def DEBUGMODE(self) -> bool:
        key = "GINKGO_DEBUG_MODE"
        mode = os.environ.get(key, None)
        if mode is None:
            mode = self._read_config()["debug"]
            mode = str(mode)
            os.environ[key] = mode
        if mode.upper() == "TRUE":
            return True
        else:
            return False

    def set_debug(self, value: bool) -> None:
        key = "GINKGO_DEBUG_MODE"
        if isinstance(value, bool):
            self._write_config("debug", value)
            os.environ[key] = str(value)

    @property
    def CPURATIO(self) -> float:
        key = "GINKGO_CPU_RATIO"
        ratio = os.environ.get(key, None)
        if ratio is None:
            ratio = self._read_config()["cpu_ratio"]
            ratio = str(ratio)
            os.environ[key] = ratio
        return float(ratio)

    def set_cpu_ratio(self, value) -> None:
        key = "GINKGO_CPU_RATIO"
        if isinstance(value, float):
            self._write_config("cpu_ratio", value)
            os.environ[key] = str(value)

    @property
    def QUIET(self) -> bool:
        key = "GINKGO_QUIET"
        quiet = os.environ.get(key, None)
        if quiet is None:
            quiet = self._read_config()["quiet"]
            quiet = str(quiet)
            os.environ[key] = quiet
        if quiet.upper() == "TRUE":
            return True
        else:
            return False


GCONF = GinkgoConfig()
