"""
性能: 219MB RSS, 1.88s, 21 tests [PASS]
RedisCRUD 单元测试（Mock Redis 连接）

覆盖范围：
- 构造与类型检查：实例属性、Redis 连接
- 基础键值操作: set, get, delete, exists, expire
- Set 操作: sadd, smembers
- Hash 操作: hset, hget, hgetall
- 系统信息: keys, info, ping
- 注意：RedisCRUD 不是 BaseCRUD 子类，直接操作 Redis
"""

import pytest
import json
from unittest.mock import MagicMock, patch


# ============================================================
# 辅助：构造 RedisCRUD 实例（mock Redis 连接）
# ============================================================


@pytest.fixture
def redis_crud():
    """构造 RedisCRUD 实例，mock 掉 create_redis_connection"""
    mock_logger = MagicMock()
    mock_redis = MagicMock()

    with patch("ginkgo.data.crud.redis_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.redis_crud.create_redis_connection", return_value=mock_redis):
        from ginkgo.data.crud.redis_crud import RedisCRUD
        crud = RedisCRUD(redis_connection=mock_redis)
        # 跳过连接测试，直接标记为已测试
        crud._connection_tested = True
        return crud


@pytest.fixture
def mock_redis():
    """独立的 mock Redis 客户端对象"""
    return MagicMock()


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestRedisCRUDConstruction:
    """RedisCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_construction_with_connection(self):
        """传入 redis_connection 时使用传入的实例"""
        mock_logger = MagicMock()
        mock_redis = MagicMock()

        with patch("ginkgo.data.crud.redis_crud.GLOG", mock_logger):
            from ginkgo.data.crud.redis_crud import RedisCRUD
            crud = RedisCRUD(redis_connection=mock_redis)

        assert crud.redis is mock_redis
        assert crud._connection_tested is False

    @pytest.mark.unit
    def test_construction_auto_create(self):
        """不传 redis_connection 时自动创建连接"""
        mock_logger = MagicMock()
        mock_redis = MagicMock()

        with patch("ginkgo.data.crud.redis_crud.GLOG", mock_logger), \
             patch("ginkgo.data.crud.redis_crud.create_redis_connection", return_value=mock_redis):
            from ginkgo.data.crud.redis_crud import RedisCRUD
            crud = RedisCRUD()

        assert crud.redis is mock_redis



# ============================================================
# 基础键值操作测试
# ============================================================


class TestRedisCRUDBasicOperations:
    """set / get / delete / exists / expire 测试"""

    @pytest.mark.unit
    def test_set_string_value(self, redis_crud):
        """设置字符串值，调用 redis.set"""
        redis_crud.redis.set.return_value = True

        result = redis_crud.set("my_key", "hello")

        assert result is True
        redis_crud.redis.set.assert_called_once_with("my_key", "hello")

    @pytest.mark.unit
    def test_set_dict_value_serialized(self, redis_crud):
        """设置字典值时自动序列化为 JSON"""
        redis_crud.redis.set.return_value = True
        test_dict = {"name": "test", "value": 123}

        result = redis_crud.set("my_key", test_dict)

        assert result is True
        call_args = redis_crud.redis.set.call_args[0]
        assert json.loads(call_args[1]) == test_dict

    @pytest.mark.unit
    def test_set_with_expire(self, redis_crud):
        """设置带过期时间的键，调用 redis.setex"""
        redis_crud.redis.setex.return_value = True

        result = redis_crud.set("temp_key", "data", expire_seconds=60)

        assert result is True
        redis_crud.redis.setex.assert_called_once_with("temp_key", 60, "data")

    @pytest.mark.unit
    def test_get_string_value(self, redis_crud):
        """获取字符串值，直接返回"""
        redis_crud.redis.get.return_value = b"hello"

        result = redis_crud.get("my_key")

        assert result == "hello"

    @pytest.mark.unit
    def test_get_json_value(self, redis_crud):
        """获取 JSON 字符串值，自动反序列化"""
        redis_crud.redis.get.return_value = b'{"name": "test"}'

        result = redis_crud.get("json_key")

        assert result == {"name": "test"}

    @pytest.mark.unit
    def test_get_nonexistent_key(self, redis_crud):
        """获取不存在的键返回 None"""
        redis_crud.redis.get.return_value = None

        result = redis_crud.get("nonexistent")

        assert result is None

    @pytest.mark.unit
    def test_delete_key(self, redis_crud):
        """删除存在的键返回 True"""
        redis_crud.redis.delete.return_value = 1

        result = redis_crud.delete("my_key")

        assert result is True

    @pytest.mark.unit
    def test_exists_key(self, redis_crud):
        """键存在时返回 True"""
        redis_crud.redis.exists.return_value = 1

        result = redis_crud.exists("my_key")

        assert result is True

    @pytest.mark.unit
    def test_expire_key(self, redis_crud):
        """设置过期时间返回 True"""
        redis_crud.redis.expire.return_value = True

        result = redis_crud.expire("my_key", 300)

        assert result is True


# ============================================================
# Set 和 Hash 操作测试
# ============================================================


class TestRedisCRUDSetAndHash:
    """Set 操作 (sadd, smembers) 和 Hash 操作 (hset, hget, hgetall) 测试"""

    @pytest.mark.unit
    def test_sadd(self, redis_crud):
        """向 Set 添加元素，返回添加数量"""
        redis_crud.redis.sadd.return_value = 2

        result = redis_crud.sadd("my_set", "a", "b", "c")

        assert result == 2
        redis_crud.redis.sadd.assert_called_once_with("my_set", "a", "b", "c")

    @pytest.mark.unit
    def test_smembers(self, redis_crud):
        """获取 Set 成员，正确解码字节数据"""
        redis_crud.redis.smembers.return_value = {b"member1", b"member2"}

        result = redis_crud.smembers("my_set")

        assert result == {"member1", "member2"}

    @pytest.mark.unit
    def test_hset(self, redis_crud):
        """设置 Hash 字段值"""
        redis_crud.redis.hset.return_value = 1

        result = redis_crud.hset("my_hash", "field1", "value1")

        assert result is True
        redis_crud.redis.hset.assert_called_once_with("my_hash", "field1", "value1")

    @pytest.mark.unit
    def test_hget(self, redis_crud):
        """获取 Hash 字段值"""
        redis_crud.redis.hget.return_value = b'"value1"'

        result = redis_crud.hget("my_hash", "field1")

        # JSON 反序列化
        assert result == "value1"

    @pytest.mark.unit
    def test_hget_nonexistent_field(self, redis_crud):
        """获取不存在的 Hash 字段返回 None"""
        redis_crud.redis.hget.return_value = None

        result = redis_crud.hget("my_hash", "nonexistent")

        assert result is None

    @pytest.mark.unit
    def test_hgetall(self, redis_crud):
        """获取 Hash 所有字段，正确解码字节数据"""
        redis_crud.redis.hgetall.return_value = {
            b"field1": b"value1",
            b"field2": b"123",
        }

        result = redis_crud.hgetall("my_hash")

        assert result["field1"] == "value1"
        assert result["field2"] == 123


# ============================================================
# 系统信息与监控测试
# ============================================================


class TestRedisCRUDSystemInfo:
    """keys / info / ping 测试"""

    @pytest.mark.unit
    def test_keys_with_pattern(self, redis_crud):
        """按模式获取键名列表，正确解码字节"""
        redis_crud.redis.keys.return_value = [b"key1", b"key2", b"key3"]

        result = redis_crud.keys("prefix:*")

        assert result == ["key1", "key2", "key3"]
        redis_crud.redis.keys.assert_called_once_with("prefix:*")

    @pytest.mark.unit
    def test_info(self, redis_crud):
        """获取 Redis 服务器信息"""
        redis_crud.redis.info.return_value = {
            "redis_version": "7.0.0",
            "used_memory_human": "1.5M",
            "connected_clients": 5,
            "uptime_in_seconds": 3600,
        }

        result = redis_crud.info()

        assert result["connected"] is True
        assert result["version"] == "7.0.0"
        assert result["used_memory"] == "1.5M"
        assert result["connected_clients"] == 5

    @pytest.mark.unit
    def test_ping_success(self, redis_crud):
        """Redis ping 成功返回 True"""
        redis_crud.redis.ping.return_value = True

        result = redis_crud.ping()

        assert result is True

    @pytest.mark.unit
    def test_ping_failure(self, redis_crud):
        """Redis ping 失败返回 False"""
        redis_crud.redis.ping.side_effect = Exception("Connection refused")

        result = redis_crud.ping()

        assert result is False
