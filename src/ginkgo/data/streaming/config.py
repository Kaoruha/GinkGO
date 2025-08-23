"""
流式查询配置管理模块

提供流式查询的配置管理、验证和热更新功能，
集成Ginkgo全局配置系统，支持环境变量覆盖。

功能特性：
- 分层配置管理（默认值 → 配置文件 → 环境变量）
- 配置验证和类型检查
- 运行时配置热更新
- 数据库特化配置支持
"""

import os
import yaml
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path

try:
    from ginkgo.libs import GCONF, GLOG

    _has_ginkgo_config = True
except ImportError:
    _has_ginkgo_config = False
    import logging

    GLOG = logging.getLogger(__name__)

from . import StreamingConfigError


@dataclass
class DatabaseConfig:
    """数据库特化配置"""

    # MySQL配置
    mysql_pool_size: int = 20
    mysql_max_overflow: int = 50
    mysql_pool_recycle: int = 7200
    mysql_pool_timeout: int = 60
    mysql_use_server_side_cursor: bool = True
    mysql_query_cache_disabled: bool = True

    # ClickHouse配置
    clickhouse_pool_size: int = 15
    clickhouse_max_overflow: int = 30
    clickhouse_max_block_size: int = 1000
    clickhouse_max_memory_usage: str = "500MB"
    clickhouse_max_execution_time: int = 3600
    clickhouse_send_progress: bool = True

    # Redis配置（用于断点存储）
    redis_checkpoint_ttl: int = 3600
    redis_cache_ttl: int = 300


@dataclass
class PerformanceConfig:
    """性能相关配置"""

    # 批次大小配置
    default_batch_size: int = 1000
    min_batch_size: int = 100
    max_batch_size: int = 10000
    auto_adjust_batch_size: bool = True

    # 内存管理配置
    memory_threshold_mb: int = 100
    memory_check_interval: int = 10
    memory_gc_threshold: float = 0.8

    # 并发配置
    max_parallel_workers: int = 4
    worker_queue_size: int = 1000

    # 超时配置
    query_timeout: int = 3600
    connection_timeout: int = 60
    read_timeout: int = 300


@dataclass
class RecoveryConfig:
    """错误恢复配置"""

    # 断点续传配置
    enable_checkpoint: bool = True
    checkpoint_interval: int = 1000
    checkpoint_auto_cleanup: bool = True

    # 重试配置
    max_retry_attempts: int = 3
    retry_base_delay: float = 1.0
    retry_max_delay: float = 60.0
    retry_exponential_base: float = 2.0
    retry_jitter: bool = True

    # 错误处理配置
    enable_auto_recovery: bool = True
    recovery_timeout: int = 300

    # 降级配置
    enable_fallback: bool = True
    fallback_to_traditional: bool = True


@dataclass
class CacheConfig:
    """缓存系统配置"""

    # 基础缓存配置
    enable_cache: bool = True
    default_ttl: int = 300
    max_cache_size: int = 1000

    # 缓存策略配置
    cache_strategy: str = "adaptive"  # aggressive, conservative, adaptive
    cache_compression: bool = True
    cache_batch_results: bool = True

    # 缓存清理配置
    auto_cleanup: bool = True
    cleanup_interval: int = 3600


@dataclass
class MonitoringConfig:
    """监控配置"""

    # 进度监控配置
    enable_progress_tracking: bool = True
    progress_update_interval: int = 1
    progress_callback_enabled: bool = False

    # 性能监控配置
    enable_performance_monitoring: bool = True
    collect_detailed_metrics: bool = True
    metrics_retention_seconds: int = 3600

    # 日志配置
    log_level: str = "INFO"
    log_streaming_operations: bool = True
    log_performance_metrics: bool = False


@dataclass
class StreamingConfig:
    """流式查询完整配置"""

    # 基础配置
    enabled: bool = False
    debug_mode: bool = False

    # 子配置模块
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    recovery: RecoveryConfig = field(default_factory=RecoveryConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "StreamingConfig":
        """从字典创建配置"""
        # 提取各个子配置
        database_config = DatabaseConfig(**config_dict.get("database", {}))
        performance_config = PerformanceConfig(**config_dict.get("performance", {}))
        recovery_config = RecoveryConfig(**config_dict.get("recovery", {}))
        cache_config = CacheConfig(**config_dict.get("cache", {}))
        monitoring_config = MonitoringConfig(**config_dict.get("monitoring", {}))

        # 创建主配置
        main_config = {
            k: v
            for k, v in config_dict.items()
            if k not in ["database", "performance", "recovery", "cache", "monitoring"]
        }

        return cls(
            **main_config,
            database=database_config,
            performance=performance_config,
            recovery=recovery_config,
            cache=cache_config,
            monitoring=monitoring_config,
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def validate(self) -> None:
        """验证配置有效性"""
        errors = []

        # 验证批次大小配置
        if self.performance.min_batch_size >= self.performance.max_batch_size:
            errors.append("min_batch_size must be less than max_batch_size")

        if not (
            self.performance.min_batch_size <= self.performance.default_batch_size <= self.performance.max_batch_size
        ):
            errors.append("default_batch_size must be between min_batch_size and max_batch_size")

        # 验证内存阈值
        if self.performance.memory_threshold_mb <= 0:
            errors.append("memory_threshold_mb must be positive")

        # 验证重试配置
        if self.recovery.max_retry_attempts < 0:
            errors.append("max_retry_attempts cannot be negative")

        if self.recovery.retry_base_delay <= 0:
            errors.append("retry_base_delay must be positive")

        # 验证超时配置
        if self.performance.query_timeout <= 0:
            errors.append("query_timeout must be positive")

        if errors:
            raise StreamingConfigError(f"Configuration validation failed: {'; '.join(errors)}")


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        self._config: Optional[StreamingConfig] = None
        self._config_file_path: Optional[Path] = None
        self._default_config = self._create_default_config()

    def _create_default_config(self) -> StreamingConfig:
        """创建默认配置"""
        return StreamingConfig()

    def load_config(self, config_path: Optional[Union[str, Path]] = None) -> StreamingConfig:
        """加载配置"""
        # 1. 从默认配置开始
        config_dict = self._default_config.to_dict()

        # 2. 尝试从Ginkgo全局配置加载
        if _has_ginkgo_config:
            try:
                ginkgo_streaming_config = GCONF.get("streaming", {})
                if ginkgo_streaming_config:
                    config_dict.update(ginkgo_streaming_config)
                    GLOG.DEBUG("Loaded streaming config from Ginkgo global config")
            except Exception as e:
                GLOG.WARNING(f"Failed to load from Ginkgo config: {e}")

        # 3. 从指定的配置文件加载
        if config_path:
            config_path = Path(config_path)
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        file_config = yaml.safe_load(f)
                    if file_config:
                        self._deep_update(config_dict, file_config)
                        self._config_file_path = config_path
                        GLOG.DEBUG(f"Loaded streaming config from file: {config_path}")
                except Exception as e:
                    GLOG.ERROR(f"Failed to load config file {config_path}: {e}")
                    raise StreamingConfigError(f"Failed to load config file: {e}")

        # 4. 从环境变量覆盖
        self._load_from_environment(config_dict)

        # 5. 创建并验证配置对象
        try:
            self._config = StreamingConfig.from_dict(config_dict)
            self._config.validate()
            GLOG.INFO("Streaming configuration loaded and validated successfully")
            return self._config
        except Exception as e:
            GLOG.ERROR(f"Failed to create or validate config: {e}")
            raise StreamingConfigError(f"Config validation failed: {e}")

    def _deep_update(self, base_dict: Dict, update_dict: Dict) -> None:
        """深度更新字典"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def _load_from_environment(self, config_dict: Dict[str, Any]) -> None:
        """从环境变量加载配置"""
        env_mappings = {
            "GINKGO_STREAMING_ENABLED": ("enabled", bool),
            "GINKGO_STREAMING_DEBUG": ("debug_mode", bool),
            "GINKGO_STREAMING_BATCH_SIZE": ("performance.default_batch_size", int),
            "GINKGO_STREAMING_MEMORY_THRESHOLD": ("performance.memory_threshold_mb", int),
            "GINKGO_STREAMING_MAX_RETRIES": ("recovery.max_retry_attempts", int),
            "GINKGO_STREAMING_CACHE_ENABLED": ("cache.enable_cache", bool),
            "GINKGO_STREAMING_CHECKPOINT_ENABLED": ("recovery.enable_checkpoint", bool),
        }

        for env_var, (config_path, config_type) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    # 类型转换
                    if config_type == bool:
                        value = env_value.lower() in ("true", "1", "yes", "on")
                    elif config_type == int:
                        value = int(env_value)
                    elif config_type == float:
                        value = float(env_value)
                    else:
                        value = env_value

                    # 设置到配置字典中
                    self._set_nested_value(config_dict, config_path, value)
                    GLOG.DEBUG(f"Set config {config_path} = {value} from environment variable {env_var}")
                except (ValueError, TypeError) as e:
                    GLOG.WARNING(f"Invalid environment variable {env_var} = {env_value}: {e}")

    def _set_nested_value(self, config_dict: Dict, path: str, value: Any) -> None:
        """设置嵌套字典的值"""
        keys = path.split(".")
        current = config_dict

        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def get_config(self) -> StreamingConfig:
        """获取当前配置"""
        if self._config is None:
            return self.load_config()
        return self._config

    def reload_config(self) -> StreamingConfig:
        """重新加载配置"""
        return self.load_config(self._config_file_path)

    def update_config(self, updates: Dict[str, Any]) -> None:
        """运行时更新配置"""
        if self._config is None:
            raise StreamingConfigError("Config not loaded yet")

        # 更新配置
        config_dict = self._config.to_dict()
        self._deep_update(config_dict, updates)

        # 重新创建和验证配置
        new_config = StreamingConfig.from_dict(config_dict)
        new_config.validate()

        self._config = new_config
        GLOG.INFO("Streaming configuration updated successfully")


# 全局配置管理器实例
_config_manager = ConfigManager()


def get_config() -> StreamingConfig:
    """获取全局流式查询配置"""
    return _config_manager.get_config()


def load_config(config_path: Optional[Union[str, Path]] = None) -> StreamingConfig:
    """加载配置"""
    return _config_manager.load_config(config_path)


def reload_config() -> StreamingConfig:
    """重新加载配置"""
    return _config_manager.reload_config()


def update_config(updates: Dict[str, Any]) -> None:
    """运行时更新配置"""
    _config_manager.update_config(updates)
