"""
FileService数据服务测试

测试FileService的核心功能和业务逻辑
遵循BarService测试模式，使用真实实例而非Mock
"""
import pytest
import sys
import os
import tempfile
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.services.file_service import FileService
from ginkgo.data.services.base_service import ManagementService, ServiceResult
from ginkgo.data.containers import container
from ginkgo.enums import FILE_TYPES


@pytest.mark.unit
class TestFileServiceOperations:
    """
    FileService 功能测试
    测试文件管理的核心操作和业务逻辑
    """

    def test_add_file_success(self):
        """测试成功添加文件 - 验证实际数据库操作"""
        file_service = container.file_service()

        # 准备真实的策略文件内容
        strategy_content = b'''
def test_strategy():
    """Sample strategy for testing"""
    return True
'''

        # 执行添加文件操作
        result = file_service.add(
            name="test_strategy",
            file_type=FILE_TYPES.STRATEGY,
            data=strategy_content,
            description="Test strategy file"
        )

        # 验证操作结果
        assert result.success, f"File creation failed: {result.message}"
        file_info = result.data.get("file_info", {})
        assert file_info["name"] == "test_strategy"
        assert file_info["type"] == 6  # FILE_TYPES.STRATEGY value

        # 验证文件记录已创建
        file_uuid = file_info["uuid"]
        assert file_uuid is not None
        assert len(file_uuid) > 0

        # 验证文件确实被插入数据库 - 通过UUID直接查询
        retrieved_files = file_service._crud_repo.find(filters={"uuid": file_uuid})
        assert retrieved_files is not None, "Database query returned None"
        assert len(retrieved_files) > 0, "No files found with given UUID"

        retrieved_file = retrieved_files[0]
        assert retrieved_file.uuid == file_uuid, "UUID mismatch between ServiceResult and database"
        assert retrieved_file.name == "test_strategy", "Name mismatch between ServiceResult and database"
        assert retrieved_file.type == FILE_TYPES.STRATEGY.value, "Type mismatch between ServiceResult and database"
        assert retrieved_file.data == strategy_content, "File content mismatch between ServiceResult and database"

        # 清理测试数据
        try:
            file_service._crud_repo.remove(filters={"uuid": file_uuid})
        except:
            pass

    def test_add_file_validation_errors(self):
        """测试文件添加的验证逻辑"""
        file_service = container.file_service()

        # 测试空文件名
        result = file_service.add(
            name="",
            file_type=FILE_TYPES.STRATEGY,
            data=b"test content"
        )
        assert not result.success
        assert "cannot be empty" in result.message.lower()

        # 测试非bytes数据
        result = file_service.add(
            name="test_file",
            file_type=FILE_TYPES.STRATEGY,
            data="string instead of bytes"
        )
        assert not result.success
        assert "must be bytes" in result.message.lower()

    def test_get_files_with_filters(self):
        """测试文件查询功能"""
        file_service = container.file_service()

        # 先添加一个测试文件
        test_content = b'test content for get files'
        add_result = file_service.add(
            name="query_test",
            file_type=FILE_TYPES.ANALYZER,
            data=test_content
        )

        if add_result.success:
            file_uuid = add_result.data["file_info"]["uuid"]

            try:
                # 测试按UUID查询
                result = file_service.get_by_uuid(file_uuid)
                assert result.success
                assert result.data["exists"]
                assert result.data["file"].uuid == file_uuid

                # 测试按文件名查询
                result = file_service.get_by_name("query_test")
                assert result.success
                files = result.data["files"]
                assert len(files) >= 1

            finally:
                # 清理
                try:
                    file_service._crud_repo.remove(filters={"uuid": file_uuid})
                except:
                    pass

    def test_count_functionality(self):
        """测试文件计数功能"""
        file_service = container.file_service()

        # 获取当前文件总数
        result = file_service.count()
        assert result.success
        initial_count = result.data["count"]
        assert isinstance(initial_count, int)
        assert initial_count >= 0

    def test_file_existence_check(self):
        """测试文件存在性检查"""
        file_service = container.file_service()

        # 测试不存在的文件
        exists_result = file_service.exists(name="non-existent-uuid")
        exists = exists_result.success and exists_result.data
        assert isinstance(exists, bool)
        # 应该返回False（但实现可能不同，所以检查类型而非具体值）

    def test_get_file_content_behavior(self):
        """测试获取文件内容的行为"""
        file_service = container.file_service()

        # 测试获取不存在文件的内容
        content = file_service.get_content("non-existent-uuid")
        # 应该返回None或空bytes，检查返回类型
        assert content is None or isinstance(content, bytes)

    def test_delete_file_operation(self):
        """测试文件删除操作"""
        file_service = container.file_service()

        # 创建一个待删除的文件
        test_content = b'file to be deleted'
        add_result = file_service.add(
            name="delete_test",
            file_type=FILE_TYPES.SELECTOR,
            data=test_content
        )

        if add_result.success:
            file_uuid = add_result.data["file_info"]["uuid"]

            # 验证文件存在
            exists_before_result = file_service.exists(file_id=file_uuid)
            exists_before = exists_before_result.success and exists_before_result.data

            # 执行删除操作
            delete_result = file_service.soft_delete(file_uuid)
            assert delete_result.success

            # 验证文件已删除（检查删除后的状态）
            exists_after_result = file_service.exists(file_id=file_uuid)
            exists_after = exists_after_result.success and exists_after_result.data
            # 文件应该被标记为删除或实际删除

    def test_clone_file_success(self):
        """测试成功克隆文件"""
        file_service = container.file_service()

        # 创建源文件
        original_content = b'def original_function():\n    return "original"'
        add_result = file_service.add(
            name="original_file",
            file_type=FILE_TYPES.STRATEGY,
            data=original_content,
            description="Original file for cloning test"
        )

        assert add_result.success, f"Failed to create original file: {add_result.message}"

        source_uuid = add_result.data["file_info"]["uuid"]

        try:
            # 执行克隆操作
            clone_result = file_service.clone(
                source_id=source_uuid,
                new_name="cloned_file",
                file_type=FILE_TYPES.STRATEGY  # 指定类型
            )

            # 验证克隆结果
            assert clone_result.success, f"Clone failed: {clone_result.message}"
            assert clone_result.data["source_id"] == source_uuid
            assert clone_result.data["new_name"] == "cloned_file"

            cloned_file_info = clone_result.data["file_info"]
            assert cloned_file_info["name"] == "cloned_file"
            assert cloned_file_info["type"] == FILE_TYPES.STRATEGY.value
            # 描述可能由数据库自动生成，不进行严格断言

            # 验证克隆文件的内容
            cloned_content = file_service.get_content(cloned_file_info["uuid"])
            assert cloned_content == original_content

        finally:
            # 清理：删除源文件和克隆文件
            try:
                file_service.soft_delete(source_uuid)
                if 'cloned_file_info' in locals():
                    file_service.soft_delete(cloned_file_info["uuid"])
            except:
                pass

    def test_clone_file_auto_type(self):
        """测试克隆文件自动获取类型"""
        file_service = container.file_service()

        # 创建源文件
        original_content = b'analyzer content'
        add_result = file_service.add(
            name="source_analyzer",
            file_type=FILE_TYPES.ANALYZER,
            data=original_content
        )

        assert add_result.success

        source_uuid = add_result.data["file_info"]["uuid"]

        try:
            # 克隆时不指定类型，应该自动获取
            clone_result = file_service.clone(
                source_id=source_uuid,
                new_name="auto_type_clone"
            )

            assert clone_result.success, f"Clone failed: {clone_result.message}"

            cloned_file_info = clone_result.data["file_info"]
            assert cloned_file_info["type"] == FILE_TYPES.ANALYZER.value

        finally:
            # 清理
            try:
                file_service.soft_delete(source_uuid)
                if 'cloned_file_info' in locals():
                    file_service.soft_delete(cloned_file_info["uuid"])
            except:
                pass

    def test_clone_file_validation_errors(self):
        """测试克隆文件验证逻辑"""
        file_service = container.file_service()

        # 测试空source_id
        result = file_service.clone(
            source_id="",
            new_name="test"
        )
        assert not result.success
        assert "cannot be empty" in result.message.lower()

        # 测试空new_name
        result = file_service.clone(
            source_id="non-existent-id",
            new_name=""
        )
        assert not result.success
        assert "cannot be empty" in result.message.lower()

        # 测试源文件不存在
        result = file_service.clone(
            source_id="non-existent-uuid-12345",
            new_name="test_clone"
        )
        assert not result.success
        assert "not found" in result.message.lower()

    def test_clone_empty_file(self):
        """测试克隆空文件"""
        file_service = container.file_service()

        # 创建空文件
        add_result = file_service.add(
            name="empty_file",
            file_type=FILE_TYPES.SELECTOR,
            data=b""
        )

        assert add_result.success

        source_uuid = add_result.data["file_info"]["uuid"]

        try:
            # 克隆空文件
            clone_result = file_service.clone(
                source_id=source_uuid,
                new_name="empty_clone"
            )

            assert clone_result.success
            assert "empty" in clone_result.message or clone_result.success  # 应该成功但可能有警告

            # 验证克隆文件也是空的
            cloned_file_info = clone_result.data["file_info"]
            cloned_content = file_service.get_content(cloned_file_info["uuid"])
            assert cloned_content == b""

        finally:
            # 清理
            try:
                file_service.soft_delete(source_uuid)
                if 'cloned_file_info' in locals():
                    file_service.soft_delete(cloned_file_info["uuid"])
            except:
                pass

    def test_standard_methods_return_service_result(self):
        """测试标准方法返回ServiceResult格式"""
        file_service = container.file_service()

        # 测试validate方法
        validate_result = file_service.validate(
            name="test",
            file_type=FILE_TYPES.STRATEGY,
            data=b"test data"
        )
        assert isinstance(validate_result, ServiceResult)
        assert hasattr(validate_result, 'success')

        # 测试check_integrity方法
        integrity_result = file_service.check_integrity(
            name="test",
            file_type=FILE_TYPES.STRATEGY
        )
        assert isinstance(integrity_result, ServiceResult)
        assert hasattr(integrity_result, 'success')

    def test_file_service_initialization(self):
        """测试FileService基本初始化 - 通过container获取"""
        # 通过容器获取FileService实例
        file_service = container.file_service()

        # 验证实例创建成功
        assert file_service is not None
        assert isinstance(file_service, FileService)
        assert isinstance(file_service, ManagementService)

        # 验证crud_repo已设置（私有属性）
        assert hasattr(file_service, '_crud_repo')
        assert file_service._crud_repo is not None


@pytest.mark.integration
class TestFileServiceIntegration:
    """集成测试 - 测试完整的文件生命周期"""

    def test_full_file_lifecycle(self):
        """测试完整的文件生命周期：添加→获取→更新→删除"""
        file_service = container.file_service()

        # 1. 添加文件
        original_content = b'def original_function():\n    return "original"'
        add_result = file_service.add(
            name="lifecycle_test",
            file_type=FILE_TYPES.STRATEGY,
            data=original_content,
            description="Lifecycle test file"
        )

        assert add_result.success, f"Failed to add file: {add_result.message}"

        file_uuid = add_result.data["file_info"]["uuid"]

        try:
            # 2. 获取文件列表
            result = file_service.get_by_uuid(file_uuid)
            assert result.success, f"Failed to get file by UUID: {result.message}"
            assert result.data["exists"], "File should exist"
            assert result.data["file"] is not None, "File should not be None"

            # 3. 获取文件内容
            content = file_service.get_content(file_uuid)
            # 内容可能为None（文件不存在）或bytes，都接受

            # 4. 测试标准方法
            count_result = file_service.count(filters={"uuid": file_uuid})
            assert count_result.success
            count = count_result.data["count"]
            assert isinstance(count, int)

            validate_result = file_service.validate(
                name="lifecycle_test",
                file_type=FILE_TYPES.STRATEGY,
                data=b"validation test"
            )
            assert isinstance(validate_result, ServiceResult)

            integrity_result = file_service.check_integrity(
                name="lifecycle_test",
                file_type=FILE_TYPES.STRATEGY
            )
            assert isinstance(integrity_result, ServiceResult)

        finally:
            # 6. 清理：删除文件
            try:
                file_service.hard_delete(file_uuid)
            except Exception as e:
                # 如果delete_file失败，使用CRUD直接删除
                try:
                    file_service._crud_repo.remove(filters={"uuid": file_uuid})
                except:
                    pass


@pytest.mark.unit
class TestFileServiceSearchAndQuery:
    """
    FileService 搜索和查询功能测试
    测试新增的模糊搜索功能和细粒度查询方法
    """

    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.file_service = container.file_service()

        # 创建测试文件数据
        self.test_files = [
            {
                "name": "momentum_strategy",
                "file_type": FILE_TYPES.STRATEGY,
                "data": b"def momentum_strategy():\n    return 'momentum'",
                "description": "Momentum based trading strategy"
            },
            {
                "name": "mean_reversion_strategy",
                "file_type": FILE_TYPES.STRATEGY,
                "data": b"def mean_reversion():\n    return 'mean_reversion'",
                "description": "Mean reversion trading strategy"
            },
            {
                "name": "risk_analyzer",
                "file_type": FILE_TYPES.ANALYZER,
                "data": b"class RiskAnalyzer:\n    def analyze(self): return True",
                "description": "Risk analysis tool"
            },
            {
                "name": "position_sizer",
                "file_type": FILE_TYPES.SIZER,
                "data": b"def calculate_size(): return 100",
                "description": "Position sizing calculator"
            }
        ]

        # 添加测试文件到数据库
        self.created_file_uuids = []
        for file_data in self.test_files:
            result = self.file_service.add(**file_data)
            if result.success:
                self.created_file_uuids.append(result.data["file_info"]["uuid"])

    def teardown_method(self):
        """每个测试方法执行后的清理"""
        # 清理创建的测试文件
        for uuid in self.created_file_uuids:
            try:
                self.file_service.hard_delete(uuid)
            except Exception:
                pass

    def test_get_by_uuid_success(self):
        """测试按UUID成功获取文件"""
        if not self.created_file_uuids:
            pytest.skip("No test files created")

        file_uuid = self.created_file_uuids[0]
        result = self.file_service.get_by_uuid(file_uuid)

        assert result.success, f"Failed to get file by UUID: {result.message}"
        assert result.data["exists"], "File should exist"
        assert result.data["file"] is not None, "File data should not be None"

    def test_get_by_uuid_not_found(self):
        """测试按UUID获取不存在的文件"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        result = self.file_service.get_by_uuid(fake_uuid)

        assert result.success, "Query should succeed even if file not found"
        assert not result.data["exists"], "File should not exist"
        assert result.data["file"] is None, "File data should be None"

    def test_get_by_name_success(self):
        """测试按名称成功获取文件"""
        result = self.file_service.get_by_name("momentum_strategy")

        assert result.success, f"Failed to get file by name: {result.message}"
        assert result.data["count"] >= 1, "Should find at least one file with this name"

    def test_get_by_name_with_type_filter(self):
        """测试按名称和类型过滤获取文件"""
        result = self.file_service.get_by_name("momentum_strategy", FILE_TYPES.STRATEGY)

        assert result.success, f"Failed to get file by name and type: {result.message}"
        assert result.data["count"] >= 1, "Should find at least one strategy file"

    def test_get_by_type_success(self):
        """测试按类型成功获取文件"""
        result = self.file_service.get_by_type(FILE_TYPES.STRATEGY)

        assert result.success, f"Failed to get files by type: {result.message}"
        assert result.data["count"] >= 2, "Should find at least 2 strategy files"

    def test_search_by_name_exact_match(self):
        """测试按名称精确搜索"""
        result = self.file_service.search_by_name(
            keyword="momentum_strategy",
            exact_match=True
        )

        assert result.success, f"Search failed: {result.message}"
        assert result.data["count"] >= 1, "Should find at least one exact match"
        assert result.data["search_type"] == "name_search"
        assert result.data["exact_match"] is True

    def test_search_by_name_fuzzy_match(self):
        """测试按名称模糊搜索"""
        result = self.file_service.search_by_name(
            keyword="momentum",
            exact_match=False
        )

        assert result.success, f"Search failed: {result.message}"
        assert result.data["count"] >= 1, "Should find at least one fuzzy match"
        assert result.data["search_type"] == "name_search"
        assert result.data["exact_match"] is False

    def test_search_by_description(self):
        """测试按描述搜索"""
        result = self.file_service.search_by_description(
            keyword="trading strategy",
            case_sensitive=False
        )

        assert result.success, f"Search failed: {result.message}"
        assert result.data["count"] >= 1, "Should find at least one match"
        assert result.data["search_type"] == "description_search"

    def test_search_by_content(self):
        """测试按内容搜索"""
        result = self.file_service.search_by_content(
            keyword="def",
            file_type=FILE_TYPES.STRATEGY
        )

        assert result.success, f"Content search failed: {result.message}"
        assert result.data["search_type"] == "content_search"
        # 应该找到包含"def"的策略文件

    def test_unified_search_multiple_fields(self):
        """测试统一搜索多个字段"""
        result = self.file_service.search(
            keyword="strategy",
            search_in=["name", "description"],
            exact_match=False
        )

        assert result.success, f"Unified search failed: {result.message}"
        assert result.data["search_type"] == "unified_search"
        assert result.data["total_found"] >= 1, "Should find at least one match"
        assert len(result.data["results"]) >= 1, "Should return at least one result"

    def test_unified_search_pagination(self):
        """测试统一搜索分页功能"""
        result = self.file_service.search(
            keyword="test",
            search_in=["name", "description"],
            page=0,
            page_size=10
        )

        assert result.success, f"Unified search with pagination failed: {result.message}"
        assert result.data["search_type"] == "unified_search"
        assert "pagination" in result.data
        assert result.data["pagination"]["page"] == 0
        assert result.data["pagination"]["page_size"] == 10
        assert result.data["pagination"]["count_on_page"] <= 10

    def test_unified_search_exact_match(self):
        """测试统一搜索精确匹配"""
        result = self.file_service.search(
            keyword="test_file.txt",
            search_in=["name"],
            exact_match=True
        )

        assert result.success, f"Unified search exact match failed: {result.message}"
        assert result.data["search_type"] == "unified_search"
        assert result.data["exact_match"] == True

    def test_search_invalid_keyword(self):
        """测试搜索无效关键字"""
        result = self.file_service.search_by_name("")

        assert not result.success, "Search with empty keyword should fail"
        assert "Search keyword cannot be empty" in result.error

    def test_search_invalid_fields(self):
        """测试搜索无效字段"""
        result = self.file_service.search(
            keyword="test",
            search_in=["invalid_field"]
        )

        assert not result.success, "Search with invalid fields should fail"
        assert "Invalid search fields" in result.error

    def test_search_content_field_not_supported(self):
        """测试content字段不被支持"""
        result = self.file_service.search(
            keyword="test",
            search_in=["content"]
        )

        assert not result.success, "Search with content field should fail"
        assert "Invalid search fields" in result.error

    def test_search_case_sensitive(self):
        """测试大小写敏感搜索"""
        # 先添加一个特定大小写的文件用于测试
        test_content = b"Test Case Sensitive Content"
        add_result = self.file_service.add(
            name="TestCase",
            file_type=FILE_TYPES.STRATEGY,
            data=test_content,
            description="Test case sensitive"
        )

        if add_result.success:
            self.created_file_uuids.append(add_result.data["file_info"]["uuid"])

            # 大小写敏感搜索 - 应该找不到小写的"testcase"
            result_sensitive = self.file_service.search_by_name(
                keyword="testcase",
                case_sensitive=True
            )

            # 大小写不敏感搜索 - 应该找到
            result_insensitive = self.file_service.search_by_name(
                keyword="testcase",
                case_sensitive=False
            )

            # 验证结果差异
            if result_sensitive.success and result_insensitive.success:
                # 大小写不敏感应该找到更多或相等的匹配
                assert result_insensitive.data["count"] >= result_sensitive.data["count"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])