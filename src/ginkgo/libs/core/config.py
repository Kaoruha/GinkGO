import os
import yaml
import shutil
import base64
import threading
import time
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
        # 初始化缓存变量
        self._config_cache = {}
        self._config_mtime = 0
        self._secure_cache = {}
        self._secure_mtime = 0

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
        Path(path).mkdir(parents=True, exist_ok=True)

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
            # 检查文件修改时间
            current_mtime = os.path.getmtime(self.setting_path)

            # 如果文件已修改或缓存为空，重新读取
            if current_mtime != self._config_mtime or not self._config_cache:
                with open(self.setting_path, "r") as file:
                    config_data = yaml.safe_load(file)
                self._config_cache = config_data
                self._config_mtime = current_mtime
                print(f"[GCONF] Config cache updated (mtime: {current_mtime})")

            return self._config_cache
        except Exception as e:
            print(f"[GCONF] Error reading config: {e}")
            return {}

    def _read_secure(self) -> dict:
        self.generate_config_file()
        try:
            # 检查文件修改时间
            current_mtime = os.path.getmtime(self.secure_path)

            # 如果文件已修改或缓存为空，重新读取
            if current_mtime != self._secure_mtime or not self._secure_cache:
                with open(self.secure_path, "r") as file:
                    secure_data = yaml.safe_load(file)
                self._secure_cache = secure_data
                self._secure_mtime = current_mtime
                print(f"[GCONF] Secure cache updated (mtime: {current_mtime})")

            return self._secure_cache
        except Exception as e:
            print(f"[GCONF] Error reading secure config: {e}")
            return {}

    def _get_config(self, key: str, default: any = None, section: str = None) -> any:
        # 统一从缓存读取，不再使用环境变量
        if section is None:
            config = self._read_config()
        else:
            secure_data = self._read_secure()
            if section in ["clickhouse", "mysql", "mongodb", "redis", "kafka"]:
                config = secure_data.get("database", {}).get(section, {})
            else:
                config = secure_data.get(section, {})
        return config.get(key, default)

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
        path = self._get_config("log_path")
        if path is None:
            # 提供默认日志路径
            import os
            default_path = os.path.join(os.path.expanduser("~"), ".ginkgo", "logs")
            return default_path
        return path

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
        return self._get_config("log_default_file", "ginkgo.log")

    @property
    def LOGGING_LEVEL_CONSOLE(self) -> str:
        return self._get_config("log_level_console", "DEBUG")

    @property
    def LOGGING_LEVEL_FILE(self) -> str:
        return self._get_config("log_level_file", "CRITICAL")

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
        final_port = f"1{port}" if self.DEBUGMODE else port
        # 更新环境变量为最终的DEBUG模式计算值
        os.environ["GINKGO_CLICKHOUSE_PORT"] = str(final_port)
        return final_port

    @property
    def MYSQLPORT(self) -> int:
        port = self._get_config("port", section="mysql")
        final_port = f"1{port}" if self.DEBUGMODE else port
        # 更新环境变量为最终的DEBUG模式计算值
        os.environ["GINKGO_MYSQL_PORT"] = str(final_port)
        return final_port

    @property
    def MONGOPORT(self) -> int:
        port = self._get_config("port", section="mongodb")
        final_port = f"1{port}" if not self.DEBUGMODE else port
        # 更新环境变量为最终的DEBUG模式计算值
        if final_port is not None:
            os.environ["GINKGO_MONGODB_PORT"] = str(final_port)
        return final_port

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
            config = self._read_config()
            date = config.get("default_start", "19000101")  # 提供默认值
            date = str(date)
            os.environ[key] = date
        return date

    @property
    def DEFAULTEND(self) -> str:
        key = "GINKGO_DEFAULT_ENDDATE"
        date = os.environ.get(key, None)
        if date is None:
            config = self._read_config()
            date = config.get("default_end", "21000101")  # 提供默认值
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

    # 装饰器配置属性
    @property
    def DECORATOR_TIME_LOGGER_ENABLED(self) -> bool:
        """时间日志装饰器是否启用"""
        value = self._get_config("time_logger_enabled", True, "decorator")
        return str(value).upper() == "TRUE"

    def set_decorator_time_logger_enabled(self, enabled: bool) -> None:
        """设置时间日志装饰器启用状态"""
        config = self._read_config()
        if "decorator" not in config:
            config["decorator"] = {}
        config["decorator"]["time_logger_enabled"] = enabled
        with open(self.setting_path, "w") as file:
            yaml.safe_dump(config, file)
        os.environ["GINKGO_DECORATOR_TIME_LOGGER_ENABLED"] = str(enabled)

    @property
    def DECORATOR_TIME_LOGGER_THRESHOLD(self) -> float:
        """时间日志装饰器阈值（秒）"""
        value = self._get_config("time_logger_threshold", 0.1, "decorator")
        return float(value)

    def set_decorator_time_logger_threshold(self, threshold: float) -> None:
        """设置时间日志装饰器阈值"""
        config = self._read_config()
        if "decorator" not in config:
            config["decorator"] = {}
        config["decorator"]["time_logger_threshold"] = threshold
        with open(self.setting_path, "w") as file:
            yaml.safe_dump(config, file)
        os.environ["GINKGO_DECORATOR_TIME_LOGGER_THRESHOLD"] = str(threshold)

    @property
    def DECORATOR_TIME_LOGGER_PROFILE_MODE(self) -> bool:
        """时间日志装饰器性能分析模式"""
        value = self._get_config("time_logger_profile_mode", False, "decorator")
        return str(value).upper() == "TRUE"

    def set_decorator_time_logger_profile_mode(self, profile_mode: bool) -> None:
        """设置时间日志装饰器性能分析模式"""
        config = self._read_config()
        if "decorator" not in config:
            config["decorator"] = {}
        config["decorator"]["time_logger_profile_mode"] = profile_mode
        with open(self.setting_path, "w") as file:
            yaml.safe_dump(config, file)
        os.environ["GINKGO_DECORATOR_TIME_LOGGER_PROFILE_MODE"] = str(profile_mode)

    @property
    def DECORATOR_RETRY_ENABLED(self) -> bool:
        """重试装饰器是否启用"""
        value = self._get_config("retry_enabled", True, "decorator")
        return str(value).upper() == "TRUE"

    @property
    def DECORATOR_RETRY_MAX_ATTEMPTS(self) -> int:
        """重试装饰器最大尝试次数"""
        value = self._get_config("retry_max_attempts", 3, "decorator")
        return int(value)

    @property
    def DECORATOR_RETRY_BACKOFF_FACTOR(self) -> float:
        """重试装饰器退避因子"""
        value = self._get_config("retry_backoff_factor", 2.0, "decorator")
        return float(value)

    @property
    def DECORATOR_CACHE_ENABLED(self) -> bool:
        """缓存装饰器是否启用"""
        value = self._get_config("cache_enabled", True, "decorator")
        return str(value).upper() == "TRUE"

    @property
    def DECORATOR_CACHE_DEFAULT_TTL(self) -> int:
        """缓存装饰器默认TTL（秒）"""
        value = self._get_config("cache_default_ttl", 300, "decorator")
        return int(value)

    # 数据源重试策略配置
    def get_datasource_retry_config(self, source_name: str) -> dict:
        """获取特定数据源的重试配置"""
        config = self._read_config()
        data_sources = config.get("data_sources", {})
        source_config = data_sources.get(source_name.lower(), {})
        
        return {
            "retry_enabled": source_config.get("retry_enabled", True),
            "retry_max_attempts": source_config.get("retry_max_attempts", self.DECORATOR_RETRY_MAX_ATTEMPTS),
            "retry_backoff_factor": source_config.get("retry_backoff_factor", self.DECORATOR_RETRY_BACKOFF_FACTOR)
        }
    
    def get_tushare_retry_config(self) -> dict:
        """获取TuShare重试配置"""
        return self.get_datasource_retry_config("tushare")
    
    def get_baostock_retry_config(self) -> dict:
        """获取BaoStock重试配置"""
        return self.get_datasource_retry_config("baostock")
    
    def get_tdx_retry_config(self) -> dict:
        """获取TDX重试配置"""
        return self.get_datasource_retry_config("tdx")
    
    def get_yahoo_retry_config(self) -> dict:
        """获取Yahoo重试配置"""
        return self.get_datasource_retry_config("yahoo")

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
