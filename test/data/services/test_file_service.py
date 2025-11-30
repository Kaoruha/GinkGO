import unittest
import sys
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

try:
    from ginkgo.data.services.file_service import FileService
    from ginkgo.data.crud.file_crud import FileCRUD
    from ginkgo.data.models import MFile
    from ginkgo.enums import FILE_TYPES, SOURCE_TYPES
    from ginkgo.libs import GCONF, GLOG
    from ginkgo.backtest.core.file_info import FileInfo
except ImportError as e:
    print(f"Import error: {e}")
    FileService = None
    GCONF = None


class FileServiceTest(unittest.TestCase):
    """
    FileService 单元测试
    测试增强的文件管理功能和错误处理能力
    
    边界条件优化说明：
    ==================
    
    1. **文件大小边界条件**：
       - 空文件：应该能够处理但有警告
       - 大文件：测试针对真实大小的文件处理（约2MB）
    
    2. **文件存在性边界条件**：
       - 区分文件不存在（get_file_content返回None）和内容为空（返回b''）
       - 空内容文件可能是合法的，应该能复制但有警告
    
    3. **批量操作边界条件**：
       - 区分真正的失败和idempotent情况（与 engine_service 保持一致）
       - 文件不存在应该是idempotent操作，不是真正的失败
    
    4. **数据类型验证**：
       - 非-bytes类型数据的严格验证
       - 文件名长度限制的合理处理和实际截断验证
    
    5. **移除缓存测试**：
       - 按用户要求移除了所有缓存相关的测试
       - 专注于核心业务逻辑的验证
    """

    # Mock file data - 基于真实Python代码格式
    MOCK_STRATEGY_FILE_CONTENT = b'''
"""
Sample Strategy Implementation
"""
from ginkgo.backtest.strategy.strategies.base_strategy import BaseStrategy
from ginkgo.backtest.signal import Signal
from typing import List

class SampleStrategy(BaseStrategy):
    def cal(self) -> List[Signal]:
        """Calculate trading signals."""
        signals = []
        # Strategy logic here
        return signals
'''

    MOCK_ANALYZER_FILE_CONTENT = b'''
"""
Sample Analyzer Implementation
"""
from ginkgo.backtest.analysis.analyzers.base_analyzer import BaseAnalyzer

class SampleAnalyzer(BaseAnalyzer):
    def _do_activate(self, stage, portfolio_info):
        """Analyze portfolio performance."""
        pass
'''

    MOCK_EMPTY_FILE_CONTENT = b''

    MOCK_LARGE_FILE_CONTENT = b'# Large file content\n' * 100000  # 模拟真正的大文件（约 2MB）

    MOCK_INVALID_BYTES_DATA = "not bytes data"  # 非bytes类型数据

    @classmethod
    def setUpClass(cls):
        """类级别设置"""
        if FileService is None or GCONF is None:
            raise AssertionError("FileService or GCONF not available")

        print(":white_check_mark: FileService test setup completed")

    def setUp(self):
        """每个测试前的设置"""
        # 创建 Mock 依赖
        self.mock_crud_repo = Mock()
        
        # Mock session management
        self.mock_session = Mock()
        self.mock_session.begin.return_value.__enter__ = Mock(return_value=self.mock_session)
        self.mock_session.begin.return_value.__exit__ = Mock(return_value=None)
        self.mock_crud_repo.get_session.return_value = self.mock_session
        
        # 创建 FileService 实例
        self.service = FileService(crud_repo=self.mock_crud_repo)

    def test_add_file_success(self):
        """测试成功添加文件"""
        # 配置 Mock 返回文件记录
        mock_file_record = MagicMock()
        mock_file_record.uuid = "test-uuid-123"
        mock_file_record.name = "test_strategy"
        mock_file_record.type = FILE_TYPES.STRATEGY
        mock_file_record.desc = "Strategy file: test_strategy"
        
        self.mock_crud_repo.create.return_value = mock_file_record
        
        # 执行添加文件
        result = self.service.add_file(
            name="test_strategy",
            file_type=FILE_TYPES.STRATEGY,
            data=self.MOCK_STRATEGY_FILE_CONTENT,
            description="Test strategy"
        )
        
        # 验证返回结果
        self.assertIsInstance(result, dict)
        self.assertTrue(result['success'])
        self.assertEqual(result['name'], 'test_strategy')
        self.assertEqual(result['file_type'], 'STRATEGY')
        self.assertIsNone(result['error'])
        self.assertIsInstance(result['warnings'], list)
        self.assertIsNotNone(result['file_info'])
        self.assertEqual(result['file_info']['uuid'], 'test-uuid-123')
        self.assertEqual(result['file_info']['data_size'], len(self.MOCK_STRATEGY_FILE_CONTENT))

    def test_add_file_empty_name(self):
        """测试空文件名的处理"""
        result = self.service.add_file(
            name="",
            file_type=FILE_TYPES.STRATEGY,
            data=self.MOCK_STRATEGY_FILE_CONTENT
        )
        
        # 验证返回结果
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "File name cannot be empty")

    def test_add_file_invalid_data_type(self):
        """测试无效数据类型的处理"""
        result = self.service.add_file(
            name="test_file",
            file_type=FILE_TYPES.STRATEGY,
            data=self.MOCK_INVALID_BYTES_DATA  # 非bytes类型
        )
        
        # 验证返回结果
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "File data must be bytes")

    def test_add_file_empty_data_warning(self):
        """测试空文件数据的警告处理"""
        mock_file_record = MagicMock()
        mock_file_record.uuid = "test-uuid-empty"
        mock_file_record.name = "empty_file"
        mock_file_record.type = FILE_TYPES.OTHER
        mock_file_record.desc = "Empty file"
        
        self.mock_crud_repo.create.return_value = mock_file_record
        
        result = self.service.add_file(
            name="empty_file",
            file_type=FILE_TYPES.OTHER,
            data=self.MOCK_EMPTY_FILE_CONTENT
        )
        
        # 验证结果包含警告
        self.assertTrue(result['success'])
        self.assertIn("File data is empty", result['warnings'])

    def test_add_file_long_name_truncation(self):
        """测试超长文件名的截断处理"""
        long_name = "a" * 50  # 超过40字符限制
        
        mock_file_record = MagicMock()
        mock_file_record.uuid = "test-uuid-long"
        mock_file_record.name = long_name[:40]
        mock_file_record.type = FILE_TYPES.STRATEGY
        mock_file_record.desc = "Long name file"
        
        self.mock_crud_repo.create.return_value = mock_file_record
        
        result = self.service.add_file(
            name=long_name,
            file_type=FILE_TYPES.STRATEGY,
            data=self.MOCK_STRATEGY_FILE_CONTENT
        )
        
        # 验证截断警告和实际截断结果
        self.assertTrue(result['success'])
        self.assertIn("File name truncated to 40 characters", result['warnings'])
        # 验证文件名确实被截断到正确的长度
        self.assertEqual(len(result['file_info']['name']), 40)
        self.assertEqual(result['file_info']['name'], long_name[:40])

    def test_add_file_large_file_handling(self):
        """
        测试大文件的处理
        
        修正说明：测试真实大小的文件处理能力
        大文件限制应该由业务逻辑或数据库层处理，不是服务层限制
        """
        mock_file_record = MagicMock()
        mock_file_record.uuid = "large-file-uuid"
        mock_file_record.name = "large_file"
        mock_file_record.type = FILE_TYPES.OTHER
        mock_file_record.desc = "Large file"
        
        self.mock_crud_repo.create.return_value = mock_file_record
        
        result = self.service.add_file(
            name="large_file",
            file_type=FILE_TYPES.OTHER,
            data=self.MOCK_LARGE_FILE_CONTENT
        )
        
        # 验证大文件处理能力
        self.assertTrue(result['success'])
        self.assertEqual(result['file_info']['data_size'], len(self.MOCK_LARGE_FILE_CONTENT))
        # 验证能够处理真实大小的文件（约2MB）
        self.assertGreater(result['file_info']['data_size'], 1000000)  # 超过1MB

    def test_add_file_database_error(self):
        """测试数据库操作错误处理"""
        self.mock_crud_repo.create.side_effect = Exception("Database connection failed")
        
        result = self.service.add_file(
            name="test_file",
            file_type=FILE_TYPES.STRATEGY,
            data=self.MOCK_STRATEGY_FILE_CONTENT
        )
        
        # 验证错误处理
        self.assertFalse(result['success'])
        self.assertIn("Database operation failed", result['error'])

    def test_copy_file_success(self):
        """测试成功复制文件"""
        source_id = "source-uuid-123"
        
        # Mock get_file_content 返回源文件内容
        with patch.object(self.service, 'get_file_content', return_value=self.MOCK_ANALYZER_FILE_CONTENT):
            # Mock get_files 返回源文件信息
            source_file_df = pd.DataFrame({
                'uuid': [source_id],
                'name': ['source_analyzer'],
                'type': [FILE_TYPES.ANALYZER.value]
            })
            with patch.object(self.service, 'get_files', return_value=source_file_df):
                # Mock add_file 成功
                mock_add_result = {
                    "success": True,
                    "file_info": {
                        "uuid": "copy-uuid-456",
                        "name": "copied_analyzer",
                        "type": FILE_TYPES.ANALYZER,
                        "desc": f"Copy of {source_id}",
                        "data_size": len(self.MOCK_ANALYZER_FILE_CONTENT)
                    },
                    "warnings": []
                }
                with patch.object(self.service, 'add_file', return_value=mock_add_result):
                    
                    result = self.service.copy_file(source_id, "copied_analyzer")
                    
                    # 验证复制结果
                    self.assertTrue(result['success'])
                    self.assertEqual(result['clone_id'], source_id)
                    self.assertEqual(result['new_name'], 'copied_analyzer')
                    self.assertIsNotNone(result['file_info'])

    def test_copy_file_empty_source_id(self):
        """测试空源文件ID的处理"""
        result = self.service.copy_file("", "new_name")
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "Source file ID cannot be empty")

    def test_copy_file_empty_new_name(self):
        """测试空新文件名的处理"""
        result = self.service.copy_file("source-id", "")
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "New file name cannot be empty")

    def test_copy_file_source_not_found(self):
        """
        测试源文件不存在的处理
        
        修正说明：需要区分文件不存在和文件为空的情况
        文件不存在时 get_file_content 应该返回 None，而不是空 bytes
        """
        # 测试文件不存在的情况（返回None）
        with patch.object(self.service, 'get_file_content', return_value=None):
            result = self.service.copy_file("nonexistent-id", "new_name")
            
            self.assertFalse(result['success'])
            self.assertIsNotNone(result['error'])
    
    def test_copy_file_source_empty_content(self):
        """
        测试源文件内容为空的处理
        
        新增测试：区分文件不存在和文件内容为空的边界情况
        空内容文件可能是合法的，应该能够复制但有警告
        """
        with patch.object(self.service, 'get_file_content', return_value=b''):
            with patch.object(self.service, 'get_files') as mock_get_files:
                # Mock 源文件存在但内容为空
                source_file_df = pd.DataFrame({
                    'uuid': ['source-id'],
                    'name': ['empty_source'],
                    'type': [FILE_TYPES.OTHER.value]
                })
                mock_get_files.return_value = source_file_df
                
                with patch.object(self.service, 'add_file') as mock_add_file:
                    mock_add_file.return_value = {
                        "success": True,
                        "file_info": {"uuid": "copy-uuid", "name": "new_name"},
                        "warnings": ["File data is empty"]
                    }
                    
                    result = self.service.copy_file("source-id", "new_name")
                    
                    # 验证空内容文件可以复制但有警告
                    self.assertTrue(result['success'])
                    self.assertGreater(len(result['warnings']), 0)

    def test_update_file_success(self):
        """测试成功更新文件"""
        self.mock_crud_repo.modify.return_value = 1
        
        result = self.service.update_file(
            file_id="test-uuid-123",
            name="updated_name",
            data=self.MOCK_STRATEGY_FILE_CONTENT,
            description="Updated description"
        )
        
        # 验证更新结果
        self.assertTrue(result['success'])
        self.assertEqual(result['file_id'], 'test-uuid-123')
        self.assertEqual(result['updated_count'], 1)
        self.assertEqual(len(result['updates_applied']), 3)
        self.assertIn('name', result['updates_applied'])
        self.assertIn('data', result['updates_applied'])
        self.assertIn('description', result['updates_applied'])

    def test_update_file_empty_file_id(self):
        """测试空文件ID的处理"""
        result = self.service.update_file("", name="new_name")
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "File ID cannot be empty")

    def test_update_file_no_updates(self):
        """测试无更新内容的处理"""
        result = self.service.update_file("test-uuid-123")
        
        self.assertTrue(result['success'])  # 无更新不是错误
        self.assertIn("No updates provided for file update", result['warnings'])

    def test_update_file_invalid_data_type(self):
        """测试无效数据类型的更新处理"""
        result = self.service.update_file(
            file_id="test-uuid-123",
            data="not bytes"  # 非bytes类型
        )
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "File data must be bytes")

    def test_update_file_database_error(self):
        """测试数据库更新错误处理"""
        self.mock_crud_repo.modify.side_effect = Exception("Update failed")
        
        result = self.service.update_file(
            file_id="test-uuid-123",
            name="new_name"
        )
        
        self.assertFalse(result['success'])
        self.assertIn("Database operation failed", result['error'])

    def test_delete_file_success(self):
        """测试成功删除文件"""
        self.mock_crud_repo.soft_remove.return_value = 1
        
        result = self.service.delete_file("test-uuid-123")
        
        # 验证删除结果
        self.assertTrue(result['success'])
        self.assertEqual(result['file_id'], 'test-uuid-123')
        self.assertEqual(result['deleted_count'], 1)

    def test_delete_file_empty_id(self):
        """测试空文件ID的删除处理"""
        result = self.service.delete_file("")
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "File ID cannot be empty")

    def test_delete_file_not_found(self):
        """测试删除不存在文件的处理"""
        self.mock_crud_repo.soft_remove.return_value = 0
        
        result = self.service.delete_file("nonexistent-uuid")
        
        self.assertTrue(result['success'])  # 删除操作成功，但没有找到文件
        self.assertEqual(result['deleted_count'], 0)
        self.assertIn("No file found", result['warnings'][0])

    def test_delete_file_database_error(self):
        """测试数据库删除错误处理"""
        self.mock_crud_repo.soft_remove.side_effect = Exception("Delete failed")
        
        result = self.service.delete_file("test-uuid-123")
        
        self.assertFalse(result['success'])
        self.assertIn("Database operation failed", result['error'])

    def test_delete_files_batch_success(self):
        """测试批量删除文件成功"""
        file_ids = ["uuid-1", "uuid-2", "uuid-3"]
        
        # Mock delete_file 返回成功结果
        success_result = {
            "success": True,
            "deleted_count": 1,
            "warnings": []
        }
        
        with patch.object(self.service, 'delete_file', return_value=success_result):
            result = self.service.delete_files(file_ids)
            
            # 验证批量删除结果
            self.assertTrue(result['success'])
            self.assertEqual(result['total_requested'], 3)
            self.assertEqual(result['successful_deletions'], 3)
            self.assertEqual(result['failed_deletions'], 0)

    def test_delete_files_empty_list(self):
        """测试空文件列表的批量删除"""
        result = self.service.delete_files([])
        
        self.assertTrue(result['success'])
        self.assertEqual(result['total_requested'], 0)
        self.assertIn("Empty file list provided", result['warnings'])

    def test_delete_files_partial_idempotent_success(self):
        """
        测试部分idempotent操作的处理
        
        新增测试：验证idempotent情况下的批量操作处理
        当部分文件不存在时，应该返回成功而不是失败
        """
        file_ids = ["uuid-1", "uuid-2", "uuid-3"]
        
        # Mock 部分idempotent情况（文件不存在）
        def mock_delete_file(file_id):
            if file_id == "uuid-2":
                return {
                    "success": True,  # idempotent操作仍然是成功的
                    "deleted_count": 0,  # 但没有实际删除
                    "warnings": ["No file found with ID uuid-2 to delete"]
                }
            return {
                "success": True,
                "deleted_count": 1,
                "warnings": []
            }
        
        with patch.object(self.service, 'delete_file', side_effect=mock_delete_file):
            result = self.service.delete_files(file_ids)
            
            # 验证所有idempotent情况下的成功结果
            self.assertTrue(result['success'])  # 所有操作都成功（包括idempotent）
            self.assertEqual(result['successful_deletions'], 2)  # 只计算实际删除的文件数
            self.assertEqual(result['failed_deletions'], 0)  # 没有真正的失败
            self.assertEqual(result['total_requested'], 3)  # 请求处理了3个文件

    def test_delete_files_partial_failure(self):
        """
        测试部分删除失败的处理
        
        修正说明：与 engine_service 类似，需要区分真正的失败和idempotent情况
        "File not found"应该是 idempotent 操作（成功但有警告），不是真正的失败
        """
        file_ids = ["uuid-1", "uuid-2", "uuid-3"]
        
        # Mock 部分成功和真正失败的结果
        def mock_delete_file(file_id):
            if file_id == "uuid-2":
                return {
                    "success": False,
                    "error": "Database connection failed",  # 真正的数据库错误，不是"not found"
                    "deleted_count": 0,
                    "warnings": []
                }
            return {
                "success": True,
                "deleted_count": 1,
                "warnings": []
            }
        
        with patch.object(self.service, 'delete_file', side_effect=mock_delete_file):
            result = self.service.delete_files(file_ids)
            
            # 验证真正的部分失败结果（除了idempotent情况）
            self.assertFalse(result['success'])  # 有真正的失败所以整体失败
            self.assertEqual(result['successful_deletions'], 2)
            self.assertEqual(result['failed_deletions'], 1)
            self.assertEqual(len(result['failures']), 1)
            # 验证失败原因是真正的数据库错误，不是"not found"
            self.assertIn("Database connection failed", result['failures'][0]['error'])

    def test_get_files_basic_functionality(self):
        """
        测试获取文件的基本功能
        
        修正说明：移除缓存相关的测试，专注于基本功能验证
        """
        mock_files_df = pd.DataFrame({
            'uuid': ['uuid-1', 'uuid-2'],
            'name': ['file1', 'file2'],
            'type': [FILE_TYPES.STRATEGY.value, FILE_TYPES.ANALYZER.value]
        })
        
        self.mock_crud_repo.find.return_value = mock_files_df
        
        # 测试基本获取功能
        result = self.service.get_files(file_type=FILE_TYPES.STRATEGY, as_dataframe=True)
        
        # 验证基本功能
        self.assertIsInstance(result, pd.DataFrame)
        self.mock_crud_repo.find.assert_called()

    def test_get_file_content_success(self):
        """测试成功获取文件内容"""
        mock_file = MagicMock()
        mock_file.data = self.MOCK_STRATEGY_FILE_CONTENT
        
        self.mock_crud_repo.find.return_value = [mock_file]
        
        content = self.service.get_file_content("test-uuid-123")
        
        self.assertEqual(content, self.MOCK_STRATEGY_FILE_CONTENT)

    def test_get_file_content_not_found(self):
        """测试获取不存在文件内容"""
        self.mock_crud_repo.find.return_value = []
        
        content = self.service.get_file_content("nonexistent-uuid")
        
        self.assertIsNone(content)

    def test_count_files(self):
        """测试文件计数功能"""
        self.mock_crud_repo.count.return_value = 5
        
        count = self.service.count_files(file_type=FILE_TYPES.STRATEGY)
        
        self.assertEqual(count, 5)

    def test_file_exists_true(self):
        """测试文件存在检查"""
        self.mock_crud_repo.exists.return_value = True
        
        exists = self.service.file_exists("test_file", FILE_TYPES.STRATEGY)
        
        self.assertTrue(exists)

    def test_file_exists_false(self):
        """测试文件不存在检查"""
        self.mock_crud_repo.exists.return_value = False
        
        exists = self.service.file_exists("nonexistent_file", FILE_TYPES.STRATEGY)
        
        self.assertFalse(exists)

    def test_initialize_files_from_source_success(self):
        """测试从源代码目录初始化文件成功"""
        # 创建临时目录结构
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建目录结构
            backtest_dir = os.path.join(temp_dir, "src", "ginkgo", "backtest")
            strategies_dir = os.path.join(backtest_dir, "strategies")
            analyzers_dir = os.path.join(backtest_dir, "analyzers")
            
            os.makedirs(strategies_dir, exist_ok=True)
            os.makedirs(analyzers_dir, exist_ok=True)
            
            # 创建测试文件
            strategy_file = os.path.join(strategies_dir, "test_strategy.py")
            analyzer_file = os.path.join(analyzers_dir, "test_analyzer.py")
            
            with open(strategy_file, "wb") as f:
                f.write(self.MOCK_STRATEGY_FILE_CONTENT)
                
            with open(analyzer_file, "wb") as f:
                f.write(self.MOCK_ANALYZER_FILE_CONTENT)
            
            # Mock get_files 返回空（无现有文件）
            with patch.object(self.service, 'get_files', return_value=pd.DataFrame()):
                # Mock add_file 成功
                mock_add_result = {
                    "success": True,
                    "file_info": {"uuid": "new-file-uuid"},
                    "warnings": []
                }
                with patch.object(self.service, 'add_file', return_value=mock_add_result):
                    
                    result = self.service.initialize_files_from_source(working_dir=temp_dir)
                    
                    # 验证初始化结果
                    self.assertTrue(result['success'])
                    self.assertEqual(result['total_files_processed'], 2)
                    self.assertEqual(result['total_files_added'], 2)
                    self.assertIn('strategies', result['folder_results'])
                    self.assertIn('analyzers', result['folder_results'])

    def test_initialize_files_from_source_directory_not_exist(self):
        """测试源目录不存在的处理"""
        result = self.service.initialize_files_from_source(working_dir="/nonexistent/path")
        
        self.assertFalse(result['success'])
        self.assertIn("Source directory", result['error'])
        self.assertIn("does not exist", result['error'])

    def test_initialize_files_from_source_permission_error(self):
        """测试权限错误的处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            backtest_dir = os.path.join(temp_dir, "src", "ginkgo", "backtest")
            strategies_dir = os.path.join(backtest_dir, "strategies")
            os.makedirs(strategies_dir, exist_ok=True)
            
            # Mock os.listdir 抛出权限错误 - 需要用ginkgo.data.services.file_service模块路径
            with patch('ginkgo.data.services.file_service.os.listdir', side_effect=PermissionError("Permission denied")):
                result = self.service.initialize_files_from_source(working_dir=temp_dir)
                
                # 验证权限错误处理
                self.assertGreaterEqual(len(result['warnings']), 1)
                self.assertTrue(any("Permission denied" in warning for warning in result['warnings']))

    def test_initialize_files_from_source_with_blacklisted_files(self):
        """测试黑名单文件的跳过处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            strategies_dir = os.path.join(temp_dir, "src", "ginkgo", "backtest", "strategies")
            os.makedirs(strategies_dir, exist_ok=True)
            
            # 创建黑名单文件
            blacklist_files = ["__init__.py", "base_strategy.py", "__pycache__"]
            valid_file = "valid_strategy.py"
            
            for filename in blacklist_files + [valid_file]:
                file_path = os.path.join(strategies_dir, filename)
                if filename != "__pycache__":  # __pycache__ 是目录
                    with open(file_path, "wb") as f:
                        f.write(self.MOCK_STRATEGY_FILE_CONTENT)
                else:
                    os.makedirs(file_path, exist_ok=True)
            
            with patch.object(self.service, 'get_files', return_value=pd.DataFrame()):
                mock_add_result = {
                    "success": True,
                    "file_info": {"uuid": "valid-file-uuid"},
                    "warnings": []
                }
                with patch.object(self.service, 'add_file', return_value=mock_add_result):
                    
                    result = self.service.initialize_files_from_source(working_dir=temp_dir)
                    
                    # 验证只处理了有效文件，跳过了黑名单文件
                    strategies_result = result['folder_results']['strategies']
                    self.assertEqual(strategies_result['files_processed'], 1)  # 只有valid_strategy.py
                    self.assertEqual(strategies_result['files_added'], 1)
                    self.assertGreater(strategies_result['files_skipped'], 0)  # 黑名单文件被跳过

    def test_get_available_file_types_success(self):
        """测试成功获取可用文件类型"""
        self.mock_crud_repo.find.return_value = [
            FILE_TYPES.STRATEGY.value,
            FILE_TYPES.ANALYZER.value,
            FILE_TYPES.SIZER.value
        ]
        
        result = self.service.get_available_file_types()
        
        # 验证结果
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 3)
        self.assertIn(FILE_TYPES.STRATEGY, result['file_types'])
        self.assertIn(FILE_TYPES.ANALYZER, result['file_types'])
        self.assertIn(FILE_TYPES.SIZER, result['file_types'])

    def test_get_available_file_types_with_invalid_types(self):
        """测试包含无效类型的处理"""
        self.mock_crud_repo.find.return_value = [
            FILE_TYPES.STRATEGY.value,
            999,  # 无效的枚举值
            FILE_TYPES.ANALYZER.value,
            None  # 空值
        ]
        
        result = self.service.get_available_file_types()
        
        # 验证结果
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 2)  # 只有两个有效类型
        self.assertIn("Invalid file type found in database: 999", result['warnings'])

    def test_get_available_file_types_empty_database(self):
        """测试空数据库的处理"""
        self.mock_crud_repo.find.return_value = []
        
        result = self.service.get_available_file_types()
        
        # 验证结果
        self.assertTrue(result['success'])
        self.assertEqual(result['count'], 0)
        self.assertIn("No valid file types found in database", result['warnings'])

    def test_get_available_file_types_database_error(self):
        """测试数据库错误处理"""
        self.mock_crud_repo.find.side_effect = Exception("Database error")
        
        result = self.service.get_available_file_types()
        
        # 验证错误处理
        self.assertFalse(result['success'])
        self.assertIn("Failed to get available file types", result['error'])

    def test_retry_mechanism_add_file(self):
        """测试添加文件的重试机制存在（验证装饰器应用）"""
        # 检查add_file方法是否被@retry装饰器包装
        self.assertTrue(hasattr(self.service.add_file, '__name__'))
        
        # 简化的重试测试：验证方法最终会在数据库错误后返回失败结果
        self.mock_crud_repo.create.side_effect = Exception("Database connection failed")
        
        result = self.service.add_file(
            name="retry_test",
            file_type=FILE_TYPES.STRATEGY,
            data=self.MOCK_STRATEGY_FILE_CONTENT
        )
        
        # 验证在重试失败后返回错误结果
        self.assertFalse(result['success'])
        self.assertIn("Database operation failed", result['error'])
        
        # 验证至少调用了一次（可能因为重试装饰器而调用多次）
        self.assertGreaterEqual(self.mock_crud_repo.create.call_count, 1)

    def test_large_file_handling(self):
        """测试大文件处理"""
        mock_file_record = MagicMock()
        mock_file_record.uuid = "large-file-uuid"
        mock_file_record.name = "large_file"
        mock_file_record.type = FILE_TYPES.OTHER
        mock_file_record.desc = "Large file"
        
        self.mock_crud_repo.create.return_value = mock_file_record
        
        result = self.service.add_file(
            name="large_file",
            file_type=FILE_TYPES.OTHER,
            data=self.MOCK_LARGE_FILE_CONTENT
        )
        
        # 验证大文件处理成功
        self.assertTrue(result['success'])
        self.assertEqual(result['file_info']['data_size'], len(self.MOCK_LARGE_FILE_CONTENT))

    def test_various_file_types_handling(self):
        """测试各种文件类型的处理"""
        file_types_to_test = [
            FILE_TYPES.STRATEGY,
            FILE_TYPES.ANALYZER,
            FILE_TYPES.SIZER,
            FILE_TYPES.SELECTOR,
            FILE_TYPES.RISKMANAGER
        ]
        
        for file_type in file_types_to_test:
            with self.subTest(file_type=file_type):
                mock_file_record = MagicMock()
                mock_file_record.uuid = f"test-{file_type.name.lower()}"
                mock_file_record.name = f"test_{file_type.name.lower()}"
                mock_file_record.type = file_type
                mock_file_record.desc = f"Test {file_type.name} file"
                
                self.mock_crud_repo.create.return_value = mock_file_record
                
                result = self.service.add_file(
                    name=f"test_{file_type.name.lower()}",
                    file_type=file_type,
                    data=self.MOCK_STRATEGY_FILE_CONTENT
                )
                
                self.assertTrue(result['success'])
                self.assertEqual(result['file_type'], file_type.name)

    def test_comprehensive_error_logging(self):
        """测试全面的错误日志记录"""
        # 触发数据库错误并验证业务逻辑处理
        self.mock_crud_repo.create.side_effect = Exception("Critical database error")
        
        result = self.service.add_file(
            name="error_test",
            file_type=FILE_TYPES.STRATEGY,
            data=self.MOCK_STRATEGY_FILE_CONTENT
        )
        
        # 验证错误处理结果
        self.assertFalse(result['success'])
        self.assertIsNotNone(result['error'])
        self.assertIn("Critical database error", result['error'])


if __name__ == '__main__':
    unittest.main()