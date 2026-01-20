"""PriceUpdateDTO单元测试"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock
from pydantic import ValidationError

from ginkgo.interfaces.dtos import PriceUpdateDTO
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.entities.tick import Tick


@pytest.mark.tdd
class TestPriceUpdateDTO:
    """PriceUpdateDTO单元测试"""

    def test_init_with_required_fields(self):
        """测试：使用必需字段初始化"""
        dto = PriceUpdateDTO(symbol="000001.SZ")
        assert dto.symbol == "000001.SZ"
        assert isinstance(dto.timestamp, datetime)
        assert dto.price is None

    def test_init_with_all_fields(self):
        """测试：使用所有字段初始化"""
        now = datetime.now()
        dto = PriceUpdateDTO(
            symbol="600000.SH",
            timestamp=now,
            price=10.50,
            bid_price=10.49,
            ask_price=10.51,
            open_price=10.40,
            high_price=10.60,
            low_price=10.35,
            volume=1000000,
            amount=10500000,
            bid_volume=5000,
            ask_volume=3000,
            source="eastmoney"
        )
        assert dto.symbol == "600000.SH"
        assert dto.timestamp == now
        assert dto.price == 10.50
        assert dto.bid_price == 10.49
        assert dto.ask_price == 10.51
        assert dto.open_price == 10.40
        assert dto.high_price == 10.60
        assert dto.low_price == 10.35
        assert dto.volume == 1000000
        assert dto.amount == 10500000

    def test_from_tick_method(self):
        """测试：from_tick方法从Tick事件创建DTO"""
        from ginkgo.enums import TICKDIRECTION_TYPES, SOURCE_TYPES

        # 创建Tick对象
        tick = Tick(
            code="000001.SZ",
            price=10.50,
            volume=1000,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.now(),
            source=SOURCE_TYPES.OTHER
        )

        # 创建EventPriceUpdate
        event = EventPriceUpdate(payload=tick)

        # 使用from_tick方法
        dto = PriceUpdateDTO.from_tick(event)

        assert dto.symbol == "000001.SZ"
        assert dto.price == 10.50
        assert dto.volume == 1000

    def test_from_tick_with_partial_fields(self):
        """测试：from_tick方法处理部分字段"""
        from ginkgo.enums import TICKDIRECTION_TYPES, SOURCE_TYPES

        tick = Tick(
            code="600000.SH",
            price=15.00,
            volume=500,
            direction=TICKDIRECTION_TYPES.ACTIVESELL,
            timestamp=datetime.now(),
            source=SOURCE_TYPES.OTHER
        )

        event = EventPriceUpdate(payload=tick)
        dto = PriceUpdateDTO.from_tick(event)

        assert dto.symbol == "600000.SH"
        assert dto.price == 15.00
        assert dto.bid_price is None
        assert dto.ask_price is None

    def test_json_serialization(self):
        """测试：JSON序列化和反序列化"""
        now = datetime.now()
        dto = PriceUpdateDTO(
            symbol="000001.SZ",
            timestamp=now,
            price=10.50,
            volume=1000000
        )

        # 序列化
        json_str = dto.model_dump_json()
        assert isinstance(json_str, str)
        assert "000001.SZ" in json_str
        assert "10.5" in json_str

        # 反序列化
        dto2 = PriceUpdateDTO.model_validate_json(json_str)
        assert dto2.symbol == dto.symbol
        assert dto2.price == dto.price

    def test_model_dump(self):
        """测试：model_dump方法"""
        dto = PriceUpdateDTO(
            symbol="000001.SZ",
            price=10.50,
            volume=1000000
        )

        data = dto.model_dump()
        assert isinstance(data, dict)
        assert data["symbol"] == "000001.SZ"
        assert data["price"] == 10.50
        assert data["volume"] == 1000000

    def test_to_bar_dict_with_price(self):
        """测试：to_bar_dict方法转换为K线字典（有price）"""
        now = datetime.now()
        dto = PriceUpdateDTO(
            symbol="000001.SZ",
            timestamp=now,
            price=10.50,
            open_price=10.40,
            high_price=10.60,
            low_price=10.35,
            volume=1000000,
            amount=10500000
        )

        bar_dict = dto.to_bar_dict()

        assert bar_dict["symbol"] == "000001.SZ"
        assert bar_dict["timestamp"] == now
        assert bar_dict["open"] == 10.40
        assert bar_dict["high"] == 10.60
        assert bar_dict["low"] == 10.35
        assert bar_dict["close"] == 10.50
        assert bar_dict["volume"] == 1000000
        assert bar_dict["amount"] == 10500000

    def test_to_bar_dict_fallback_to_price(self):
        """测试：to_bar_dict方法fallback到price（OHLC缺失时）"""
        dto = PriceUpdateDTO(
            symbol="000001.SZ",
            price=10.50,
            volume=1000000
        )

        bar_dict = dto.to_bar_dict()

        # 当OHLC缺失时，使用price作为fallback
        assert bar_dict["open"] == 10.50
        assert bar_dict["high"] == 10.50
        assert bar_dict["low"] == 10.50
        assert bar_dict["close"] == 10.50
        assert bar_dict["volume"] == 1000000

    def test_to_bar_dict_zero_volume_fallback(self):
        """测试：to_bar_dict方法volume为0时的fallback"""
        dto = PriceUpdateDTO(
            symbol="000001.SZ",
            price=10.50
        )

        bar_dict = dto.to_bar_dict()

        assert bar_dict["volume"] == 0
        assert bar_dict["amount"] == 0
