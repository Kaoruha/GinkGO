"""
RedisService单元测试

使用真实Redis连接测试Redis缓存服务的所有功能：
- 数据同步进度管理
- 任务状态管理  
- 通用缓存操作
- 系统监控
- 错误处理
"""

import unittest
import time
import json
from datetime import datetime, timedelta
from typing import Set, Dict, Any

from ginkgo.data.services.redis_service import RedisService
from ginkgo.data.crud.redis_crud import RedisCRUD


class TestRedisService(unittest.TestCase):
    """RedisService单元测试类 - 使用真实Redis连接"""

    def setUp(self):
        """每个测试方法执行前的设置"""
        # 创建真实RedisService实例
        self.redis_service = RedisService()
        
        # 检查Redis连接可用性
        redis_info = self.redis_service.get_redis_info()
        if not redis_info.get("connected", False):
            self.skipTest("Redis connection not available")
        
        # 设置测试键前缀，避免与生产数据冲突
        self.test_prefix = f"test_service_{int(time.time())}_{id(self)}"
        self.test_keys = []
        
    def tearDown(self):
        """每个测试方法执行后的清理"""
        # 清理所有测试过程中创建的键
        for key in self.test_keys:
            self.redis_service.delete_cache(key)
        
        # 清理可能的模式键
        crud = self.redis_service._crud_repo
        pattern_keys = crud.keys(f"{self.test_prefix}*")
        for key in pattern_keys:
            crud.delete(key)
    
    def _get_test_key(self, suffix: str = "") -> str:
        """生成测试专用键名"""
        key = f"{self.test_prefix}_{suffix}" if suffix else f"{self.test_prefix}"
        self.test_keys.append(key)
        return key

    def test_init_with_provided_crud(self):
        """测试使用提供的RedisCRUD初始化"""
        redis_crud = RedisCRUD()
        service = RedisService(redis_crud=redis_crud)
        
        self.assertEqual(service._crud_repo, redis_crud)
        self.assertEqual(service._data_source, redis_crud)
        self.assertEqual(service.service_name, "RedisService")

    def test_init_with_auto_crud_creation(self):
        """测试自动创建RedisCRUD"""
        service = RedisService()
        
        self.assertIsInstance(service._crud_repo, RedisCRUD)
        self.assertIsInstance(service._data_source, RedisCRUD)
        self.assertEqual(service._crud_repo, service._data_source)

    # ==================== 数据同步进度管理测试 ====================

    def test_save_sync_progress_success(self):
        """测试保存同步进度 - 成功情况"""
        code = "000001.SZ"
        date = datetime(2024, 1, 15)
        data_type = "tick"
        
        # 保存同步进度
        result = self.redis_service.save_sync_progress(code, date, data_type)
        self.assertTrue(result)
        
        # 验证数据确实被保存
        sync_progress = self.redis_service.get_sync_progress(code, data_type)
        self.assertIn("2024-01-15", sync_progress)
        
        # 清理测试数据
        self.redis_service.clear_sync_progress(code, data_type)

    def test_save_sync_progress_with_different_data_type(self):
        """测试保存同步进度 - 不同数据类型"""
        code = "000002.SH"
        date = datetime(2024, 2, 20)
        data_type = "bar"
        
        # 保存同步进度
        result = self.redis_service.save_sync_progress(code, date, data_type)
        self.assertTrue(result)
        
        # 验证数据确实被保存
        sync_progress = self.redis_service.get_sync_progress(code, data_type)
        self.assertIn("2024-02-20", sync_progress)
        
        # 清理测试数据
        self.redis_service.clear_sync_progress(code, data_type)

    def test_multiple_sync_progress_dates(self):
        """测试保存多个同步进度日期"""
        code = "000001.SZ"
        dates = [
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
            datetime(2024, 1, 3)
        ]
        data_type = "tick"
        
        # 保存多个日期
        for date in dates:
            result = self.redis_service.save_sync_progress(code, date, data_type)
            self.assertTrue(result)
        
        # 验证所有日期都被保存
        sync_progress = self.redis_service.get_sync_progress(code, data_type)
        for date in dates:
            date_str = date.strftime("%Y-%m-%d")
            self.assertIn(date_str, sync_progress)
        
        # 清理测试数据
        self.redis_service.clear_sync_progress(code, data_type)

    def test_get_sync_progress_success(self):
        """测试获取同步进度 - 成功情况"""
        code = f"test_{self.test_prefix}_SZ"
        data_type = "tick"
        dates = [datetime(2024, 1, 1), datetime(2024, 1, 2), datetime(2024, 1, 3)]
        
        # 先清理可能的残留数据
        self.redis_service.clear_sync_progress(code, data_type)
        
        # 保存测试数据
        for date in dates:
            self.redis_service.save_sync_progress(code, date, data_type)
        
        # 获取同步进度
        result = self.redis_service.get_sync_progress(code, data_type)
        
        # 验证结果
        expected = {"2024-01-01", "2024-01-02", "2024-01-03"}
        self.assertEqual(result, expected)
        
        # 清理测试数据
        self.redis_service.clear_sync_progress(code, data_type)

    def test_get_sync_progress_empty_result(self):
        """测试获取同步进度 - 空结果"""
        code = f"test_{self.test_prefix}_empty"
        data_type = "tick"
        
        # 确保没有数据
        self.redis_service.clear_sync_progress(code, data_type)
        
        # 获取同步进度
        result = self.redis_service.get_sync_progress(code, data_type)
        
        # 验证结果为空
        self.assertEqual(result, set())

    def test_get_sync_progress_different_data_types(self):
        """测试不同数据类型的同步进度独立性"""
        code = f"test_{self.test_prefix}_types"
        date = datetime(2024, 1, 15)
        
        # 为不同数据类型保存进度
        self.redis_service.save_sync_progress(code, date, "tick")
        self.redis_service.save_sync_progress(code, date, "bar")
        
        # 验证不同数据类型的进度独立
        tick_progress = self.redis_service.get_sync_progress(code, "tick")
        bar_progress = self.redis_service.get_sync_progress(code, "bar")
        
        self.assertIn("2024-01-15", tick_progress)
        self.assertIn("2024-01-15", bar_progress)
        
        # 清理测试数据
        self.redis_service.clear_sync_progress(code, "tick")
        self.redis_service.clear_sync_progress(code, "bar")

    def test_check_date_synced_true(self):
        """测试检查日期是否已同步 - 已同步"""
        code = f"test_{self.test_prefix}_sync_check"
        date = datetime(2024, 1, 15)
        data_type = "tick"
        
        # 先清理残留数据
        self.redis_service.clear_sync_progress(code, data_type)
        
        # 保存同步进度
        self.redis_service.save_sync_progress(code, date, data_type)
        
        # 检查日期是否已同步
        result = self.redis_service.check_date_synced(code, date, data_type)
        self.assertTrue(result)
        
        # 清理测试数据
        self.redis_service.clear_sync_progress(code, data_type)

    def test_check_date_synced_false(self):
        """测试检查日期是否已同步 - 未同步"""
        code = f"test_{self.test_prefix}_sync_check_false"
        test_date = datetime(2024, 1, 15)
        other_date = datetime(2024, 1, 16)
        data_type = "tick"
        
        # 先清理残留数据
        self.redis_service.clear_sync_progress(code, data_type)
        
        # 只保存其他日期
        self.redis_service.save_sync_progress(code, other_date, data_type)
        
        # 检查目标日期是否已同步（应该为False）
        result = self.redis_service.check_date_synced(code, test_date, data_type)
        self.assertFalse(result)
        
        # 清理测试数据
        self.redis_service.clear_sync_progress(code, data_type)

    def test_clear_sync_progress_success(self):
        """测试清除同步进度 - 成功"""
        code = f"test_{self.test_prefix}_clear"
        data_type = "tick"
        date = datetime(2024, 1, 15)
        
        # 先保存一些数据
        self.redis_service.save_sync_progress(code, date, data_type)
        
        # 验证数据存在
        progress_before = self.redis_service.get_sync_progress(code, data_type)
        self.assertGreater(len(progress_before), 0)
        
        # 清除进度
        result = self.redis_service.clear_sync_progress(code, data_type)
        self.assertTrue(result)
        
        # 验证数据已清除
        progress_after = self.redis_service.get_sync_progress(code, data_type)
        self.assertEqual(len(progress_after), 0)

    def test_clear_sync_progress_empty_key(self):
        """测试清除不存在的同步进度"""
        code = f"test_{self.test_prefix}_nonexistent"
        data_type = "tick"
        
        # 确保没有数据
        self.redis_service.clear_sync_progress(code, data_type)
        
        # 再次清除（应该仍然成功）
        result = self.redis_service.clear_sync_progress(code, data_type)
        self.assertTrue(result)

    def test_get_progress_summary_complete_range(self):
        """测试获取进度摘要 - 完整范围"""
        code = f"test_{self.test_prefix}_summary_complete"
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 3)
        data_type = "tick"
        
        # 先清理残留数据
        self.redis_service.clear_sync_progress(code, data_type)
        
        # 保存所有日期的同步进度
        dates = [datetime(2024, 1, 1), datetime(2024, 1, 2), datetime(2024, 1, 3)]
        for date in dates:
            self.redis_service.save_sync_progress(code, date, data_type)
        
        # 获取进度摘要
        result = self.redis_service.get_progress_summary(code, start_date, end_date, data_type)
        
        # 验证结果
        self.assertEqual(result["code"], code)
        self.assertEqual(result["data_type"], data_type)
        self.assertEqual(result["total_dates"], 3)
        self.assertEqual(result["synced_count"], 3)
        self.assertEqual(result["missing_count"], 0)
        self.assertEqual(result["completion_rate"], 1.0)
        self.assertEqual(result["missing_dates"], [])
        self.assertIsNone(result["first_missing_date"])
        
        # 清理测试数据
        self.redis_service.clear_sync_progress(code, data_type)

    def test_get_progress_summary_partial_range(self):
        """测试获取进度摘要 - 部分完成"""
        code = f"test_{self.test_prefix}_summary_partial"
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)
        data_type = "tick"
        
        # 先清理残留数据
        self.redis_service.clear_sync_progress(code, data_type)
        
        # 只保存部分日期的同步进度
        synced_dates = [datetime(2024, 1, 1), datetime(2024, 1, 3)]
        for date in synced_dates:
            self.redis_service.save_sync_progress(code, date, data_type)
        
        # 获取进度摘要
        result = self.redis_service.get_progress_summary(code, start_date, end_date, data_type)
        
        # 验证结果
        self.assertEqual(result["total_dates"], 5)
        self.assertEqual(result["synced_count"], 2)
        self.assertEqual(result["missing_count"], 3)
        self.assertEqual(result["completion_rate"], 0.4)
        self.assertEqual(len(result["missing_dates"]), 3)
        self.assertEqual(result["first_missing_date"], datetime(2024, 1, 2).date())
        
        # 清理测试数据
        self.redis_service.clear_sync_progress(code, data_type)

    def test_get_progress_summary_empty_range(self):
        """测试获取进度摘要 - 空范围"""
        code = f"test_{self.test_prefix}_summary_empty"
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        data_type = "tick"
        
        # 确保没有数据
        self.redis_service.clear_sync_progress(code, data_type)
        
        # 获取进度摘要
        result = self.redis_service.get_progress_summary(code, start_date, end_date, data_type)
        
        # 验证结果
        self.assertEqual(result["total_dates"], 1)
        self.assertEqual(result["completion_rate"], 0.0)

    # ==================== 任务状态管理测试 ====================

    def test_save_task_status_success(self):
        """测试保存任务状态 - 成功"""
        task_id = f"test_task_{int(time.time())}"
        status = "RUNNING"
        metadata = {"progress": 50, "total": 100}
        
        # 保存任务状态
        result = self.redis_service.save_task_status(task_id, status, metadata)
        self.assertTrue(result)
        
        # 验证数据已保存
        saved_status = self.redis_service.get_task_status(task_id)
        self.assertIsNotNone(saved_status)
        self.assertEqual(saved_status["task_id"], task_id)
        self.assertEqual(saved_status["status"], status)
        self.assertEqual(saved_status["metadata"], metadata)
        self.assertIn("updated_at", saved_status)
        
        # 清理测试数据
        self.redis_service.delete_cache(f"task_status_{task_id}")

    def test_save_task_status_without_metadata(self):
        """测试保存任务状态 - 无元数据"""
        task_id = f"test_task_no_meta_{int(time.time())}"
        status = "SUCCESS"
        
        # 保存任务状态（不提供metadata）
        result = self.redis_service.save_task_status(task_id, status)
        self.assertTrue(result)
        
        # 验证数据已保存且metadata为空
        saved_status = self.redis_service.get_task_status(task_id)
        self.assertIsNotNone(saved_status)
        self.assertEqual(saved_status["metadata"], {})
        
        # 清理测试数据
        self.redis_service.delete_cache(f"task_status_{task_id}")

    def test_save_and_get_task_status_lifecycle(self):
        """测试任务状态完整生命周期"""
        task_id = f"test_task_lifecycle_{int(time.time())}"
        
        # 1. 初始状态 - 任务不存在
        initial_status = self.redis_service.get_task_status(task_id)
        self.assertIsNone(initial_status)
        
        # 2. 保存初始状态
        result = self.redis_service.save_task_status(task_id, "PENDING", {"stage": "init"})
        self.assertTrue(result)
        
        # 3. 更新状态
        result = self.redis_service.save_task_status(task_id, "RUNNING", {"progress": 50})
        self.assertTrue(result)
        
        # 4. 获取最终状态
        final_status = self.redis_service.get_task_status(task_id)
        self.assertEqual(final_status["status"], "RUNNING")
        self.assertEqual(final_status["metadata"]["progress"], 50)
        
        # 清理测试数据
        self.redis_service.delete_cache(f"task_status_{task_id}")

    def test_get_task_status_not_found(self):
        """测试获取不存在的任务状态"""
        task_id = f"nonexistent_task_{int(time.time())}"
        
        # 获取不存在的任务状态
        result = self.redis_service.get_task_status(task_id)
        
        # 应该返回None
        self.assertIsNone(result)




    # ==================== 通用缓存操作测试 ====================

    def test_set_cache_dict_data(self):
        """测试设置缓存 - 字典数据"""
        key = self._get_test_key("dict")
        value = {"name": "test", "value": 123}
        expire_seconds = 10
        
        # 设置缓存
        result = self.redis_service.set_cache(key, value, expire_seconds)
        self.assertTrue(result)
        
        # 验证缓存内容
        retrieved_value = self.redis_service.get_cache(key)
        self.assertEqual(retrieved_value, value)

    def test_set_cache_list_data(self):
        """测试设置缓存 - 列表数据"""
        key = self._get_test_key("list")
        value = ["item1", "item2", "item3"]
        
        # 设置缓存
        result = self.redis_service.set_cache(key, value)
        self.assertTrue(result)
        
        # 验证缓存内容
        retrieved_value = self.redis_service.get_cache(key)
        self.assertEqual(retrieved_value, value)

    def test_set_cache_string_data(self):
        """测试设置缓存 - 字符串数据"""
        key = self._get_test_key("string")
        value = "simple string"
        
        # 设置缓存
        result = self.redis_service.set_cache(key, value)
        self.assertTrue(result)
        
        # 验证缓存内容
        retrieved_value = self.redis_service.get_cache(key)
        self.assertEqual(retrieved_value, value)

    def test_cache_with_expiration(self):
        """测试带过期时间的缓存"""
        key = self._get_test_key("expire")
        value = "expiring value"
        expire_seconds = 2
        
        # 设置带过期时间的缓存
        result = self.redis_service.set_cache(key, value, expire_seconds)
        self.assertTrue(result)
        
        # 立即检查值存在
        retrieved_value = self.redis_service.get_cache(key)
        self.assertEqual(retrieved_value, value)
        
        # 等待过期
        time.sleep(expire_seconds + 1)
        
        # 检查值已过期
        expired_value = self.redis_service.get_cache(key)
        self.assertIsNone(expired_value)

    def test_get_cache_nonexistent_key(self):
        """测试获取不存在的缓存"""
        key = self._get_test_key("nonexistent")
        
        # 获取不存在的键
        result = self.redis_service.get_cache(key)
        
        # 应该返回None
        self.assertIsNone(result)

    def test_cache_complex_data_types(self):
        """测试缓存复杂数据类型"""
        test_cases = [
            ("string", "simple string"),
            ("dict", {"name": "test", "value": 123}),
            ("list", [1, 2, 3, "four"]),
            ("nested", {"data": [{"id": 1}, {"id": 2}]}),
            ("empty_dict", {}),
            ("empty_list", [])
        ]
        
        for suffix, value in test_cases:
            key = self._get_test_key(suffix)
            
            # 设置缓存
            set_result = self.redis_service.set_cache(key, value)
            self.assertTrue(set_result)
            
            # 获取缓存
            get_result = self.redis_service.get_cache(key)
            self.assertEqual(get_result, value)





    def test_delete_cache_success(self):
        """测试删除缓存 - 成功"""
        key = self._get_test_key("delete_test")
        value = "test value"
        
        # 先设置缓存
        self.redis_service.set_cache(key, value)
        
        # 确认键存在
        result = self.redis_service.exists(key)
        self.assertTrue(result.success)
        self.assertTrue(result.data)
        
        # 删除缓存
        result = self.redis_service.delete_cache(key)
        self.assertTrue(result)
        
        # 确认键不存在
        result = self.redis_service.exists(key)
        self.assertTrue(result.success)
        self.assertFalse(result.data)

    def test_delete_cache_not_found(self):
        """测试删除不存在的缓存"""
        key = self._get_test_key("nonexistent_delete")
        
        # 删除不存在的键
        result = self.redis_service.delete_cache(key)
        
        # 应该返回False
        self.assertFalse(result)


    def test_exists_true(self):
        """测试检查键是否存在 - 存在"""
        key = self._get_test_key("exists_true")
        value = "test value"
        
        # 先设置缓存
        self.redis_service.set_cache(key, value)
        
        # 检查键存在
        result = self.redis_service.exists(key)
        self.assertTrue(result.success)
        self.assertTrue(result.data)

    def test_exists_false(self):
        """测试检查键是否存在 - 不存在"""
        key = self._get_test_key("exists_false")
        
        # 检查不存在的键
        result = self.redis_service.exists(key)
        self.assertTrue(result.success)
        self.assertFalse(result.data)


    # ==================== 系统监控测试 ====================

    def test_get_redis_info_success(self):
        """测试获取Redis信息 - 成功"""
        # 获取Redis信息
        result = self.redis_service.get_redis_info()
        
        # 验证基本信息存在
        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("connected", False))
        self.assertIn("version", result)
        self.assertIsNotNone(result.get("version"))



    # ==================== 边界条件和错误处理测试 ====================

    def test_progress_summary_single_day(self):
        """测试进度摘要 - 单日范围"""
        code = f"test_{self.test_prefix}_single_day"
        date = datetime(2024, 1, 15)
        data_type = "tick"
        
        # 先清理残留数据
        self.redis_service.clear_sync_progress(code, data_type)
        
        # 保存同步进度
        self.redis_service.save_sync_progress(code, date, data_type)
        
        # 获取进度摘要
        result = self.redis_service.get_progress_summary(code, date, date, data_type)
        
        # 验证结果
        self.assertEqual(result["total_dates"], 1)
        self.assertEqual(result["synced_count"], 1)
        self.assertEqual(result["completion_rate"], 1.0)
        
        # 清理测试数据
        self.redis_service.clear_sync_progress(code, data_type)

    def test_save_sync_progress_date_formatting(self):
        """测试保存同步进度的日期格式化"""
        code = f"test_{self.test_prefix}_date_format"
        data_type = "tick"
        
        # 先清理残留数据
        self.redis_service.clear_sync_progress(code, data_type)
        
        # 测试不同的日期格式
        dates = [
            datetime(2024, 1, 5),    # 单位数月日
            datetime(2024, 12, 25),  # 双位数月日
            datetime(2024, 2, 29),   # 闰年
        ]
        
        for date in dates:
            result = self.redis_service.save_sync_progress(code, date, data_type)
            self.assertTrue(result)
        
        # 验证所有日期都被保存
        progress = self.redis_service.get_sync_progress(code, data_type)
        expected_dates = {date.strftime("%Y-%m-%d") for date in dates}
        self.assertEqual(progress, expected_dates)
        
        # 清理测试数据
        self.redis_service.clear_sync_progress(code, data_type)

    def test_data_type_variations(self):
        """测试不同数据类型的键名生成"""
        code = f"test_{self.test_prefix}_data_types"
        date = datetime(2024, 1, 15)
        
        data_types = ["tick", "bar", "adjustfactor", "custom_type"]
        
        # 先清理所有数据类型的残留数据
        for data_type in data_types:
            self.redis_service.clear_sync_progress(code, data_type)
        
        # 保存不同数据类型的进度
        for data_type in data_types:
            result = self.redis_service.save_sync_progress(code, date, data_type)
            self.assertTrue(result)
        
        # 验证每种数据类型都独立存储
        for data_type in data_types:
            progress = self.redis_service.get_sync_progress(code, data_type)
            self.assertIn("2024-01-15", progress)
        
        # 清理测试数据
        for data_type in data_types:
            self.redis_service.clear_sync_progress(code, data_type)

    def test_task_status_datetime_serialization(self):
        """测试任务状态的日期时间序列化"""
        task_id = f"datetime_test_{int(time.time())}"
        status = "RUNNING"
        
        # 保存任务状态
        result = self.redis_service.save_task_status(task_id, status)
        self.assertTrue(result)
        
        # 获取保存的数据并验证日期时间格式
        saved_status = self.redis_service.get_task_status(task_id)
        self.assertIsNotNone(saved_status)
        self.assertIn("updated_at", saved_status)
        
        # 验证日期时间格式为ISO格式
        updated_at = saved_status["updated_at"]
        self.assertRegex(updated_at, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        
        # 清理测试数据
        self.redis_service.delete_cache(f"task_status_{task_id}")

    # ==================== 集成场景测试 ====================

    def test_sync_progress_workflow(self):
        """测试同步进度的完整工作流程"""
        code = f"test_{self.test_prefix}_workflow"
        dates = [datetime(2024, 1, i) for i in range(1, 6)]  # 1月1日到5日
        data_type = "tick"
        
        # 1. 清除进度
        cleared = self.redis_service.clear_sync_progress(code, data_type)
        self.assertTrue(cleared)
        
        # 2. 保存部分进度
        for date in dates[:3]:  # 只保存前3天
            result = self.redis_service.save_sync_progress(code, date, data_type)
            self.assertTrue(result)
        
        # 3. 检查进度摘要
        summary = self.redis_service.get_progress_summary(
            code, dates[0], dates[-1], data_type
        )
        
        # 验证结果
        self.assertEqual(summary["total_dates"], 5)
        self.assertEqual(summary["synced_count"], 3)
        self.assertEqual(summary["completion_rate"], 0.6)
        self.assertEqual(len(summary["missing_dates"]), 2)
        
        # 清理测试数据
        self.redis_service.clear_sync_progress(code, data_type)

    def test_task_lifecycle_management(self):
        """测试任务生命周期管理"""
        task_id = f"lifecycle_test_{int(time.time())}"
        
        # 1. 保存初始状态
        result1 = self.redis_service.save_task_status(task_id, "PENDING", {"stage": "init"})
        self.assertTrue(result1)
        
        # 2. 更新运行状态
        result2 = self.redis_service.save_task_status(task_id, "RUNNING", {"progress": 50})
        self.assertTrue(result2)
        
        # 3. 完成状态
        result3 = self.redis_service.save_task_status(
            task_id, "SUCCESS", {"completed_at": "2024-01-15T15:00:00"}
        )
        self.assertTrue(result3)
        
        # 4. 获取最终状态
        status = self.redis_service.get_task_status(task_id)
        self.assertEqual(status["status"], "SUCCESS")
        self.assertEqual(status["metadata"]["completed_at"], "2024-01-15T15:00:00")
        
        # 清理测试数据
        self.redis_service.delete_cache(f"task_status_{task_id}")


    # ==================== 性能和并发测试 ====================

    def test_bulk_sync_progress_operations(self):
        """测试批量同步进度操作"""
        code = f"test_{self.test_prefix}_bulk"
        date_range = [datetime(2024, 1, i) for i in range(1, 11)]  # 1月10日
        data_type = "tick"
        
        # 先清理残留数据
        self.redis_service.clear_sync_progress(code, data_type)
        
        # 批量保存进度
        for date in date_range:
            result = self.redis_service.save_sync_progress(code, date, data_type)
            self.assertTrue(result)
        
        # 验证保存的数据
        progress = self.redis_service.get_sync_progress(code, data_type)
        self.assertEqual(len(progress), len(date_range))
        
        # 清理测试数据
        self.redis_service.clear_sync_progress(code, data_type)

    def test_concurrent_task_status_updates(self):
        """测试并发任务状态更新"""
        task_ids = [f"test_task_{int(time.time())}_{i:03d}" for i in range(5)]
        
        # 模拟并发更新
        for task_id in task_ids:
            result = self.redis_service.save_task_status(
                task_id, "RUNNING", {"worker_id": task_id[-3:]}
            )
            self.assertTrue(result)
        
        # 验证所有任务都被保存
        for task_id in task_ids:
            status = self.redis_service.get_task_status(task_id)
            self.assertIsNotNone(status)
            self.assertEqual(status["status"], "RUNNING")
        
        # 清理测试数据
        for task_id in task_ids:
            self.redis_service.delete_cache(f"task_status_{task_id}")


if __name__ == '__main__':
    unittest.main()