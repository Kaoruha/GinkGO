import unittest
import sys
import os
import pandas as pd
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

try:
    from ginkgo.data.services.engine_service import EngineService
    from ginkgo.data.services.base_service import ServiceResult
    from ginkgo.data.crud.engine_crud import EngineCRUD
    from ginkgo.data.crud.engine_portfolio_mapping_crud import EnginePortfolioMappingCRUD
    from ginkgo.data.models import MEngine, MEnginePortfolioMapping
    from ginkgo.enums import ENGINESTATUS_TYPES, SOURCE_TYPES
    from ginkgo.libs import GCONF, GLOG
    from ginkgo.data.containers import container
except ImportError as e:
    print(f"Import error: {e}")
    EngineService = None
    GCONF = None
    container = None


class EngineServiceTest(unittest.TestCase):
    """
    EngineService 集成测试
    测试引擎管理功能和数据库操作
    使用真实数据库验证业务逻辑正确性
    """

    @classmethod
    def setUpClass(cls):
        """类级别设置"""
        if EngineService is None or GCONF is None or container is None:
            raise AssertionError("Required components not available")

        print(":white_check_mark: EngineService test setup completed")

    def setUp(self):
        """每个测试前的设置"""
        # 使用真实的引擎服务，不使用Mock
        self.service = container.engine_service()
        self.test_engines = []  # 存储测试中创建的引擎UUID
        self.test_mappings = []  # 存储测试中创建的映射UUID

    def tearDown(self):
        """每个测试后的清理"""
        # 清理测试创建的映射
        for mapping_uuid in self.test_mappings:
            try:
                mapping_crud = EnginePortfolioMappingCRUD()
                mapping_crud.soft_remove(filters={"uuid": mapping_uuid})
            except Exception as e:
                print(f"Warning: Failed to cleanup mapping {mapping_uuid}: {e}")

        # 清理测试创建的引擎
        for engine_uuid in self.test_engines:
            try:
                self.service.delete(engine_uuid)
            except Exception as e:
                print(f"Warning: Failed to cleanup engine {engine_uuid}: {e}")

    def test_create_engine_success(self):
        """
        测试成功创建引擎 - 使用真实数据库操作

        评审问题：
        - 原测试过度使用Mock，失去了测试真实性
        - 修改为使用真实数据库操作，验证实际数据持久化

        评审改进建议：
        - 返回格式不一致：使用了result.is_success()而不是result.is_success()
        - 缺少ServiceResult完整性验证：没有验证result.data结构
        - 建议统一使用ServiceResult格式验证
        - 建议增加对时间戳字段和默认状态的验证
        """
        # 创建唯一引擎名称
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        engine_name = f"test_engine_{timestamp}"

        # 执行创建引擎操作
        result = self.service.add(
            name=engine_name,
            is_live=False,
            description="Test engine for unit testing"
        )

        # 验证操作结果
        self.assertIsInstance(result, ServiceResult)
        self.assertTrue(result.is_success(), f"Engine creation failed: {result.error}")

        # 验证返回的引擎数据
        self.assertIsNotNone(result.data)
        engine_info = result.data['engine_info']
        self.assertEqual(engine_info['name'], engine_name)
        self.assertFalse(engine_info['is_live'])

        # 验证引擎确实被创建 - 通过UUID查询
        engine_uuid = engine_info['uuid']
        self.assertIsNotNone(engine_uuid)
        self.assertGreater(len(engine_uuid), 0)

        # 验证数据库中的实际数据
        get_result = self.service.get(engine_id=engine_uuid)
        self.assertIsInstance(get_result, ServiceResult)
        self.assertTrue(get_result.is_success())
        self.assertEqual(len(get_result.data), 1)
        created_engine = get_result.data[0]
        self.assertEqual(created_engine.name, engine_name)
        self.assertEqual(created_engine.is_live, False)

        # 存储引擎UUID用于tearDown清理
        self.test_engines.append(engine_uuid)

    def test_create_engine_empty_name(self):
        """
        测试空引擎名的处理 - 使用真实数据库操作

        评审问题：
        - 原测试使用Mock，只验证接口调用
        - 修改为使用真实数据库操作，验证实际的参数验证逻辑

        评审改进建议：
        - 返回格式不一致：使用了result.is_success()而不是result.is_success()
        - 缺少ServiceResult.error和ServiceResult.message的区分验证
        - 建议增加对边界情况的测试：None值、特殊字符、超长名称等
        """
        result = self.service.add(name="", is_live=False)

        # 验证返回结果 - 应该失败
        self.assertIsInstance(result, ServiceResult)
        self.assertFalse(result.is_success())
        self.assertIsNotNone(result.error)
        self.assertTrue(len(result.error) > 0)  # 验证有错误信息
        self.assertIn("空", result.error.lower())  # 验证错误信息提到空参数

    def test_create_engine_name_already_exists(self):
        """
        测试引擎名已存在的处理 - 使用真实数据库操作

        评审问题：
        - 原测试使用Mock，无法验证真实的重复名称检查逻辑
        - 修改为使用真实数据库操作，先创建引擎，再尝试创建同名引擎
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        engine_name = f"duplicate_engine_{timestamp}"

        # 先创建一个引擎
        result1 = self.service.add(
            name=engine_name,
            is_live=False,
            description="First engine for duplicate test"
        )

        self.assertTrue(result1.is_success(), f"First engine creation failed: {result1.error}")
        self.test_engines.append(result1.data['engine_info']['uuid'])

        # 尝试创建同名的第二个引擎
        result2 = self.service.add(
            name=engine_name,
            is_live=False,
            description="Second engine for duplicate test"
        )

        # 验证第二个引擎创建应该失败
        self.assertFalse(result2.is_success())
        self.assertIsNotNone(result2.error)
        self.assertTrue(len(result2.error) > 0)  # 验证有错误信息

    def test_create_engine_long_name_truncation(self):
        """
        测试超长引擎名的截断处理 - 使用真实数据库操作

        评审问题：
        - 原测试使用Mock，无法验证真实的截断逻辑
        - 修改为使用真实数据库操作，测试实际的名称截断功能
        """
        long_name = "a" * 60  # 超过50字符限制
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        engine_name = f"long_name_test_{timestamp}_{long_name}"

        # 执行创建引擎操作
        result = self.service.add(name=engine_name, is_live=False, description="Long name test engine")

        # 验证操作结果
        self.assertIsInstance(result, ServiceResult)
        self.assertTrue(result.is_success(), f"Long name engine creation failed: {result.error}")
        self.assertTrue(len(result.warnings) > 0, "Should have truncation warning")
        self.assertIn("长", result.warnings[0].lower())  # 验证警告提到长名称

        # 验证名称被截断
        engine_info = result.data['engine_info']
        self.assertLessEqual(len(engine_info['name']), 50, "Engine name should be truncated to 50 characters")

        # 验证引擎确实被创建
        self.assertIsNotNone(engine_info['uuid'])
        self.test_engines.append(engine_info['uuid'])

    def test_get_engines_cached(self):
        """
        测试获取引擎的缓存功能 - 使用真实数据库操作

        评审问题：
        - 原测试使用Mock，无法验证真实的缓存机制
        - 修改为使用真实数据库操作，验证实际的数据获取功能

        评审改进建议：
        - 缺少真正的缓存验证：只是验证了数据获取，没有验证缓存机制
        - 建议增加缓存性能测试：比较首次查询和重复查询的响应时间
        - 建议验证缓存失效机制：更新数据后缓存是否正确失效
        - 建议测试缓存命中率和缓存键的生成逻辑
        - 建议增加并发访问缓存的测试场景
        """
        # 先创建一些测试引擎
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        engines_created = []

        for i in range(3):
            result = self.service.add(
                name=f"cache_test_engine_{i}_{timestamp}",
                is_live=False,
                description=f"Cache test engine {i}"
            )
            if result.is_success():
                engines_created.append(result.data['engine_info']['uuid'])

        try:
            # 测试获取所有引擎
            engines_result = self.service.get()
            self.assertTrue(engines_result.is_success())
            self.assertIsNotNone(engines_result.data)
            self.assertGreaterEqual(len(engines_result.data), len(engines_created))

            # 验证返回的引擎包含我们创建的引擎
            created_uuids = engines_created  # engines_created已经包含UUID字符串
            returned_uuids = [engine.uuid for engine in engines_result.data]
            for uuid in created_uuids:
                self.assertIn(uuid, returned_uuids)

        finally:
            # 清理测试数据
            for engine_uuid in engines_created:
                try:
                    self.service.delete(engine_uuid)
                except Exception as e:
                    print(f"Warning: Failed to cleanup cache test engine {engine_uuid}: {e}")

    def test_create_live_engine(self):
        """
        测试创建实盘引擎 - 使用真实数据库操作

        评审问题：
        - 原测试使用Mock验证实盘引擎创建，不够真实
        - 修改为使用真实数据库操作，验证实际的实盘引擎创建
        """
        engine_name = f"live_engine_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # 调用创建实盘引擎API - 使用真实数据库操作
        result = self.service.add(name=engine_name, is_live=True)

        # 验证返回结果
        self.assertTrue(result.is_success(), f"创建实盘引擎失败: {result.message}")

        # 检查返回数据结构
        self.assertIsInstance(result.data, dict)
        self.assertIn("engine_info", result.data)
        engine_info = result.data["engine_info"]
        self.assertIsInstance(engine_info, dict)
        engine_uuid = engine_info["uuid"]
        self.test_engines.append(engine_uuid)

        self.assertTrue(engine_info["is_live"])

        # 验证实际数据库中的数据
        engines_result = self.service.get()
        self.assertTrue(engines_result.is_success())

        # 在ModelList中查找创建的引擎
        created_engine = None
        for engine in engines_result.data:
            if engine.uuid == engine_uuid:
                created_engine = engine
                break
        self.assertIsNotNone(created_engine, "应该找到创建的引擎")
        self.assertEqual(created_engine.name, engine_name)
        self.assertTrue(created_engine.is_live)

    def test_update_engine_success(self):
        """
        测试成功更新引擎 - 使用真实数据库操作

        评审问题：
        - 原测试使用Mock验证引擎更新，不够真实
        - 修改为使用真实数据库操作，验证实际的引擎更新功能

        评审改进建议：
        - 缺少部分更新测试：只测试了全字段更新，没有测试单字段更新
        - 建议增加更新时间戳验证：验证updated_at字段是否正确更新
        - 建议测试无效状态枚举值的处理
        - 建议测试无效日期格式的处理（如果有日期字段）
        """
        # 先创建一个引擎用于更新
        create_result = self.service.add(
            name=f"update_test_engine_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            is_live=False,
            description="Original description"
        )

        self.assertTrue(create_result.is_success(), f"创建测试引擎失败: {create_result.message}")
        engine_uuid = create_result.data["engine_info"]["uuid"]
        self.test_engines.append(engine_uuid)

        # 更新引擎
        result = self.service.update(
            engine_id=engine_uuid,
            name="updated_engine_name",
            is_live=True,
            description="Updated description"
        )

        # 验证更新结果
        self.assertTrue(result.is_success(), f"更新引擎失败: {result.message}")

        # 验证实际数据库中的更新
        engines_result = self.service.get()
        self.assertTrue(engines_result.is_success())

        # 在ModelList中查找更新的引擎
        updated_engine = None
        for engine in engines_result.data:
            if engine.uuid == engine_uuid:
                updated_engine = engine
                break
        self.assertIsNotNone(updated_engine, "应该找到更新的引擎")
        self.assertEqual(updated_engine.name, "updated_engine_name")
        self.assertTrue(updated_engine.is_live)
        self.assertEqual(updated_engine.desc, "Updated description")

    def test_update_engine_empty_engine_id(self):
        """
        测试空引擎ID的处理 - 使用真实数据库操作

        评审问题：
        - 原测试使用Mock验证空ID处理，不够真实
        - 修改为使用真实数据库操作，验证实际的参数验证逻辑
        """
        result = self.service.update("", name="new_name")

        self.assertFalse(result.is_success(), "空引擎ID应该返回失败")
        self.assertIn("不能为空", result.error)

    def test_update_engine_empty_name(self):
        """
        测试空名称的更新处理 - 使用真实数据库操作

        评审问题：
        - 原测试使用Mock验证空名称处理，不够真实
        - 修改为使用真实数据库操作，验证实际的参数验证逻辑
        """
        result = self.service.update(
            engine_id="test-uuid-123",
            name=""  # 空名称
        )

        self.assertFalse(result.is_success(), "空名称应该返回失败")
        self.assertIn("不能为空", result.error)

    def test_update_engine_no_updates(self):
        """
        测试无更新内容的处理 - 使用真实数据库操作

        评审问题：
        - 原测试使用Mock验证无更新处理，不够真实
        - 修改为使用真实数据库操作，验证实际的无更新逻辑
        - 评审改进建议：错误消息验证需要根据实际实现调整，"未提供任何更新参数"可能需要改为实际返回的消息
        """
        result = self.service.update("test-uuid-123")

        self.assertTrue(result.is_success(), "无更新应该成功，但给出警告")
        self.assertIn("未提供任何更新参数", result.message)

    def test_update_engine_name_conflict(self):
        """
        测试更新时名称冲突的处理 - 使用真实数据库操作

        评审问题：
        - 原测试使用Mock验证名称冲突，不够真实
        - 修改为使用真实数据库操作，验证实际的名称冲突检测
        """
        # 先创建两个引擎
        engine1_result = self.service.add(
            name=f"conflict_engine_1_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            is_live=False
        )
        self.assertTrue(engine1_result.is_success())
        engine1_uuid = engine1_result.data["engine_info"]["uuid"]
        self.test_engines.append(engine1_uuid)

        engine2_result = self.service.add(
            name=f"conflict_engine_2_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            is_live=False
        )
        self.assertTrue(engine2_result.is_success())
        engine2_uuid = engine2_result.data["engine_info"]["uuid"]
        self.test_engines.append(engine2_uuid)

        # 尝试将engine2的名称更新为engine1的名称（应该失败）
        result = self.service.update(
            engine_id=engine2_uuid,
            name=engine1_result.data["engine_info"]["name"]
        )

        self.assertFalse(result.is_success(), "名称冲突应该返回失败")
        self.assertIn("已存在", result.error)

    def test_set_status_success(self):
        """
        测试成功更新引擎状态 - 使用真实数据库操作

        评审问题：
        - 原测试使用Mock验证状态更新，不够真实
        - 修改为使用真实数据库操作，验证实际的状态更新功能

        评审改进建议：
        - 关键缺失：没有验证数据库中的实际状态变化！
        - 需要增加更新前后的数据库记录对比验证
        - 建议验证状态枚举值的正确性和一致性
        - 建议测试状态转换的业务逻辑（如：IDLE→RUNNING是否合法）
        - 建议测试无效状态枚举值的处理
        """
        # 先创建一个引擎
        create_result = self.service.add(
            name=f"status_test_engine_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            is_live=False
        )

        self.assertTrue(create_result.is_success(), f"创建测试引擎失败: {create_result.message}")
        engine_uuid = create_result.data["engine_info"]["uuid"]
        self.test_engines.append(engine_uuid)

        # 更新引擎状态
        result = self.service.set_status(engine_uuid, ENGINESTATUS_TYPES.RUNNING)

        # 验证状态更新结果
        self.assertTrue(result.is_success(), f"更新引擎状态失败: {result.message}")

    def test_set_status_empty_id(self):
        """
        测试空引擎ID的状态更新处理 - 使用真实数据库操作

        评审问题：
        - 原测试使用Mock验证空ID处理，不够真实
        - 修改为使用真实数据库操作，验证实际的参数验证逻辑
        """
        result = self.service.set_status("", ENGINESTATUS_TYPES.RUNNING)

        self.assertFalse(result.is_success(), "空引擎ID应该返回失败")
        self.assertIn("不能为空", result.error)

    def test_delete_engine_success(self):
        """
        测试成功删除引擎 - 使用真实数据库操作

        评审问题：
        - 原测试使用Mock验证引擎删除，不够真实
        - 修改为使用真实数据库操作，验证实际的引擎删除功能
        """
        # 先创建一个引擎用于删除
        create_result = self.service.add(
            name=f"delete_test_engine_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            is_live=False,
            description="Engine for delete testing"
        )

        self.assertTrue(create_result.is_success(), f"创建测试引擎失败: {create_result.message}")
        engine_uuid = create_result.data["engine_info"]["uuid"]
        # 不添加到self.test_engines，因为我们要测试删除

        # 删除引擎
        result = self.service.delete(engine_uuid)

        # 验证删除结果
        self.assertTrue(result.is_success(), f"删除引擎失败: {result.message}")

        # 验证引擎已被删除
        engines_result = self.service.get()
        self.assertTrue(engines_result.is_success())

        # 在ModelList中查找已删除的引擎
        deleted_engine = [engine for engine in engines_result.data if engine.uuid == engine_uuid]
        self.assertEqual(len(deleted_engine), 0, "引擎应该已被删除")

    def test_delete_engine_empty_id(self):
        """
        测试空引擎ID的删除处理 - 使用真实数据库操作

        评审问题：
        - 原测试使用Mock验证空ID处理，不够真实
        - 修改为使用真实数据库操作，验证实际的参数验证逻辑
        """
        result = self.service.delete("")

        self.assertFalse(result.is_success(), "空引擎ID应该返回失败")
        self.assertIn("不能为空", result.error)
    def test_get_engine_by_uuid_success(self):
        """
        测试通过UUID获取引擎 - 使用真实数据库操作

        评审问题：
        - 原测试使用Mock验证引擎获取，不够真实
        - 修改为使用真实数据库操作，验证实际的引擎查询功能
        """
        # 先创建一个引擎用于查询
        create_result = self.service.add(
            name=f"get_test_engine_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            is_live=False,
            description="Engine for get testing"
        )

        self.assertTrue(create_result.is_success(), f"创建测试引擎失败: {create_result.message}")
        engine_uuid = create_result.data["engine_info"]["uuid"]
        self.test_engines.append(engine_uuid)

        # 获取引擎
        result = self.service.get(engine_uuid)

        # 验证获取结果
        self.assertTrue(result.is_success(), f"获取引擎失败: {result.message}")
        self.assertIsNotNone(result.data, "返回数据不应为空")
        self.assertIsInstance(result.data, list)
        self.assertGreater(len(result.data), 0)
        found_engine = None
        for engine in result.data:
            if engine.uuid == engine_uuid:
                found_engine = engine
                break
        self.assertIsNotNone(found_engine, "应该找到创建的引擎")
        self.assertEqual(found_engine.uuid, engine_uuid)

    def test_get_engine_by_uuid_not_found(self):
        """
        测试获取不存在的引擎UUID - 使用真实数据库操作

        评审问题：
        - 原测试使用Mock验证不存在的引擎，不够真实
        - 修改为使用真实数据库操作，验证实际的查询逻辑

        评审改进建议：
        - 建议增加更多边界情况测试：无效UUID格式、None值、空字符串等
        - 建议测试已删除引擎的查询（软删除后的查询行为）
        """

        result = self.service.get("nonexistent-engine-uuid-12345")

        self.assertTrue(result.is_success(), "获取不存在的引擎应该返回成功")
        self.assertEqual(len(result.data), 0, "不存在的引擎应该返回空列表")

    # 评审发现缺失的重要测试用例建议：

    def test_engine_portfolio_mapping_operations(self):
        """
        评审建议新增：测试引擎-投资组合映射操作

        评审问题：
        - 当前测试完全缺少引擎与投资组合映射关系的测试
        - 这是EngineService的核心功能之一，需要完整覆盖

        建议测试内容：
        - 添加投资组合到引擎：add_portfolio_to_engine()
        - 移除投资组合：remove_portfolio_from_engine()
        - 获取映射关系：get_engine_portfolio_mappings()
        - 映射关系的冲突检测和验证
        - 映射数据的级联删除处理
        """
        # TODO: 实现完整的映射关系测试
        pass

    def test_engine_status_workflow(self):
        """
        评审建议新增：测试引擎状态工作流

        评审问题：
        - 当前只测试了单一状态更新，缺少状态转换工作流测试
        - 引擎状态有其业务逻辑，需要验证完整的生命周期

        建议测试内容：
        - IDLE → RUNNING 状态转换
        - RUNNING → STOPPED 状态转换
        - STOPPED → IDLE 状态转换
        - 无效状态转换的处理
        - 状态转换时的业务逻辑验证
        """
        # TODO: 实现状态工作流测试
        pass

    def test_engine_concurrent_operations(self):
        """
        评审建议新增：测试并发操作场景

        评审问题：
        - 当前测试都是单线程操作，缺少并发安全性测试
        - 引擎服务可能面临并发访问场景

        建议测试内容：
        - 并发创建同名引擎的处理
        - 并发更新同一引擎的数据一致性
        - 并发删除操作的幂等性
        - 缓存在并发环境下的表现
        """
        # TODO: 实现并发操作测试
        pass

    def test_engine_error_handling_and_recovery(self):
        """
        评审建议新增：测试错误处理和恢复机制

        评审问题：
        - 当前测试主要关注正常流程，错误处理覆盖不足
        - 需要验证各种异常情况下的行为

        建议测试内容：
        - 数据库连接中断时的处理
        - 事务回滚机制的验证
        - 部分失败时的数据一致性
        - 错误恢复后的状态验证
        """
        # TODO: 实现错误处理和恢复测试
        pass


if __name__ == '__main__':
    unittest.main()
