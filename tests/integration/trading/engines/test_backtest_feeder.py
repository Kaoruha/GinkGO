"""
BacktestFeeder回测数据馈送器TDD测试

通过TDD方式开发BacktestFeeder的核心逻辑测试套件
聚焦于配置管理、状态生命周期、时间控制、事件生成和数据预加载
"""
import pytest
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# 导入BacktestFeeder相关组件
from ginkgo.trading.feeders.backtest_feeder import BacktestFeeder
from ginkgo.trading.feeders.interfaces import DataFeedStatus
from ginkgo.trading.events import EventPriceUpdate, EventInterestUpdate
from ginkgo.trading.time.providers import LogicalTimeProvider
from datetime import datetime, date


@pytest.mark.unit
@pytest.mark.backtest
class TestBacktestFeederConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self):
        """测试默认参数构造 - 包括继承属性"""
        feeder = BacktestFeeder()

        # BacktestFeeder自身属性
        assert feeder.name == "backtest_feeder"
        assert feeder.status == DataFeedStatus.IDLE

        # 继承自BaseFeeder的属性
        from ginkgo.data.services.bar_service import BarService
        assert feeder.bar_service is not None, "bar_service应该从container自动注入"
        assert isinstance(feeder.bar_service, BarService)
        assert feeder._engine_put is None

        # 继承自TimeMixin的属性
        assert feeder.timestamp is not None, "timestamp应存在"

    def test_dual_inheritance(self):
        """测试双继承 - 验证两个父类的接口"""
        from ginkgo.trading.feeders.base_feeder import BaseFeeder
        from ginkgo.trading.feeders.interfaces import IBacktestDataFeeder

        feeder = BacktestFeeder()

        # 验证继承BaseFeeder和IBacktestDataFeeder
        assert isinstance(feeder, BaseFeeder)
        assert isinstance(feeder, IBacktestDataFeeder)

        # 验证BaseFeeder的接口
        assert getattr(feeder, 'bar_service', None) is not None, "BaseFeeder的DI属性"
        assert getattr(feeder, 'timestamp', None) is not None, "TimeMixin属性"

        # 验证IBacktestDataFeeder的接口
        assert callable(getattr(feeder, 'advance_time', None)), "IBacktestDataFeeder核心方法"
        assert callable(getattr(feeder, 'get_historical_data', None)), "IBacktestDataFeeder数据方法"
        assert callable(getattr(feeder, 'validate_time_access', None)), "IBacktestDataFeeder时间验证"

    def test_initial_attributes(self):
        """测试初始属性状态 - 验证所有BacktestFeeder特有属性"""
        feeder = BacktestFeeder()

        # 验证time_controller初始化为None
        assert feeder.time_controller is None

        # 验证event_publisher初始化为None
        assert feeder.event_publisher is None

        # 验证_interested_codes初始化为空列表
        assert feeder._interested_codes == []

        # 验证_data_cache初始化为空字典
        assert feeder._data_cache == {}


@pytest.mark.unit
@pytest.mark.backtest
class TestStatusLifecycle:
    """2. 状态生命周期测试（原3，Config类已删除）"""

    def test_initial_status_idle(self):
        """测试初始状态为IDLE"""
        feeder = BacktestFeeder()

        # 验证BacktestFeeder创建后status为IDLE
        assert feeder.status == DataFeedStatus.IDLE
        assert feeder.get_status() == DataFeedStatus.IDLE

    def test_initialize_method(self):
        """测试initialize方法"""
        feeder = BacktestFeeder()

        # 测试无time_controller时的初始化
        result = feeder.initialize()
        assert result is True
        assert feeder.status == DataFeedStatus.IDLE

        # 测试有time_provider时的初始化
        time_provider = LogicalTimeProvider(datetime(2023, 1, 1))
        feeder.set_time_provider(time_provider)
        result = feeder.initialize()

        # 验证time_boundary_validator被创建
        assert result is True
        assert feeder.time_boundary_validator is not None

    def test_start_method_transitions_to_connected(self):
        """测试start方法转换到CONNECTED"""
        feeder = BacktestFeeder()

        # 验证初始状态为IDLE
        assert feeder.status == DataFeedStatus.IDLE

        # 调用start()
        result = feeder.start()

        # 验证status从IDLE转换为CONNECTED
        assert result is True
        assert feeder.status == DataFeedStatus.CONNECTED

    def test_start_fails_if_not_idle(self):
        """测试非IDLE状态start失败"""
        feeder = BacktestFeeder()

        # 先启动一次
        feeder.start()
        assert feeder.status == DataFeedStatus.CONNECTED

        # 再次调用start()应该失败
        result = feeder.start()
        assert result is False
        assert feeder.status == DataFeedStatus.CONNECTED

    def test_stop_method_transitions_to_disconnected(self):
        """测试stop方法转换到DISCONNECTED"""
        feeder = BacktestFeeder()

        # 添加一些缓存数据
        feeder._data_cache['test_key'] = 'test_value'
        assert len(feeder._data_cache) > 0

        # 先start()再stop()
        feeder.start()
        assert feeder.status == DataFeedStatus.CONNECTED

        result = feeder.stop()

        # 验证status从CONNECTED转换为DISCONNECTED
        assert result is True
        assert feeder.status == DataFeedStatus.DISCONNECTED

        # 验证_data_cache被清空
        assert len(feeder._data_cache) == 0

    def test_get_status_method(self):
        """测试get_status方法"""
        feeder = BacktestFeeder()

        # 验证IDLE状态
        assert feeder.get_status() == DataFeedStatus.IDLE

        # 验证CONNECTED状态
        feeder.start()
        assert feeder.get_status() == DataFeedStatus.CONNECTED

        # 验证DISCONNECTED状态
        feeder.stop()
        assert feeder.get_status() == DataFeedStatus.DISCONNECTED


@pytest.mark.unit
@pytest.mark.backtest
class TestTimeControl:
    """4. 时间控制测试"""

    def test_set_time_controller_method(self):
        """测试set_time_provider绑定"""
        feeder = BacktestFeeder()

        # 创建LogicalTimeProvider
        time_provider = LogicalTimeProvider(datetime(2023, 1, 1))

        # 调用set_time_provider(time_provider)
        feeder.set_time_provider(time_provider)

        # 验证self.time_controller被正确设置
        assert feeder.time_controller is time_provider

    def test_time_boundary_validator_creation(self):
        """测试TimeBoundaryValidator创建"""
        from ginkgo.trading.time.providers import TimeBoundaryValidator

        feeder = BacktestFeeder()
        assert feeder.time_boundary_validator is None

        # 调用set_time_provider()自动创建validator
        time_provider = LogicalTimeProvider(datetime(2023, 1, 1))
        feeder.set_time_provider(time_provider)

        # 验证self.time_boundary_validator被创建
        assert feeder.time_boundary_validator is not None
        assert isinstance(feeder.time_boundary_validator, TimeBoundaryValidator)

    def test_validate_time_access_prevents_future_data(self):
        """测试validate_time_access阻止未来数据"""
        feeder = BacktestFeeder()

        # 设置时间控制器
        time_provider = LogicalTimeProvider(datetime(2023, 1, 1, 10, 0, 0))
        feeder.set_time_provider(time_provider)

        # 设置当前时间
        feeder.advance_time(datetime(2023, 1, 1, 10, 0, 0))

        # 尝试访问未来数据
        request_time = datetime(2023, 1, 1, 10, 0, 0)
        future_data_time = datetime(2023, 1, 2, 10, 0, 0)

        # 验证返回False（不能访问未来数据）
        result = feeder.validate_time_access(request_time, future_data_time)
        assert result is False

    def test_validate_time_access_allows_historical_data(self):
        """测试validate_time_access允许历史数据"""
        feeder = BacktestFeeder()

        # 设置时间控制器
        time_provider = LogicalTimeProvider(datetime(2023, 1, 10, 10, 0, 0))
        feeder.set_time_provider(time_provider)

        # 设置当前时间
        feeder.advance_time(datetime(2023, 1, 10, 10, 0, 0))

        # 访问历史数据
        request_time = datetime(2023, 1, 10, 10, 0, 0)
        historical_data_time = datetime(2023, 1, 5, 10, 0, 0)

        # 验证返回True（可以访问历史数据）
        result = feeder.validate_time_access(request_time, historical_data_time)
        assert result is True

    @pytest.mark.xfail(reason="validate_time_access()默认路径引用self.now属性（源代码bug）")
    def test_validate_time_access_without_validator(self):
        """测试无validator时的默认验证"""
        feeder = BacktestFeeder()

        # 不设置time_boundary_validator，只设置now
        feeder.advance_time(datetime(2023, 1, 5, 10, 0, 0))
        assert feeder.time_boundary_validator is None

        # 测试访问未来数据被拒绝（默认逻辑）
        request_time = datetime(2023, 1, 5)
        future_data_time = datetime(2023, 1, 10)
        result = feeder.validate_time_access(request_time, future_data_time)
        assert result is False

        # 测试访问历史数据被允许
        historical_data_time = datetime(2023, 1, 1)
        result = feeder.validate_time_access(request_time, historical_data_time)
        assert result is True

    def test_advance_time_callback(self):
        """测试advance_time回调"""
        feeder = BacktestFeeder()

        # 调用advance_time需要时间提供者
        time_provider = LogicalTimeProvider(datetime(2023, 1, 1))
        feeder.set_time_provider(time_provider)

        # 调用advance_time(datetime(2023, 1, 1))
        target_time = datetime(2023, 1, 1, 10, 0, 0)
        result = feeder.advance_time(target_time)

        # 验证advance_time成功执行
        assert result is True
        # timestamp是实体数据的创建时间，不由advance_time直接更新


@pytest.mark.unit
@pytest.mark.backtest
class TestEventGeneration:
    """5. 事件生成测试（原6，数据预加载功能已删除）"""

    @pytest.mark.database
    @pytest.mark.xfail(reason="ClickHouse异步写入延迟：crud.add()后立即查询可能返回空结果（数据库行为限制）")
    def test_advance_time_core_flow(self):
        """测试advance_time核心流程 - 使用真实数据库"""
        from unittest.mock import Mock
        from ginkgo.data.crud import BarCRUD
        from ginkgo.data.models import MBar
        from decimal import Decimal
        from ginkgo.enums import FREQUENCY_TYPES

        # 准备测试数据
        crud = BarCRUD()
        test_bar = MBar(
            code="TEST_FEEDER.SZ",
            timestamp=datetime(2023, 6, 1, 9, 30, 0),
            open=Decimal('100.0'), high=Decimal('105.0'),
            low=Decimal('98.0'), close=Decimal('103.0'),
            volume=1000000, amount=Decimal('102000000.0'),
            frequency=FREQUENCY_TYPES.DAY
        )

        try:
            # 清理旧数据并插入测试数据
            crud.remove(filters={"code": "TEST_FEEDER.SZ"})
            crud.add(test_bar)

            # 创建Feeder并设置time_provider（advance_time需要time provider）
            feeder = BacktestFeeder()
            time_provider = LogicalTimeProvider(datetime(2023, 6, 1))
            feeder.set_time_provider(time_provider)

            # 注入Mock发布器
            mock_publisher = Mock()
            feeder.set_event_publisher(mock_publisher)

            # 设置兴趣股票
            feeder._interested_codes = ["TEST_FEEDER.SZ"]

            # 调用advance_time
            feeder.advance_time(datetime(2023, 6, 1, 9, 30, 0))

            # 验证publisher被调用
            assert mock_publisher.called

            # 验证调用参数是EventPriceUpdate
            call_args = mock_publisher.call_args[0][0]
            assert isinstance(call_args, EventPriceUpdate)

        finally:
            # 清理测试数据
            crud.remove(filters={"code": "TEST_FEEDER.SZ"})

    def test_advance_time_updates_internal_time(self):
        """测试advance_time更新内部时间"""
        feeder = BacktestFeeder()
        feeder._interested_codes = []  # 空列表避免数据查询

        # 设置time_provider（advance_time需要）
        time_provider = LogicalTimeProvider(datetime(2023, 1, 1))
        feeder.set_time_provider(time_provider)

        # 调用advance_time(target_time)
        target_time = datetime(2023, 1, 15, 10, 0, 0)
        feeder.advance_time(target_time)

        # 验证time_provider的时间被更新为target_time
        assert time_provider.now().replace(tzinfo=None) == target_time

    def test_advance_time_with_no_interested_codes(self):
        """测试无兴趣股票时不推送事件"""
        from unittest.mock import Mock

        feeder = BacktestFeeder()
        feeder._interested_codes = []

        # 设置time_provider（advance_time需要）
        time_provider = LogicalTimeProvider(datetime(2023, 1, 1))
        feeder.set_time_provider(time_provider)

        # 注入Mock发布器
        mock_publisher = Mock()
        feeder.set_event_publisher(mock_publisher)

        # 调用advance_time()
        target_time = datetime(2023, 1, 1, 10, 0, 0)
        feeder.advance_time(target_time)

        # 验证publisher未被调用
        assert not mock_publisher.called

    @pytest.mark.database
    @pytest.mark.xfail(reason="ClickHouse异步写入延迟：crud.add()后立即查询可能返回空结果（数据库行为限制）")
    def test_generate_price_events_creates_event_price_update(self):
        """测试_generate_price_events创建EventPriceUpdate - 使用真实数据库"""
        from ginkgo.data.crud import BarCRUD
        from ginkgo.data.models import MBar
        from ginkgo.entities import Bar
        from decimal import Decimal
        from ginkgo.enums import FREQUENCY_TYPES

        # 准备测试数据
        crud = BarCRUD()
        test_bar = MBar(
            code="TEST_EVENT.SZ",
            timestamp=datetime(2023, 6, 2, 9, 30, 0),
            open=Decimal('50.0'), high=Decimal('52.0'),
            low=Decimal('49.0'), close=Decimal('51.0'),
            volume=500000, amount=Decimal('25500000.0'),
            frequency=FREQUENCY_TYPES.DAY
        )

        try:
            crud.remove(filters={"code": "TEST_EVENT.SZ"})
            crud.add(test_bar)

            # 使用真实BarService
            feeder = BacktestFeeder()
            target_time = datetime(2023, 6, 2, 9, 30, 0)
            events = feeder._generate_price_events("TEST_EVENT.SZ", target_time)

            # 验证返回EventPriceUpdate事件
            assert len(events) == 1
            assert isinstance(events[0], EventPriceUpdate)

            # 验证event.payload是Bar对象
            assert isinstance(events[0].payload, Bar)

        finally:
            crud.remove(filters={"code": "TEST_EVENT.SZ"})

    def test_generate_price_events_with_no_data(self):
        """测试无数据时_generate_price_events处理 - 无需数据库"""
        # 使用不存在的股票代码
        feeder = BacktestFeeder()
        target_time = datetime(2099, 12, 31, 9, 30, 0)
        events = feeder._generate_price_events("NODATA.SZ", target_time)

        # 验证返回空列表
        assert events == []
        assert isinstance(events, list)

    @pytest.mark.database
    @pytest.mark.xfail(reason="ClickHouse异步写入延迟：crud.add()后立即查询可能返回空结果（数据库行为限制）")
    def test_generate_price_events_sets_event_source(self):
        """测试事件设置SOURCE_TYPES.BACKTESTFEEDER - 使用真实数据库"""
        from ginkgo.data.crud import BarCRUD
        from ginkgo.data.models import MBar
        from ginkgo.enums import SOURCE_TYPES, FREQUENCY_TYPES
        from decimal import Decimal

        # 准备测试数据
        crud = BarCRUD()
        test_bar = MBar(
            code="TEST_SOURCE.SZ",
            timestamp=datetime(2023, 6, 3, 9, 30, 0),
            open=Decimal('60.0'), high=Decimal('62.0'),
            low=Decimal('59.0'), close=Decimal('61.0'),
            volume=600000, amount=Decimal('36600000.0'),
            frequency=FREQUENCY_TYPES.DAY
        )

        try:
            crud.remove(filters={"code": "TEST_SOURCE.SZ"})
            crud.add(test_bar)

            # 使用真实BarService
            feeder = BacktestFeeder()
            target_time = datetime(2023, 6, 3, 9, 30, 0)
            events = feeder._generate_price_events("TEST_SOURCE.SZ", target_time)

            # 验证event.source = SOURCE_TYPES.BACKTESTFEEDER
            assert len(events) == 1
            assert events[0].source == SOURCE_TYPES.BACKTESTFEEDER

        finally:
            crud.remove(filters={"code": "TEST_SOURCE.SZ"})

    @pytest.mark.database
    @pytest.mark.xfail(reason="ClickHouse异步写入延迟：crud.add()后立即查询可能返回空结果（数据库行为限制）")
    def test_advance_time_for_multiple_symbols(self):
        """测试多个股票的事件生成 - 使用真实数据库"""
        from unittest.mock import Mock
        from ginkgo.data.crud import BarCRUD
        from ginkgo.data.models import MBar
        from ginkgo.enums import FREQUENCY_TYPES
        from decimal import Decimal

        # 准备2个股票的测试数据
        crud = BarCRUD()
        test_bars = [
            MBar(
                code="TEST_MULTI1.SZ",
                timestamp=datetime(2023, 6, 4, 9, 30, 0),
                open=Decimal('70.0'), high=Decimal('72.0'),
                low=Decimal('69.0'), close=Decimal('71.0'),
                volume=700000, amount=Decimal('49700000.0'),
                frequency=FREQUENCY_TYPES.DAY
            ),
            MBar(
                code="TEST_MULTI2.SZ",
                timestamp=datetime(2023, 6, 4, 9, 30, 0),
                open=Decimal('80.0'), high=Decimal('82.0'),
                low=Decimal('79.0'), close=Decimal('81.0'),
                volume=800000, amount=Decimal('64800000.0'),
                frequency=FREQUENCY_TYPES.DAY
            )
        ]

        try:
            crud.remove(filters={"code": "TEST_MULTI1.SZ"})
            crud.remove(filters={"code": "TEST_MULTI2.SZ"})
            crud.add_batch(test_bars)

            # 使用真实BarService并设置time_provider
            feeder = BacktestFeeder()
            time_provider = LogicalTimeProvider(datetime(2023, 6, 1))
            feeder.set_time_provider(time_provider)
            feeder._interested_codes = ["TEST_MULTI1.SZ", "TEST_MULTI2.SZ"]

            # 注入Mock发布器
            mock_publisher = Mock()
            feeder.set_event_publisher(mock_publisher)

            # 调用advance_time
            target_time = datetime(2023, 6, 4, 9, 30, 0)
            feeder.advance_time(target_time)

            # 验证发布了2个事件
            assert mock_publisher.call_count == 2

            # 验证两次调用都是EventPriceUpdate
            for call_args in mock_publisher.call_args_list:
                event = call_args[0][0]
                assert isinstance(event, EventPriceUpdate)

        finally:
            crud.remove(filters={"code": "TEST_MULTI1.SZ"})
            crud.remove(filters={"code": "TEST_MULTI2.SZ"})

    def test_event_generation_error_handling(self):
        """测试事件生成错误处理 - 使用Mock模拟异常"""
        from unittest.mock import Mock

        feeder = BacktestFeeder()

        # 让bar_service.get_bars抛出异常
        feeder.bar_service = Mock()
        feeder.bar_service.get_bars = Mock(side_effect=Exception("Database error"))

        # 调用_generate_price_events
        target_time = datetime(2023, 1, 3, 9, 30, 0)
        events = feeder._generate_price_events("000001.SZ", target_time)

        # 验证捕获异常，返回空列表
        assert events == []
        assert isinstance(events, list)


@pytest.fixture
def configured_feeder():
    """创建已配置time_provider和run_id的BacktestFeeder"""
    feeder = BacktestFeeder()
    provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1))
    feeder.set_time_provider(provider)
    feeder.set_run_id("test_hist_run")

    # 正确的时间推进顺序：先推进Provider，再通知组件
    provider.set_current_time(datetime(2023, 6, 10))
    feeder.on_time_update(datetime(2023, 6, 10))  # 使用ITimeAwareComponent接口

    return feeder


@pytest.mark.unit
@pytest.mark.backtest
class TestInterestUpdate:
    """7. 兴趣集合更新测试"""

    def test_interest_update_from_empty(self):
        """测试从空列表添加兴趣代码"""
        feeder = BacktestFeeder()

        # 初始状态：空列表
        assert feeder._interested_codes == []

        # 发送兴趣更新事件
        from ginkgo.trading.events.interest_update import EventInterestUpdate
        event = EventInterestUpdate(
            portfolio_id="test_portfolio",
            codes=["000001.SZ", "000003.SZ", "000002.SZ"],
            timestamp=datetime(2023, 6, 1)
        )
        feeder.on_interest_update(event)

        # 验证：已添加且排序
        assert len(feeder._interested_codes) == 3
        assert feeder._interested_codes == ["000001.SZ", "000002.SZ", "000003.SZ"]

    def test_interest_update_merge_existing(self):
        """测试合并已有代码和新代码"""
        feeder = BacktestFeeder()

        # 初始设置已有codes
        feeder._interested_codes = ["000001.SZ", "000003.SZ"]

        # 发送新的兴趣代码
        from ginkgo.trading.events.interest_update import EventInterestUpdate
        event = EventInterestUpdate(
            portfolio_id="test_portfolio",
            codes=["000002.SZ", "000004.SZ"],
            timestamp=datetime(2023, 6, 1)
        )
        feeder.on_interest_update(event)

        # 验证：合并后包含全部4个，已排序
        assert len(feeder._interested_codes) == 4
        assert feeder._interested_codes == [
            "000001.SZ", "000002.SZ", "000003.SZ", "000004.SZ"
        ]

    def test_interest_update_deduplicate(self):
        """测试去重处理"""
        feeder = BacktestFeeder()

        # 已有codes
        feeder._interested_codes = ["000001.SZ"]

        # 发送包含重复代码的事件
        from ginkgo.trading.events.interest_update import EventInterestUpdate
        event = EventInterestUpdate(
            portfolio_id="test_portfolio",
            codes=["000001.SZ", "000002.SZ"],  # 000001.SZ重复
            timestamp=datetime(2023, 6, 1)
        )
        feeder.on_interest_update(event)

        # 验证：去重后只有2个
        assert len(feeder._interested_codes) == 2
        assert feeder._interested_codes == ["000001.SZ", "000002.SZ"]

    def test_interest_update_error_handling(self):
        """测试异常处理：传入异常数据不崩溃"""
        feeder = BacktestFeeder()
        feeder._interested_codes = ["000001.SZ"]

        # 创建异常的event（codes属性为None）
        from ginkgo.trading.events.interest_update import EventInterestUpdate
        event = EventInterestUpdate(
            portfolio_id="test_portfolio",
            codes=[],  # 空列表
            timestamp=datetime(2023, 6, 1)
        )
        # 手动置空codes（模拟异常情况）
        event._codes = None

        # 调用on_interest_update不应该崩溃
        feeder.on_interest_update(event)

        # 验证：保留原有codes（未被破坏）
        assert feeder._interested_codes == ["000001.SZ"]


@pytest.mark.unit
@pytest.mark.backtest
@pytest.mark.db_cleanup  # 👈 类级别标记：所有测试自动清理数据库
class TestHistoricalDataAccess:
    """8. 历史数据访问测试"""

    # 定义清理配置：清理Bar表中code匹配TEST_HIST_%的数据
    CLEANUP_CONFIG = {
        'bar': {'code__like': 'TEST_HIST_%'}
    }

    def test_get_historical_data_single_symbol(self, configured_feeder):
        """测试单个股票成功获取数据"""
        from ginkgo.data.crud.bar_crud import BarCRUD
        from ginkgo.data.models import MBar
        from ginkgo.enums import FREQUENCY_TYPES
        import pandas as pd

        bar_crud = BarCRUD()
        test_code = "TEST_HIST_001.SZ"

        # 准备：插入3条Bar数据
        test_bars = [
            MBar(
                code=test_code,
                timestamp=datetime(2023, 6, 1, 9, 30),
                open=100.0,
                high=102.0,
                low=99.0,
                close=101.0,
                volume=1000000,
                amount=100500000.0,
                frequency=FREQUENCY_TYPES.DAY
            ),
            MBar(
                code=test_code,
                timestamp=datetime(2023, 6, 2, 9, 30),
                open=101.0,
                high=103.0,
                low=100.0,
                close=102.0,
                volume=1100000,
                amount=111000000.0,
                frequency=FREQUENCY_TYPES.DAY
            ),
            MBar(
                code=test_code,
                timestamp=datetime(2023, 6, 3, 9, 30),
                open=102.0,
                high=104.0,
                low=101.0,
                close=103.0,
                volume=1200000,
                amount=122000000.0,
                frequency=FREQUENCY_TYPES.DAY
            ),
        ]

        bar_crud.add_batch(test_bars)

        # 使用已配置的Feeder获取历史数据
        # bar_service.get()使用exclusive end_date，需要多加1天
        result = configured_feeder.get_historical_data(
            symbols=[test_code],
            start_time=datetime(2023, 6, 1),
            end_time=datetime(2023, 6, 4),
            data_type="bar"
        )

        # 验证：返回DataFrame
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

        # 验证：包含正确的股票代码
        assert (result["code"] == test_code).all()

        # 验证：数据正确性
        assert result.iloc[0]["close"] == 101.0
        assert result.iloc[1]["close"] == 102.0
        assert result.iloc[2]["close"] == 103.0

    def test_get_historical_data_multiple_symbols(self, configured_feeder):
        """测试多个股票数据同时获取并拼接"""
        from ginkgo.data.crud.bar_crud import BarCRUD
        from ginkgo.data.models import MBar
        from ginkgo.enums import FREQUENCY_TYPES
        import pandas as pd

        bar_crud = BarCRUD()
        test_code_1 = "TEST_HIST_002.SZ"
        test_code_2 = "TEST_HIST_003.SZ"

        # 步骤1：先查询，验证清理成功（应该为空）
        result_empty = configured_feeder.get_historical_data(
            symbols=[test_code_1, test_code_2],
            start_time=datetime(2023, 6, 1),
            end_time=datetime(2023, 6, 3),
            data_type="bar"
        )

        # 验证：返回空DataFrame
        assert isinstance(result_empty, pd.DataFrame)
        assert len(result_empty) == 0
        assert result_empty.empty

        # 步骤2：插入两个股票的数据
        test_bars = [
            # 股票1的数据
            MBar(code=test_code_1, timestamp=datetime(2023, 6, 1, 9, 30),
                 open=100.0, high=102.0, low=99.0, close=101.0,
                 volume=1000000, amount=100500000.0, frequency=FREQUENCY_TYPES.DAY),
            MBar(code=test_code_1, timestamp=datetime(2023, 6, 2, 9, 30),
                 open=101.0, high=103.0, low=100.0, close=102.0,
                 volume=1100000, amount=111000000.0, frequency=FREQUENCY_TYPES.DAY),
            # 股票2的数据
            MBar(code=test_code_2, timestamp=datetime(2023, 6, 1, 9, 30),
                 open=200.0, high=202.0, low=199.0, close=201.0,
                 volume=2000000, amount=200500000.0, frequency=FREQUENCY_TYPES.DAY),
            MBar(code=test_code_2, timestamp=datetime(2023, 6, 2, 9, 30),
                 open=201.0, high=203.0, low=200.0, close=202.0,
                 volume=2100000, amount=211000000.0, frequency=FREQUENCY_TYPES.DAY),
        ]
        bar_crud.add_batch(test_bars)

        # 步骤3：再次查询
        result = configured_feeder.get_historical_data(
            symbols=[test_code_1, test_code_2],
            start_time=datetime(2023, 6, 1),
            end_time=datetime(2023, 6, 3),
            data_type="bar"
        )

        # 验证：返回DataFrame包含4条数据
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 4

        # 验证：包含2个不同的股票代码
        codes = result["code"].unique()
        assert len(codes) == 2
        assert test_code_1 in codes
        assert test_code_2 in codes

        # 验证：每个股票有2条数据
        stock1_data = result[result["code"] == test_code_1]
        stock2_data = result[result["code"] == test_code_2]
        assert len(stock1_data) == 2
        assert len(stock2_data) == 2

        # 验证：数据值正确
        assert stock1_data.iloc[0]["close"] == 101.0
        assert stock2_data.iloc[0]["close"] == 201.0

    def test_get_historical_data_time_range_filter(self, configured_feeder):
        """测试时间范围过滤功能"""
        from ginkgo.data.crud.bar_crud import BarCRUD
        from ginkgo.data.models import MBar
        from ginkgo.enums import FREQUENCY_TYPES
        import pandas as pd

        bar_crud = BarCRUD()
        test_code = "TEST_HIST_004.SZ"

        # 插入5天数据（6/1 - 6/5）
        test_bars = [
            MBar(
                code=test_code,
                timestamp=datetime(2023, 6, day, 9, 30),
                open=100.0 + day,
                high=102.0 + day,
                low=99.0 + day,
                close=101.0 + day,  # close价格=101+day，便于验证
                volume=1000000,
                amount=100000000.0,
                frequency=FREQUENCY_TYPES.DAY
            )
            for day in range(1, 6)  # day=1,2,3,4,5 对应6/1-6/5
        ]
        bar_crud.add_batch(test_bars)

        # 查询，只要6/2 - 6/4的数据（bar_service end_date exclusive，需+1天）
        result = configured_feeder.get_historical_data(
            symbols=[test_code],
            start_time=datetime(2023, 6, 2),
            end_time=datetime(2023, 6, 5),
            data_type="bar"
        )

        # 验证：只返回3条记录（时间范围过滤生效）
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

        # 验证：数据正确性（按close价格判断是哪一天）
        assert result.iloc[0]["close"] == 103.0  # 6/2: 101+2
        assert result.iloc[1]["close"] == 104.0  # 6/3: 101+3
        assert result.iloc[2]["close"] == 105.0  # 6/4: 101+4

    def test_get_historical_data_no_data_returns_empty(self, configured_feeder):
        """测试无数据时返回空DataFrame"""
        import pandas as pd

        # 查询不存在的股票
        result = configured_feeder.get_historical_data(
            symbols=["TEST_HIST_999.SZ"],
            start_time=datetime(2023, 6, 1),
            end_time=datetime(2023, 6, 3),
            data_type="bar"
        )

        # 验证：返回空DataFrame
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        assert result.empty

    def test_get_historical_data_multiple_symbols_with_time_filter(self, configured_feeder):
        """测试多股票+时间范围过滤组合功能"""
        from ginkgo.data.crud.bar_crud import BarCRUD
        from ginkgo.data.models import MBar
        from ginkgo.enums import FREQUENCY_TYPES
        import pandas as pd

        bar_crud = BarCRUD()
        test_code_1 = "TEST_HIST_006.SZ"
        test_code_2 = "TEST_HIST_007.SZ"

        # 插入2个股票各5天数据（6/1-6/5）
        test_bars = []
        for code, base_price in [(test_code_1, 100.0), (test_code_2, 200.0)]:
            for day in range(1, 6):
                test_bars.append(
                    MBar(
                        code=code,
                        timestamp=datetime(2023, 6, day, 9, 30),
                        open=base_price + day,
                        high=base_price + day + 2,
                        low=base_price + day - 1,
                        close=base_price + day + 1,  # close=base+day+1
                        volume=1000000,
                        amount=100000000.0,
                        frequency=FREQUENCY_TYPES.DAY
                    )
                )
        bar_crud.add_batch(test_bars)

        # 查询6/2-6/4（3天，bar_service end_date exclusive，需+1天）
        result = configured_feeder.get_historical_data(
            symbols=[test_code_1, test_code_2],
            start_time=datetime(2023, 6, 2),
            end_time=datetime(2023, 6, 5),
            data_type="bar"
        )

        # 验证：返回6条数据（2股票×3天）
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 6

        # 验证：每个股票3条数据
        stock1_data = result[result["code"] == test_code_1]
        stock2_data = result[result["code"] == test_code_2]
        assert len(stock1_data) == 3
        assert len(stock2_data) == 3

        # 验证：数据时间正确（通过close价格判断）
        assert stock1_data.iloc[0]["close"] == 103.0  # 6/2: 100+2+1
        assert stock2_data.iloc[0]["close"] == 203.0  # 6/2: 200+2+1

    def test_get_historical_data_unsupported_datatype(self, configured_feeder):
        """测试不支持的数据类型返回空结果（容错处理）"""
        import pandas as pd

        test_code = "TEST_HIST_006.SZ"
        start_time = datetime(2023, 6, 1)
        end_time = datetime(2023, 6, 5)

        # 执行：使用不支持的数据类型 "tick"（目前只支持 "bar"）
        result = configured_feeder.get_historical_data(
            symbols=[test_code],
            start_time=start_time,
            end_time=end_time,
            data_type="tick"  # 不支持的类型
        )

        # 验证：返回空DataFrame（不抛异常）
        assert isinstance(result, pd.DataFrame)
        assert result.empty
        assert len(result) == 0
