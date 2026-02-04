# Upstream: All Modules (全局访问GCONF获取配置)
# Downstream: Standard Library (os/yaml/threading)
# Role: GinkgoConfig全局配置管理器单例模式确保线程安全配置文件存储在~/.ginkgo提供get/set等方法






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
        # 文件存在性缓存（避免每次查询文件系统）
        self._has_local_config = None  # None=未检查, True=存在, False=不存在
        self._has_local_secure = None
        # 环境变量是否已初始化的标记
        self._env_vars_initialized = False

    def _ensure_env_vars(self) -> None:
        """
        确保环境变量已设置（从配置文件加载）
        只执行一次，将配置文件中的值设置到环境变量
        配置文件优先级最高：覆盖环境变量
        """
        if self._env_vars_initialized:
            return

        self.generate_config_file()

        # 如果有本地配置文件，将配置设置到环境变量（覆盖环境变量）
        if self._has_local_config:
            try:
                config = self._read_config()
                # 通知配置
                notifications = config.get("notifications", {})
                discord = notifications.get("discord", {})
                email = notifications.get("email", {})

                os.environ["GINKGO_NOTIFICATION_DISCORD_TIMEOUT"] = str(discord.get("timeout", 3))
                os.environ["GINKGO_NOTIFICATION_DISCORD_MAX_RETRIES"] = str(discord.get("max_retries", 3))
                os.environ["GINKGO_NOTIFICATION_EMAIL_TIMEOUT"] = str(email.get("timeout", 10))
                os.environ["GINKGO_NOTIFICATION_EMAIL_MAX_RETRIES"] = str(email.get("max_retries", 3))

                # Email SMTP 配置（从 config.yml）
                smtp_host = email.get("smtp_host", "")
                smtp_port = email.get("smtp_port", "")
                from_addr = email.get("from_address", "")
                from_name = email.get("from_name", "Ginkgo Notification")
                # 只有配置文件中有值时才设置（保留容器环境变量的优先级）
                if smtp_host:
                    os.environ["GINKGO_SMTP_HOST"] = smtp_host
                if smtp_port:
                    os.environ["GINKGO_SMTP_PORT"] = str(smtp_port)
                if from_addr:
                    os.environ["GINKGO_FROM_ADDRESS"] = from_addr
                os.environ["GINKGO_FROM_NAME"] = from_name
            except Exception as e:
                print(f"[GCONF] Error loading config to env: {e}")

        if self._has_local_secure:
            try:
                secure_data = self._read_secure()
                database = secure_data.get("database", {})

                # Kafka
                kafka = database.get("kafka", {})
                os.environ["GINKGO_KAFKA_HOST"] = kafka.get("host", "localhost")
                os.environ["GINKGO_KAFKA_PORT"] = str(kafka.get("port", "9092"))

                # Redis
                redis = database.get("redis", {})
                os.environ["GINKGO_REDIS_HOST"] = redis.get("host", "localhost")
                os.environ["GINKGO_REDIS_PORT"] = str(redis.get("port", "6379"))

                # ClickHouse
                clickhouse = database.get("clickhouse", {})
                os.environ["GINKGO_CLICKHOUSE_HOST"] = clickhouse.get("host", "localhost")
                os.environ["GINKGO_CLICKHOUSE_PORT"] = str(clickhouse.get("port", "8123"))
                os.environ["GINKGO_CLICKHOUSE_USER"] = clickhouse.get("username", "default")
                os.environ["GINKGO_CLICKHOUSE_PASSWORD"] = self._decode_password(clickhouse.get("password", ""))
                os.environ["GINKGO_CLICKHOUSE_DATABASE"] = clickhouse.get("database", "ginkgo")

                # MySQL
                mysql = database.get("mysql", {})
                os.environ["GINKGO_MYSQL_HOST"] = mysql.get("host", "localhost")
                os.environ["GINKGO_MYSQL_PORT"] = str(mysql.get("port", "3306"))
                os.environ["GINKGO_MYSQL_USER"] = mysql.get("username", "root")
                os.environ["GINKGO_MYSQL_PASSWORD"] = self._decode_password(mysql.get("password", ""))
                os.environ["GINKGO_MYSQL_DATABASE"] = mysql.get("database", "ginkgo")

                # MongoDB
                mongodb = database.get("mongodb", {})
                os.environ["GINKGO_MONGODB_HOST"] = mongodb.get("host", "localhost")
                os.environ["GINKGO_MONGODB_PORT"] = str(mongodb.get("port", "27017"))
                os.environ["GINKGO_MONGODB_USERNAME"] = mongodb.get("username", "root")
                os.environ["GINKGO_MONGODB_PASSWORD"] = self._decode_password(mongodb.get("password", ""))
                os.environ["GINKGO_MONGODB_DATABASE"] = mongodb.get("database", "ginkgo")

                # 通知系统敏感配置（从 secure.yml）
                notifications = secure_data.get("notifications", {})
                email_secure = notifications.get("email", {})
                smtp_user = email_secure.get("smtp_user", "")
                smtp_pwd = email_secure.get("smtp_password", "")
                if smtp_user:
                    os.environ["GINKGO_SMTP_USER"] = smtp_user
                if smtp_pwd:
                    os.environ["GINKGO_SMTP_PASSWORD"] = smtp_pwd

                # 数据源API密钥配置（从 secure.yml）
                data_sources = secure_data.get("data_sources", {})
                if data_sources:
                    eastmoney = data_sources.get("eastmoney", {})
                    if eastmoney.get("api_key"):
                        os.environ["GINKGO_EASTMONEY_API_KEY"] = eastmoney["api_key"]

                    alpaca = data_sources.get("alpaca", {})
                    if alpaca.get("api_key"):
                        os.environ["GINKGO_ALPACA_API_KEY"] = alpaca["api_key"]
                    if alpaca.get("api_secret"):
                        os.environ["GINKGO_ALPACA_API_SECRET"] = alpaca["api_secret"]

                    fushu = data_sources.get("fushu", {})
                    if fushu.get("api_key"):
                        os.environ["GINKGO_FUSHU_API_KEY"] = fushu["api_key"]
            except Exception as e:
                print(f"[GCONF] Error loading secure config to env: {e}")

        self._env_vars_initialized = True

    def _decode_password(self, pwd: str) -> str:
        """解码密码（Base64编码）"""
        if not pwd:
            return ""
        # 尝试Base64解码，如果能解码就返回解码值
        try:
            import base64
            decoded = base64.b64decode(pwd)
            decoded = str(decoded, "utf-8")
            return decoded.replace("\n", "")
        except Exception:
            # 解码失败，返回原值
            return pwd

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

        # 处理 config.yml
        config_path = os.path.join(path, "config.yml")
        if not os.path.exists(config_path):
            origin_path = os.path.join(current_path, "src/ginkgo/config/config.yml")
            if os.path.exists(origin_path):
                shutil.copy(origin_path, config_path)
                print(f"[GCONF] Copy config.yml from {origin_path} to {config_path}")
                self._has_local_config = True  # ✅ 更新缓存
            else:
                print(f"[GCONF] Source config not found, will use environment variables")
                self._has_local_config = False  # ✅ 更新缓存
        else:
            self._has_local_config = True  # ✅ 文件已存在

        # 处理 secure.yml
        secure_path = os.path.join(path, "secure.yml")
        if not os.path.exists(secure_path):
            origin_path = os.path.join(current_path, "src/ginkgo/config/secure.backup")
            if os.path.exists(origin_path):
                shutil.copy(origin_path, secure_path)
                print(f"[GCONF] Copy secure.yml from {origin_path} to {secure_path}")
                self._has_local_secure = True  # ✅ 更新缓存
            else:
                print(f"[GCONF] Source secure config not found, will use environment variables")
                self._has_local_secure = False  # ✅ 更新缓存
        else:
            self._has_local_secure = True  # ✅ 文件已存在

    def _read_config(self) -> dict:
        self.generate_config_file()
        # 如果缓存标记为无本地文件，直接返回空字典
        if self._has_local_config is False:
            return {}
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
        # 如果缓存标记为无本地文件，直接返回空字典
        if self._has_local_secure is False:
            return {}
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
        """
        配置获取优先级：
        1. 配置文件（如果存在）
        2. 环境变量 GINKGO_{KEY}
        3. 默认值

        支持嵌套路径：section 参数可以是 "notifications.email" 这样的路径
        """
        # 判断是否需要读取配置文件（使用缓存）
        if section is None:
            has_file = self._has_local_config
        else:
            has_file = self._has_local_secure

        # 优先级1: 尝试从配置文件读取
        if has_file:
            try:
                if section is None:
                    config = self._read_config()
                else:
                    secure_data = self._read_secure()
                    # 支持嵌套路径，如 "notifications.email"
                    if "." in section:
                        parts = section.split(".")
                        config = secure_data
                        for part in parts:
                            config = config.get(part, {})
                    elif section in ["clickhouse", "mysql", "mongodb", "redis", "kafka"]:
                        config = secure_data.get("database", {}).get(section, {})
                    else:
                        config = secure_data.get(section, {})

                # 如果配置文件中有该key且值不为None，直接返回
                if key in config and config[key] is not None:
                    return config[key]
            except Exception as e:
                print(f"[GCONF] Error reading config file: {e}")

        # 优先级2: 尝试环境变量
        env_key = f"GINKGO_{key.upper()}"
        env_value = os.environ.get(env_key)
        if env_value is not None:
            return env_value

        # 优先级3: 返回默认值
        return default

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
        """ClickHouse 数据库名（核心基础设施，有默认值）"""
        return self._get_config("database", "ginkgo", section="clickhouse")

    @property
    def MYSQLDB(self) -> str:
        """MySQL 数据库名（核心基础设施，有默认值）"""
        return self._get_config("database", "ginkgo", section="mysql")

    @property
    def MONGODB(self) -> str:
        """MongoDB 数据库名（核心基础设施，有默认值）"""
        return self._get_config("database", "ginkgo", section="mongodb")

    @property
    def CLICKUSER(self) -> str:
        """ClickHouse 用户名（核心基础设施，有默认值）"""
        self._ensure_env_vars()
        return os.environ.get("GINKGO_CLICKHOUSE_USER", "default")

    @property
    def MYSQLUSER(self) -> str:
        """MySQL 用户名（核心基础设施，有默认值）"""
        self._ensure_env_vars()
        return os.environ.get("GINKGO_MYSQL_USER", "root")

    @property
    def MONGOUSER(self) -> str:
        """MongoDB 用户名（敏感信息，无默认值）"""
        self._ensure_env_vars()
        if "GINKGO_MONGODB_USERNAME" not in os.environ or not os.environ["GINKGO_MONGODB_USERNAME"]:
            raise ValueError("GINKGO_MONGODB_USERNAME not configured")
        return os.environ["GINKGO_MONGODB_USERNAME"]

    @property
    def CLICKPWD(self) -> str:
        """ClickHouse 密码（敏感信息，无默认值）"""
        self._ensure_env_vars()
        if "GINKGO_CLICKHOUSE_PASSWORD" not in os.environ or not os.environ["GINKGO_CLICKHOUSE_PASSWORD"]:
            raise ValueError("GINKGO_CLICKHOUSE_PASSWORD not configured")
        return os.environ["GINKGO_CLICKHOUSE_PASSWORD"]

    @property
    def MYSQLPWD(self) -> str:
        """MySQL 密码（敏感信息，无默认值）"""
        self._ensure_env_vars()
        if "GINKGO_MYSQL_PASSWORD" not in os.environ or not os.environ["GINKGO_MYSQL_PASSWORD"]:
            raise ValueError("GINKGO_MYSQL_PASSWORD not configured")
        return os.environ["GINKGO_MYSQL_PASSWORD"]

    @property
    def MONGOPWD(self) -> str:
        """MongoDB 密码（敏感信息，无默认值）"""
        self._ensure_env_vars()
        if "GINKGO_MONGODB_PASSWORD" not in os.environ or not os.environ["GINKGO_MONGODB_PASSWORD"]:
            raise ValueError("GINKGO_MONGODB_PASSWORD not configured")
        return os.environ["GINKGO_MONGODB_PASSWORD"]

    @property
    def CLICKHOST(self) -> str:
        """ClickHouse 主机（核心基础设施，有默认值）"""
        self._ensure_env_vars()
        return os.environ.get("GINKGO_CLICKHOUSE_HOST", "localhost")

    @property
    def MYSQLHOST(self) -> str:
        """MySQL 主机（核心基础设施，有默认值）"""
        self._ensure_env_vars()
        return os.environ.get("GINKGO_MYSQL_HOST", "localhost")

    @property
    def MONGOHOST(self) -> str:
        """MongoDB 主机（核心基础设施，有默认值）"""
        self._ensure_env_vars()
        return os.environ.get("GINKGO_MONGODB_HOST", "localhost")

    @property
    def CLICKPORT(self) -> int:
        """ClickHouse 端口（核心基础设施，有默认值）"""
        self._ensure_env_vars()
        port = os.environ.get("GINKGO_CLICKHOUSE_PORT", "8123")
        # DEBUG 模式：端口首位 +1（例如 8123 -> 18123）
        # 检查是否已经是DEBUG模式端口（避免重复加前缀）
        if self.DEBUGMODE and not str(port).startswith("1"):
            port = f"1{port}"
        return int(port)

    @property
    def MYSQLPORT(self) -> int:
        """MySQL 端口（核心基础设施，有默认值）"""
        self._ensure_env_vars()
        port = os.environ.get("GINKGO_MYSQL_PORT", "3306")
        # DEBUG 模式：端口首位 +1（例如 3306 -> 13306）
        # 检查是否已经是DEBUG模式端口（避免重复加前缀）
        if self.DEBUGMODE and not str(port).startswith("1"):
            port = f"1{port}"
        return int(port)

    @property
    def MONGOPORT(self) -> int:
        """MongoDB 端口（核心基础设施，有默认值）"""
        self._ensure_env_vars()
        return int(os.environ.get("GINKGO_MONGODB_PORT", "27017"))

    @property
    def KAFKAHOST(self) -> str:
        """Kafka 主机（核心基础设施，有默认值）"""
        self._ensure_env_vars()
        return os.environ.get("GINKGO_KAFKA_HOST", "localhost")

    @property
    def KAFKAPORT(self) -> str:
        """Kafka 端口（核心基础设施，有默认值）"""
        self._ensure_env_vars()
        return os.environ.get("GINKGO_KAFKA_PORT", "9092")

    @property
    def REDISHOST(self) -> str:
        """Redis 主机（核心基础设施，有默认值）"""
        self._ensure_env_vars()
        return os.environ.get("GINKGO_REDIS_HOST", "localhost")

    @property
    def REDISPORT(self) -> str:
        """Redis 端口（核心基础设施，有默认值）"""
        self._ensure_env_vars()
        return os.environ.get("GINKGO_REDIS_PORT", "6379")

    @property
    def HEARTBEAT(self) -> float:
        """心跳间隔（环境标识，有默认值）"""
        key = "GINKGO_HEARTBEAT"
        hb = os.environ.get(key, None)
        if hb is None:
            config = self._read_config()
            hb = config.get("heart_beat", "0.1")
            hb = str(hb)
            os.environ[key] = hb
        return float(hb)

    @property
    def TUSHARETOKEN(self) -> str:
        key = "TUSHARE_TOKEN"
        token = os.environ.get(key, None)
        if token is None:
            secure_data = self._read_secure()
            # 安全地获取 tushare token
            if isinstance(secure_data, dict):
                tushare_config = secure_data.get("tushare", {})
                if isinstance(tushare_config, dict):
                    token = tushare_config.get("token", "")
                    if token:
                        token = str(token)
                        os.environ[key] = token
            # 如果没有找到 token，返回空字符串
            if not token:
                token = ""
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
        """DEBUG模式开关（环境标识，有默认值）"""
        key = "GINKGO_DEBUG_MODE"
        mode = os.environ.get(key, None)
        if mode is None:
            # 从配置文件读取（安全访问，添加默认值）
            config = self._read_config()
            mode = config.get("debug", "False")
            mode = str(mode)
            os.environ[key] = mode
        return mode.upper() == "TRUE"

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
        """CPU使用率（环境标识，有默认值）"""
        key = "GINKGO_CPU_RATIO"
        ratio = os.environ.get(key, None)
        if ratio is None:
            config = self._read_config()
            ratio = config.get("cpu_ratio", "0.8")
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
        """静默模式（环境标识，有默认值）"""
        key = "GINKGO_QUIET"
        quiet = os.environ.get(key, None)
        if quiet is None:
            config = self._read_config()
            quiet = config.get("quiet", "False")
            quiet = str(quiet)
            os.environ[key] = quiet
        return quiet.upper() == "TRUE"

    @property
    def PYTHONPATH(self) -> str:
        """Python路径（环境标识，有默认值）"""
        key = "GINKGO_PYTHON_PATH"
        path = os.environ.get(key, None)
        if path is None:
            config = self._read_config()
            path = config.get("python_path", "")
            path = str(path)
            os.environ[key] = path
        return str(path)

    def set_python_path(self, value) -> None:
        # import pdb
        # pdb.set_trace()
        key = "GINKGO_PYTHON_PATH"
        if isinstance(value, str):
            self._write_config("python_path", value)
            os.environ[key] = str(value)

    # ==================== 通知超时配置 ====================

    @property
    def NOTIFICATION_DISCORD_TIMEOUT(self) -> int:
        """
        Discord Webhook 请求超时时间（秒）

        默认值: 3秒
        配置路径: notifications.discord.timeout
        """
        key = "GINKGO_NOTIFICATION_DISCORD_TIMEOUT"
        timeout = os.environ.get(key, None)
        if timeout is None:
            # 尝试从配置文件读取
            config = self._read_config()
            notifications = config.get("notifications", {})
            discord = notifications.get("discord", {})
            timeout = discord.get("timeout", 3)  # 默认 3 秒
            os.environ[key] = str(timeout)
        return int(timeout)

    @property
    def NOTIFICATION_EMAIL_TIMEOUT(self) -> int:
        """
        Email SMTP 请求超时时间（秒）

        默认值: 10秒
        配置路径: notifications.email.timeout
        """
        key = "GINKGO_NOTIFICATION_EMAIL_TIMEOUT"
        timeout = os.environ.get(key, None)
        if timeout is None:
            # 尝试从配置文件读取
            config = self._read_config()
            notifications = config.get("notifications", {})
            email = notifications.get("email", {})
            timeout = email.get("timeout", 10)  # 默认 10 秒
            os.environ[key] = str(timeout)
        return int(timeout)

    @property
    def NOTIFICATION_DISCORD_MAX_RETRIES(self) -> int:
        """
        Discord Webhook 最大重试次数

        默认值: 3
        配置路径: notifications.discord.max_retries
        """
        key = "GINKGO_NOTIFICATION_DISCORD_MAX_RETRIES"
        retries = os.environ.get(key, None)
        if retries is None:
            config = self._read_config()
            notifications = config.get("notifications", {})
            discord = notifications.get("discord", {})
            retries = discord.get("max_retries", 3)  # 默认 3 次
            os.environ[key] = str(retries)
        return int(retries)

    @property
    def NOTIFICATION_EMAIL_MAX_RETRIES(self) -> int:
        """
        Email SMTP 最大重试次数

        默认值: 3
        配置路径: notifications.email.max_retries
        """
        key = "GINKGO_NOTIFICATION_EMAIL_MAX_RETRIES"
        retries = os.environ.get(key, None)
        if retries is None:
            config = self._read_config()
            notifications = config.get("notifications", {})
            email = notifications.get("email", {})
            retries = email.get("max_retries", 3)  # 默认 3 次
            os.environ[key] = str(retries)
        return int(retries)

    # ==================== Email SMTP 配置 ====================

    @property
    def EMAIL_SMTP_HOST(self) -> str:
        """Email SMTP 服务器地址（业务配置，无默认值）"""
        self._ensure_env_vars()
        if "GINKGO_SMTP_HOST" not in os.environ or not os.environ["GINKGO_SMTP_HOST"]:
            raise ValueError("GINKGO_SMTP_HOST not configured")
        return os.environ["GINKGO_SMTP_HOST"]

    @property
    def EMAIL_SMTP_PORT(self) -> int:
        """Email SMTP 端口（业务配置，无默认值）"""
        self._ensure_env_vars()
        if "GINKGO_SMTP_PORT" not in os.environ or not os.environ["GINKGO_SMTP_PORT"]:
            raise ValueError("GINKGO_SMTP_PORT not configured")
        return int(os.environ["GINKGO_SMTP_PORT"])

    @property
    def EMAIL_SMTP_USER(self) -> str:
        """Email SMTP 用户名（敏感信息，无默认值）"""
        self._ensure_env_vars()
        if "GINKGO_SMTP_USER" not in os.environ or not os.environ["GINKGO_SMTP_USER"]:
            raise ValueError("GINKGO_SMTP_USER not configured")
        return os.environ["GINKGO_SMTP_USER"]

    @property
    def EMAIL_SMTP_PASSWORD(self) -> str:
        """Email SMTP 密码/应用专用密码（敏感信息，无默认值）"""
        self._ensure_env_vars()
        if "GINKGO_SMTP_PASSWORD" not in os.environ or not os.environ["GINKGO_SMTP_PASSWORD"]:
            raise ValueError("GINKGO_SMTP_PASSWORD not configured")
        return os.environ["GINKGO_SMTP_PASSWORD"]

    @property
    def EMAIL_FROM_ADDRESS(self) -> str:
        """Email 发件人地址（业务配置，无默认值）"""
        self._ensure_env_vars()
        if "GINKGO_FROM_ADDRESS" not in os.environ or not os.environ["GINKGO_FROM_ADDRESS"]:
            raise ValueError("GINKGO_FROM_ADDRESS not configured")
        return os.environ["GINKGO_FROM_ADDRESS"]

    @property
    def EMAIL_FROM_NAME(self) -> str:
        """Email 发件人名称（环境标识，有默认值）"""
        self._ensure_env_vars()
        return os.environ.get("GINKGO_FROM_NAME", "Ginkgo Notification")

    # ==================== 数据源API密钥配置 ====================

    @property
    def EASTMONEY_API_KEY(self) -> str:
        """东方财富API密钥（可选配置）"""
        self._ensure_env_vars()
        return os.environ.get("GINKGO_EASTMONEY_API_KEY", "")

    @property
    def ALPACA_API_KEY(self) -> str:
        """Alpaca API密钥（可选配置）"""
        self._ensure_env_vars()
        return os.environ.get("GINKGO_ALPACA_API_KEY", "")

    @property
    def ALPACA_API_SECRET(self) -> str:
        """Alpaca API密钥（可选配置）"""
        self._ensure_env_vars()
        return os.environ.get("GINKGO_ALPACA_API_SECRET", "")

    @property
    def FUSHU_API_KEY(self) -> str:
        """FuShu API密钥（可选配置）"""
        self._ensure_env_vars()
        return os.environ.get("GINKGO_FUSHU_API_KEY", "")

    @property
    def STREAMING_CONFIG(self) -> dict:
        """流式处理配置（从config.yml读取）"""
        config = self._read_config()
        return config.get("streaming", {})


GCONF = GinkgoConfig()
