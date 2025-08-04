import os
import yaml
import shutil
import base64
import threading
from pathlib import Path


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

    def _get_config(self, key: str, default: any = None, section: str = None) -> any:
        if section:
            env_key = f"GINKGO_{section.upper()}_{key.upper()}"
        else:
            env_key = f"GINKGO_{key.upper()}"
        value = os.environ.get(env_key, None)
        if value is None:
            if section is None:
                config = self._read_config()
            else:
                secure_data = self._read_secure()
                if section in ["clickhouse", "mysql", "mongodb", "redis", "kafka"]:
                    config = secure_data.get("database", {}).get(section, {})
                else:
                    config = secure_data.get(section, {})
            value = config.get(key, default)
            if value is not None:
                os.environ[env_key] = str(value)
        return value

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
        return self._get_config("token", section="telegram")

    @property
    def TELEGRAM_PWD(self) -> str:
        return self._get_config("password", section="telegram")

    @property
    def Telegram_ChatIDs(self) -> list:
        return self._get_config("chatids", section="telegram")

    @property
    def EPSILON(self) -> float:
        return float(self._get_config("epsilon"))

    @property
    def LOGGING_PATH(self) -> str:
        return self._get_config("log_path")

    def set_logging_path(self, path: str) -> None:
        self._write_config("log_path", path)

    @property
    def WORKING_PATH(self) -> str:
        return self._get_config("working_directory")

    def set_work_path(self, path: str) -> None:
        self._write_config("working_directory", path)

    @property
    def UNITTEST_PATH(self) -> str:
        return self._get_config("unittest_path")

    def set_unittest_path(self, path: str) -> None:
        self._write_config("unittest_path", path)

    @property
    def LOGGING_FILE_ON(self) -> str:
        return bool(self._get_config("log_file_on"))

    @property
    def LOGGING_DEFAULT_FILE(self) -> str:
        return self._get_config("log_default_file")

    @property
    def LOGGING_LEVEL_CONSOLE(self) -> str:
        return self._get_config("log_level_console")

    @property
    def LOGGING_LEVEL_FILE(self) -> str:
        return self._get_config("log_level_file")

    @property
    def LOGGING_COLOR(self) -> dict:
        return self._get_config("log_color")

    @property
    def CLICKDB(self) -> str:
        return self._get_config("database", section="clickhouse")

    @property
    def MYSQLDB(self) -> str:
        return self._get_config("database", section="mysql")

    @property
    def MONGODB(self) -> str:
        return self._get_config("database", section="mongodb")

    @property
    def CLICKUSER(self) -> str:
        return self._get_config("username", section="clickhouse")

    @property
    def MYSQLUSER(self) -> str:
        return self._get_config("username", section="mysql")

    @property
    def MONGOUSER(self) -> str:
        return self._get_config("username", section="mongodb")

    @property
    def CLICKPWD(self) -> str:
        """
        Password for clickhouse
        """
        pwd = self._get_config("password", section="clickhouse")
        pwd = base64.b64decode(pwd)
        pwd = str(pwd, "utf-8")
        pwd = pwd.replace("\n", "")
        return pwd

    @property
    def MYSQLPWD(self) -> str:
        """
        Password for clickhouse
        """
        pwd = self._get_config("password", section="mysql")
        pwd = base64.b64decode(pwd)
        pwd = str(pwd, "utf-8")
        pwd = pwd.replace("\n", "")
        return pwd

    @property
    def MONGOPWD(self) -> str:
        pwd = self._get_config("password", section="mongodb")
        pwd = base64.b64decode(pwd)
        pwd = str(pwd, "utf-8")
        pwd = pwd.replace("\n", "")
        return pwd

    @property
    def CLICKHOST(self) -> int:
        return self._get_config("host", section="clickhouse")

    @property
    def MYSQLHOST(self) -> int:
        return self._get_config("host", section="mysql")

    @property
    def MONGOHOST(self) -> int:
        return self._get_config("host", section="mongodb")

    @property
    def CLICKPORT(self) -> int:
        port = self._get_config("port", section="clickhouse")
        if self.DEBUGMODE:
            return f"1{port}"
        else:
            return port

    @property
    def MYSQLPORT(self) -> int:
        port = self._get_config("port", section="mysql")
        if self.DEBUGMODE:
            return f"1{port}"
        else:
            return port

    @property
    def MONGOPORT(self) -> int:
        port = self._get_config("port", section="mongodb")
        if not self.DEBUGMODE:
            return f"1{port}"
        else:
            return port

    @property
    def KAFKAHOST(self) -> str:
        return self._get_config("host", section="kafka")

    @property
    def KAFKAPORT(self) -> str:
        return self._get_config("port", section="kafka")

    @property
    def REDISHOST(self) -> str:
        return self._get_config("host", section="redis")

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
            value = str(value)
            os.environ[key] = value

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

    @property
    def PYTHONPATH(self) -> str:
        key = "GINKGO_PYTHON_PATH"
        ratio = os.environ.get(key, None)
        if ratio is None:
            ratio = self._read_config()["python_path"]
            ratio = str(ratio)
            os.environ[key] = ratio
        return str(ratio)

    def set_python_path(self, value) -> None:
        # import pdb
        # pdb.set_trace()
        key = "GINKGO_PYTHON_PATH"
        if isinstance(value, str):
            self._write_config("python_path", value)
            os.environ[key] = str(value)


GCONF = GinkgoConfig()
