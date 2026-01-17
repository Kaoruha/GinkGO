"""ControlCommandDTO单元测试"""

import pytest
from datetime import datetime

from ginkgo.interfaces.dtos import ControlCommandDTO


@pytest.mark.tdd
class TestControlCommandDTO:
    """ControlCommandDTO单元测试"""

    def test_init_with_required_fields(self):
        """测试：使用必需字段初始化"""
        dto = ControlCommandDTO(command="bar_snapshot")
        assert dto.command == "bar_snapshot"
        assert dto.params == {}  # 默认空字典
        assert isinstance(dto.timestamp, datetime)
        assert dto.source == "task_timer"  # 默认source

    def test_init_with_params(self):
        """测试：使用参数初始化"""
        dto = ControlCommandDTO(
            command="update_selector",
            params={"portfolio_id": "p001", "timestamp": "2024-01-01T00:00:00"}
        )
        assert dto.command == "update_selector"
        assert dto.params["portfolio_id"] == "p001"
        assert dto.params["timestamp"] == "2024-01-01T00:00:00"

    def test_command_type_checkers(self):
        """测试：命令类型判断方法（is_bar_snapshot/is_update_selector/is_update_data）"""
        # 测试bar_snapshot
        dto_bar = ControlCommandDTO(command=ControlCommandDTO.Commands.BAR_SNAPSHOT)
        assert dto_bar.is_bar_snapshot()
        assert not dto_bar.is_update_selector()
        assert not dto_bar.is_update_data()

        # 测试update_selector
        dto_selector = ControlCommandDTO(command=ControlCommandDTO.Commands.UPDATE_SELECTOR)
        assert dto_selector.is_update_selector()
        assert not dto_selector.is_bar_snapshot()
        assert not dto_selector.is_update_data()

        # 测试update_data
        dto_data = ControlCommandDTO(command=ControlCommandDTO.Commands.UPDATE_DATA)
        assert dto_data.is_update_data()
        assert not dto_data.is_bar_snapshot()
        assert not dto_data.is_update_selector()

    def test_command_type_checkers_with_string(self):
        """测试：命令类型判断方法（使用字符串命令）"""
        dto = ControlCommandDTO(command="bar_snapshot")
        assert dto.is_bar_snapshot()
        assert not dto.is_update_selector()
        assert not dto.is_update_data()

    def test_get_param_method(self):
        """测试：get_param方法获取命令参数"""
        dto = ControlCommandDTO(
            command="test_command",
            params={"key1": "value1", "key2": "value2"}
        )

        assert dto.get_param("key1") == "value1"
        assert dto.get_param("key2") == "value2"
        assert dto.get_param("key3") is None
        assert dto.get_param("key3", "default") == "default"

    def test_get_param_with_empty_params(self):
        """测试：get_param方法处理空参数"""
        dto = ControlCommandDTO(command="test_command")
        assert dto.get_param("any_key") is None
        assert dto.get_param("any_key", "default") == "default"

    def test_predefined_commands(self):
        """测试：预定义命令常量"""
        assert ControlCommandDTO.Commands.BAR_SNAPSHOT == "bar_snapshot"
        assert ControlCommandDTO.Commands.UPDATE_SELECTOR == "update_selector"
        assert ControlCommandDTO.Commands.UPDATE_DATA == "update_data"

    def test_json_serialization(self):
        """测试：JSON序列化和反序列化"""
        dto = ControlCommandDTO(
            command="bar_snapshot",
            params={"timestamp": "2024-01-01T00:00:00"}
        )

        # 序列化
        json_str = dto.model_dump_json()
        assert isinstance(json_str, str)
        assert "bar_snapshot" in json_str
        assert "2024-01-01T00:00:00" in json_str

        # 反序列化
        dto2 = ControlCommandDTO.model_validate_json(json_str)
        assert dto2.command == dto.command
        assert dto2.params == dto.params

    def test_model_dump(self):
        """测试：model_dump方法"""
        dto = ControlCommandDTO(
            command="update_selector",
            correlation_id="corr_123"
        )

        data = dto.model_dump()
        assert isinstance(data, dict)
        assert data["command"] == "update_selector"
        assert data["correlation_id"] == "corr_123"
        assert data["source"] == "task_timer"

    def test_source_custom(self):
        """测试：自定义source"""
        dto = ControlCommandDTO(
            command="bar_snapshot",
            source="api_gateway"
        )
        assert dto.source == "api_gateway"
