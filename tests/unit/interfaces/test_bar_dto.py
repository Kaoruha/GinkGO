"""BarDTO单元测试"""

import pytest
from datetime import datetime
from unittest.mock import Mock
from decimal import Decimal

from ginkgo.interfaces.dtos import BarDTO
from ginkgo.data.models.model_bar import MBar


@pytest.mark.tdd
class TestBarDTO:
    """BarDTO单元测试"""

    def test_init_with_required_fields(self):
        """测试：使用必需字段初始化"""
        now = datetime.now()
        dto = BarDTO(
            symbol="000001.SZ",
            timestamp=now,
            open=10.40,
            high=10.60,
            low=10.35,
            close=10.50
        )
        assert dto.symbol == "000001.SZ"
        assert dto.period == "1d"  # 默认值
        assert dto.timestamp == now
        assert dto.open == 10.40
        assert dto.close == 10.50
        assert dto.volume == 0  # 默认值

    def test_init_with_all_fields(self):
        """测试：使用所有字段初始化"""
        now = datetime.now()
        dto = BarDTO(
            symbol="600000.SH",
            period="1d",
            timestamp=now,
            open=10.40,
            high=10.60,
            low=10.35,
            close=10.50,
            volume=1000000,
            amount=10500000,
            turnover=2.5,
            change=0.30,
            change_pct=2.94,
            source="eastmoney"
        )
        assert dto.symbol == "600000.SH"
        assert dto.period == "1d"
        assert dto.volume == 1000000
        assert dto.amount == 10500000
        assert dto.turnover == 2.5
        assert dto.change == 0.30
        assert abs(dto.change_pct - 2.94) < 0.01

    def test_from_bar_method(self):
        """测试：from_bar方法从Bar对象创建DTO"""
        # 创建Mock MBar对象
        bar = Mock(spec=MBar)
        bar.code = "000001.SZ"
        bar.timestamp = datetime.now()
        bar.open = Decimal("10.40")
        bar.high = Decimal("10.60")
        bar.low = Decimal("10.35")
        bar.close = Decimal("10.50")
        bar.volume = 1000000
        bar.amount = Decimal("10500000")
        bar.turnover = None
        bar.change = None
        bar.change_pct = None

        dto = BarDTO.from_bar(bar)

        assert dto.symbol == "000001.SZ"
        assert dto.open == 10.40
        assert dto.high == 10.60
        assert dto.low == 10.35
        assert dto.close == 10.50
        assert dto.volume == 1000000
        assert dto.amount == 10500000

    def test_from_bar_with_optional_fields(self):
        """测试：from_bar方法处理可选字段"""
        bar = Mock(spec=MBar)
        bar.code = "600000.SH"
        bar.timestamp = datetime.now()
        bar.open = Decimal("15.00")
        bar.high = Decimal("15.50")
        bar.low = Decimal("14.80")
        bar.close = Decimal("15.30")
        bar.volume = 500000
        bar.amount = Decimal("7650000")
        bar.turnover = Decimal("1.8")
        bar.change = Decimal("0.30")
        bar.change_pct = Decimal("2.0")

        dto = BarDTO.from_bar(bar)

        assert dto.turnover == 1.8
        assert dto.change == 0.30
        assert dto.change_pct == 2.0

    def test_json_serialization(self):
        """测试：JSON序列化和反序列化"""
        now = datetime.now()
        dto = BarDTO(
            symbol="000001.SZ",
            timestamp=now,
            open=10.40,
            high=10.60,
            low=10.35,
            close=10.50,
            volume=1000000
        )

        # 序列化
        json_str = dto.model_dump_json()
        assert isinstance(json_str, str)
        assert "000001.SZ" in json_str
        assert "10.5" in json_str

        # 反序列化
        dto2 = BarDTO.model_validate_json(json_str)
        assert dto2.symbol == dto.symbol
        assert dto2.close == dto.close

    def test_model_dump(self):
        """测试：model_dump方法"""
        now = datetime.now()
        dto = BarDTO(
            symbol="000001.SZ",
            timestamp=now,
            open=10.40,
            high=10.60,
            low=10.35,
            close=10.50
        )

        data = dto.model_dump()
        assert isinstance(data, dict)
        assert data["symbol"] == "000001.SZ"
        assert data["open"] == 10.40
        assert data["close"] == 10.50

    def test_to_price_update(self):
        """测试：to_price_update方法转换为PriceUpdate格式"""
        now = datetime.now()
        dto = BarDTO(
            symbol="000001.SZ",
            timestamp=now,
            open=10.40,
            high=10.60,
            low=10.35,
            close=10.50,
            volume=1000000,
            amount=10500000
        )

        price_update = dto.to_price_update()

        assert price_update["symbol"] == "000001.SZ"
        assert price_update["timestamp"] == now
        assert price_update["price"] == 10.50  # close作为price
        assert price_update["open_price"] == 10.40
        assert price_update["high_price"] == 10.60
        assert price_update["low_price"] == 10.35
        assert price_update["volume"] == 1000000
        assert price_update["amount"] == 10500000
        assert price_update["source"] == "bar_snapshot"

    def test_to_price_update_without_amount(self):
        """测试：to_price_update方法处理无成交额情况"""
        now = datetime.now()
        dto = BarDTO(
            symbol="600000.SH",
            timestamp=now,
            open=15.00,
            high=15.50,
            low=14.80,
            close=15.30,
            volume=500000
            # amount is None
        )

        price_update = dto.to_price_update()

        assert price_update["symbol"] == "600000.SH"
        assert price_update["price"] == 15.30
        assert price_update["amount"] is None
