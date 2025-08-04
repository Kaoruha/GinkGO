"""
RedisCRUD - Redis缓存CRUD操作

提供统一的Redis基础操作接口，符合项目CRUD架构模式
"""

import json
from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime

from ...libs import GLOG, time_logger, retry
from ..drivers import create_redis_connection


class RedisCRUD:
    """
    Redis基础CRUD操作类
    
    提供原子级Redis操作，负责：
    - Redis连接管理
    - 基础键值操作（get/set/delete/exists）
    - Redis数据结构操作（Set, Hash等）
    - 连接状态监控和错误处理
    """
    
    def __init__(self, redis_connection=None):
        """
        初始化RedisCRUD
        
        Args:
            redis_connection: Redis连接实例，如果为None则自动创建
        """
        if redis_connection is None:
            redis_connection = create_redis_connection()
            
        self._redis = redis_connection
        self._connection_tested = False
        
        GLOG.DEBUG("RedisCRUD initialized")
    
    @property
    def redis(self):
        """获取Redis连接实例"""
        return self._redis
    
    def _test_connection(self) -> bool:
        """
        测试Redis连接可用性
        
        Returns:
            bool: 连接是否可用
        """
        if self._connection_tested:
            return True
            
        try:
            self._redis.ping()
            self._connection_tested = True
            GLOG.DEBUG("Redis connection test successful")
            return True
        except Exception as e:
            GLOG.ERROR(f"Redis connection test failed: {e}")
            return False
    
    # ==================== 基础键值操作 ====================
    
    @time_logger
    @retry(max_try=3)
    def set(self, key: str, value: Any, expire_seconds: Optional[int] = None) -> bool:
        """
        设置键值对
        
        Args:
            key: 键名
            value: 值（支持字符串、字典、列表等）
            expire_seconds: 过期时间（秒），None表示不过期
            
        Returns:
            bool: 操作是否成功
        """
        try:
            if not self._test_connection():
                return False
                
            # 序列化复杂数据类型
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value)
            else:
                serialized_value = value
            
            if expire_seconds is not None:
                result = self._redis.setex(key, expire_seconds, serialized_value)
            else:
                result = self._redis.set(key, serialized_value)
                
            success = bool(result)
            if success:
                GLOG.DEBUG(f"Set Redis key: {key}")
            return success
            
        except Exception as e:
            GLOG.ERROR(f"Failed to set Redis key {key}: {e}")
            return False
    
    @time_logger
    def get(self, key: str) -> Optional[Any]:
        """
        获取键值
        
        Args:
            key: 键名
            
        Returns:
            Any: 键对应的值，不存在时返回None
        """
        try:
            if not self._test_connection():
                return None
                
            data = self._redis.get(key)
            if data is None:
                return None
                
            # 尝试反序列化
            data_str = data if isinstance(data, str) else data.decode('utf-8')
            try:
                return json.loads(data_str)
            except json.JSONDecodeError:
                return data_str
                
        except Exception as e:
            GLOG.ERROR(f"Failed to get Redis key {key}: {e}")
            return None
    
    @time_logger
    def delete(self, key: str) -> bool:
        """
        删除键
        
        Args:
            key: 键名
            
        Returns:
            bool: 删除成功返回True，键不存在返回False
        """
        try:
            if not self._test_connection():
                return False
                
            result = self._redis.delete(key)
            success = bool(result)
            if success:
                GLOG.DEBUG(f"Deleted Redis key: {key}")
            return success
            
        except Exception as e:
            GLOG.ERROR(f"Failed to delete Redis key {key}: {e}")
            return False
    
    @time_logger  
    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 键名
            
        Returns:
            bool: 键存在返回True，否则返回False
        """
        try:
            if not self._test_connection():
                return False
                
            result = self._redis.exists(key)
            return bool(result)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to check Redis key existence {key}: {e}")
            return False
    
    @time_logger
    def expire(self, key: str, seconds: int) -> bool:
        """
        设置键的过期时间
        
        Args:
            key: 键名
            seconds: 过期时间（秒）
            
        Returns:
            bool: 操作是否成功
        """
        try:
            if not self._test_connection():
                return False
                
            result = self._redis.expire(key, seconds)
            return bool(result)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to set expire for Redis key {key}: {e}")
            return False
    
    @time_logger
    def ttl(self, key: str) -> int:
        """
        获取键的剩余过期时间
        
        Args:
            key: 键名
            
        Returns:
            int: 剩余过期时间（秒）
                 -1: 键存在但没有设置过期时间
                 -2: 键不存在
        """
        try:
            if not self._test_connection():
                return -2
                
            result = self._redis.ttl(key)
            return result
            
        except Exception as e:
            GLOG.ERROR(f"Failed to get TTL for Redis key {key}: {e}")
            return -2
    
    # ==================== Set数据结构操作 ====================
    
    @time_logger
    def sadd(self, key: str, *values) -> int:
        """
        向Set中添加元素
        
        Args:
            key: Set键名
            *values: 要添加的值
            
        Returns:
            int: 实际添加的元素数量
        """
        try:
            if not self._test_connection():
                return 0
                
            result = self._redis.sadd(key, *values)
            GLOG.DEBUG(f"Added {result} elements to Redis set {key}")
            return result
            
        except Exception as e:
            GLOG.ERROR(f"Failed to add to Redis set {key}: {e}")
            return 0
    
    @time_logger
    def smembers(self, key: str) -> Set[str]:
        """
        获取Set的所有成员
        
        Args:
            key: Set键名
            
        Returns:
            Set[str]: Set的所有成员
        """
        try:
            if not self._test_connection():
                return set()
                
            members = self._redis.smembers(key)
            # 处理字节数据
            result = {
                member.decode('utf-8') if isinstance(member, bytes) else member
                for member in members
            }
            GLOG.DEBUG(f"Retrieved {len(result)} members from Redis set {key}")
            return result
            
        except Exception as e:
            GLOG.ERROR(f"Failed to get Redis set members {key}: {e}")
            return set()
    
    @time_logger
    def srem(self, key: str, *values) -> int:
        """
        从Set中移除元素
        
        Args:
            key: Set键名
            *values: 要移除的值
            
        Returns:
            int: 实际移除的元素数量
        """
        try:
            if not self._test_connection():
                return 0
                
            result = self._redis.srem(key, *values)
            GLOG.DEBUG(f"Removed {result} elements from Redis set {key}")
            return result
            
        except Exception as e:
            GLOG.ERROR(f"Failed to remove from Redis set {key}: {e}")
            return 0
    
    @time_logger
    def scard(self, key: str) -> int:
        """
        获取Set的大小
        
        Args:
            key: Set键名
            
        Returns:
            int: Set中元素的数量
        """
        try:
            if not self._test_connection():
                return 0
                
            return self._redis.scard(key)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to get Redis set size {key}: {e}")
            return 0
    
    # ==================== Hash数据结构操作 ====================
    
    @time_logger
    def hset(self, key: str, field: str, value: Any) -> bool:
        """
        设置Hash字段值
        
        Args:
            key: Hash键名
            field: 字段名
            value: 字段值
            
        Returns:
            bool: 操作是否成功
        """
        try:
            if not self._test_connection():
                return False
                
            # 序列化复杂数据类型
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value)
            else:
                serialized_value = str(value)
                
            result = self._redis.hset(key, field, serialized_value)
            success = bool(result is not None)  # hset返回字段数或None
            if success:
                GLOG.DEBUG(f"Set Redis hash field: {key}.{field}")
            return success
            
        except Exception as e:
            GLOG.ERROR(f"Failed to set Redis hash field {key}.{field}: {e}")
            return False
    
    @time_logger
    def hget(self, key: str, field: str) -> Optional[Any]:
        """
        获取Hash字段值
        
        Args:
            key: Hash键名
            field: 字段名
            
        Returns:
            Any: 字段值，不存在时返回None
        """
        try:
            if not self._test_connection():
                return None
                
            data = self._redis.hget(key, field)
            if data is None:
                return None
                
            # 尝试反序列化
            data_str = data if isinstance(data, str) else data.decode('utf-8')
            try:
                return json.loads(data_str)
            except json.JSONDecodeError:
                return data_str
                
        except Exception as e:
            GLOG.ERROR(f"Failed to get Redis hash field {key}.{field}: {e}")
            return None
    
    @time_logger
    def hgetall(self, key: str) -> Dict[str, Any]:
        """
        获取Hash的所有字段和值
        
        Args:
            key: Hash键名
            
        Returns:
            Dict[str, Any]: 所有字段和值的字典
        """
        try:
            if not self._test_connection():
                return {}
                
            data = self._redis.hgetall(key)
            result = {}
            
            for field, value in data.items():
                # 处理字节数据
                field_str = field.decode('utf-8') if isinstance(field, bytes) else field
                value_str = value.decode('utf-8') if isinstance(value, bytes) else value
                
                # 尝试反序列化值
                try:
                    result[field_str] = json.loads(value_str)
                except json.JSONDecodeError:
                    result[field_str] = value_str
                    
            GLOG.DEBUG(f"Retrieved {len(result)} fields from Redis hash {key}")
            return result
            
        except Exception as e:
            GLOG.ERROR(f"Failed to get Redis hash {key}: {e}")
            return {}
    
    @time_logger
    def hdel(self, key: str, *fields) -> int:
        """
        删除Hash字段
        
        Args:
            key: Hash键名
            *fields: 要删除的字段名
            
        Returns:
            int: 实际删除的字段数量
        """
        try:
            if not self._test_connection():
                return 0
                
            result = self._redis.hdel(key, *fields)
            GLOG.DEBUG(f"Deleted {result} fields from Redis hash {key}")
            return result
            
        except Exception as e:
            GLOG.ERROR(f"Failed to delete Redis hash fields {key}: {e}")
            return 0
    
    # ==================== 批量操作 ====================
    
    @time_logger
    def mget(self, keys: List[str]) -> List[Optional[Any]]:
        """
        批量获取多个键的值
        
        Args:
            keys: 键名列表
            
        Returns:
            List[Optional[Any]]: 对应键的值列表
        """
        try:
            if not self._test_connection():
                return [None] * len(keys)
                
            values = self._redis.mget(keys)
            results = []
            
            for value in values:
                if value is None:
                    results.append(None)
                else:
                    # 尝试反序列化
                    value_str = value if isinstance(value, str) else value.decode('utf-8')
                    try:
                        results.append(json.loads(value_str))
                    except json.JSONDecodeError:
                        results.append(value_str)
                        
            GLOG.DEBUG(f"Retrieved {len(keys)} keys from Redis")
            return results
            
        except Exception as e:
            GLOG.ERROR(f"Failed to get multiple Redis keys: {e}")
            return [None] * len(keys)
    
    @time_logger
    def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的所有键
        
        Args:
            pattern: 键名模式（支持通配符）
            
        Returns:
            int: 删除的键数量
        """
        try:
            if not self._test_connection():
                return 0
                
            keys = self._redis.keys(pattern)
            if not keys:
                return 0
                
            result = self._redis.delete(*keys)
            GLOG.DEBUG(f"Deleted {result} keys matching pattern: {pattern}")
            return result
            
        except Exception as e:
            GLOG.ERROR(f"Failed to delete Redis keys by pattern {pattern}: {e}")
            return 0
    
    # ==================== 系统信息和监控 ====================
    
    @time_logger
    def info(self) -> Dict[str, Any]:
        """
        获取Redis服务器信息
        
        Returns:
            Dict[str, Any]: Redis服务器信息
        """
        try:
            if not self._test_connection():
                return {"connected": False, "error": "Connection failed"}
                
            info_data = self._redis.info()
            return {
                "connected": True,
                "version": info_data.get("redis_version"),
                "used_memory": info_data.get("used_memory_human"),
                "connected_clients": info_data.get("connected_clients"),
                "uptime": info_data.get("uptime_in_seconds"),
                "raw_info": info_data
            }
            
        except Exception as e:
            GLOG.ERROR(f"Failed to get Redis info: {e}")
            return {"connected": False, "error": str(e)}
    
    @time_logger
    def ping(self) -> bool:
        """
        测试Redis连接
        
        Returns:
            bool: 连接是否正常
        """
        try:
            self._redis.ping()
            return True
        except Exception as e:
            GLOG.ERROR(f"Redis ping failed: {e}")
            return False
    
    @time_logger
    def flushdb(self) -> bool:
        """
        清空当前数据库的所有键（谨慎使用）
        
        Returns:
            bool: 操作是否成功
        """
        try:
            if not self._test_connection():
                return False
                
            result = self._redis.flushdb()
            GLOG.WARN("Redis database flushed - all keys deleted")
            return bool(result)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to flush Redis database: {e}")
            return False
    
    # ==================== List数据结构操作 ====================
    
    @time_logger
    def lpush(self, key: str, *values) -> int:
        """
        向List左侧添加元素
        
        Args:
            key: List键名
            *values: 要添加的值
            
        Returns:
            int: 添加后List的长度
        """
        try:
            if not self._test_connection():
                return 0
                
            result = self._redis.lpush(key, *values)
            GLOG.DEBUG(f"Added {len(values)} elements to Redis list {key}")
            return result
            
        except Exception as e:
            GLOG.ERROR(f"Failed to lpush to Redis list {key}: {e}")
            return 0
    
    @time_logger
    def lpop(self, key: str) -> Optional[str]:
        """
        从List左侧弹出元素
        
        Args:
            key: List键名
            
        Returns:
            Optional[str]: 弹出的元素，List为空时返回None
        """
        try:
            if not self._test_connection():
                return None
                
            result = self._redis.lpop(key)
            if result:
                # 处理字节数据
                result = result.decode('utf-8') if isinstance(result, bytes) else result
                GLOG.DEBUG(f"Popped element from Redis list {key}")
            return result
            
        except Exception as e:
            GLOG.ERROR(f"Failed to lpop from Redis list {key}: {e}")
            return None
    
    @time_logger
    def lrem(self, key: str, count: int, value: Any) -> int:
        """
        从List中移除指定值的元素
        
        Args:
            key: List键名
            count: 移除数量（0表示移除所有匹配的元素）
            value: 要移除的值
            
        Returns:
            int: 实际移除的元素数量
        """
        try:
            if not self._test_connection():
                return 0
                
            result = self._redis.lrem(key, count, value)
            GLOG.DEBUG(f"Removed {result} elements from Redis list {key}")
            return result
            
        except Exception as e:
            GLOG.ERROR(f"Failed to lrem from Redis list {key}: {e}")
            return 0
    
    @time_logger
    def llen(self, key: str) -> int:
        """
        获取List的长度
        
        Args:
            key: List键名
            
        Returns:
            int: List的长度
        """
        try:
            if not self._test_connection():
                return 0
                
            return self._redis.llen(key)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to get Redis list length {key}: {e}")
            return 0

    # ==================== 扫描操作 ====================
    
    @time_logger
    def sscan(self, key: str, cursor: int = 0, match: str = None, count: int = 10) -> tuple:
        """
        扫描Set的成员
        
        Args:
            key: Set键名
            cursor: 扫描游标
            match: 匹配模式
            count: 每次扫描的数量
            
        Returns:
            tuple: (下一个游标, 成员列表)
        """
        try:
            if not self._test_connection():
                return (0, [])
                
            cursor, members = self._redis.sscan(key, cursor=cursor, match=match, count=count)
            
            # 处理字节数据
            processed_members = [
                member.decode('utf-8') if isinstance(member, bytes) else member
                for member in members
            ]
            
            GLOG.DEBUG(f"Scanned {len(processed_members)} members from Redis set {key}")
            return (cursor, processed_members)
            
        except Exception as e:
            GLOG.ERROR(f"Failed to sscan Redis set {key}: {e}")
            return (0, [])

    # ==================== 高级操作 ====================
    
    def pipeline(self):
        """
        创建Redis pipeline用于批量操作
        
        Returns:
            Redis pipeline对象
        """
        try:
            if not self._test_connection():
                return None
                
            return self._redis.pipeline()
            
        except Exception as e:
            GLOG.ERROR(f"Failed to create Redis pipeline: {e}")
            return None
    
    @time_logger
    def keys(self, pattern: str = "*") -> List[str]:
        """
        获取匹配模式的所有键名
        
        Args:
            pattern: 键名模式（支持通配符）
            
        Returns:
            List[str]: 匹配的键名列表
        """
        try:
            if not self._test_connection():
                return []
                
            keys = self._redis.keys(pattern)
            # 处理字节数据
            result = [
                key.decode('utf-8') if isinstance(key, bytes) else key
                for key in keys
            ]
            GLOG.DEBUG(f"Found {len(result)} keys matching pattern: {pattern}")
            return result
            
        except Exception as e:
            GLOG.ERROR(f"Failed to get Redis keys by pattern {pattern}: {e}")
            return []