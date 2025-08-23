"""
流式查询缓存管理器

提供高效的查询结果缓存、智能缓存策略和性能监控，
通过缓存机制显著提升重复查询的响应速度。

核心功能：
- LRU缓存策略与自动过期管理
- 查询结果分片缓存和增量更新
- 缓存命中率统计和性能分析
- 内存限制和智能缓存清理
"""

import time
import threading
import hashlib
import pickle
import json
from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from dataclasses import dataclass, field
from collections import OrderedDict, defaultdict
from enum import Enum

try:
    from ginkgo.libs import GLOG

    _has_ginkgo_logger = True
except ImportError:
    _has_ginkgo_logger = False
    import logging

    GLOG = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """缓存策略"""

    LRU = "lru"  # 最近最少使用
    LFU = "lfu"  # 最少使用频率
    TTL = "ttl"  # 基于时间的过期
    ADAPTIVE = "adaptive"  # 自适应策略


@dataclass
class CacheConfig:
    """缓存配置"""

    max_memory_mb: float = 100.0  # 最大内存使用（MB）
    default_ttl_seconds: int = 3600  # 默认过期时间（1小时）
    max_entries: int = 1000  # 最大缓存条目数
    strategy: CacheStrategy = CacheStrategy.LRU
    enable_compression: bool = True  # 启用压缩
    cache_batch_results: bool = True  # 缓存批次结果
    cache_query_metadata: bool = True  # 缓存查询元数据
    cleanup_interval: int = 300  # 清理间隔（5分钟）


@dataclass
class CacheEntry:
    """缓存条目"""

    key: str
    data: Any
    created_at: float
    last_accessed: float
    access_count: int
    size_bytes: int
    ttl_seconds: Optional[int] = None
    compressed: bool = False

    @property
    def age_seconds(self) -> float:
        """缓存年龄"""
        return time.time() - self.created_at

    @property
    def idle_seconds(self) -> float:
        """空闲时间"""
        return time.time() - self.last_accessed

    @property
    def is_expired(self) -> bool:
        """是否过期"""
        if self.ttl_seconds is None:
            return False
        return self.age_seconds > self.ttl_seconds


@dataclass
class CacheMetrics:
    """缓存指标"""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0
    avg_access_time_ms: float = 0.0

    @property
    def hit_rate(self) -> float:
        """命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    @property
    def total_size_mb(self) -> float:
        """总大小（MB）"""
        return self.total_size_bytes / (1024 * 1024)


class StreamingCache:
    """流式查询缓存"""

    def __init__(self, config: CacheConfig):
        """
        初始化流式缓存

        Args:
            config: 缓存配置
        """
        self.config = config
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.metrics = CacheMetrics()
        self._lock = threading.RLock()

        # 频率统计（用于LFU策略）
        self.access_frequencies = defaultdict(int)

        # 自动清理
        self._cleanup_enabled = False
        self._cleanup_thread = None

        GLOG.DEBUG(f"StreamingCache initialized with strategy: {config.strategy.value}")

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存数据

        Args:
            key: 缓存键

        Returns:
            缓存的数据，如果不存在则返回None
        """
        start_time = time.time()

        with self._lock:
            entry = self.cache.get(key)

            if entry is None:
                self.metrics.misses += 1
                GLOG.DEBUG(f"Cache miss for key: {key[:32]}...")
                return None

            # 检查过期
            if entry.is_expired:
                self.cache.pop(key, None)
                self.access_frequencies.pop(key, None)
                self.metrics.misses += 1
                self.metrics.evictions += 1
                GLOG.DEBUG(f"Cache expired for key: {key[:32]}...")
                return None

            # 更新访问信息
            entry.last_accessed = time.time()
            entry.access_count += 1
            self.access_frequencies[key] += 1

            # LRU策略：移动到末尾
            if self.config.strategy == CacheStrategy.LRU:
                self.cache.move_to_end(key)

            self.metrics.hits += 1

            # 解压缩数据
            data = self._decompress_data(entry.data) if entry.compressed else entry.data

            # 更新平均访问时间
            access_time = (time.time() - start_time) * 1000  # 毫秒
            self._update_avg_access_time(access_time)

            GLOG.DEBUG(f"Cache hit for key: {key[:32]}... (access count: {entry.access_count})")
            return data

    def put(self, key: str, data: Any, ttl_seconds: Optional[int] = None) -> bool:
        """
        存储数据到缓存

        Args:
            key: 缓存键
            data: 要缓存的数据
            ttl_seconds: 过期时间，None使用默认值

        Returns:
            是否成功存储
        """
        try:
            # 序列化和压缩数据
            serialized_data = data
            compressed = False

            if self.config.enable_compression:
                serialized_data = self._compress_data(data)
                compressed = True

            # 计算数据大小
            data_size = self._calculate_size(serialized_data)

            with self._lock:
                # 检查内存限制
                if self._would_exceed_memory_limit(data_size):
                    if not self._make_space(data_size):
                        GLOG.WARNING(f"Cannot cache data: would exceed memory limit")
                        return False

                # 检查条目数量限制
                if len(self.cache) >= self.config.max_entries:
                    self._evict_entries(1)

                # 创建缓存条目
                current_time = time.time()
                entry = CacheEntry(
                    key=key,
                    data=serialized_data,
                    created_at=current_time,
                    last_accessed=current_time,
                    access_count=1,
                    size_bytes=data_size,
                    ttl_seconds=ttl_seconds or self.config.default_ttl_seconds,
                    compressed=compressed,
                )

                # 存储到缓存
                self.cache[key] = entry
                self.access_frequencies[key] = 1

                # 更新指标
                self.metrics.entry_count = len(self.cache)
                self.metrics.total_size_bytes += data_size

                GLOG.DEBUG(f"Cached data for key: {key[:32]}... (size: {data_size} bytes)")
                return True

        except Exception as e:
            GLOG.ERROR(f"Failed to cache data: {e}")
            return False

    def invalidate(self, key: str) -> bool:
        """
        删除缓存条目

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        with self._lock:
            entry = self.cache.pop(key, None)
            if entry:
                self.access_frequencies.pop(key, None)
                self.metrics.total_size_bytes -= entry.size_bytes
                self.metrics.entry_count = len(self.cache)
                self.metrics.evictions += 1
                GLOG.DEBUG(f"Invalidated cache for key: {key[:32]}...")
                return True
            return False

    def clear(self):
        """清空缓存"""
        with self._lock:
            self.cache.clear()
            self.access_frequencies.clear()
            self.metrics.total_size_bytes = 0
            self.metrics.entry_count = 0
            GLOG.INFO("Cache cleared")

    def start_cleanup(self):
        """启动自动清理"""
        with self._lock:
            if self._cleanup_enabled:
                return

            self._cleanup_enabled = True
            self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True, name="CacheCleanup")
            self._cleanup_thread.start()

        GLOG.INFO("Cache cleanup started")

    def stop_cleanup(self):
        """停止自动清理"""
        with self._lock:
            if not self._cleanup_enabled:
                return

            self._cleanup_enabled = False

        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=10)

        GLOG.INFO("Cache cleanup stopped")

    def get_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            # 计算缓存分布
            size_distribution = defaultdict(int)
            access_distribution = defaultdict(int)
            age_distribution = defaultdict(int)

            for entry in self.cache.values():
                # 大小分布
                size_kb = entry.size_bytes // 1024
                if size_kb < 1:
                    size_distribution["<1KB"] += 1
                elif size_kb < 10:
                    size_distribution["1-10KB"] += 1
                elif size_kb < 100:
                    size_distribution["10-100KB"] += 1
                else:
                    size_distribution[">100KB"] += 1

                # 访问频率分布
                if entry.access_count == 1:
                    access_distribution["1"] += 1
                elif entry.access_count <= 5:
                    access_distribution["2-5"] += 1
                elif entry.access_count <= 10:
                    access_distribution["6-10"] += 1
                else:
                    access_distribution[">10"] += 1

                # 年龄分布
                age_minutes = entry.age_seconds / 60
                if age_minutes < 5:
                    age_distribution["<5min"] += 1
                elif age_minutes < 30:
                    age_distribution["5-30min"] += 1
                elif age_minutes < 60:
                    age_distribution["30-60min"] += 1
                else:
                    age_distribution[">1hour"] += 1

            return {
                "metrics": {
                    "hit_rate": self.metrics.hit_rate,
                    "hits": self.metrics.hits,
                    "misses": self.metrics.misses,
                    "evictions": self.metrics.evictions,
                    "total_size_mb": self.metrics.total_size_mb,
                    "entry_count": self.metrics.entry_count,
                    "avg_access_time_ms": self.metrics.avg_access_time_ms,
                },
                "config": {
                    "strategy": self.config.strategy.value,
                    "max_memory_mb": self.config.max_memory_mb,
                    "max_entries": self.config.max_entries,
                    "default_ttl_seconds": self.config.default_ttl_seconds,
                },
                "distributions": {
                    "size": dict(size_distribution),
                    "access": dict(access_distribution),
                    "age": dict(age_distribution),
                },
                "memory_usage": {
                    "used_mb": self.metrics.total_size_mb,
                    "available_mb": self.config.max_memory_mb - self.metrics.total_size_mb,
                    "usage_percent": (self.metrics.total_size_mb / self.config.max_memory_mb) * 100,
                },
            }

    def _compress_data(self, data: Any) -> bytes:
        """压缩数据"""
        import gzip

        serialized = pickle.dumps(data)
        return gzip.compress(serialized)

    def _decompress_data(self, compressed_data: bytes) -> Any:
        """解压缩数据"""
        import gzip

        decompressed = gzip.decompress(compressed_data)
        return pickle.loads(decompressed)

    def _calculate_size(self, data: Any) -> int:
        """计算数据大小"""
        if isinstance(data, bytes):
            return len(data)
        elif isinstance(data, str):
            return len(data.encode("utf-8"))
        else:
            return len(pickle.dumps(data))

    def _would_exceed_memory_limit(self, additional_size: int) -> bool:
        """检查是否会超过内存限制"""
        max_bytes = self.config.max_memory_mb * 1024 * 1024
        return (self.metrics.total_size_bytes + additional_size) > max_bytes

    def _make_space(self, required_size: int) -> bool:
        """为新数据腾出空间"""
        max_bytes = self.config.max_memory_mb * 1024 * 1024
        target_size = max_bytes - required_size

        if target_size < 0:
            return False  # 单个数据项太大

        # 计算需要清理的大小
        size_to_free = self.metrics.total_size_bytes - target_size
        if size_to_free <= 0:
            return True

        # 根据策略选择要清理的条目
        entries_to_remove = self._select_eviction_candidates(size_to_free)

        # 清理选中的条目
        freed_size = 0
        for key in entries_to_remove:
            entry = self.cache.pop(key, None)
            if entry:
                self.access_frequencies.pop(key, None)
                freed_size += entry.size_bytes
                self.metrics.evictions += 1

                if freed_size >= size_to_free:
                    break

        # 更新指标
        self.metrics.total_size_bytes -= freed_size
        self.metrics.entry_count = len(self.cache)

        GLOG.DEBUG(f"Freed {freed_size} bytes from cache")
        return freed_size >= size_to_free

    def _select_eviction_candidates(self, size_to_free: int) -> List[str]:
        """选择要清理的缓存条目"""
        candidates = []

        if self.config.strategy == CacheStrategy.LRU:
            # LRU: 选择最少最近使用的
            candidates = list(self.cache.keys())
        elif self.config.strategy == CacheStrategy.LFU:
            # LFU: 选择使用频率最低的
            candidates = sorted(self.cache.keys(), key=lambda k: self.access_frequencies.get(k, 0))
        elif self.config.strategy == CacheStrategy.TTL:
            # TTL: 选择最旧的
            candidates = sorted(self.cache.keys(), key=lambda k: self.cache[k].created_at)
        else:  # ADAPTIVE
            # 自适应：综合考虑年龄、频率和大小
            candidates = sorted(self.cache.keys(), key=lambda k: self._adaptive_score(self.cache[k]))

        return candidates

    def _adaptive_score(self, entry: CacheEntry) -> float:
        """计算自适应评分（越低越容易被清理）"""
        age_factor = entry.age_seconds / 3600  # 年龄权重
        frequency_factor = 1.0 / (entry.access_count + 1)  # 频率权重
        size_factor = entry.size_bytes / (1024 * 1024)  # 大小权重（MB）

        return age_factor + frequency_factor + size_factor * 0.1

    def _evict_entries(self, count: int):
        """清理指定数量的条目"""
        candidates = self._select_eviction_candidates(0)[:count]

        for key in candidates:
            entry = self.cache.pop(key, None)
            if entry:
                self.access_frequencies.pop(key, None)
                self.metrics.total_size_bytes -= entry.size_bytes
                self.metrics.evictions += 1

        self.metrics.entry_count = len(self.cache)

    def _update_avg_access_time(self, access_time_ms: float):
        """更新平均访问时间"""
        if self.metrics.avg_access_time_ms == 0:
            self.metrics.avg_access_time_ms = access_time_ms
        else:
            # 指数移动平均
            alpha = 0.1
            self.metrics.avg_access_time_ms = alpha * access_time_ms + (1 - alpha) * self.metrics.avg_access_time_ms

    def _cleanup_loop(self):
        """清理循环"""
        GLOG.DEBUG("Cache cleanup loop started")

        while self._cleanup_enabled:
            try:
                self._cleanup_expired_entries()
                time.sleep(self.config.cleanup_interval)
            except Exception as e:
                GLOG.ERROR(f"Error in cache cleanup loop: {e}")
                time.sleep(self.config.cleanup_interval)

        GLOG.DEBUG("Cache cleanup loop stopped")

    def _cleanup_expired_entries(self):
        """清理过期条目"""
        expired_keys = []

        with self._lock:
            for key, entry in self.cache.items():
                if entry.is_expired:
                    expired_keys.append(key)

        # 清理过期条目
        for key in expired_keys:
            self.invalidate(key)

        if expired_keys:
            GLOG.DEBUG(f"Cleaned up {len(expired_keys)} expired cache entries")


class CacheManager:
    """缓存管理器"""

    def __init__(self, config: CacheConfig):
        """
        初始化缓存管理器

        Args:
            config: 缓存配置
        """
        self.config = config
        self.cache = StreamingCache(config)

        # 查询哈希缓存
        self.query_hashes: Dict[str, str] = {}

        # 启动自动清理
        self.cache.start_cleanup()

        GLOG.DEBUG("CacheManager initialized")

    def generate_cache_key(self, query: str, filters: Dict[str, Any], batch_info: Optional[Dict] = None) -> str:
        """
        生成缓存键

        Args:
            query: SQL查询
            filters: 过滤条件
            batch_info: 批次信息

        Returns:
            缓存键
        """
        key_data = {
            "query": query.strip(),
            "filters": sorted(filters.items()) if filters else [],
            "batch_info": batch_info or {},
        }

        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def cache_query_result(
        self, query: str, filters: Dict[str, Any], result: Any, ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        缓存查询结果

        Args:
            query: SQL查询
            filters: 过滤条件
            result: 查询结果
            ttl_seconds: 过期时间

        Returns:
            是否成功缓存
        """
        cache_key = self.generate_cache_key(query, filters)
        return self.cache.put(cache_key, result, ttl_seconds)

    def get_cached_result(self, query: str, filters: Dict[str, Any]) -> Optional[Any]:
        """
        获取缓存的查询结果

        Args:
            query: SQL查询
            filters: 过滤条件

        Returns:
            缓存的结果，如果不存在则返回None
        """
        cache_key = self.generate_cache_key(query, filters)
        return self.cache.get(cache_key)

    def invalidate_query_cache(self, query: str, filters: Dict[str, Any]) -> bool:
        """
        使查询缓存失效

        Args:
            query: SQL查询
            filters: 过滤条件

        Returns:
            是否成功使失效
        """
        cache_key = self.generate_cache_key(query, filters)
        return self.cache.invalidate(cache_key)

    def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return self.cache.get_statistics()

    def optimize_cache(self) -> Dict[str, Any]:
        """优化缓存"""
        stats_before = self.cache.get_statistics()

        # 强制清理过期条目
        self.cache._cleanup_expired_entries()

        # 如果内存使用过高，清理一些条目
        if self.cache.metrics.total_size_mb > self.config.max_memory_mb * 0.8:
            entries_to_remove = max(1, len(self.cache.cache) // 10)  # 清理10%
            self.cache._evict_entries(entries_to_remove)

        stats_after = self.cache.get_statistics()

        optimization_report = {
            "before": stats_before["metrics"],
            "after": stats_after["metrics"],
            "improvement": {
                "freed_mb": stats_before["metrics"]["total_size_mb"] - stats_after["metrics"]["total_size_mb"],
                "freed_entries": stats_before["metrics"]["entry_count"] - stats_after["metrics"]["entry_count"],
            },
        }

        GLOG.INFO(f"Cache optimization completed: {optimization_report}")
        return optimization_report


# 全局缓存管理器实例
default_cache_config = CacheConfig()
cache_manager = CacheManager(default_cache_config)
