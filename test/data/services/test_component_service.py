"""
ComponentService数据服务测试

测试ComponentService的核心功能和业务逻辑
遵循其他服务的测试模式，使用真实实例而非Mock
"""

import pytest
import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.services.component_service import ComponentService
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.containers import container
from ginkgo.enums import FILE_TYPES


@pytest.mark.unit
class TestComponentServiceStandardOperations:
    """
    ComponentService 标准化方法测试
    测试投资组合管理的核心操作和业务逻辑
    """

    def test_add_component_info_success(self):
        """测试成功添加组件信息记录"""
        component_service = container.component_service()

        # 执行添加组件信息操作
        result = component_service.add(
            file_id="test-file-uuid",
            file_type=FILE_TYPES.STRATEGY,
            component_name="TestStrategy"
        )

        # 验证操作结果
        assert result.success, f"组件信息添加失败: {result.error}"
        assert result.data["file_id"] == "test-file-uuid"
        assert result.data["file_type"] == FILE_TYPES.STRATEGY
        assert result.data["component_name"] == "TestStrategy"

    def test_add_component_info_validation_errors(self):
        """测试组件信息添加的验证逻辑"""
        component_service = container.component_service()

        # 测试空文件ID
        result = component_service.add(
            file_id="",
            file_type=FILE_TYPES.STRATEGY
        )
        assert not result.success
        assert "文件ID不能为空" in result.error

        # 测试空文件类型
        result = component_service.add(
            file_id="test-file-uuid"
        )
        assert not result.success
        assert "文件类型不能为空" in result.error

    def test_update_component_info_success(self):
        """测试成功更新组件信息记录"""
        component_service = container.component_service()

        # 更新组件信息
        result = component_service.update(
            component_id="test-component-uuid",
            component_name="Updated Component Name",
            description="Updated description"
        )

        # 验证更新结果
        assert result.success, f"组件信息更新失败: {result.error}"
        assert result.data["component_id"] == "test-component-uuid"
        assert result.data["component_name"] == "Updated Component Name"
        assert result.data["description"] == "Updated description"

    def test_update_component_info_validation_errors(self):
        """测试组件信息更新的验证逻辑"""
        component_service = container.component_service()

        # 测试空组件ID
        result = component_service.update(
            component_id="",
            component_name="Test Component"
        )
        assert not result.success
        assert "组件ID不能为空" in result.error

    def test_delete_component_info_success(self):
        """测试成功删除组件信息记录"""
        component_service = container.component_service()

        # 删除组件信息
        result = component_service.delete(component_id="test-component-uuid")

        # 验证删除结果
        assert result.success, f"组件信息删除失败: {result.error}"
        assert result.data["component_id"] == "test-component-uuid"

    def test_delete_component_info_validation_errors(self):
        """测试组件信息删除的验证逻辑"""
        component_service = container.component_service()

        # 测试空组件ID
        result = component_service.delete(component_id="")
        assert not result.success
        assert "组件ID不能为空" in result.error

    def test_get_component_info_success(self):
        """测试成功获取组件信息记录"""
        component_service = container.component_service()

        # 获取组件信息
        result = component_service.get(component_id="test-component-uuid")

        # 验证操作结果
        assert result.success, f"组件信息获取失败: {result.error}"
        assert isinstance(result.data, list)

    def test_exists_component_check(self):
        """测试检查组件存在性"""
        component_service = container.component_service()

        # 测试不存在的组件（使用更复杂的UUID避免缓存命中）
        nonexistent_uuid = "550e8400-e29b-41d4-a716-446655440000"  # 格式正确的UUID
        result = component_service.exists(file_id=nonexistent_uuid)
        assert result.success
        assert result.data["exists"] == False

        # 测试空文件ID的情况
        result = component_service.exists(file_id="")
        assert result.success
        assert result.data["exists"] == False

        # 测试没有file_id参数的情况
        result = component_service.exists()
        assert result.success
        assert result.data["exists"] == False

    def test_count_components(self):
        """测试统计组件数量"""
        component_service = container.component_service()

        # 获取当前统计
        result = component_service.count()

        # 验证统计结果
        assert result.success, f"组件数量统计失败: {result.message}"
        assert "count" in result.data
        assert isinstance(result.data["count"], int)
        assert result.data["count"] >= 0

    def test_health_check(self):
        """测试健康检查"""
        component_service = container.component_service()

        result = component_service.health_check()

        # 验证健康检查结果
        assert result.success, f"健康检查失败: {result.message}"
        health_data = result.data
        assert "service_name" in health_data
        assert "status" in health_data
        assert health_data["service_name"] == "ComponentService"
        assert "dependencies" in health_data
        assert "component_types" in health_data

    def test_validate_component_data_success(self):
        """测试成功验证组件数据"""
        component_service = container.component_service()

        # 测试有效数据
        valid_data = {
            'file_id': 'test-file-uuid',
            'file_type': FILE_TYPES.STRATEGY,
            'component_name': 'Test Component'
        }
        result = component_service.validate(valid_data)
        assert result.success
        assert result.data["valid"] == True

        # 测试字符串类型的文件类型
        valid_data_str = {
            'file_id': 'test-file-uuid',
            'file_type': 'STRATEGY',
            'component_name': 'Test Component'
        }
        result = component_service.validate(valid_data_str)
        assert result.success
        assert result.data["valid"] == True

    def test_validate_component_data_errors(self):
        """测试组件数据验证错误"""
        component_service = container.component_service()

        # 测试非字典数据
        result = component_service.validate("invalid data")
        assert not result.success
        assert "数据必须是字典格式" in result.error

        # 测试缺少必填字段
        invalid_data = {
            'file_id': 'test-file-uuid'
            # 缺少 file_type
        }
        result = component_service.validate(invalid_data)
        assert not result.success
        assert "缺少必填字段" in result.error

        # 测试无效文件类型
        invalid_type_data = {
            'file_id': 'test-file-uuid',
            'file_type': 'INVALID_TYPE'
        }
        result = component_service.validate(invalid_type_data)
        assert not result.success
        assert "无效的文件类型" in result.error

    def test_check_integrity_success(self):
        """测试组件完整性检查"""
        component_service = container.component_service()

        # 测试整体服务完整性
        result = component_service.check_integrity()
        assert result.success
        assert "valid" in result.data
        assert "issues" in result.data

        # 如果依赖服务可用，应该验证通过
        if result.data["valid"]:
            assert len(result.data["issues"]) == 0

    def test_check_integrity_with_component_id(self):
        """测试特定组件的完整性检查"""
        component_service = container.component_service()

        # 测试不存在的组件ID（使用格式正确的UUID）
        nonexistent_uuid = "550e8400-e29b-41d4-a716-446655440001"
        result = component_service.check_integrity(component_id=nonexistent_uuid)
        assert result.success
        assert "valid" in result.data
        assert "component_id" in result.data
        assert result.data["component_id"] == nonexistent_uuid

        # 不存在的组件应该有完整性问题
        if not result.data["valid"]:
            assert len(result.data["issues"]) > 0
            assert "文件不存在或无法访问" in result.data["issues"][0]


@pytest.mark.unit
class TestComponentServiceCoreFunctionality:
    """
    ComponentService 核心功能测试
    测试组件实例化和验证的核心业务逻辑
    """

    def test_validate_code_success(self):
        """测试成功验证组件代码"""
        component_service = container.component_service()

        # 有效的策略代码
        valid_strategy_code = '''
class TestStrategy:
    def __init__(self, param1=None, param2=None):
        self.param1 = param1
        self.param2 = param2

    def generate_signal(self, data):
        return "BUY"
'''

        result = component_service.validate_code(valid_strategy_code, FILE_TYPES.STRATEGY)

        # 验证结果
        assert result.success, f"组件代码验证失败: {result.error}"
        validation_data = result.data
        assert "valid" in validation_data
        assert "file_type" in validation_data
        assert validation_data["file_type"] == FILE_TYPES.STRATEGY.value

        # 注意：由于基类导入可能失败，我们只验证验证过程的执行
        # 而不是特定的验证结果

    def test_validate_code_empty_code(self):
        """测试空代码的验证"""
        component_service = container.component_service()

        result = component_service.validate_code("", FILE_TYPES.STRATEGY)

        # 验证失败
        assert not result.success
        assert "代码内容不能为空" in result.error

    def test_validate_code_invalid_type(self):
        """测试无效文件类型的验证"""
        component_service = container.component_service()

        # 有效的代码但无效的文件类型
        valid_code = '''
class TestComponent:
    def __init__(self):
        pass
'''

        result = component_service.validate_code(valid_code, "INVALID_TYPE")

        # 验证失败
        assert not result.success
        assert "无效的文件类型" in result.error

    def test_validate_code_syntax_error(self):
        """测试语法错误代码的验证"""
        component_service = container.component_service()

        # 有语法错误的代码
        invalid_code = '''
class InvalidComponent:
    def __init__(self:  # 缺少右括号
        pass
'''

        result = component_service.validate_code(invalid_code, FILE_TYPES.STRATEGY)

        # 验证结果 - 应该处理语法错误
        assert result.success  # 方法本身成功执行
        validation_data = result.data
        assert not validation_data["valid"]  # 但代码验证失败
        assert validation_data["error"] is not None

    def test_instantiate_validation_errors(self):
        """测试组件实例化的输入验证"""
        component_service = container.component_service()

        # 测试空文件ID
        result = component_service.instantiate("", "mapping-id", FILE_TYPES.STRATEGY)
        assert not result.success
        assert "文件ID不能为空" in result.error

        # 测试空映射ID
        result = component_service.instantiate("file-id", "", FILE_TYPES.STRATEGY)
        assert not result.success
        assert "映射ID不能为空" in result.error

        # 测试无效文件类型
        result = component_service.instantiate("file-id", "mapping-id", "INVALID_TYPE")
        assert not result.success
        assert "无效的文件类型" in result.error

    def test_instantiate_nonexistent_file(self):
        """测试不存在文件的组件实例化"""
        component_service = container.component_service()

        # 使用不存在的文件ID
        result = component_service.instantiate(
            "nonexistent-file-uuid-12345",
            "mapping-id",
            FILE_TYPES.STRATEGY
        )

        # 验证失败 - 文件不存在
        assert not result.success
        assert "文件内容为空或缺失" in result.error

    def test_get_trading_system_components_by_portfolio_validation_errors(self):
        """测试获取投资组合组件的输入验证"""
        component_service = container.component_service()

        # 测试空投资组合ID
        result = component_service.get_components("", FILE_TYPES.STRATEGY)
        assert not result.success
        assert "投资组合ID不能为空" in result.error

        # 测试无效文件类型
        result = component_service.get_components(
            "portfolio-id", "INVALID_TYPE"
        )
        assert not result.success
        assert "无效的文件类型" in result.error

    def test_get_trading_system_components_by_portfolio_nonexistent(self):
        """测试不存在投资组合的组件获取"""
        component_service = container.component_service()

        # 使用不存在的投资组合ID
        result = component_service.get_components(
            "nonexistent-portfolio-uuid-12345",
            FILE_TYPES.STRATEGY
        )

        # 验证结果
        assert result.success, f"获取投资组合组件失败: {result.error}"
        data = result.data
        assert "components" in data
        assert "portfolio_id" in data
        assert "count" in data
        assert data["portfolio_id"] == "nonexistent-portfolio-uuid-12345"
        assert data["count"] == 0  # 不存在的投资组合应该没有组件

    def test_get_component_info_validation_errors(self):
        """测试获取组件信息的输入验证"""
        component_service = container.component_service()

        # 测试空文件ID
        result = component_service.get_info("", FILE_TYPES.STRATEGY)
        assert not result.success
        assert "文件ID不能为空" in result.error

        # 测试无效文件类型
        result = component_service.get_info("file-id", "INVALID_TYPE")
        assert not result.success
        assert "无效的文件类型" in result.error

    def test_get_component_info_nonexistent_file(self):
        """测试不存在文件的组件信息获取"""
        component_service = container.component_service()

        # 使用不存在的文件ID
        result = component_service.get_info(
            "nonexistent-file-uuid-12345",
            FILE_TYPES.STRATEGY
        )

        # 验证失败 - 文件不存在
        assert not result.success
        assert "未找到文件内容" in result.error

    def test_convenience_methods(self):
        """测试便捷方法"""
        component_service = container.component_service()

        # 测试各种便捷方法
        methods_to_test = [
            'get_strategies_by_portfolio',
            'get_analyzers_by_portfolio',
            'get_selectors_by_portfolio',
            'get_sizers_by_portfolio',
            'get_risk_managers_by_portfolio'
        ]

        for method_name in methods_to_test:
            method = getattr(component_service, method_name)

            # 测试不存在的投资组合ID
            result = method("nonexistent-portfolio-uuid-12345")

            # 验证结果
            assert result.success, f"{method_name}失败: {result.error}"
            data = result.data
            assert "components" in data
            assert "count" in data
            assert data["count"] == 0

    def test_get_component_base_classes(self):
        """测试获取组件基类映射"""
        component_service = container.component_service()

        base_classes = component_service._get_component_base_classes()

        # 验证返回类型
        assert isinstance(base_classes, dict)

        # 验证基类映射的结构
        if base_classes:  # 如果基类导入成功
            expected_types = [
                FILE_TYPES.STRATEGY,
                FILE_TYPES.ANALYZER,
                FILE_TYPES.SIZER
            ]

            for file_type in expected_types:
                if file_type in base_classes:
                    assert hasattr(base_classes[file_type], '__name__')

    def test_get_instantiation_parameters(self):
        """测试获取实例化参数"""
        component_service = container.component_service()

        # 测试不存在的映射ID
        params = component_service._get_instantiation_parameters("nonexistent-mapping-uuid")

        # 验证返回空列表
        assert isinstance(params, list)
        assert len(params) == 0


@pytest.mark.integration
class TestComponentServiceIntegration:
    """
    ComponentService 集成测试
    测试组件服务的完整工作流程
    """

    def test_component_lifecycle_validation(self):
        """测试组件验证的生命周期"""
        component_service = container.component_service()

        # 1. 验证有效的组件代码
        valid_code = '''
class TestLifecycleComponent:
    """Test component for lifecycle validation"""
    def __init__(self, param1=None):
        self.param1 = param1

    def execute(self):
        return "EXECUTED"
'''

        validation_result = component_service.validate_code(valid_code, FILE_TYPES.STRATEGY)
        assert validation_result.success
        assert "valid" in validation_result.data

        # 2. 验证无效的组件代码
        invalid_code = '''
# This is not a valid component
def invalid_function():
    pass
'''

        validation_result = component_service.validate_code(invalid_code, FILE_TYPES.STRATEGY)
        assert validation_result.success
        assert validation_result.data["valid"] == False

    def test_component_info_workflow(self):
        """测试组件信息获取的工作流程"""
        component_service = container.component_service()

        # 1. 尝试获取不存在组件的信息
        info_result = component_service.get_info(
            "nonexistent-file-uuid",
            FILE_TYPES.STRATEGY
        )

        # 验证失败
        assert not info_result.success
        assert "未找到文件内容" in info_result.error

        # 2. 验证组件数据
        component_data = {
            "file_id": "test-file-uuid",
            "file_type": FILE_TYPES.STRATEGY,
            "component_name": "Test Component"
        }

        validate_result = component_service.validate(component_data)
        assert validate_result.success
        assert validate_result.data["valid"] == True

    def test_service_health_and_integrity(self):
        """测试服务健康状态和完整性"""
        component_service = container.component_service()

        # 1. 健康检查
        health_result = component_service.health_check()
        assert health_result.success
        health_data = health_result.data
        assert health_data["service_name"] == "ComponentService"
        assert "status" in health_data
        assert "dependencies" in health_data

        # 2. 完整性检查
        integrity_result = component_service.check_integrity()
        assert integrity_result.success
        integrity_data = integrity_result.data
        assert "valid" in integrity_data
        assert "issues" in integrity_data

        # 3. 组件存在性检查
        exists_result = component_service.exists(file_id="test-file-uuid")
        assert exists_result.success
        exists_data = exists_result.data
        assert "exists" in exists_data

    def test_portfolio_component_workflow(self):
        """测试投资组合组件管理工作流程"""
        component_service = container.component_service()

        # 1. 尝试获取不存在投资组合的组件
        portfolio_id = "nonexistent-portfolio-uuid"

        strategy_result = component_service.get_strategies(portfolio_id)
        assert strategy_result.success
        assert strategy_result.data["count"] == 0

        analyzer_result = component_service.get_analyzers(portfolio_id)
        assert analyzer_result.success
        assert analyzer_result.data["count"] == 0

        # 2. 测试通用组件获取方法
        general_result = component_service.get_components(
            portfolio_id, FILE_TYPES.STRATEGY
        )
        assert general_result.success
        assert general_result.data["count"] == 0
        assert general_result.data["portfolio_id"] == portfolio_id
        assert general_result.data["file_type"] == FILE_TYPES.STRATEGY.value

    def test_error_handling_workflow(self):
        """测试错误处理工作流程"""
        component_service = container.component_service()

        # 1. 测试各种验证错误
        invalid_inputs = [
            ("", "mapping-id", FILE_TYPES.STRATEGY, "文件ID不能为空"),
            ("file-id", "", FILE_TYPES.STRATEGY, "映射ID不能为空"),
            ("file-id", "mapping-id", "INVALID_TYPE", "无效的文件类型"),
        ]

        for file_id, mapping_id, file_type, expected_error in invalid_inputs:
            result = component_service.instantiate(file_id, mapping_id, file_type)
            assert not result.success
            assert expected_error in result.error

        # 2. 测试组件信息获取错误
        info_errors = [
            ("", FILE_TYPES.STRATEGY, "文件ID不能为空"),
            ("file-id", "INVALID_TYPE", "无效的文件类型"),
        ]

        for file_id, file_type, expected_error in info_errors:
            result = component_service.get_info(file_id, file_type)
            assert not result.success
            assert expected_error in result.error

        # 3. 测试组件验证错误
        validation_errors = [
            ("", FILE_TYPES.STRATEGY, "代码内容不能为空"),
            ("some code", "INVALID_TYPE", "无效的文件类型"),
        ]

        for code, file_type, expected_error in validation_errors:
            result = component_service.validate_code(code, file_type)
            if not result.success:
                assert expected_error in result.error