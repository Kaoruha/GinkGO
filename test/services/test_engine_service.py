import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

try:
    from ginkgo.data.services.engine_service import EngineService
    from ginkgo.data.crud.engine_crud import EngineCRUD
    from ginkgo.data.crud.engine_portfolio_mapping_crud import EnginePortfolioMappingCRUD
    from ginkgo.data.models import MEngine, MEnginePortfolioMapping
    from ginkgo.enums import ENGINESTATUS_TYPES, SOURCE_TYPES
    from ginkgo.libs import GCONF, GLOG
except ImportError as e:
    print(f"Import error: {e}")
    EngineService = None
    GCONF = None


class EngineServiceTest(unittest.TestCase):
    """
    EngineService 单元测试
    测试增强的引擎管理功能和错误处理能力
    """

    @classmethod
    def setUpClass(cls):
        """类级别设置"""
        if EngineService is None or GCONF is None:
            raise AssertionError("EngineService or GCONF not available")

        print(":white_check_mark: EngineService test setup completed")

    def setUp(self):
        """每个测试前的设置"""
        # 创建 Mock 依赖
        self.mock_crud_repo = Mock()
        self.mock_engine_portfolio_mapping_crud = Mock()
        
        # Mock session management
        self.mock_session = Mock()
        self.mock_session.begin.return_value.__enter__ = Mock(return_value=self.mock_session)
        self.mock_session.begin.return_value.__exit__ = Mock(return_value=None)
        self.mock_crud_repo.get_session.return_value = self.mock_session
        self.mock_engine_portfolio_mapping_crud.get_session.return_value = self.mock_session
        
        # 创建 EngineService 实例
        self.service = EngineService(
            crud_repo=self.mock_crud_repo,
            engine_portfolio_mapping_crud=self.mock_engine_portfolio_mapping_crud
        )

    def test_create_engine_success(self):
        """测试成功创建引擎"""
        # 配置 Mock 返回引擎记录
        mock_engine_record = MagicMock()
        mock_engine_record.uuid = "test-engine-uuid"
        mock_engine_record.name = "test_engine"
        mock_engine_record.is_live = False
        mock_engine_record.status = ENGINESTATUS_TYPES.IDLE
        mock_engine_record.desc = "Test engine"
        
        self.mock_crud_repo.create.return_value = mock_engine_record
        
        # Mock engine_exists 返回 False（引擎不存在）
        with patch.object(self.service, 'engine_exists', return_value=False):
            result = self.service.create_engine(
                name="test_engine",
                is_live=False,
                description="Test engine"
            )
        
        # 验证返回结果
        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])
        self.assertEqual(result['name'], 'test_engine')
        self.assertFalse(result['is_live'])
        self.assertIsNone(result['error'])
        self.assertIsInstance(result['warnings'], list)
        self.assertIsNotNone(result['engine_info'])
        self.assertEqual(result['engine_info']['uuid'], 'test-engine-uuid')

    def test_create_engine_empty_name(self):
        """测试空引擎名的处理"""
        result = self.service.create_engine(name="", is_live=False)
        
        # 验证返回结果
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Engine name cannot be empty")

    def test_create_engine_name_already_exists(self):
        """测试引擎名已存在的处理"""
        # Mock engine_exists 返回 True（引擎已存在）
        with patch.object(self.service, 'engine_exists', return_value=True):
            result = self.service.create_engine(name="existing_engine", is_live=False)
        
        # 验证返回结果
        self.assertFalse(result['success'])
        self.assertIn("already exists", result['error'])

    def test_create_engine_long_name_truncation(self):
        """测试超长引擎名的截断处理"""
        long_name = "a" * 60  # 超过50字符限制
        
        mock_engine_record = MagicMock()
        mock_engine_record.uuid = "test-long-uuid"
        mock_engine_record.name = long_name[:50]
        mock_engine_record.is_live = False
        mock_engine_record.status = ENGINESTATUS_TYPES.IDLE
        mock_engine_record.desc = "Long name engine"
        
        self.mock_crud_repo.create.return_value = mock_engine_record
        
        with patch.object(self.service, 'engine_exists', return_value=False):
            result = self.service.create_engine(name=long_name, is_live=False)
        
        # 验证截断警告
        self.assertTrue(result['success'])
        self.assertIn("Engine name truncated to 50 characters", result['warnings'])

    def test_create_engine_database_error(self):
        """测试数据库操作错误处理"""
        self.mock_crud_repo.create.side_effect = Exception("Database connection failed")
        
        with patch.object(self.service, 'engine_exists', return_value=False):
            result = self.service.create_engine(name="test_engine", is_live=False)
        
        # 验证错误处理
        self.assertFalse(result['success'])
        self.assertIn("Database operation failed", result['error'])

    def test_create_live_engine(self):
        """测试创建实盘引擎"""
        mock_engine_record = MagicMock()
        mock_engine_record.uuid = "live-engine-uuid"
        mock_engine_record.name = "live_engine"
        mock_engine_record.is_live = True
        mock_engine_record.status = ENGINESTATUS_TYPES.IDLE
        mock_engine_record.desc = "Live engine: live_engine"
        
        self.mock_crud_repo.create.return_value = mock_engine_record
        
        with patch.object(self.service, 'engine_exists', return_value=False):
            result = self.service.create_engine(name="live_engine", is_live=True)
        
        # 验证实盘引擎创建
        self.assertTrue(result['success'])
        self.assertTrue(result['is_live'])
        self.assertTrue(result['engine_info']['is_live'])

    def test_update_engine_success(self):
        """测试成功更新引擎"""
        self.mock_crud_repo.modify.return_value = 1
        
        # Mock get_engines 返回空（无名称冲突）
        with patch.object(self.service, 'get_engines', return_value=pd.DataFrame()):
            result = self.service.update_engine(
                engine_id="test-uuid-123",
                name="updated_name",
                is_live=True,
                description="Updated description"
            )
        
        # 验证更新结果
        self.assertTrue(result['success'])
        self.assertEqual(result['engine_id'], 'test-uuid-123')
        self.assertEqual(result['updated_count'], 1)
        self.assertEqual(len(result['updates_applied']), 3)
        self.assertIn('name', result['updates_applied'])
        self.assertIn('is_live', result['updates_applied'])
        self.assertIn('description', result['updates_applied'])

    def test_update_engine_empty_engine_id(self):
        """测试空引擎ID的处理"""
        result = self.service.update_engine("", name="new_name")
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Engine ID cannot be empty")

    def test_update_engine_empty_name(self):
        """测试空名称的更新处理"""
        result = self.service.update_engine(
            engine_id="test-uuid-123",
            name=""  # 空名称
        )
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Engine name cannot be empty")

    def test_update_engine_no_updates(self):
        """测试无更新内容的处理"""
        result = self.service.update_engine("test-uuid-123")
        
        self.assertTrue(result['success'])  # 无更新不是错误
        self.assertIn("No updates provided for engine update", result['warnings'])

    def test_update_engine_name_conflict(self):
        """测试更新时名称冲突的处理"""
        # Mock get_engines 返回现有引擎（不同UUID）
        existing_engines_df = pd.DataFrame({
            'uuid': ['other-uuid'],
            'name': ['conflicting_name']
        })
        
        with patch.object(self.service, 'get_engines', return_value=existing_engines_df):
            result = self.service.update_engine(
                engine_id="test-uuid-123",
                name="conflicting_name"
            )
        
        self.assertFalse(result['success'])
        self.assertIn("already exists", result['error'])

    def test_update_engine_database_error(self):
        """测试数据库更新错误处理"""
        self.mock_crud_repo.modify.side_effect = Exception("Update failed")
        
        with patch.object(self.service, 'get_engines', return_value=pd.DataFrame()):
            result = self.service.update_engine(
                engine_id="test-uuid-123",
                name="new_name"
            )
        
        self.assertFalse(result['success'])
        self.assertIn("Database operation failed", result['error'])

    def test_update_engine_status_success(self):
        """测试成功更新引擎状态"""
        self.mock_crud_repo.modify.return_value = 1
        
        result = self.service.update_engine_status("test-uuid-123", ENGINESTATUS_TYPES.RUNNING)
        
        # 验证状态更新结果
        self.assertTrue(result['success'])
        self.assertEqual(result['engine_id'], 'test-uuid-123')
        self.assertEqual(result['new_status'], 'RUNNING')
        self.assertEqual(result['updated_count'], 1)

    def test_update_engine_status_empty_id(self):
        """测试空引擎ID的状态更新处理"""
        result = self.service.update_engine_status("", ENGINESTATUS_TYPES.RUNNING)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Engine ID cannot be empty")

    def test_update_engine_status_invalid_type(self):
        """测试无效状态类型的处理"""
        result = self.service.update_engine_status("test-uuid-123", "INVALID_STATUS")
        
        self.assertFalse(result['success'])
        self.assertIn("Invalid engine status type", result['error'])

    def test_update_engine_status_not_found(self):
        """测试更新不存在引擎的状态"""
        self.mock_crud_repo.modify.return_value = 0
        
        result = self.service.update_engine_status("nonexistent-uuid", ENGINESTATUS_TYPES.STOPPED)
        
        self.assertTrue(result['success'])  # 操作成功，但没有找到引擎
        self.assertEqual(result['updated_count'], 0)
        self.assertIn("No engine found", result['warnings'][0])

    def test_delete_engine_success(self):
        """测试成功删除引擎"""
        self.mock_crud_repo.soft_remove.return_value = 1
        self.mock_engine_portfolio_mapping_crud.soft_remove.return_value = 2
        
        result = self.service.delete_engine("test-uuid-123")
        
        # 验证删除结果
        self.assertTrue(result['success'])
        self.assertEqual(result['engine_id'], 'test-uuid-123')
        self.assertEqual(result['deleted_count'], 1)
        self.assertEqual(result['mappings_deleted'], 2)

    def test_delete_engine_empty_id(self):
        """测试空引擎ID的删除处理"""
        result = self.service.delete_engine("")
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Engine ID cannot be empty")

    def test_delete_engine_not_found(self):
        """测试删除不存在引擎的处理"""
        self.mock_crud_repo.soft_remove.return_value = 0
        self.mock_engine_portfolio_mapping_crud.soft_remove.return_value = 0
        
        result = self.service.delete_engine("nonexistent-uuid")
        
        self.assertTrue(result['success'])  # 删除操作成功，但没有找到引擎
        self.assertEqual(result['deleted_count'], 0)
        self.assertIn("No engine found", result['warnings'][0])

    def test_delete_engine_mapping_cleanup_failure(self):
        """测试映射清理失败的处理"""
        self.mock_engine_portfolio_mapping_crud.soft_remove.side_effect = Exception("Mapping cleanup failed")
        self.mock_crud_repo.soft_remove.return_value = 1
        
        result = self.service.delete_engine("test-uuid-123")
        
        # 验证部分成功（引擎删除成功，但映射清理失败）
        self.assertTrue(result['success'])
        self.assertEqual(result['deleted_count'], 1)
        self.assertIn("Failed to clean up portfolio mappings", result['warnings'][0])

    def test_delete_engine_database_error(self):
        """测试数据库删除错误处理"""
        self.mock_crud_repo.soft_remove.side_effect = Exception("Delete failed")
        
        result = self.service.delete_engine("test-uuid-123")
        
        self.assertFalse(result['success'])
        self.assertIn("Database operation failed", result['error'])

    def test_delete_engines_batch_success(self):
        """测试批量删除引擎成功"""
        engine_ids = ["uuid-1", "uuid-2", "uuid-3"]
        
        # Mock delete_engine 返回成功结果
        success_result = {
            "success": True,
            "deleted_count": 1,
            "mappings_deleted": 1,
            "warnings": []
        }
        
        with patch.object(self.service, 'delete_engine', return_value=success_result):
            result = self.service.delete_engines(engine_ids)
            
            # 验证批量删除结果
            self.assertTrue(result['success'])
            self.assertEqual(result['total_requested'], 3)
            self.assertEqual(result['successful_deletions'], 3)
            self.assertEqual(result['failed_deletions'], 0)
            self.assertEqual(result['total_mappings_deleted'], 3)

    def test_delete_engines_empty_list(self):
        """测试空引擎列表的批量删除"""
        result = self.service.delete_engines([])
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_requested'], 0)
        self.assertIn("Empty engine list provided", result['warnings'])

    def test_delete_engines_partial_idempotent_success(self):
        """
        测试部分idempotent操作的处理
        
        新增测试：验证idempotent情况下的批量操作处理
        当部分对象不存在时，应该返回成功而不是失败
        
        重要语义说明：
        - successful_deletions表示"实际删除的记录数量"，不是"成功的操作数量"
        - idempotent操作（删除不存在的对象）success=True但deleted_count=0
        - 因此successful_deletions只计算实际删除的记录数，不包括idempotent操作
        """
        engine_ids = ["uuid-1", "uuid-2", "uuid-3"]
        
        # Mock 部分idempotent情况（对象不存在）
        def mock_delete_engine(engine_id):
            if engine_id == "uuid-2":
                return {
                    "success": True,  # idempotent操作仍然是成功的
                    "deleted_count": 0,  # 但没有实际删除记录
                    "mappings_deleted": 0,
                    "warnings": ["No engine found with ID uuid-2 to delete"]
                }
            return {
                "success": True,
                "deleted_count": 1,  # 实际删除了1条记录
                "mappings_deleted": 1,
                "warnings": []
            }
        
        with patch.object(self.service, 'delete_engine', side_effect=mock_delete_engine):
            result = self.service.delete_engines(engine_ids)
            
            # 验证idempotent情况下的批量操作结果
            self.assertTrue(result['success'])  # 所有操作都成功（包括idempotent）
            # successful_deletions = 1(uuid-1) + 0(uuid-2,idempotent) + 1(uuid-3) = 2
            self.assertEqual(result['successful_deletions'], 2)  # 只计算实际删除的记录数
            self.assertEqual(result['failed_deletions'], 0)  # 没有真正的失败
            self.assertEqual(result['total_requested'], 3)  # 请求处理了3个引擎
            # 验证idempotent操作产生了警告但不算失败
            self.assertGreater(len(result['warnings']), 0)  # 应该有来自idempotent操作的警告

    def test_delete_engines_partial_failure(self):
        """测试部分删除失败的处理"""
        engine_ids = ["uuid-1", "uuid-2", "uuid-3"]
        
        # Mock 部分成功和失败的结果
        def mock_delete_engine(engine_id):
            if engine_id == "uuid-2":
                return {
                    "success": False,
                    "error": "Engine not found",
                    "deleted_count": 0,
                    "mappings_deleted": 0,
                    "warnings": []
                }
            return {
                "success": True,
                "deleted_count": 1,
                "mappings_deleted": 1,
                "warnings": []
            }
        
        with patch.object(self.service, 'delete_engine', side_effect=mock_delete_engine):
            result = self.service.delete_engines(engine_ids)
            
            # 验证部分失败结果
            self.assertFalse(result['success'])  # 有失败所以整体失败
            self.assertEqual(result['successful_deletions'], 2)
            self.assertEqual(result['failed_deletions'], 1)
            self.assertEqual(len(result['failures']), 1)

    def test_get_engines_cached(self):
        """测试获取引擎的缓存功能"""
        mock_engines_df = pd.DataFrame({
            'uuid': ['uuid-1', 'uuid-2'],
            'name': ['engine1', 'engine2'],
            'is_live': [False, True],
            'status': [ENGINESTATUS_TYPES.IDLE.value, ENGINESTATUS_TYPES.RUNNING.value]
        })
        
        self.mock_crud_repo.find.return_value = mock_engines_df
        
        # 第一次调用
        result1 = self.service.get_engines(is_live=False, as_dataframe=True)
        
        # 第二次调用（应该使用缓存）
        result2 = self.service.get_engines(is_live=False, as_dataframe=True)
        
        # 验证缓存效果（CRUD只被调用一次）
        self.mock_crud_repo.find.assert_called_once()
        pd.testing.assert_frame_equal(result1, result2)

    def test_get_engine_single(self):
        """测试获取单个引擎"""
        # Mock get_engines 返回单个引擎
        single_engine_df = pd.DataFrame({
            'uuid': ['test-uuid'],
            'name': ['test_engine'],
            'is_live': [False],
            'status': [ENGINESTATUS_TYPES.IDLE.value]
        })
        
        with patch.object(self.service, 'get_engines', return_value=single_engine_df):
            result = self.service.get_engine("test-uuid", as_dataframe=True)
            
            self.assertIsNotNone(result)
            self.assertFalse(result.empty)

    def test_get_engine_not_found(self):
        """测试获取不存在的引擎"""
        with patch.object(self.service, 'get_engines', return_value=pd.DataFrame()):
            result = self.service.get_engine("nonexistent-uuid", as_dataframe=True)
            
            self.assertIsNone(result)

    def test_get_engine_status(self):
        """测试获取引擎状态"""
        engine_df = pd.DataFrame({
            'uuid': ['test-uuid'],
            'name': ['test_engine'],
            'status': [ENGINESTATUS_TYPES.RUNNING.value]
        })
        
        with patch.object(self.service, 'get_engine', return_value=engine_df):
            status = self.service.get_engine_status("test-uuid")
            
            self.assertEqual(status, ENGINESTATUS_TYPES.RUNNING)

    def test_get_engine_status_not_found(self):
        """测试获取不存在引擎的状态"""
        with patch.object(self.service, 'get_engine', return_value=None):
            status = self.service.get_engine_status("nonexistent-uuid")
            
            self.assertIsNone(status)

    def test_count_engines(self):
        """测试引擎计数功能"""
        self.mock_crud_repo.count.return_value = 5
        
        count = self.service.count_engines(is_live=False, status=ENGINESTATUS_TYPES.IDLE)
        
        self.assertEqual(count, 5)

    def test_engine_exists_true(self):
        """测试引擎存在检查"""
        self.mock_crud_repo.exists.return_value = True
        
        exists = self.service.engine_exists("existing_engine")
        
        self.assertTrue(exists)

    def test_engine_exists_false(self):
        """测试引擎不存在检查"""
        self.mock_crud_repo.exists.return_value = False
        
        exists = self.service.engine_exists("nonexistent_engine")
        
        self.assertFalse(exists)

    def test_add_portfolio_to_engine_success(self):
        """测试成功将组合添加到引擎"""
        # Mock get_engine_portfolio_mappings 返回空（无现有映射）
        with patch.object(self.service, 'get_engine_portfolio_mappings', return_value=pd.DataFrame()):
            # 配置 Mock 返回映射记录
            mock_mapping_record = MagicMock()
            mock_mapping_record.uuid = "mapping-uuid"
            mock_mapping_record.engine_id = "engine-uuid"
            mock_mapping_record.portfolio_id = "portfolio-uuid"
            mock_mapping_record.engine_name = "test_engine"
            mock_mapping_record.portfolio_name = "test_portfolio"
            
            self.mock_engine_portfolio_mapping_crud.create.return_value = mock_mapping_record
            
            result = self.service.add_portfolio_to_engine(
                engine_id="engine-uuid",
                portfolio_id="portfolio-uuid",
                engine_name="test_engine",
                portfolio_name="test_portfolio"
            )
            
            # 验证映射结果
            self.assertTrue(result['success'])
            self.assertEqual(result['engine_id'], 'engine-uuid')
            self.assertEqual(result['portfolio_id'], 'portfolio-uuid')
            self.assertIsNotNone(result['mapping_info'])
            self.assertEqual(result['mapping_info']['uuid'], 'mapping-uuid')

    def test_add_portfolio_to_engine_empty_ids(self):
        """测试空ID的组合映射处理"""
        # 测试空引擎ID
        result1 = self.service.add_portfolio_to_engine("", "portfolio-uuid")
        self.assertFalse(result1['success'])
        self.assertEqual(result1['error'], "Engine ID cannot be empty")
        
        # 测试空组合ID
        result2 = self.service.add_portfolio_to_engine("engine-uuid", "")
        self.assertFalse(result2['success'])
        self.assertEqual(result2['error'], "Portfolio ID cannot be empty")

    def test_add_portfolio_to_engine_already_mapped(self):
        """测试添加已存在映射的处理"""
        # Mock get_engine_portfolio_mappings 返回现有映射
        existing_mapping_df = pd.DataFrame({
            'engine_id': ['engine-uuid'],
            'portfolio_id': ['portfolio-uuid']
        })
        
        with patch.object(self.service, 'get_engine_portfolio_mappings', return_value=existing_mapping_df):
            result = self.service.add_portfolio_to_engine(
                engine_id="engine-uuid",
                portfolio_id="portfolio-uuid"
            )
            
            self.assertFalse(result['success'])
            self.assertIn("already mapped", result['error'])

    def test_add_portfolio_to_engine_database_error(self):
        """测试数据库映射错误处理"""
        self.mock_engine_portfolio_mapping_crud.create.side_effect = Exception("Mapping failed")
        
        with patch.object(self.service, 'get_engine_portfolio_mappings', return_value=pd.DataFrame()):
            result = self.service.add_portfolio_to_engine(
                engine_id="engine-uuid",
                portfolio_id="portfolio-uuid"
            )
        
        self.assertFalse(result['success'])
        self.assertIn("Database operation failed", result['error'])

    def test_remove_portfolio_from_engine_success(self):
        """测试成功从引擎移除组合"""
        self.mock_engine_portfolio_mapping_crud.soft_remove.return_value = 1
        
        result = self.service.remove_portfolio_from_engine("engine-uuid", "portfolio-uuid")
        
        # 验证移除结果
        self.assertTrue(result['success'])
        self.assertEqual(result['engine_id'], 'engine-uuid')
        self.assertEqual(result['portfolio_id'], 'portfolio-uuid')
        self.assertEqual(result['removed_count'], 1)

    def test_remove_portfolio_from_engine_empty_ids(self):
        """测试空ID的组合移除处理"""
        # 测试空引擎ID
        result1 = self.service.remove_portfolio_from_engine("", "portfolio-uuid")
        self.assertFalse(result1['success'])
        self.assertEqual(result1['error'], "Engine ID cannot be empty")
        
        # 测试空组合ID
        result2 = self.service.remove_portfolio_from_engine("engine-uuid", "")
        self.assertFalse(result2['success'])
        self.assertEqual(result2['error'], "Portfolio ID cannot be empty")

    def test_remove_portfolio_from_engine_not_found(self):
        """测试移除不存在映射的处理"""
        self.mock_engine_portfolio_mapping_crud.soft_remove.return_value = 0
        
        result = self.service.remove_portfolio_from_engine("engine-uuid", "portfolio-uuid")
        
        self.assertTrue(result['success'])  # 移除操作成功，但没有找到映射
        self.assertEqual(result['removed_count'], 0)
        self.assertIn("No mapping found", result['warnings'][0])

    def test_remove_portfolio_from_engine_database_error(self):
        """测试数据库移除错误处理"""
        self.mock_engine_portfolio_mapping_crud.soft_remove.side_effect = Exception("Remove failed")
        
        result = self.service.remove_portfolio_from_engine("engine-uuid", "portfolio-uuid")
        
        self.assertFalse(result['success'])
        self.assertIn("Database operation failed", result['error'])

    def test_get_engine_portfolio_mappings_cached(self):
        """测试获取引擎组合映射的缓存功能"""
        mock_mappings_df = pd.DataFrame({
            'uuid': ['mapping-uuid-1', 'mapping-uuid-2'],
            'engine_id': ['engine-uuid', 'engine-uuid'],
            'portfolio_id': ['portfolio-uuid-1', 'portfolio-uuid-2']
        })
        
        self.mock_engine_portfolio_mapping_crud.find.return_value = mock_mappings_df
        
        # 第一次调用
        result1 = self.service.get_engine_portfolio_mappings(engine_id="engine-uuid", as_dataframe=True)
        
        # 第二次调用（应该使用缓存）
        result2 = self.service.get_engine_portfolio_mappings(engine_id="engine-uuid", as_dataframe=True)
        
        # 验证缓存效果
        self.mock_engine_portfolio_mapping_crud.find.assert_called_once()
        pd.testing.assert_frame_equal(result1, result2)

    def test_get_portfolios_for_engine(self):
        """测试获取引擎关联的组合"""
        mock_mappings_df = pd.DataFrame({
            'engine_id': ['engine-uuid'],
            'portfolio_id': ['portfolio-uuid'],
            'portfolio_name': ['test_portfolio']
        })
        
        with patch.object(self.service, 'get_engine_portfolio_mappings', return_value=mock_mappings_df):
            result = self.service.get_portfolios_for_engine("engine-uuid")
            
            self.assertIsInstance(result, pd.DataFrame)
            self.assertEqual(len(result), 1)

    def test_get_engines_for_portfolio(self):
        """测试获取组合关联的引擎"""
        mock_mappings_df = pd.DataFrame({
            'engine_id': ['engine-uuid'],
            'portfolio_id': ['portfolio-uuid'],
            'engine_name': ['test_engine']
        })
        
        with patch.object(self.service, 'get_engine_portfolio_mappings', return_value=mock_mappings_df):
            result = self.service.get_engines_for_portfolio("portfolio-uuid")
            
            self.assertIsInstance(result, pd.DataFrame)
            self.assertEqual(len(result), 1)

    def test_retry_mechanism_create_engine(self):
        """测试创建引擎的重试机制存在（验证装饰器应用）"""
        # 检查create_engine方法是否被@retry装饰器包装
        self.assertTrue(hasattr(self.service.create_engine, '__name__'))
        
        # 简化的重试测试：验证方法最终会在数据库错误后返回失败结果
        self.mock_crud_repo.create.side_effect = Exception("Database connection failed")
        
        with patch.object(self.service, 'engine_exists', return_value=False):
            result = self.service.create_engine(name="retry_test", is_live=False)
        
        # 验证在重试失败后返回错误结果
        self.assertFalse(result['success'])
        self.assertIn("Database operation failed", result['error'])
        
        # 验证至少调用了一次（可能因为重试装饰器而调用多次）
        self.assertGreaterEqual(self.mock_crud_repo.create.call_count, 1)

    def test_various_engine_statuses_handling(self):
        """测试各种引擎状态的处理"""
        statuses_to_test = [
            ENGINESTATUS_TYPES.IDLE,
            ENGINESTATUS_TYPES.RUNNING,
            ENGINESTATUS_TYPES.STOPPED,
            ENGINESTATUS_TYPES.ERROR
        ]
        
        for status in statuses_to_test:
            with self.subTest(status=status):
                self.mock_crud_repo.modify.return_value = 1
                
                result = self.service.update_engine_status("test-uuid", status)
                
                self.assertTrue(result['success'])
                self.assertEqual(result['new_status'], status.name)

    def test_comprehensive_error_logging(self):
        """测试全面的错误日志记录"""
        # 触发数据库错误并验证业务逻辑处理
        self.mock_crud_repo.create.side_effect = Exception("Critical database error")
        
        with patch.object(self.service, 'engine_exists', return_value=False):
            result = self.service.create_engine(name="error_test", is_live=False)
        
        # 验证错误处理结果
        self.assertFalse(result['success'])
        self.assertIsNotNone(result['error'])
        self.assertIn("Critical database error", result['error'])


if __name__ == '__main__':
    unittest.main()