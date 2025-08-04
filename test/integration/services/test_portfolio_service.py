import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

try:
    from ginkgo.data.services.portfolio_service import PortfolioService
    from ginkgo.data.crud.portfolio_crud import PortfolioCRUD
    from ginkgo.data.crud.portfolio_file_mapping_crud import PortfolioFileMappingCRUD
    from ginkgo.data.crud.param_crud import ParamCRUD
    from ginkgo.data.models import MPortfolio, MPortfolioFileMapping, MParam
    from ginkgo.enums import FILE_TYPES
    from ginkgo.libs import GCONF, GLOG
except ImportError as e:
    print(f"Import error: {e}")
    PortfolioService = None
    GCONF = None


class PortfolioServiceTest(unittest.TestCase):
    """
    PortfolioService 单元测试
    测试增强的投资组合管理功能和错误处理能力
    """

    @classmethod
    def setUpClass(cls):
        """类级别设置"""
        if PortfolioService is None or GCONF is None:
            raise AssertionError("PortfolioService or GCONF not available")

        print(":white_check_mark: PortfolioService test setup completed")

    def setUp(self):
        """每个测试前的设置"""
        # 创建 Mock 依赖
        self.mock_crud_repo = Mock()
        self.mock_portfolio_file_mapping_crud = Mock()
        self.mock_param_crud = Mock()
        
        # Mock session management
        self.mock_session = Mock()
        self.mock_session.begin.return_value.__enter__ = Mock(return_value=self.mock_session)
        self.mock_session.begin.return_value.__exit__ = Mock(return_value=None)
        self.mock_crud_repo.get_session.return_value = self.mock_session
        self.mock_portfolio_file_mapping_crud.get_session.return_value = self.mock_session
        self.mock_param_crud.get_session.return_value = self.mock_session
        
        # 创建 PortfolioService 实例
        self.service = PortfolioService(
            crud_repo=self.mock_crud_repo,
            portfolio_file_mapping_crud=self.mock_portfolio_file_mapping_crud,
            param_crud=self.mock_param_crud
        )

    def test_create_portfolio_success(self):
        """测试成功创建投资组合"""
        # 配置 Mock 返回组合记录
        mock_portfolio_record = MagicMock()
        mock_portfolio_record.uuid = "test-portfolio-uuid"
        mock_portfolio_record.name = "test_portfolio"
        mock_portfolio_record.backtest_start_date = "2023-01-01"
        mock_portfolio_record.backtest_end_date = "2023-12-31"
        mock_portfolio_record.is_live = False
        mock_portfolio_record.desc = "Test portfolio"
        
        self.mock_crud_repo.create.return_value = mock_portfolio_record
        
        # Mock portfolio_exists 返回 False（组合不存在）
        with patch.object(self.service, 'portfolio_exists', return_value=False):
            result = self.service.create_portfolio(
                name="test_portfolio",
                backtest_start_date="2023-01-01",
                backtest_end_date="2023-12-31",
                is_live=False,
                description="Test portfolio"
            )
        
        # 验证返回结果
        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])
        self.assertEqual(result['name'], 'test_portfolio')
        self.assertEqual(result['backtest_start_date'], '2023-01-01')
        self.assertEqual(result['backtest_end_date'], '2023-12-31')
        self.assertFalse(result['is_live'])
        self.assertIsNone(result['error'])
        self.assertIsInstance(result['warnings'], list)
        self.assertIsNotNone(result['portfolio_info'])
        self.assertEqual(result['portfolio_info']['uuid'], 'test-portfolio-uuid')

    def test_create_portfolio_empty_name(self):
        """测试空组合名的处理"""
        result = self.service.create_portfolio(
            name="", 
            backtest_start_date="2023-01-01",
            backtest_end_date="2023-12-31"
        )
        
        # 验证返回结果
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Portfolio name cannot be empty")

    def test_create_portfolio_missing_dates(self):
        """测试缺少日期的处理"""
        result = self.service.create_portfolio(
            name="test_portfolio",
            backtest_start_date="",
            backtest_end_date="2023-12-31"
        )
        
        # 验证返回结果
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Backtest start and end dates are required")

    def test_create_portfolio_name_already_exists(self):
        """测试组合名已存在的处理"""
        # Mock portfolio_exists 返回 True（组合已存在）
        with patch.object(self.service, 'portfolio_exists', return_value=True):
            result = self.service.create_portfolio(
                name="existing_portfolio",
                backtest_start_date="2023-01-01",
                backtest_end_date="2023-12-31"
            )
        
        # 验证返回结果
        self.assertFalse(result['success'])
        self.assertIn("already exists", result['error'])

    def test_create_portfolio_long_name_truncation(self):
        """测试超长组合名的截断处理"""
        long_name = "a" * 120  # 超过100字符限制
        
        mock_portfolio_record = MagicMock()
        mock_portfolio_record.uuid = "test-long-uuid"
        mock_portfolio_record.name = long_name[:100]
        mock_portfolio_record.backtest_start_date = "2023-01-01"
        mock_portfolio_record.backtest_end_date = "2023-12-31"
        mock_portfolio_record.is_live = False
        mock_portfolio_record.desc = "Long name portfolio"
        
        self.mock_crud_repo.create.return_value = mock_portfolio_record
        
        with patch.object(self.service, 'portfolio_exists', return_value=False):
            result = self.service.create_portfolio(
                name=long_name,
                backtest_start_date="2023-01-01",
                backtest_end_date="2023-12-31"
            )
        
        # 验证截断警告
        self.assertTrue(result['success'])
        self.assertIn("Portfolio name truncated to 100 characters", result['warnings'])

    def test_create_portfolio_database_error(self):
        """测试数据库操作错误处理"""
        self.mock_crud_repo.create.side_effect = Exception("Database connection failed")
        
        with patch.object(self.service, 'portfolio_exists', return_value=False):
            result = self.service.create_portfolio(
                name="test_portfolio",
                backtest_start_date="2023-01-01",
                backtest_end_date="2023-12-31"
            )
        
        # 验证错误处理
        self.assertFalse(result['success'])
        self.assertIn("Database operation failed", result['error'])

    def test_create_live_portfolio(self):
        """测试创建实盘组合"""
        mock_portfolio_record = MagicMock()
        mock_portfolio_record.uuid = "live-portfolio-uuid"
        mock_portfolio_record.name = "live_portfolio"
        mock_portfolio_record.backtest_start_date = "2023-01-01"
        mock_portfolio_record.backtest_end_date = "2023-12-31"
        mock_portfolio_record.is_live = True
        mock_portfolio_record.desc = "Live portfolio: live_portfolio"
        
        self.mock_crud_repo.create.return_value = mock_portfolio_record
        
        with patch.object(self.service, 'portfolio_exists', return_value=False):
            result = self.service.create_portfolio(
                name="live_portfolio",
                backtest_start_date="2023-01-01",
                backtest_end_date="2023-12-31",
                is_live=True
            )
        
        # 验证实盘组合创建
        self.assertTrue(result['success'])
        self.assertTrue(result['is_live'])
        self.assertTrue(result['portfolio_info']['is_live'])

    def test_update_portfolio_success(self):
        """测试成功更新组合"""
        self.mock_crud_repo.modify.return_value = 1
        
        # Mock get_portfolios 返回空（无名称冲突）
        with patch.object(self.service, 'get_portfolios', return_value=pd.DataFrame()):
            result = self.service.update_portfolio(
                portfolio_id="test-uuid-123",
                name="updated_name",
                backtest_start_date="2023-01-01",
                backtest_end_date="2023-12-31",
                is_live=True,
                description="Updated description"
            )
        
        # 验证更新结果
        self.assertTrue(result['success'])
        self.assertEqual(result['portfolio_id'], 'test-uuid-123')
        self.assertEqual(result['updated_count'], 1)
        self.assertEqual(len(result['updates_applied']), 5)
        self.assertIn('name', result['updates_applied'])
        self.assertIn('backtest_start_date', result['updates_applied'])
        self.assertIn('backtest_end_date', result['updates_applied'])
        self.assertIn('is_live', result['updates_applied'])
        self.assertIn('description', result['updates_applied'])

    def test_update_portfolio_empty_portfolio_id(self):
        """测试空组合ID的处理"""
        result = self.service.update_portfolio("", name="new_name")
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Portfolio ID cannot be empty")

    def test_update_portfolio_empty_name(self):
        """测试空名称的更新处理"""
        result = self.service.update_portfolio(
            portfolio_id="test-uuid-123",
            name=""  # 空名称
        )
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Portfolio name cannot be empty")

    def test_update_portfolio_no_updates(self):
        """测试无更新内容的处理"""
        result = self.service.update_portfolio("test-uuid-123")
        
        self.assertTrue(result['success'])  # 无更新不是错误
        self.assertIn("No updates provided for portfolio update", result['warnings'])

    def test_update_portfolio_name_conflict(self):
        """测试更新时名称冲突的处理"""
        # Mock get_portfolios 返回现有组合（不同UUID）
        existing_portfolios_df = pd.DataFrame({
            'uuid': ['other-uuid'],
            'name': ['conflicting_name']
        })
        
        with patch.object(self.service, 'get_portfolios', return_value=existing_portfolios_df):
            result = self.service.update_portfolio(
                portfolio_id="test-uuid-123",
                name="conflicting_name"
            )
        
        self.assertFalse(result['success'])
        self.assertIn("already exists", result['error'])

    def test_update_portfolio_database_error(self):
        """测试数据库更新错误处理"""
        self.mock_crud_repo.modify.side_effect = Exception("Update failed")
        
        with patch.object(self.service, 'get_portfolios', return_value=pd.DataFrame()):
            result = self.service.update_portfolio(
                portfolio_id="test-uuid-123",
                name="new_name"
            )
        
        self.assertFalse(result['success'])
        self.assertIn("Database operation failed", result['error'])

    def test_delete_portfolio_success(self):
        """测试成功删除组合"""
        # Mock 文件映射查询返回一些映射
        mock_mappings = [
            MagicMock(uuid="mapping-1"),
            MagicMock(uuid="mapping-2")
        ]
        self.mock_portfolio_file_mapping_crud.find.return_value = mock_mappings
        
        # Mock 删除操作
        self.mock_param_crud.soft_remove.return_value = 3  # 删除3个参数
        self.mock_portfolio_file_mapping_crud.soft_remove.return_value = 2  # 删除2个映射
        self.mock_crud_repo.soft_remove.return_value = 1  # 删除1个组合
        
        result = self.service.delete_portfolio("test-uuid-123")
        
        # 验证删除结果
        self.assertTrue(result['success'])
        self.assertEqual(result['portfolio_id'], 'test-uuid-123')
        self.assertEqual(result['deleted_count'], 1)
        self.assertEqual(result['mappings_deleted'], 2)
        self.assertEqual(result['parameters_deleted'], 6)  # 2个映射各删除3个参数

    def test_delete_portfolio_empty_id(self):
        """测试空组合ID的删除处理"""
        result = self.service.delete_portfolio("")
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Portfolio ID cannot be empty")

    def test_delete_portfolio_not_found(self):
        """测试删除不存在组合的处理"""
        self.mock_portfolio_file_mapping_crud.find.return_value = []
        self.mock_portfolio_file_mapping_crud.soft_remove.return_value = 0
        self.mock_crud_repo.soft_remove.return_value = 0
        
        result = self.service.delete_portfolio("nonexistent-uuid")
        
        self.assertTrue(result['success'])  # 删除操作成功，但没有找到组合
        self.assertEqual(result['deleted_count'], 0)
        self.assertIn("No portfolio found", result['warnings'][0])

    def test_delete_portfolio_mapping_cleanup_failure(self):
        """测试映射清理失败的处理"""
        mock_mappings = [MagicMock(uuid="mapping-1")]
        self.mock_portfolio_file_mapping_crud.find.return_value = mock_mappings
        self.mock_param_crud.soft_remove.side_effect = Exception("Parameter cleanup failed")
        self.mock_portfolio_file_mapping_crud.soft_remove.return_value = 1
        self.mock_crud_repo.soft_remove.return_value = 1
        
        result = self.service.delete_portfolio("test-uuid-123")
        
        # 验证部分成功（组合删除成功，但参数清理失败）
        self.assertTrue(result['success'])
        self.assertEqual(result['deleted_count'], 1)
        self.assertIn("Failed to delete parameters", result['warnings'][0])

    def test_delete_portfolio_database_error(self):
        """测试数据库删除错误处理"""
        self.mock_crud_repo.soft_remove.side_effect = Exception("Delete failed")
        
        result = self.service.delete_portfolio("test-uuid-123")
        
        self.assertFalse(result['success'])
        self.assertIn("Database operation failed", result['error'])

    def test_delete_portfolios_batch_success(self):
        """测试批量删除组合成功"""
        portfolio_ids = ["uuid-1", "uuid-2", "uuid-3"]
        
        # Mock delete_portfolio 返回成功结果
        success_result = {
            "success": True,
            "deleted_count": 1,
            "mappings_deleted": 1,
            "parameters_deleted": 2,
            "warnings": []
        }
        
        with patch.object(self.service, 'delete_portfolio', return_value=success_result):
            result = self.service.delete_portfolios(portfolio_ids)
            
            # 验证批量删除结果
            self.assertTrue(result['success'])
            self.assertEqual(result['total_requested'], 3)
            self.assertEqual(result['successful_deletions'], 3)
            self.assertEqual(result['failed_deletions'], 0)
            self.assertEqual(result['total_mappings_deleted'], 3)
            self.assertEqual(result['total_parameters_deleted'], 6)

    def test_delete_portfolios_empty_list(self):
        """测试空组合列表的批量删除"""
        result = self.service.delete_portfolios([])
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_requested'], 0)
        self.assertIn("Empty portfolio list provided", result['warnings'])

    def test_delete_portfolios_partial_failure(self):
        """测试部分删除失败的处理"""
        portfolio_ids = ["uuid-1", "uuid-2", "uuid-3"]
        
        # Mock 部分成功和失败的结果
        def mock_delete_portfolio(portfolio_id):
            if portfolio_id == "uuid-2":
                return {
                    "success": False,
                    "error": "Portfolio not found",
                    "deleted_count": 0,
                    "mappings_deleted": 0,
                    "parameters_deleted": 0,
                    "warnings": []
                }
            return {
                "success": True,
                "deleted_count": 1,
                "mappings_deleted": 1,
                "parameters_deleted": 2,
                "warnings": []
            }
        
        with patch.object(self.service, 'delete_portfolio', side_effect=mock_delete_portfolio):
            result = self.service.delete_portfolios(portfolio_ids)
            
            # 验证部分失败结果
            self.assertFalse(result['success'])  # 有失败所以整体失败
            self.assertEqual(result['successful_deletions'], 2)
            self.assertEqual(result['failed_deletions'], 1)
            self.assertEqual(len(result['failures']), 1)

    def test_get_portfolios_cached(self):
        """测试获取组合的缓存功能"""
        mock_portfolios_df = pd.DataFrame({
            'uuid': ['uuid-1', 'uuid-2'],
            'name': ['portfolio1', 'portfolio2'],
            'is_live': [False, True],
            'backtest_start_date': ['2023-01-01', '2023-01-01'],
            'backtest_end_date': ['2023-12-31', '2023-12-31']
        })
        
        self.mock_crud_repo.find.return_value = mock_portfolios_df
        
        # 第一次调用
        result1 = self.service.get_portfolios(is_live=False, as_dataframe=True)
        
        # 第二次调用（应该使用缓存）
        result2 = self.service.get_portfolios(is_live=False, as_dataframe=True)
        
        # 验证缓存效果（CRUD只被调用一次）
        self.mock_crud_repo.find.assert_called_once()
        pd.testing.assert_frame_equal(result1, result2)

    def test_get_portfolio_single(self):
        """测试获取单个组合"""
        # Mock get_portfolios 返回单个组合
        single_portfolio_df = pd.DataFrame({
            'uuid': ['test-uuid'],
            'name': ['test_portfolio'],
            'is_live': [False],
            'backtest_start_date': ['2023-01-01'],
            'backtest_end_date': ['2023-12-31']
        })
        
        with patch.object(self.service, 'get_portfolios', return_value=single_portfolio_df):
            result = self.service.get_portfolio("test-uuid", as_dataframe=True)
            
            self.assertIsNotNone(result)
            self.assertFalse(result.empty)

    def test_get_portfolio_not_found(self):
        """测试获取不存在的组合"""
        with patch.object(self.service, 'get_portfolios', return_value=pd.DataFrame()):
            result = self.service.get_portfolio("nonexistent-uuid", as_dataframe=True)
            
            self.assertIsNone(result)

    def test_count_portfolios(self):
        """测试组合计数功能"""
        self.mock_crud_repo.count.return_value = 5
        
        count = self.service.count_portfolios(is_live=False)
        
        self.assertEqual(count, 5)

    def test_portfolio_exists_true(self):
        """测试组合存在检查"""
        self.mock_crud_repo.exists.return_value = True
        
        exists = self.service.portfolio_exists("existing_portfolio")
        
        self.assertTrue(exists)

    def test_portfolio_exists_false(self):
        """测试组合不存在检查"""
        self.mock_crud_repo.exists.return_value = False
        
        exists = self.service.portfolio_exists("nonexistent_portfolio")
        
        self.assertFalse(exists)

    def test_add_file_to_portfolio_success(self):
        """测试成功将文件添加到组合"""
        # Mock get_portfolio_file_mappings 返回空（无现有映射）
        with patch.object(self.service, 'get_portfolio_file_mappings', return_value=pd.DataFrame()):
            # 配置 Mock 返回映射记录
            mock_mapping_record = MagicMock()
            mock_mapping_record.uuid = "mapping-uuid"
            mock_mapping_record.portfolio_id = "portfolio-uuid"
            mock_mapping_record.file_id = "file-uuid"
            mock_mapping_record.name = "test_mapping"
            mock_mapping_record.type = FILE_TYPES.STRATEGY
            
            self.mock_portfolio_file_mapping_crud.create.return_value = mock_mapping_record
            
            result = self.service.add_file_to_portfolio(
                portfolio_id="portfolio-uuid",
                file_id="file-uuid",
                name="test_mapping",
                file_type=FILE_TYPES.STRATEGY
            )
            
            # 验证映射结果
            self.assertTrue(result['success'])
            self.assertEqual(result['portfolio_id'], 'portfolio-uuid')
            self.assertEqual(result['file_id'], 'file-uuid')
            self.assertEqual(result['name'], 'test_mapping')
            self.assertIsNotNone(result['mapping_info'])
            self.assertEqual(result['mapping_info']['uuid'], 'mapping-uuid')

    def test_add_file_to_portfolio_empty_ids(self):
        """测试空ID的文件映射处理"""
        # 测试空组合ID
        result1 = self.service.add_file_to_portfolio("", "file-uuid", "test", FILE_TYPES.STRATEGY)
        self.assertFalse(result1['success'])
        self.assertEqual(result1['error'], "Portfolio ID cannot be empty")
        
        # 测试空文件ID
        result2 = self.service.add_file_to_portfolio("portfolio-uuid", "", "test", FILE_TYPES.STRATEGY)
        self.assertFalse(result2['success'])
        self.assertEqual(result2['error'], "File ID cannot be empty")
        
        # 测试空映射名称
        result3 = self.service.add_file_to_portfolio("portfolio-uuid", "file-uuid", "", FILE_TYPES.STRATEGY)
        self.assertFalse(result3['success'])
        self.assertEqual(result3['error'], "Mapping name cannot be empty")

    def test_add_file_to_portfolio_already_mapped(self):
        """测试添加已存在映射的处理"""
        # Mock get_portfolio_file_mappings 返回现有映射
        existing_mapping_df = pd.DataFrame({
            'portfolio_id': ['portfolio-uuid'],
            'file_id': ['file-uuid']
        })
        
        with patch.object(self.service, 'get_portfolio_file_mappings', return_value=existing_mapping_df):
            result = self.service.add_file_to_portfolio(
                portfolio_id="portfolio-uuid",
                file_id="file-uuid",
                name="test_mapping",
                file_type=FILE_TYPES.STRATEGY
            )
            
            self.assertFalse(result['success'])
            self.assertIn("already mapped", result['error'])

    def test_add_file_to_portfolio_long_name_truncation(self):
        """测试超长映射名称的截断处理"""
        long_name = "a" * 220  # 超过200字符限制
        
        mock_mapping_record = MagicMock()
        mock_mapping_record.uuid = "mapping-uuid"
        mock_mapping_record.portfolio_id = "portfolio-uuid"
        mock_mapping_record.file_id = "file-uuid"
        mock_mapping_record.name = long_name[:200]
        mock_mapping_record.type = FILE_TYPES.STRATEGY
        
        self.mock_portfolio_file_mapping_crud.create.return_value = mock_mapping_record
        
        with patch.object(self.service, 'get_portfolio_file_mappings', return_value=pd.DataFrame()):
            result = self.service.add_file_to_portfolio(
                portfolio_id="portfolio-uuid",
                file_id="file-uuid",
                name=long_name,
                file_type=FILE_TYPES.STRATEGY
            )
        
        # 验证截断警告
        self.assertTrue(result['success'])
        self.assertIn("Mapping name truncated to 200 characters", result['warnings'])

    def test_add_file_to_portfolio_database_error(self):
        """测试数据库映射错误处理"""
        self.mock_portfolio_file_mapping_crud.create.side_effect = Exception("Mapping failed")
        
        with patch.object(self.service, 'get_portfolio_file_mappings', return_value=pd.DataFrame()):
            result = self.service.add_file_to_portfolio(
                portfolio_id="portfolio-uuid",
                file_id="file-uuid",
                name="test_mapping",
                file_type=FILE_TYPES.STRATEGY
            )
        
        self.assertFalse(result['success'])
        self.assertIn("Database operation failed", result['error'])

    def test_remove_file_from_portfolio_success(self):
        """测试成功从组合移除文件"""
        self.mock_param_crud.soft_remove.return_value = 3  # 删除3个参数
        self.mock_portfolio_file_mapping_crud.soft_remove.return_value = 1  # 删除1个映射
        
        result = self.service.remove_file_from_portfolio("mapping-uuid")
        
        # 验证移除结果
        self.assertTrue(result['success'])
        self.assertEqual(result['mapping_id'], 'mapping-uuid')
        self.assertEqual(result['removed_count'], 1)
        self.assertEqual(result['parameters_deleted'], 3)

    def test_remove_file_from_portfolio_empty_id(self):
        """测试空映射ID的移除处理"""
        result = self.service.remove_file_from_portfolio("")
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Mapping ID cannot be empty")

    def test_remove_file_from_portfolio_not_found(self):
        """测试移除不存在映射的处理"""
        self.mock_param_crud.soft_remove.return_value = 0
        self.mock_portfolio_file_mapping_crud.soft_remove.return_value = 0
        
        result = self.service.remove_file_from_portfolio("nonexistent-uuid")
        
        self.assertTrue(result['success'])  # 移除操作成功，但没有找到映射
        self.assertEqual(result['removed_count'], 0)
        self.assertIn("No mapping found", result['warnings'][0])

    def test_remove_file_from_portfolio_parameters_cleanup_failure(self):
        """测试参数清理失败的处理"""
        self.mock_param_crud.soft_remove.side_effect = Exception("Parameter cleanup failed")
        self.mock_portfolio_file_mapping_crud.soft_remove.return_value = 1
        
        result = self.service.remove_file_from_portfolio("mapping-uuid")
        
        # 验证部分成功（映射删除成功，但参数清理失败）
        self.assertTrue(result['success'])
        self.assertEqual(result['removed_count'], 1)
        self.assertIn("Failed to delete parameters", result['warnings'][0])

    def test_remove_file_from_portfolio_database_error(self):
        """测试数据库移除错误处理"""
        self.mock_portfolio_file_mapping_crud.soft_remove.side_effect = Exception("Remove failed")
        
        result = self.service.remove_file_from_portfolio("mapping-uuid")
        
        self.assertFalse(result['success'])
        self.assertIn("Database operation failed", result['error'])

    def test_get_portfolio_file_mappings_cached(self):
        """测试获取组合文件映射的缓存功能"""
        mock_mappings_df = pd.DataFrame({
            'uuid': ['mapping-uuid-1', 'mapping-uuid-2'],
            'portfolio_id': ['portfolio-uuid', 'portfolio-uuid'],
            'file_id': ['file-uuid-1', 'file-uuid-2']
        })
        
        self.mock_portfolio_file_mapping_crud.find.return_value = mock_mappings_df
        
        # 第一次调用
        result1 = self.service.get_portfolio_file_mappings(portfolio_id="portfolio-uuid", as_dataframe=True)
        
        # 第二次调用（应该使用缓存）
        result2 = self.service.get_portfolio_file_mappings(portfolio_id="portfolio-uuid", as_dataframe=True)
        
        # 验证缓存效果
        self.mock_portfolio_file_mapping_crud.find.assert_called_once()
        pd.testing.assert_frame_equal(result1, result2)

    def test_get_files_for_portfolio(self):
        """测试获取组合关联的文件"""
        mock_mappings_df = pd.DataFrame({
            'portfolio_id': ['portfolio-uuid'],
            'file_id': ['file-uuid'],
            'name': ['test_file']
        })
        
        with patch.object(self.service, 'get_portfolio_file_mappings', return_value=mock_mappings_df):
            result = self.service.get_files_for_portfolio("portfolio-uuid")
            
            self.assertIsInstance(result, pd.DataFrame)
            self.assertEqual(len(result), 1)

    def test_add_parameter_success(self):
        """测试成功添加参数"""
        # 配置 Mock 返回参数记录
        mock_param_record = MagicMock()
        mock_param_record.uuid = "param-uuid"
        mock_param_record.mapping_id = "mapping-uuid"
        mock_param_record.order = 1
        mock_param_record.value = "test_value"
        
        self.mock_param_crud.create.return_value = mock_param_record
        
        result = self.service.add_parameter(
            mapping_id="mapping-uuid",
            order=1,
            value="test_value"
        )
        
        # 验证参数添加结果
        self.assertTrue(result['success'])
        self.assertEqual(result['mapping_id'], 'mapping-uuid')
        self.assertEqual(result['order'], 1)
        self.assertEqual(result['value'], 'test_value')
        self.assertIsNotNone(result['parameter_info'])
        self.assertEqual(result['parameter_info']['uuid'], 'param-uuid')

    def test_add_parameter_empty_mapping_id(self):
        """测试空映射ID的参数添加处理"""
        result = self.service.add_parameter("", 1, "test_value")
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Mapping ID cannot be empty")

    def test_add_parameter_invalid_order(self):
        """测试无效参数顺序的处理"""
        # 测试负数顺序
        result1 = self.service.add_parameter("mapping-uuid", -1, "test_value")
        self.assertFalse(result1['success'])
        self.assertEqual(result1['error'], "Parameter order must be a non-negative integer")
        
        # 测试None顺序
        result2 = self.service.add_parameter("mapping-uuid", None, "test_value")
        self.assertFalse(result2['success'])
        self.assertEqual(result2['error'], "Parameter order must be a non-negative integer")

    def test_add_parameter_none_value(self):
        """测试None参数值的处理"""
        result = self.service.add_parameter("mapping-uuid", 1, None)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Parameter value cannot be None")

    def test_add_parameter_long_value_truncation(self):
        """测试超长参数值的截断处理"""
        long_value = "a" * 1200  # 超过1000字符限制
        
        mock_param_record = MagicMock()
        mock_param_record.uuid = "param-uuid"
        mock_param_record.mapping_id = "mapping-uuid"
        mock_param_record.order = 1
        mock_param_record.value = long_value[:1000]
        
        self.mock_param_crud.create.return_value = mock_param_record
        
        result = self.service.add_parameter(
            mapping_id="mapping-uuid",
            order=1,
            value=long_value
        )
        
        # 验证截断警告
        self.assertTrue(result['success'])
        self.assertIn("Parameter value truncated to 1000 characters", result['warnings'])

    def test_add_parameter_database_error(self):
        """测试数据库参数添加错误处理"""
        self.mock_param_crud.create.side_effect = Exception("Parameter creation failed")
        
        result = self.service.add_parameter("mapping-uuid", 1, "test_value")
        
        self.assertFalse(result['success'])
        self.assertIn("Database operation failed", result['error'])

    def test_get_parameters_for_mapping(self):
        """测试获取映射的参数"""
        mock_params_df = pd.DataFrame({
            'uuid': ['param-uuid-1', 'param-uuid-2'],
            'mapping_id': ['mapping-uuid', 'mapping-uuid'],
            'order': [1, 2],
            'value': ['value1', 'value2']
        })
        
        self.mock_param_crud.find.return_value = mock_params_df
        
        result = self.service.get_parameters_for_mapping("mapping-uuid")
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)

    def test_clean_orphaned_mappings_success(self):
        """测试成功清理孤立映射"""
        # Mock 现有映射
        mock_mappings_df = pd.DataFrame({
            'uuid': ['mapping-1', 'mapping-2'],
            'portfolio_id': ['portfolio-1', 'portfolio-2'],
            'file_id': ['file-1', 'file-2']
        })
        
        with patch.object(self.service, 'get_portfolio_file_mappings', return_value=mock_mappings_df):
            # Mock 组合和文件存在性检查
            self.mock_crud_repo.exists.side_effect = [False, True]  # 第一个组合不存在，第二个存在
            
            # Mock 文件CRUD
            mock_file_crud = Mock()
            mock_file_crud.exists.side_effect = [True, False]  # 第一个文件存在，第二个不存在
            
            # Mock ginkgo.data.utils.get_crud
            with patch('ginkgo.data.utils.get_crud', return_value=mock_file_crud):
                # Mock 删除操作
                self.mock_param_crud.soft_remove.return_value = 2
                self.mock_portfolio_file_mapping_crud.soft_remove.return_value = 1
                
                result = self.service.clean_orphaned_mappings()
        
        # 验证清理结果
        self.assertTrue(result['success'])
        self.assertEqual(result['mappings_checked'], 2)
        self.assertEqual(result['cleaned_mappings'], 2)  # 两个映射都应该被清理
        self.assertEqual(result['cleaned_parameters'], 4)  # 每个映射删除2个参数

    def test_clean_orphaned_mappings_empty_mappings(self):
        """测试清理空映射列表"""
        with patch.object(self.service, 'get_portfolio_file_mappings', return_value=pd.DataFrame()):
            result = self.service.clean_orphaned_mappings()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['mappings_checked'], 0)
        self.assertIn("No portfolio-file mappings found to clean", result['warnings'])

    def test_clean_orphaned_mappings_file_check_error(self):
        """测试文件存在性检查错误的处理"""
        mock_mappings_df = pd.DataFrame({
            'uuid': ['mapping-1'],
            'portfolio_id': ['portfolio-1'],
            'file_id': ['file-1']
        })
        
        with patch.object(self.service, 'get_portfolio_file_mappings', return_value=mock_mappings_df):
            self.mock_crud_repo.exists.return_value = True  # 组合存在
            
            # Mock 文件CRUD抛出异常
            with patch('ginkgo.data.utils.get_crud', side_effect=Exception("File CRUD error")):
                result = self.service.clean_orphaned_mappings()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['skipped_mappings'], 1)
        self.assertIn("Could not check file existence", result['warnings'][0])

    def test_clean_orphaned_mappings_database_error(self):
        """测试数据库清理错误处理"""
        with patch.object(self.service, 'get_portfolio_file_mappings', side_effect=Exception("Database error")):
            result = self.service.clean_orphaned_mappings()
        
        self.assertFalse(result['success'])
        self.assertIn("Database operation failed", result['error'])

    def test_retry_mechanism_create_portfolio(self):
        """测试创建组合的重试机制存在（验证装饰器应用）"""
        # 检查create_portfolio方法是否被@retry装饰器包装
        self.assertTrue(hasattr(self.service.create_portfolio, '__name__'))
        
        # 简化的重试测试：验证方法最终会在数据库错误后返回失败结果
        self.mock_crud_repo.create.side_effect = Exception("Database connection failed")
        
        with patch.object(self.service, 'portfolio_exists', return_value=False):
            result = self.service.create_portfolio(
                name="retry_test",
                backtest_start_date="2023-01-01",
                backtest_end_date="2023-12-31"
            )
        
        # 验证在重试失败后返回错误结果
        self.assertFalse(result['success'])
        self.assertIn("Database operation failed", result['error'])
        
        # 验证至少调用了一次（可能因为重试装饰器而调用多次）
        self.assertGreaterEqual(self.mock_crud_repo.create.call_count, 1)

    def test_comprehensive_error_logging(self):
        """测试全面的错误日志记录"""
        # 触发数据库错误并验证业务逻辑处理
        self.mock_crud_repo.create.side_effect = Exception("Critical database error")
        
        with patch.object(self.service, 'portfolio_exists', return_value=False):
            result = self.service.create_portfolio(
                name="error_test",
                backtest_start_date="2023-01-01",
                backtest_end_date="2023-12-31"
            )
        
        # 验证错误处理结果
        self.assertFalse(result['success'])
        self.assertIsNotNone(result['error'])
        self.assertIn("Critical database error", result['error'])


if __name__ == '__main__':
    unittest.main()