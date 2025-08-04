"""
RedisCRUD单元测试

使用真实Redis连接测试RedisCRUD的所有功能：
- 基础键值操作
- Set数据结构操作
- Hash数据结构操作
- 批量操作
- 系统信息和监控
- 错误处理和边界条件
"""

import unittest
import time
import json
from datetime import datetime
from typing import Dict, List, Set, Any

from ginkgo.data.crud.redis_crud import RedisCRUD


class TestRedisCRUD(unittest.TestCase):
    """RedisCRUD单元测试类 - 使用真实Redis连接"""

    def setUp(self):
        """每个测试方法执行前的设置"""
        # 创建真实RedisCRUD实例
        self.redis_crud = RedisCRUD()
        
        # 检查Redis连接可用性
        if not self.redis_crud.ping():
            self.skipTest("Redis connection not available")
        
        # 设置测试键前缀，避免与生产数据冲突
        self.test_prefix = f"test_crud_{int(time.time())}_{id(self)}"
        self.test_keys = []
        
    def tearDown(self):
        """每个测试方法执行后的清理"""
        # 清理所有测试过程中创建的键
        for key in self.test_keys:
            self.redis_crud.delete(key)
        
        # 清理可能的模式键
        pattern_keys = self.redis_crud.keys(f"{self.test_prefix}*")
        for key in pattern_keys:
            self.redis_crud.delete(key)
    
    def _get_test_key(self, suffix: str = "") -> str:
        """生成测试专用键名"""
        key = f"{self.test_prefix}_{suffix}" if suffix else f"{self.test_prefix}"
        self.test_keys.append(key)
        return key

    # ==================== 基础键值操作测试 ====================

    def test_set_and_get_string_value(self):
        """测试设置和获取字符串值"""
        key = self._get_test_key("string")
        value = "test string value"
        
        # 设置值
        result = self.redis_crud.set(key, value)
        self.assertTrue(result)
        
        # 获取值
        retrieved_value = self.redis_crud.get(key)
        self.assertEqual(retrieved_value, value)

    def test_set_and_get_dict_value(self):
        """测试设置和获取字典值"""
        key = self._get_test_key("dict")
        value = {"name": "test", "value": 123, "nested": {"a": 1, "b": 2}}
        
        # 设置值
        result = self.redis_crud.set(key, value)
        self.assertTrue(result)
        
        # 获取值
        retrieved_value = self.redis_crud.get(key)
        self.assertEqual(retrieved_value, value)

    def test_set_and_get_list_value(self):
        """测试设置和获取列表值"""
        key = self._get_test_key("list")
        value = ["item1", "item2", {"nested": "object"}, 42]
        
        # 设置值
        result = self.redis_crud.set(key, value)
        self.assertTrue(result)
        
        # 获取值
        retrieved_value = self.redis_crud.get(key)
        self.assertEqual(retrieved_value, value)

    def test_set_with_expiration(self):
        """测试设置带过期时间的键值"""
        key = self._get_test_key("expire")
        value = "expiring value"
        expire_seconds = 2
        
        # 设置带过期时间的值
        result = self.redis_crud.set(key, value, expire_seconds)
        self.assertTrue(result)
        
        # 立即获取应该成功
        retrieved_value = self.redis_crud.get(key)
        self.assertEqual(retrieved_value, value)
        
        # 等待过期
        time.sleep(expire_seconds + 1)
        
        # 过期后获取应该返回None
        expired_value = self.redis_crud.get(key)
        self.assertIsNone(expired_value)

    def test_get_nonexistent_key(self):
        """测试获取不存在的键"""
        key = self._get_test_key("nonexistent")
        
        result = self.redis_crud.get(key)
        self.assertIsNone(result)

    def test_delete_existing_key(self):
        """测试删除存在的键"""
        key = self._get_test_key("delete")
        value = "to be deleted"
        
        # 设置值
        self.redis_crud.set(key, value)
        
        # 确认键存在
        self.assertTrue(self.redis_crud.exists(key))
        
        # 删除键
        result = self.redis_crud.delete(key)
        self.assertTrue(result)
        
        # 确认键不存在
        self.assertFalse(self.redis_crud.exists(key))

    def test_delete_nonexistent_key(self):
        """测试删除不存在的键"""
        key = self._get_test_key("nonexistent_delete")
        
        result = self.redis_crud.delete(key)
        self.assertFalse(result)

    def test_exists_key(self):
        """测试检查键是否存在"""
        key = self._get_test_key("exists")
        value = "test value"
        
        # 键不存在时
        self.assertFalse(self.redis_crud.exists(key))
        
        # 设置键
        self.redis_crud.set(key, value)
        
        # 键存在时
        self.assertTrue(self.redis_crud.exists(key))

    def test_expire_key(self):
        """测试设置键的过期时间"""
        key = self._get_test_key("expire_later")
        value = "test value"
        
        # 设置键
        self.redis_crud.set(key, value)
        
        # 设置过期时间
        result = self.redis_crud.expire(key, 2)
        self.assertTrue(result)
        
        # 立即检查键存在
        self.assertTrue(self.redis_crud.exists(key))
        
        # 等待过期
        time.sleep(3)
        
        # 检查键已过期
        self.assertFalse(self.redis_crud.exists(key))

    # ==================== Set数据结构操作测试 ====================

    def test_sadd_and_smembers(self):
        """测试Set添加和获取成员"""
        key = self._get_test_key("set")
        values = ["member1", "member2", "member3"]
        
        # 添加成员
        result = self.redis_crud.sadd(key, *values)
        self.assertEqual(result, len(values))
        
        # 获取所有成员
        members = self.redis_crud.smembers(key)
        self.assertEqual(len(members), len(values))
        for value in values:
            self.assertIn(value, members)

    def test_sadd_duplicate_members(self):
        """测试Set添加重复成员"""
        key = self._get_test_key("set_dup")
        
        # 首次添加
        result1 = self.redis_crud.sadd(key, "member1", "member2")
        self.assertEqual(result1, 2)
        
        # 添加重复成员
        result2 = self.redis_crud.sadd(key, "member1", "member3")
        self.assertEqual(result2, 1)  # 只有member3是新的
        
        # 检查总成员数
        members = self.redis_crud.smembers(key)
        self.assertEqual(len(members), 3)

    def test_srem_members(self):
        """测试Set移除成员"""
        key = self._get_test_key("set_rem")
        values = ["member1", "member2", "member3"]
        
        # 添加成员
        self.redis_crud.sadd(key, *values)
        
        # 移除部分成员
        result = self.redis_crud.srem(key, "member1", "member2")
        self.assertEqual(result, 2)
        
        # 检查剩余成员
        members = self.redis_crud.smembers(key)
        self.assertEqual(len(members), 1)
        self.assertIn("member3", members)

    def test_scard_set_size(self):
        """测试获取Set大小"""
        key = self._get_test_key("set_size")
        
        # 空Set
        size = self.redis_crud.scard(key)
        self.assertEqual(size, 0)
        
        # 添加成员
        self.redis_crud.sadd(key, "member1", "member2", "member3")
        
        # 检查大小
        size = self.redis_crud.scard(key)
        self.assertEqual(size, 3)

    # ==================== Hash数据结构操作测试 ====================

    def test_hset_and_hget(self):
        """测试Hash设置和获取字段"""
        key = self._get_test_key("hash")
        field = "test_field"
        value = "test_value"
        
        # 设置字段
        result = self.redis_crud.hset(key, field, value)
        self.assertTrue(result)
        
        # 获取字段
        retrieved_value = self.redis_crud.hget(key, field)
        self.assertEqual(retrieved_value, value)

    def test_hset_and_hget_complex_value(self):
        """测试Hash设置和获取复杂值"""
        key = self._get_test_key("hash_complex")
        field = "complex_field"
        value = {"nested": "object", "numbers": [1, 2, 3]}
        
        # 设置字段
        result = self.redis_crud.hset(key, field, value)
        self.assertTrue(result)
        
        # 获取字段
        retrieved_value = self.redis_crud.hget(key, field)
        self.assertEqual(retrieved_value, value)

    def test_hgetall(self):
        """测试获取Hash的所有字段"""
        key = self._get_test_key("hash_all")
        fields_values = {
            "field1": "value1",
            "field2": {"nested": "object"},
            "field3": [1, 2, 3]
        }
        
        # 设置多个字段
        for field, value in fields_values.items():
            self.redis_crud.hset(key, field, value)
        
        # 获取所有字段
        all_fields = self.redis_crud.hgetall(key)
        
        self.assertEqual(len(all_fields), len(fields_values))
        for field, expected_value in fields_values.items():
            self.assertIn(field, all_fields)
            self.assertEqual(all_fields[field], expected_value)

    def test_hdel_fields(self):
        """测试删除Hash字段"""
        key = self._get_test_key("hash_del")
        
        # 设置字段
        self.redis_crud.hset(key, "field1", "value1")
        self.redis_crud.hset(key, "field2", "value2")
        self.redis_crud.hset(key, "field3", "value3")
        
        # 删除字段
        result = self.redis_crud.hdel(key, "field1", "field2")
        self.assertEqual(result, 2)
        
        # 检查剩余字段
        all_fields = self.redis_crud.hgetall(key)
        self.assertEqual(len(all_fields), 1)
        self.assertIn("field3", all_fields)

    def test_hget_nonexistent_field(self):
        """测试获取不存在的Hash字段"""
        key = self._get_test_key("hash_nonexistent")
        
        result = self.redis_crud.hget(key, "nonexistent_field")
        self.assertIsNone(result)

    # ==================== 批量操作测试 ====================

    def test_mget_multiple_keys(self):
        """测试批量获取多个键"""
        keys = [self._get_test_key(f"mget_{i}") for i in range(3)]
        values = [f"value_{i}" for i in range(3)]
        
        # 设置多个键
        for key, value in zip(keys, values):
            self.redis_crud.set(key, value)
        
        # 批量获取
        results = self.redis_crud.mget(keys)
        
        self.assertEqual(len(results), len(keys))
        for result, expected_value in zip(results, values):
            self.assertEqual(result, expected_value)

    def test_mget_with_nonexistent_keys(self):
        """测试批量获取包含不存在键的情况"""
        existing_key = self._get_test_key("mget_existing")
        nonexistent_key = self._get_test_key("mget_nonexistent")
        
        # 只设置一个键
        self.redis_crud.set(existing_key, "existing_value")
        
        # 批量获取
        results = self.redis_crud.mget([existing_key, nonexistent_key])
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], "existing_value")
        self.assertIsNone(results[1])

    def test_delete_pattern(self):
        """测试按模式删除键"""
        pattern_prefix = f"{self.test_prefix}_pattern"
        keys = [f"{pattern_prefix}_{i}" for i in range(3)]
        
        # 设置多个匹配模式的键
        for key in keys:
            self.redis_crud.set(key, f"value_{key}")
            self.test_keys.append(key)  # 添加到清理列表
        
        # 设置一个不匹配的键
        other_key = self._get_test_key("other")
        self.redis_crud.set(other_key, "other_value")
        
        # 按模式删除
        deleted_count = self.redis_crud.delete_pattern(f"{pattern_prefix}_*")
        self.assertEqual(deleted_count, len(keys))
        
        # 检查匹配的键被删除
        for key in keys:
            self.assertFalse(self.redis_crud.exists(key))
        
        # 检查不匹配的键仍存在
        self.assertTrue(self.redis_crud.exists(other_key))

    def test_keys_pattern_matching(self):
        """测试按模式获取键名"""
        pattern_prefix = f"{self.test_prefix}_keys"
        keys = [f"{pattern_prefix}_{i}" for i in range(3)]
        
        # 设置多个匹配模式的键
        for key in keys:
            self.redis_crud.set(key, f"value_{key}")
            self.test_keys.append(key)
        
        # 设置一个不匹配的键
        other_key = self._get_test_key("other")
        self.redis_crud.set(other_key, "other_value")
        
        # 按模式获取键名
        matching_keys = self.redis_crud.keys(f"{pattern_prefix}_*")
        
        self.assertEqual(len(matching_keys), len(keys))
        for key in keys:
            self.assertIn(key, matching_keys)
        
        # 不匹配的键不应该在结果中
        self.assertNotIn(other_key, matching_keys)

    # ==================== 系统信息和监控测试 ====================

    def test_redis_info(self):
        """测试获取Redis服务器信息"""
        info = self.redis_crud.info()
        
        self.assertIsInstance(info, dict)
        self.assertTrue(info.get("connected", False))
        self.assertIn("version", info)
        self.assertIsNotNone(info.get("version"))

    def test_ping_connection(self):
        """测试Redis连接测试"""
        result = self.redis_crud.ping()
        self.assertTrue(result)

    def test_pipeline_creation(self):
        """测试Redis pipeline创建"""
        pipeline = self.redis_crud.pipeline()
        self.assertIsNotNone(pipeline)
        
        # 测试pipeline基本操作
        key = self._get_test_key("pipeline")
        pipeline.set(key, "pipeline_value")
        pipeline.get(key)
        results = pipeline.execute()
        
        # pipeline.set通常返回True，pipeline.get返回实际值
        self.assertEqual(len(results), 2)
        self.assertTrue(results[0])  # set操作结果
        self.assertEqual(results[1], b"pipeline_value" if isinstance(results[1], bytes) else "pipeline_value")

    # ==================== 错误处理和边界条件测试 ====================

    def test_large_value_handling(self):
        """测试大值处理"""
        key = self._get_test_key("large_value")
        large_value = "x" * 10000  # 10KB字符串
        
        # 设置大值
        result = self.redis_crud.set(key, large_value)
        self.assertTrue(result)
        
        # 获取大值
        retrieved_value = self.redis_crud.get(key)
        self.assertEqual(retrieved_value, large_value)

    def test_special_characters_in_values(self):
        """测试值中的特殊字符处理"""
        key = self._get_test_key("special_chars")
        special_value = "测试中文\n换行\t制表符\"引号'单引号\\反斜杠"
        
        # 设置包含特殊字符的值
        result = self.redis_crud.set(key, special_value)
        self.assertTrue(result)
        
        # 获取值
        retrieved_value = self.redis_crud.get(key)
        self.assertEqual(retrieved_value, special_value)

    def test_nested_complex_data(self):
        """测试嵌套复杂数据结构"""
        key = self._get_test_key("nested_complex")
        complex_value = {
            "users": [
                {"id": 1, "name": "张三", "tags": ["developer", "python"]},
                {"id": 2, "name": "李四", "tags": ["designer", "ui/ux"]}
            ],
            "metadata": {
                "created_at": "2024-01-15T10:30:00",
                "version": "1.0.0",
                "settings": {
                    "debug": True,
                    "max_connections": 100
                }
            }
        }
        
        # 设置复杂值
        result = self.redis_crud.set(key, complex_value)
        self.assertTrue(result)
        
        # 获取复杂值
        retrieved_value = self.redis_crud.get(key)
        self.assertEqual(retrieved_value, complex_value)

    def test_empty_values(self):
        """测试空值处理"""
        # 空字符串
        key1 = self._get_test_key("empty_string")
        self.redis_crud.set(key1, "")
        self.assertEqual(self.redis_crud.get(key1), "")
        
        # 空字典
        key2 = self._get_test_key("empty_dict")
        self.redis_crud.set(key2, {})
        self.assertEqual(self.redis_crud.get(key2), {})
        
        # 空列表
        key3 = self._get_test_key("empty_list")
        self.redis_crud.set(key3, [])
        self.assertEqual(self.redis_crud.get(key3), [])

    def test_numeric_values(self):
        """测试数值类型处理"""
        key = self._get_test_key("numeric")
        numeric_data = {
            "integer": 42,
            "float": 3.14159,
            "negative": -100,
            "zero": 0,
            "large_number": 999999999999
        }
        
        # 设置数值数据
        result = self.redis_crud.set(key, numeric_data)
        self.assertTrue(result)
        
        # 获取数值数据
        retrieved_value = self.redis_crud.get(key)
        self.assertEqual(retrieved_value, numeric_data)

    # ==================== 集成场景测试 ====================

    def test_data_lifecycle_workflow(self):
        """测试数据完整生命周期"""
        key = self._get_test_key("lifecycle")
        initial_value = {"status": "created", "data": [1, 2, 3]}
        
        # 1. 创建数据
        self.redis_crud.set(key, initial_value)
        self.assertEqual(self.redis_crud.get(key), initial_value)
        
        # 2. 更新数据
        updated_value = {"status": "updated", "data": [1, 2, 3, 4]}
        self.redis_crud.set(key, updated_value)
        self.assertEqual(self.redis_crud.get(key), updated_value)
        
        # 3. 设置过期时间
        self.redis_crud.expire(key, 300)  # 5分钟过期
        self.assertTrue(self.redis_crud.exists(key))
        
        # 4. 删除数据
        self.redis_crud.delete(key)
        self.assertFalse(self.redis_crud.exists(key))

    def test_multiple_data_structures(self):
        """测试多种数据结构的协同使用"""
        # String类型
        string_key = self._get_test_key("multi_string")
        self.redis_crud.set(string_key, "string_value")
        
        # Set类型
        set_key = self._get_test_key("multi_set")
        self.redis_crud.sadd(set_key, "member1", "member2")
        
        # Hash类型
        hash_key = self._get_test_key("multi_hash")
        self.redis_crud.hset(hash_key, "field1", "hash_value")
        
        # 验证所有数据结构都正常工作
        self.assertEqual(self.redis_crud.get(string_key), "string_value")
        self.assertEqual(len(self.redis_crud.smembers(set_key)), 2)
        self.assertEqual(self.redis_crud.hget(hash_key, "field1"), "hash_value")

    def test_concurrent_operations_simulation(self):
        """模拟并发操作场景"""
        keys = [self._get_test_key(f"concurrent_{i}") for i in range(10)]
        
        # 批量设置数据
        for i, key in enumerate(keys):
            self.redis_crud.set(key, f"value_{i}")
        
        # 批量验证数据
        for i, key in enumerate(keys):
            value = self.redis_crud.get(key)
            self.assertEqual(value, f"value_{i}")
        
        # 批量删除数据
        for key in keys:
            self.redis_crud.delete(key)
        
        # 验证删除结果
        for key in keys:
            self.assertFalse(self.redis_crud.exists(key))


if __name__ == '__main__':
    unittest.main()