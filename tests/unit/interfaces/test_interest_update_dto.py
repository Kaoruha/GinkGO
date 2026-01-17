"""InterestUpdateDTO单元测试"""

import pytest
from datetime import datetime

from ginkgo.interfaces.dtos import InterestUpdateDTO


@pytest.mark.tdd
class TestInterestUpdateDTO:
    """InterestUpdateDTO单元测试"""

    def test_init_with_required_fields(self):
        """测试：使用必需字段初始化"""
        dto = InterestUpdateDTO(
            portfolio_id="portfolio_001",
            node_id="node_001"
        )
        assert dto.portfolio_id == "portfolio_001"
        assert dto.node_id == "node_001"
        assert dto.symbols == []  # 默认空列表
        assert dto.update_type == "replace"  # 默认replace
        assert isinstance(dto.timestamp, datetime)

    def test_init_with_symbols(self):
        """测试：使用symbols列表初始化"""
        dto = InterestUpdateDTO(
            portfolio_id="portfolio_002",
            node_id="node_002",
            symbols=["000001.SZ", "600000.SH", "00700.HK"]
        )
        assert len(dto.symbols) == 3
        assert "000001.SZ" in dto.symbols
        assert "600000.SH" in dto.symbols

    def test_init_with_update_type(self):
        """测试：使用update_type初始化"""
        dto = InterestUpdateDTO(
            portfolio_id="portfolio_003",
            node_id="node_003",
            update_type="add"
        )
        assert dto.update_type == "add"

    def test_get_all_symbols(self):
        """测试：get_all_symbols方法返回标的集合"""
        dto = InterestUpdateDTO(
            portfolio_id="portfolio_001",
            node_id="node_001",
            symbols=["000001.SZ", "600000.SH", "000001.SZ"]  # 包含重复
        )

        symbols_set = dto.get_all_symbols()
        assert isinstance(symbols_set, set)
        assert len(symbols_set) == 2  # 去重
        assert "000001.SZ" in symbols_set
        assert "600000.SH" in symbols_set

    def test_get_all_symbols_empty(self):
        """测试：get_all_symbols方法处理空列表"""
        dto = InterestUpdateDTO(
            portfolio_id="portfolio_001",
            node_id="node_001"
        )

        symbols_set = dto.get_all_symbols()
        assert len(symbols_set) == 0
        assert isinstance(symbols_set, set)

    def test_update_type_methods(self):
        """测试：update_type判断方法（is_replace/is_add/is_remove）"""
        # 测试replace
        dto_replace = InterestUpdateDTO(
            portfolio_id="p1",
            node_id="n1",
            update_type="replace"
        )
        assert dto_replace.is_replace()
        assert not dto_replace.is_add()
        assert not dto_replace.is_remove()

        # 测试add
        dto_add = InterestUpdateDTO(
            portfolio_id="p2",
            node_id="n2",
            update_type="add"
        )
        assert dto_add.is_add()
        assert not dto_add.is_replace()
        assert not dto_add.is_remove()

        # 测试remove
        dto_remove = InterestUpdateDTO(
            portfolio_id="p3",
            node_id="n3",
            update_type="remove"
        )
        assert dto_remove.is_remove()
        assert not dto_remove.is_replace()
        assert not dto_remove.is_add()

    def test_json_serialization(self):
        """测试：JSON序列化和反序列化"""
        dto = InterestUpdateDTO(
            portfolio_id="portfolio_001",
            node_id="node_001",
            symbols=["000001.SZ", "600000.SH"],
            update_type="replace"
        )

        # 序列化
        json_str = dto.model_dump_json()
        assert isinstance(json_str, str)
        assert "portfolio_001" in json_str
        assert "000001.SZ" in json_str

        # 反序列化
        dto2 = InterestUpdateDTO.model_validate_json(json_str)
        assert dto2.portfolio_id == dto.portfolio_id
        assert dto2.node_id == dto.node_id
        assert dto2.symbols == dto.symbols
        assert dto2.update_type == dto.update_type

    def test_model_dump(self):
        """测试：model_dump方法"""
        dto = InterestUpdateDTO(
            portfolio_id="portfolio_001",
            node_id="node_001",
            symbols=["000001.SZ"]
        )

        data = dto.model_dump()
        assert isinstance(data, dict)
        assert data["portfolio_id"] == "portfolio_001"
        assert data["node_id"] == "node_001"
        assert data["symbols"] == ["000001.SZ"]
        assert data["update_type"] == "replace"
