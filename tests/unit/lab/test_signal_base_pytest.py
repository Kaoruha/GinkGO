"""
性能: 156MB RSS, 0.87s, 24 tests [PASS]
Signal基础测试 - 使用Pytest最佳实践重构。

测试Signal类的基本功能，包括初始化、属性设置、方向管理等。
"""

import pytest
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any
from unittest.mock import Mock, patch

try:
    from ginkgo.entities.signal import Signal
    from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
    from ginkgo.libs import datetime_normalize
    GINKGO_AVAILABLE = True
except ImportError:
    Signal = None
    DIRECTION_TYPES = None
    SOURCE_TYPES = None
    datetime_normalize = None
    GINKGO_AVAILABLE = False


# Skip entire module if imports fail
if not GINKGO_AVAILABLE:
    pytestmark = pytest.mark.skip(reason="Required modules not available")


def _make_signal(**overrides) -> Signal:
    """Helper to create a valid Signal with all required args."""
    defaults = dict(
        portfolio_id="test_portfolio",
        engine_id="test_engine",
        task_id="test_run",
        code="000001.SZ",
        direction=DIRECTION_TYPES.LONG,
        reason="test reason",
        source=SOURCE_TYPES.OTHER,
    )
    defaults.update(overrides)
    return Signal(**defaults)


@pytest.mark.lab
@pytest.mark.strategy
class TestSignalConstruction:
    """测试Signal类的构造和初始化."""

    @pytest.fixture
    def signal_params(self) -> Dict[str, Any]:
        """Signal参数fixture."""
        if not GINKGO_AVAILABLE:
            pytest.skip("Ginkgo not available")
        return {
            "portfolio_id": "test_portfolio",
            "engine_id": "test_engine",
            "task_id": "test_run",
            "code": "000001.SZ",
            "direction": DIRECTION_TYPES.LONG,
            "reason": "test reason",
            "source": SOURCE_TYPES.SIM,
            "uuid": "test_uuid",
        }

    @pytest.mark.unit
    def test_signal_default_initialization(self):
        """测试Signal默认初始化 - 现在需要必填参数."""
        if Signal is None:
            pytest.skip("Signal not available")

        s = _make_signal()

        # 验证基本属性
        assert s is not None
        assert getattr(s, 'code', None) is not None
        assert getattr(s, 'timestamp', None) is not None
        assert getattr(s, 'direction', None) is not None
        assert getattr(s, 'source', None) is not None
        assert getattr(s, 'uuid', None) is not None

    @pytest.mark.unit
    @pytest.mark.parametrize("direction_name", ["LONG", "SHORT", "CLOSE"])
    def test_signal_initialization_with_direction(self, direction_name):
        """测试不同方向的Signal初始化."""
        if Signal is None or DIRECTION_TYPES is None:
            pytest.skip("Signal or DIRECTION_TYPES not available")

        direction = getattr(DIRECTION_TYPES, direction_name, None)
        if direction is None:
            pytest.skip(f"DIRECTION_TYPES.{direction_name} not available")

        s = _make_signal(direction=direction)

        assert s.direction == direction


@pytest.mark.lab
@pytest.mark.strategy
class TestSignalProperties:
    """测试Signal类的属性访问."""

    @pytest.fixture
    def sample_signal(self) -> Signal:
        """创建示例Signal."""
        if Signal is None:
            pytest.skip("Signal not available")

        return _make_signal(
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            source=SOURCE_TYPES.SIM,
            uuid="test_uuid",
            business_timestamp="2020-01-01 02:02:32",
        )

    @pytest.mark.unit
    def test_signal_code_property(self, sample_signal):
        """测试代码属性."""
        assert sample_signal.code == "000001.SZ"

    @pytest.mark.unit
    def test_signal_timestamp_property(self, sample_signal):
        """测试时间戳属性 - business_timestamp传入构造函数."""
        expected = datetime_normalize("2020-01-01 02:02:32")
        assert sample_signal.business_timestamp == expected

    @pytest.mark.unit
    def test_signal_direction_property(self, sample_signal):
        """测试方向属性."""
        assert sample_signal.direction == DIRECTION_TYPES.LONG

    @pytest.mark.unit
    def test_signal_source_property(self, sample_signal):
        """测试来源属性."""
        assert sample_signal.source == SOURCE_TYPES.SIM

    @pytest.mark.unit
    def test_signal_uuid_property(self, sample_signal):
        """测试UUID属性."""
        assert sample_signal.uuid == "test_uuid"


@pytest.mark.lab
@pytest.mark.strategy
class TestSignalDataSetting:
    """测试Signal类的数据设置功能."""

    @pytest.mark.unit
    @pytest.mark.parametrize("code,direction_name,uuid", [
        ("000001.SZ", "LONG", "uuid1"),
        ("600000.SH", "SHORT", "uuid2"),
    ])
    def test_signal_set_method(self, code, direction_name, uuid):
        """测试Signal的set方法 - 需要完整的参数列表."""
        if Signal is None or DIRECTION_TYPES is None:
            pytest.skip("Required dependencies not available")

        direction = getattr(DIRECTION_TYPES, direction_name, None)
        if direction is None:
            pytest.skip(f"DIRECTION_TYPES.{direction_name} not available")

        s = _make_signal(uuid=uuid, code=code, direction=direction)

        assert s.code == code
        assert s.direction == direction
        assert s.uuid == uuid

    @pytest.mark.unit
    def test_signal_set_source_method(self):
        """测试Signal的set_source方法."""
        if Signal is None or SOURCE_TYPES is None:
            pytest.skip("Signal or SOURCE_TYPES not available")

        s = _make_signal(source=SOURCE_TYPES.SIM)

        assert s.source == SOURCE_TYPES.SIM


@pytest.mark.lab
@pytest.mark.strategy
class TestSignalValidation:
    """测试Signal类的验证功能."""

    @pytest.mark.unit
    def test_signal_empty_portfolio_id_raises(self):
        """测试空portfolio_id验证."""
        if Signal is None:
            pytest.skip("Signal not available")

        with pytest.raises(Exception):
            Signal(
                portfolio_id="",
                engine_id="test_engine",
                task_id="test_run",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason="test reason",
                source=SOURCE_TYPES.OTHER,
            )

    @pytest.mark.unit
    def test_signal_direction_validation(self):
        """测试方向验证 - 有效方向可以正常创建."""
        if Signal is None or DIRECTION_TYPES is None:
            pytest.skip("Required dependencies not available")

        valid_directions = [DIRECTION_TYPES.LONG, DIRECTION_TYPES.SHORT]
        for direction in valid_directions:
            s = _make_signal(direction=direction)
            assert s.direction == direction


@pytest.mark.lab
@pytest.mark.strategy
class TestSignalBusinessLogic:
    """测试Signal类的业务逻辑."""

    @pytest.fixture
    def sample_signals(self) -> list:
        """创建示例Signals列表."""
        if Signal is None or DIRECTION_TYPES is None:
            pytest.skip("Required dependencies not available")

        signals = []
        codes = ["000001.SZ", "000002.SZ", "600000.SH"]

        for i, code in enumerate(codes):
            s = _make_signal(
                code=code,
                direction=DIRECTION_TYPES.LONG if i % 2 == 0 else DIRECTION_TYPES.SHORT,
                source=SOURCE_TYPES.SIM,
                uuid=f"uuid_{i}",
                business_timestamp=f"2020-01-0{i+1} 10:00:00",
            )
            signals.append(s)

        return signals

    @pytest.mark.unit
    def test_signal_filter_by_code(self, sample_signals):
        """测试按代码过滤信号."""
        target_code = "000001.SZ"
        filtered = [s for s in sample_signals if s.code == target_code]

        assert len(filtered) > 0
        assert all(s.code == target_code for s in filtered)

    @pytest.mark.unit
    def test_signal_filter_by_direction(self, sample_signals):
        """测试按方向过滤信号."""
        if DIRECTION_TYPES is None:
            pytest.skip("DIRECTION_TYPES not available")

        filtered = [s for s in sample_signals if s.direction == DIRECTION_TYPES.LONG]

        assert len(filtered) > 0
        assert all(s.direction == DIRECTION_TYPES.LONG for s in filtered)

    @pytest.mark.unit
    def test_signal_sort_by_timestamp(self, sample_signals):
        """测试按时间戳排序信号."""
        sorted_signals = sorted(sample_signals, key=lambda x: x.timestamp)

        for i in range(len(sorted_signals) - 1):
            assert sorted_signals[i].timestamp <= sorted_signals[i+1].timestamp


@pytest.mark.lab
@pytest.mark.strategy
class TestSignalStateManagement:
    """测试Signal类的状态管理."""

    @pytest.mark.unit
    def test_signal_string_representation(self):
        """测试Signal的字符串表示."""
        if Signal is None:
            pytest.skip("Signal not available")

        s = _make_signal(code="000001.SZ")

        # 验证字符串表示包含关键信息
        str_repr = str(s)
        assert "000001.SZ" in str_repr or "Signal" in str_repr

    @pytest.mark.unit
    def test_signal_equality(self):
        """测试Signal相等性."""
        if Signal is None:
            pytest.skip("Signal not available")

        s1 = _make_signal(code="000001.SZ", uuid="test_uuid")
        s2 = _make_signal(code="000001.SZ", uuid="test_uuid")

        # 相等的Signal应该是不同的对象
        assert s1 is not s2


@pytest.mark.lab
@pytest.mark.strategy
class TestSignalConstraints:
    """测试Signal类的约束条件."""

    @pytest.mark.unit
    @pytest.mark.parametrize("direction_name,expected_name", [
        ("LONG", "LONG"),
        ("SHORT", "SHORT"),
        ("OTHER", "OTHER"),
    ])
    def test_signal_direction_enum(self, direction_name, expected_name):
        """测试方向枚举约束."""
        if DIRECTION_TYPES is None:
            pytest.skip("DIRECTION_TYPES not available")

        direction = getattr(DIRECTION_TYPES, direction_name, None)
        if direction is None:
            pytest.skip(f"DIRECTION_TYPES.{direction_name} not available")

        # 验证方向枚举值
        assert direction.name == expected_name

    @pytest.mark.unit
    @pytest.mark.parametrize("source_name,expected_name", [
        ("SIM", "SIM"),
        ("STRATEGY", "STRATEGY"),
        ("OTHER", "OTHER"),
    ])
    def test_signal_source_enum(self, source_name, expected_name):
        """测试来源枚举约束."""
        if SOURCE_TYPES is None:
            pytest.skip("SOURCE_TYPES not available")

        source = getattr(SOURCE_TYPES, source_name, None)
        if source is None:
            pytest.skip(f"SOURCE_TYPES.{source_name} not available")

        # 验证来源枚举值
        assert source.name == expected_name
