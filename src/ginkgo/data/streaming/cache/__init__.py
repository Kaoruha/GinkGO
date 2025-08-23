"""
流式查询缓存模块

提供流式查询结果的缓存管理、缓存策略选择等功能，
通过智能缓存提升查询性能和响应速度。

主要组件：
- StreamingCache: 流式查询结果缓存
- CacheStrategy: 缓存策略管理器
- CacheMetrics: 缓存性能指标
- QueryCache: 查询级别缓存
"""

from .cache_manager import StreamingCache, CacheManager, CacheConfig, CacheMetrics, CacheStrategy

# 暂时注释未实现的模块
# from .query_cache import QueryCache, QueryCacheEntry, QueryCacheConfig

__all__ = [
    "StreamingCache",
    "CacheManager",
    "CacheConfig", 
    "CacheMetrics",
    "CacheStrategy",
    # "QueryCache",
    # "QueryCacheEntry",
    # "QueryCacheConfig",
]
