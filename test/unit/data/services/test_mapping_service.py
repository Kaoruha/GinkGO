#!/usr/bin/env python3
"""
MappingService 单元测试

测试MappingService的所有API功能，包括：
1. Engine-Portfolio映射管理
2. Portfolio-File组件绑定
3. 参数管理
4. 清理和维护功能
5. 工具方法
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# 设置路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../../src'))

from ginkgo.data.services.mapping_service import MappingService
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.enums import FILE_TYPES


class TestMappingService:
    """MappingService单元测试类"""

    @pytest.fixture
    def mock_cruds(self):
        """模拟CRUD依赖"""
        return {
            'engine_portfolio_mapping_crud': Mock(),
            'portfolio_file_mapping_crud': Mock(),
            'engine_handler_mapping_crud': Mock(),
            'param_crud': Mock()
        }

    @pytest.fixture
    def mapping_service(self, mock_cruds):
        """创建MappingService实例"""
        return MappingService(**mock_cruds)

    def test_init(self, mock_cruds):
        """测试初始化"""
        service = MappingService(**mock_cruds)

        # 验证CRUD实例正确存储
        assert service._engine_portfolio_mapping_crud == mock_cruds['engine_portfolio_mapping_crud']
        assert service._portfolio_file_mapping_crud == mock_cruds['portfolio_file_mapping_crud']
        assert service._engine_handler_mapping_crud == mock_cruds['engine_handler_mapping_crud']
        assert service._param_crud == mock_cruds['param_crud']

    @pytest.mark.tdd
    class TestEnginePortfolioMapping:
        """测试Engine-Portfolio映射管理"""

        def test_create_engine_portfolio_mapping_success(self, mapping_service, mock_cruds):
            """测试成功创建Engine-Portfolio映射"""
            # 设置模拟
            mock_mapping = Mock()
            mock_mapping.uuid = "mapping_123"
            mock_mapping.engine_uuid = "engine_123"
            mock_mapping.portfolio_uuid = "portfolio_456"

            mock_cruds['engine_portfolio_mapping_crud'].add_batch.return_value = [mock_mapping]
            mock_cruds['engine_portfolio_mapping_crud'].find.return_value = []

            # 执行
            result = mapping_service.create_engine_portfolio_mapping(
                engine_uuid="engine_123",
                portfolio_uuid="portfolio_456",
                engine_name="test_engine",
                portfolio_name="test_portfolio"
            )

            # 验证
            assert result.success
            assert result.data.uuid == "mapping_123"
            mock_cruds['engine_portfolio_mapping_crud'].add_batch.assert_called_once()

        def test_create_engine_portfolio_mapping_failure(self, mapping_service, mock_cruds):
            """测试创建Engine-Portfolio映射失败"""
            # 设置模拟 - 添加失败
            mock_cruds['engine_portfolio_mapping_crud'].add_batch.side_effect = Exception("Database error")

            # 执行
            result = mapping_service.create_engine_portfolio_mapping(
                engine_uuid="engine_123",
                portfolio_uuid="portfolio_456"
            )

            # 验证
            assert not result.success
            assert "Database error" in result.error

        def test_get_engine_portfolio_mapping_by_engine(self, mapping_service, mock_cruds):
            """测试根据Engine UUID获取映射"""
            # 设置模拟数据
            mock_mapping = Mock()
            mock_mapping.uuid = "mapping_123"
            mock_mapping.engine_uuid = "engine_123"
            mock_mapping.portfolio_uuid = "portfolio_456"

            mock_cruds['engine_portfolio_mapping_crud'].find.return_value = [mock_mapping]

            # 执行
            result = mapping_service.get_engine_portfolio_mapping(engine_uuid="engine_123")

            # 验证
            assert result.success
            assert len(result.data) == 1
            assert result.data[0].engine_uuid == "engine_123"
            mock_cruds['engine_portfolio_mapping_crud'].find.assert_called_once_with(
                filters={'engine_id': 'engine_123'}
            )

        def test_get_engine_portfolio_mapping_by_portfolio(self, mapping_service, mock_cruds):
            """测试根据Portfolio UUID获取映射"""
            # 设置模拟数据
            mock_mapping = Mock()
            mock_mapping.uuid = "mapping_123"
            mock_mapping.engine_uuid = "engine_123"
            mock_mapping.portfolio_uuid = "portfolio_456"

            mock_cruds['engine_portfolio_mapping_crud'].find.return_value = [mock_mapping]

            # 执行
            result = mapping_service.get_engine_portfolio_mapping(portfolio_uuid="portfolio_456")

            # 验证
            assert result.success
            assert len(result.data) == 1
            assert result.data[0].portfolio_uuid == "portfolio_456"
            mock_cruds['engine_portfolio_mapping_crud'].find.assert_called_once_with(
                filters={'portfolio_id': 'portfolio_456'}
            )

    @pytest.mark.tdd
    class TestPortfolioFileBinding:
        """测试Portfolio-File组件绑定"""

        def test_create_portfolio_file_binding_success(self, mapping_service, mock_cruds):
            """测试成功创建Portfolio-File绑定"""
            # 设置模拟
            mock_cruds['portfolio_file_mapping_crud'].add.return_value = True
            mock_cruds['portfolio_file_mapping_crud'].find.return_value = []

            # 执行
            result = mapping_service.create_portfolio_file_binding(
                portfolio_uuid="portfolio_123",
                file_uuid="file_456",
                file_name="fixed_selector",
                file_type=FILE_TYPES.SELECTOR
            )

            # 验证
            assert result.success
            assert result.data.portfolio_uuid == "portfolio_123"
            assert result.data.file_uuid == "file_456"
            assert result.data.file_name == "fixed_selector"
            assert result.data.file_type == FILE_TYPES.SELECTOR
            mock_cruds['portfolio_file_mapping_crud'].add.assert_called_once()

        def test_get_portfolio_file_bindings_all(self, mapping_service, mock_cruds):
            """测试获取Portfolio的所有文件绑定"""
            # 设置模拟数据
            mock_binding1 = Mock()
            mock_binding1.uuid = "binding_1"
            mock_binding1.file_uuid = "file_1"
            mock_binding1.type = FILE_TYPES.SELECTOR

            mock_binding2 = Mock()
            mock_binding2.uuid = "binding_2"
            mock_binding2.file_uuid = "file_2"
            mock_binding2.type = FILE_TYPES.STRATEGY

            mock_cruds['portfolio_file_mapping_crud'].find.return_value = [mock_binding1, mock_binding2]

            # 执行
            result = mapping_service.get_portfolio_file_bindings(portfolio_uuid="portfolio_123")

            # 验证
            assert result.success
            assert len(result.data) == 2
            mock_cruds['portfolio_file_mapping_crud'].find.assert_called_once_with(
                filters={'portfolio_uuid': 'portfolio_123'}
            )

        def test_get_portfolio_file_bindings_by_type(self, mapping_service, mock_cruds):
            """测试按类型获取Portfolio文件绑定"""
            # 设置模拟数据
            mock_binding = Mock()
            mock_binding.uuid = "binding_1"
            mock_binding.file_uuid = "file_1"
            mock_binding.type = FILE_TYPES.SELECTOR

            mock_cruds['portfolio_file_mapping_crud'].find.return_value = [mock_binding]

            # 执行
            result = mapping_service.get_portfolio_file_bindings(
                portfolio_uuid="portfolio_123",
                file_type=FILE_TYPES.SELECTOR
            )

            # 验证
            assert result.success
            assert len(result.data) == 1
            assert result.data[0].type == FILE_TYPES.SELECTOR
            mock_cruds['portfolio_file_mapping_crud'].find.assert_called_once_with(
                filters={'portfolio_uuid': 'portfolio_123', 'type': FILE_TYPES.SELECTOR}
            )

        def test_create_preset_bindings_success(self, mapping_service, mock_cruds):
            """测试批量创建预设绑定"""
            # 设置模拟
            mock_cruds['portfolio_file_mapping_crud'].add.return_value = True
            mock_cruds['portfolio_file_mapping_crud'].find.return_value = []

            # 设置绑定规则
            binding_rules = {
                "selectors": [
                    {"name": "fixed_selector"}
                ],
                "strategies": [
                    {"name": "random_signal"}
                ]
            }

            # 执行
            result = mapping_service.create_preset_bindings(
                engine_uuid="engine_123",
                portfolio_uuid="portfolio_456",
                binding_rules=binding_rules
            )

            # 验证
            assert result.success
            assert result.data['bindings_created'] >= 0
            assert isinstance(result.data['binding_details'], list)

    @pytest.mark.tdd
    class TestParameterManagement:
        """测试参数管理"""

        def test_create_component_parameters_success(self, mapping_service, mock_cruds):
            """测试成功创建组件参数"""
            # 设置模拟
            mock_cruds['param_crud'].add_all.return_value = True

            # 设置参数
            parameters = {
                0: "default_selector",
                1: '["000001.SZ", "000002.SZ"]'
            }

            # 执行
            result = mapping_service.create_component_parameters(
                mapping_uuid="mapping_123",
                file_uuid="file_456",
                parameters=parameters
            )

            # 验证
            assert result.success
            assert result.data['params_created'] == 2
            mock_cruds['param_crud'].add_all.assert_called_once()

        def test_create_component_parameters_empty(self, mapping_service, mock_cruds):
            """测试创建空参数"""
            # 设置模拟
            mock_cruds['param_crud'].add_all.return_value = True

            # 空参数
            parameters = {}

            # 执行
            result = mapping_service.create_component_parameters(
                mapping_uuid="mapping_123",
                file_uuid="file_456",
                parameters=parameters
            )

            # 验证
            assert result.success
            assert result.data['params_created'] == 0

        def test_get_portfolio_parameters_success(self, mapping_service, mock_cruds):
            """测试获取Portfolio参数"""
            # 设置模拟数据
            mock_param1 = Mock()
            mock_param1.mapping_uuid = "mapping_1"
            mock_param1.index = 0
            mock_param1.value = "param_value_1"

            mock_param2 = Mock()
            mock_param2.mapping_uuid = "mapping_2"
            mock_param2.index = 1
            mock_param2.value = "param_value_2"

            mock_cruds['param_crud'].find.return_value = [mock_param1, mock_param2]

            # 执行
            result = mapping_service.get_portfolio_parameters(portfolio_uuid="portfolio_123")

            # 验证
            assert result.success
            assert len(result.data) == 2
            mock_cruds['param_crud'].find.assert_called_once()

    @pytest.mark.tdd
    class TestCleanupOperations:
        """测试清理操作"""

        def test_cleanup_orphaned_mappings_success(self, mapping_service, mock_cruds):
            """测试清理孤立映射成功"""
            # 设置模拟 - 这里需要模拟SQLAlchemy text查询
            mock_cruds['engine_portfolio_mapping_crud'].execute_query.return_value = 10

            # 执行
            result = mapping_service.cleanup_orphaned_mappings()

            # 验证
            assert result.success
            assert "清理了10个孤立的映射关系" in result.data

        def test_cleanup_by_names_success(self, mapping_service, mock_cruds):
            """测试按名称模式清理成功"""
            # 设置模拟
            mock_cruds['engine_portfolio_mapping_crud'].delete_by_filter.return_value = 2
            mock_cruds['portfolio_file_mapping_crud'].delete_by_filter.return_value = 3
            mock_cruds['param_crud'].delete_by_filter.return_value = 5

            # 执行
            result = mapping_service.cleanup_by_names(name_pattern="test_%")

            # 验证
            assert result.success
            assert "清理了10个映射关系" in result.data

    @pytest.mark.tdd
    class TestUtilityMethods:
        """测试工具方法"""

        def test_get_component_types_for_portfolio(self, mapping_service, mock_cruds):
            """测试获取Portfolio组件类型统计"""
            # 设置模拟数据
            mock_binding1 = Mock()
            mock_binding1.type = FILE_TYPES.SELECTOR

            mock_binding2 = Mock()
            mock_binding2.type = FILE_TYPES.SELECTOR

            mock_binding3 = Mock()
            mock_binding3.type = FILE_TYPES.STRATEGY

            mock_cruds['portfolio_file_mapping_crud'].find.return_value = [
                mock_binding1, mock_binding2, mock_binding3
            ]

            # 执行
            result = mapping_service.get_component_types_for_portfolio("portfolio_123")

            # 验证
            assert isinstance(result, dict)
            # 验证统计结果
            mock_cruds['portfolio_file_mapping_crud'].find.assert_called_once_with(
                filters={'portfolio_uuid': 'portfolio_123'}
            )

        def test_get_component_types_for_portfolio_empty(self, mapping_service, mock_cruds):
            """测试空Portfolio的组件类型统计"""
            # 设置空结果
            mock_cruds['portfolio_file_mapping_crud'].find.return_value = []

            # 执行
            result = mapping_service.get_component_types_for_portfolio("portfolio_empty")

            # 验证
            assert isinstance(result, dict)
            assert len(result) == 0


@pytest.mark.tdd
class TestMappingServiceIntegration:
    """MappingService集成测试"""

    @pytest.fixture
    def real_mapping_service(self):
        """创建真实的MappingService实例（用于集成测试）"""
        # 这里可以从容器获取真实的CRUD实例
        from ginkgo.data.containers import container

        return MappingService(
            engine_portfolio_mapping_crud=container.cruds.engine_portfolio_mapping(),
            portfolio_file_mapping_crud=container.cruds.portfolio_file_mapping(),
            engine_handler_mapping_crud=container.cruds.engine_handler_mapping(),
            param_crud=container.cruds.param()
        )

    def test_service_initialization(self, real_mapping_service):
        """测试服务初始化"""
        assert real_mapping_service is not None
        assert hasattr(real_mapping_service, '_engine_portfolio_mapping_crud')
        assert hasattr(real_mapping_service, '_portfolio_file_mapping_crud')
        assert hasattr(real_mapping_service, '_engine_handler_mapping_crud')
        assert hasattr(real_mapping_service, '_param_crud')

    def test_component_types_conversion(self):
        """测试组件类型转换功能"""
        from ginkgo.enums import FILE_TYPES

        # 测试类型枚举
        assert hasattr(FILE_TYPES, 'SELECTOR')
        assert hasattr(FILE_TYPES, 'STRATEGY')
        assert hasattr(FILE_TYPES, 'SIZER')
        assert hasattr(FILE_TYPES, 'RISKMANAGER')
        assert hasattr(FILE_TYPES, 'ANALYZER')


if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v"])