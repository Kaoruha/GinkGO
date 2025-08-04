"""
RedisService单元测试 - 新架构版本

使用真实Redis连接测试RedisService的核心功能：
- 数据同步进度管理
- 任务状态管理
- 通用缓存操作
- 系统监控
"""

import unittest
import time
from datetime import datetime, timedelta
from typing import Set, Dict, Any

from ginkgo.data.services.redis_service import RedisService
from ginkgo.data.crud.redis_crud import RedisCRUD


class TestRedisServiceNew(unittest.TestCase):
    """RedisService单元测试类 - 新架构适配"""

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
        crud = self.redis_service.crud_repo
        pattern_keys = crud.keys(f"{self.test_prefix}*")
        for key in pattern_keys:
            crud.delete(key)
    
    def _get_test_key(self, suffix: str = "") -> str:
        """生成测试专用键名"""
        key = f"{self.test_prefix}_{suffix}" if suffix else f"{self.test_prefix}"
        self.test_keys.append(key)
        return key

    # ==================== 架构测试 ====================

    def test_service_architecture(self):
        """测试服务架构"""
        # 检查继承关系
        from ginkgo.data.services.base_service import DataService
        self.assertIsInstance(self.redis_service, DataService)
        
        # 检查CRUD依赖
        self.assertIsInstance(self.redis_service.crud_repo, RedisCRUD)
        self.assertIsInstance(self.redis_service.data_source, RedisCRUD)
        self.assertEqual(self.redis_service.crud_repo, self.redis_service.data_source)
        
        # 检查向后兼容的redis属性
        self.assertIsNotNone(self.redis_service.redis)

    def test_custom_crud_injection(self):
        """测试自定义CRUD注入"""
        custom_crud = RedisCRUD()
        service = RedisService(redis_crud=custom_crud)
        
        self.assertEqual(service.crud_repo, custom_crud)
        self.assertEqual(service.data_source, custom_crud)

    # ==================== 数据同步进度管理测试 ====================

    def test_sync_progress_workflow(self):
        """测试同步进度完整工作流"""
        code = f"test_{self.test_prefix}_SZ"  # 使用唯一的测试代码
        dates = [datetime(2024, 1, i) for i in range(1, 4)]
        data_type = "tick"
        
        # 0. 先清理可能的残留数据
        self.redis_service.clear_sync_progress(code, data_type)
        
        # 1. 初始状态 - 无进度
        progress = self.redis_service.get_sync_progress(code, data_type)
        self.assertEqual(len(progress), 0)
        
        # 2. 保存进度
        for date in dates:
            result = self.redis_service.save_sync_progress(code, date, data_type)
            self.assertTrue(result)
        
        # 3. 检查进度
        progress = self.redis_service.get_sync_progress(code, data_type)
        self.assertEqual(len(progress), len(dates))
        
        for date in dates:
            date_str = date.strftime("%Y-%m-%d")
            self.assertIn(date_str, progress)
            self.assertTrue(self.redis_service.check_date_synced(code, date, data_type))
        
        # 4. 获取进度摘要
        start_date = dates[0]
        end_date = dates[-1] + timedelta(days=2)  # 包含未同步日期
        
        summary = self.redis_service.get_progress_summary(code, start_date, end_date, data_type)
        
        self.assertEqual(summary["code"], code)
        self.assertEqual(summary["data_type"], data_type)
        self.assertEqual(summary["synced_count"], len(dates))
        self.assertGreater(summary["missing_count"], 0)
        self.assertGreater(summary["completion_rate"], 0)
        self.assertLess(summary["completion_rate"], 1.0)
        
        # 5. 清除进度
        cleared = self.redis_service.clear_sync_progress(code, data_type)
        self.assertTrue(cleared)
        
        # 6. 验证清除结果
        progress_after_clear = self.redis_service.get_sync_progress(code, data_type)
        self.assertEqual(len(progress_after_clear), 0)

    def test_sync_progress_different_data_types(self):
        """测试不同数据类型的同步进度管理"""
        code = f"test_{self.test_prefix}_types"  # 使用唯一的测试代码
        date = datetime(2024, 1, 15)
        data_types = ["tick", "bar", "adjustfactor"]
        
        # 先清理可能的残留数据
        for data_type in data_types:
            self.redis_service.clear_sync_progress(code, data_type)
        
        # 为不同数据类型保存进度
        for data_type in data_types:
            result = self.redis_service.save_sync_progress(code, date, data_type)
            self.assertTrue(result)
        
        # 验证各数据类型的进度独立存储
        for data_type in data_types:
            progress = self.redis_service.get_sync_progress(code, data_type)
            self.assertEqual(len(progress), 1)
            self.assertIn("2024-01-15", progress)
        
        # 清理
        for data_type in data_types:
            self.redis_service.clear_sync_progress(code, data_type)

    # ==================== 任务状态管理测试 ====================

    def test_task_status_lifecycle(self):
        """测试任务状态生命周期管理"""
        task_id = f"test_task_{int(time.time())}"
        
        # 1. 初始状态 - 任务不存在
        status = self.redis_service.get_task_status(task_id)
        self.assertIsNone(status)
        
        # 2. 保存任务状态
        metadata = {"stage": "init", "progress": 0}
        result = self.redis_service.save_task_status(task_id, "PENDING", metadata)
        self.assertTrue(result)
        
        # 3. 获取任务状态
        status = self.redis_service.get_task_status(task_id)
        self.assertIsNotNone(status)
        self.assertEqual(status["task_id"], task_id)
        self.assertEqual(status["status"], "PENDING")
        self.assertEqual(status["metadata"], metadata)
        self.assertIn("updated_at", status)
        
        # 4. 更新任务状态
        updated_metadata = {"stage": "processing", "progress": 50}
        result = self.redis_service.save_task_status(task_id, "RUNNING", updated_metadata)
        self.assertTrue(result)
        
        status = self.redis_service.get_task_status(task_id)
        self.assertEqual(status["status"], "RUNNING")
        self.assertEqual(status["metadata"], updated_metadata)
        
        # 5. 完成任务
        final_metadata = {"stage": "complete", "progress": 100}
        self.redis_service.save_task_status(task_id, "SUCCESS", final_metadata)
        
        status = self.redis_service.get_task_status(task_id)
        self.assertEqual(status["status"], "SUCCESS")
        
        # 清理测试数据
        task_key = f"task_status_{task_id}"
        self.redis_service.delete_cache(task_key)

    # ==================== 通用缓存操作测试 ====================

    def test_cache_operations(self):
        """测试通用缓存操作"""
        key = self._get_test_key("cache_test")
        
        # 1. 设置和获取字符串值
        string_value = "test string"
        result = self.redis_service.set_cache(key, string_value)
        self.assertTrue(result)
        
        retrieved_value = self.redis_service.get_cache(key)
        self.assertEqual(retrieved_value, string_value)
        
        # 2. 设置和获取复杂对象
        complex_value = {
            "name": "test",
            "data": [1, 2, 3],
            "nested": {"key": "value"}
        }
        
        result = self.redis_service.set_cache(key, complex_value)
        self.assertTrue(result)
        
        retrieved_value = self.redis_service.get_cache(key)
        self.assertEqual(retrieved_value, complex_value)
        
        # 3. 检查键存在
        self.assertTrue(self.redis_service.exists(key))
        
        # 4. 删除缓存
        result = self.redis_service.delete_cache(key)
        self.assertTrue(result)
        
        # 5. 验证删除结果
        self.assertFalse(self.redis_service.exists(key))
        retrieved_value = self.redis_service.get_cache(key)
        self.assertIsNone(retrieved_value)

    def test_cache_with_expiration(self):
        """测试带过期时间的缓存"""
        key = self._get_test_key("expire_test")
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
        retrieved_value = self.redis_service.get_cache(key)
        self.assertIsNone(retrieved_value)
        self.assertFalse(self.redis_service.exists(key))

    # ==================== 系统监控测试 ====================

    def test_redis_info(self):
        """测试Redis信息获取"""
        info = self.redis_service.get_redis_info()
        
        self.assertIsInstance(info, dict)
        self.assertTrue(info.get("connected", False))
        self.assertIn("version", info)
        self.assertIsNotNone(info.get("version"))

    # ==================== 错误处理和边界条件测试 ====================

    def test_nonexistent_key_operations(self):
        """测试对不存在键的操作"""
        nonexistent_key = self._get_test_key("nonexistent")
        
        # 获取不存在的键
        result = self.redis_service.get_cache(nonexistent_key)
        self.assertIsNone(result)
        
        # 删除不存在的键
        result = self.redis_service.delete_cache(nonexistent_key)
        self.assertFalse(result)
        
        # 检查不存在的键
        result = self.redis_service.exists(nonexistent_key)
        self.assertFalse(result)

    def test_empty_values(self):
        """测试空值处理"""
        key = self._get_test_key("empty_values")
        
        # 空字符串
        self.redis_service.set_cache(key, "")
        self.assertEqual(self.redis_service.get_cache(key), "")
        
        # 空字典
        self.redis_service.set_cache(key, {})
        self.assertEqual(self.redis_service.get_cache(key), {})
        
        # 空列表
        self.redis_service.set_cache(key, [])
        self.assertEqual(self.redis_service.get_cache(key), [])

    # ==================== 集成场景测试 ====================

    def test_mixed_operations_workflow(self):
        """测试混合操作工作流"""
        code = f"test_{self.test_prefix}_mixed"  # 使用唯一的测试代码
        task_id = f"sync_task_{int(time.time())}"
        
        # 先清理可能的残留数据
        self.redis_service.clear_sync_progress(code, "tick")
        
        # 1. 开始任务
        self.redis_service.save_task_status(task_id, "RUNNING", {"progress": 0})
        
        # 2. 保存同步进度
        dates = [datetime(2024, 1, i) for i in range(1, 4)]
        for i, date in enumerate(dates):
            self.redis_service.save_sync_progress(code, date, "tick")
            
            # 更新任务进度
            progress = (i + 1) / len(dates) * 100
            self.redis_service.save_task_status(task_id, "RUNNING", {"progress": progress})
        
        # 3. 完成任务
        self.redis_service.save_task_status(task_id, "SUCCESS", {"progress": 100})
        
        # 4. 验证结果
        task_status = self.redis_service.get_task_status(task_id)
        self.assertEqual(task_status["status"], "SUCCESS")
        
        sync_progress = self.redis_service.get_sync_progress(code, "tick")
        self.assertEqual(len(sync_progress), len(dates))
        
        # 5. 清理
        self.redis_service.clear_sync_progress(code, "tick")
        task_key = f"task_status_{task_id}"
        self.redis_service.delete_cache(task_key)


if __name__ == '__main__':
    unittest.main()