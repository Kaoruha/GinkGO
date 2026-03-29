"""
Ginkgo Trading 测试配置

定义pytest标记、共享fixtures和测试配置
"""

import pytest
from datetime import datetime
from decimal import Decimal
from typing import Dict, List
from unittest.mock import Mock, MagicMock
from pathlib import Path


# 添加项目路径
project_root = Path(__file__).parent.parent.parent


def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line(
        "markers", "unit: 单元测试标记（不依赖外部资源）"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试标记（需要数据库等资源）"
    )
    config.addinivalue_line(
        "markers", "financial: 金融业务逻辑测试标记"
    )
    config.addinivalue_line(
        "markers", "slow: 慢速测试标记（执行时间较长）"
    )
    config.addinivalue_line(
        "markers", "tdd: TDD测试标记（测试驱动开发）"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    # 为没有标记的测试添加默认标记
    for item in items:
        # 如果测试文件在entities目录，默认标记为unit
        if "entities" in str(item.fspath):
            if not any(item.iter_markers()):
                item.add_marker(pytest.mark.unit)

        # 如果测试文件在events目录，默认标记为unit
        elif "events" in str(item.fspath):
            if not any(item.iter_markers()):
                item.add_marker(pytest.mark.unit)

        # 如果测试文件在strategy目录，默认标记为unit
        elif "strategy" in str(item.fspath):
            if not any(item.iter_markers()):
                item.add_marker(pytest.mark.unit)

        # 如果测试文件在engines目录，默认标记为unit
        elif "engines" in str(item.fspath):
            if not any(item.iter_markers()):
                item.add_marker(pytest.mark.unit)

        # 如果测试文件在portfolios目录，默认标记为financial
        elif "portfolios" in str(item.fspath):
            if not any(item.iter_markers()):
                item.add_marker(pytest.mark.financial)

        # 如果测试文件在feeders目录，默认标记为unit
        elif "feeders" in str(item.fspath):
            if not any(item.iter_markers()):
                item.add_marker(pytest.mark.unit)

        # 如果测试文件在analysis目录，默认标记为unit
        elif "analysis" in str(item.fspath):
            if not any(item.iter_markers()):
                item.add_marker(pytest.mark.unit)


def pytest_report_header(config):
    """添加测试报告头"""
    return [
        "Ginkgo Trading Test Suite",
        "Testing trading components with pytest"
    ]


def pytest_report_teststatus(report):
    """自定义测试状态报告"""
    if report.when == "call":
        if report.passed:
            pass
        elif report.failed:
            pass
        elif report.skipped:
            pass


# ============================================================================
# 共享Fixtures
# ============================================================================

@pytest.fixture
def sample_portfolio_info() -> Dict:
    """示例投资组合信息"""
    return {
        "uuid": "test_portfolio_uuid",
        "name": "TestPortfolio",
        "cash": Decimal("100000"),
        "frozen": Decimal("0"),
        "worth": Decimal("100000"),
        "profit": Decimal("0"),
        "positions": {}
    }


@pytest.fixture
def sample_bar_data() -> Dict:
    """示例K线数据"""
    return {
        "code": "000001.SZ",
        "timestamp": datetime(2024, 1, 1, 9, 30, 0),
        "open": Decimal("10.0"),
        "close": Decimal("10.5"),
        "high": Decimal("11.0"),
        "low": Decimal("9.8"),
        "volume": 1000000,
        "amount": Decimal("10500000")
    }


@pytest.fixture
def sample_order_data() -> Dict:
    """示例订单数据"""
    return {
        "code": "000001.SZ",
        "volume": 1000,
        "direction": "LONG",
        "price": Decimal("10.5"),
        "type": "LIMIT",
        "status": "NEW"
    }


@pytest.fixture
def sample_position_data() -> Dict:
    """示例持仓数据"""
    return {
        "code": "000001.SZ",
        "volume": 1000,
        "available_volume": 1000,
        "cost_price": Decimal("10.0"),
        "current_price": Decimal("10.5"),
        "profit": Decimal("500"),
        "worth": Decimal("10500")
    }


@pytest.fixture
def sample_signal_data() -> Dict:
    """示例信号数据"""
    return {
        "code": "000001.SZ",
        "direction": "LONG",
        "reason": "Test Signal"
    }


@pytest.fixture
def mock_strategy():
    """模拟策略对象"""
    strategy = Mock()
    strategy.name = "TestStrategy"
    strategy.uuid = "test_strategy_uuid"
    strategy.cal = Mock(return_value=[])
    strategy.bind_data_feeder = Mock()
    return strategy


@pytest.fixture
def mock_risk_manager():
    """模拟风控管理器对象"""
    risk_manager = Mock()
    risk_manager.name = "TestRiskManager"
    risk_manager.uuid = "test_risk_uuid"
    risk_manager.cal = Mock(return_value=None)
    risk_manager.generate_signals = Mock(return_value=[])
    return risk_manager


@pytest.fixture
def mock_selector():
    """模拟选择器对象"""
    selector = Mock()
    selector.name = "TestSelector"
    selector.uuid = "test_selector_uuid"
    selector.pick = Mock(return_value=[])
    return selector


@pytest.fixture
def mock_sizer():
    """模拟仓位管理器对象"""
    sizer = Mock()
    sizer.name = "TestSizer"
    sizer.uuid = "test_sizer_uuid"
    sizer.cal = Mock(return_value=100)
    return sizer


@pytest.fixture
def mock_data_feeder():
    """模拟数据馈送器对象"""
    feeder = Mock()
    feeder.name = "TestDataFeeder"
    feeder.get_bars = Mock(return_value=[])
    feeder.get_daybar = Mock(return_value=None)
    return feeder


@pytest.fixture
def sample_stock_codes() -> List[str]:
    """示例股票代码列表"""
    return [
        "000001.SZ",
        "000002.SZ",
        "600000.SH",
        "300001.SZ",
        "688001.SH"
    ]


@pytest.fixture
def sample_trading_dates() -> List[datetime]:
    """示例交易日期列表"""
    return [
        datetime(2024, 1, 2),
        datetime(2024, 1, 3),
        datetime(2024, 1, 4),
        datetime(2024, 1, 5),
    ]


@pytest.fixture
def mock_price_event():
    """模拟价格事件"""
    event = Mock()
    event.type = "PRICE_UPDATE"
    event.code = "000001.SZ"
    event.timestamp = datetime(2024, 1, 1, 9, 30, 0)
    event.price = Decimal("10.5")
    event.volume = 1000000
    return event


@pytest.fixture
def mock_signal_event():
    """模拟信号事件"""
    event = Mock()
    event.type = "SIGNAL_GENERATION"
    event.code = "000001.SZ"
    event.direction = "LONG"
    event.timestamp = datetime(2024, 1, 1, 9, 30, 0)
    return event


@pytest.fixture
def mock_order_event():
    """模拟订单事件"""
    event = Mock()
    event.type = "ORDER_SUBMISSION"
    event.code = "000001.SZ"
    event.volume = 1000
    event.direction = "LONG"
    event.timestamp = datetime(2024, 1, 1, 9, 30, 0)
    return event
