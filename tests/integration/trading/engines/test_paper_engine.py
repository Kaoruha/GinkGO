# Upstream: ginkgo.trading.paper.paper_engine
# Downstream: pytest
# Role: PaperTradingEngine 单元测试

"""
PaperTradingEngine 测试

TDD Green 阶段: 测试用例实现
"""

import pytest
from datetime import datetime
from decimal import Decimal


@pytest.mark.unit
class TestPaperTradingEngine:
    """PaperTradingEngine 单元测试"""

    def test_init(self):
        """测试引擎初始化"""
        from ginkgo.trading.paper.paper_engine import PaperTradingEngine

        engine = PaperTradingEngine()
        assert engine.slippage_model is not None
        assert engine.is_running == False

    def test_init_with_portfolio(self):
        """测试带 Portfolio 初始化"""
        from ginkgo.trading.paper.paper_engine import PaperTradingEngine

        engine = PaperTradingEngine(portfolio_id="test_portfolio")
        assert engine.portfolio_id == "test_portfolio"
        assert engine.is_running == False

    def test_init_with_slippage_options(self):
        """测试滑点模型选项"""
        from ginkgo.trading.paper.paper_engine import PaperTradingEngine
        from ginkgo.trading.paper.slippage_models import FixedSlippage

        # 使用字符串初始化
        engine = PaperTradingEngine(slippage_model="fixed", slippage_value=Decimal("0.01"))
        assert isinstance(engine.slippage_model, FixedSlippage)

        # 使用实例初始化
        model = FixedSlippage(slippage=Decimal("0.05"))
        engine2 = PaperTradingEngine(slippage_model=model)
        assert engine2.slippage_model is model

    def test_start(self):
        """测试启动引擎"""
        from ginkgo.trading.paper.paper_engine import PaperTradingEngine

        engine = PaperTradingEngine(portfolio_id="test")
        result = engine.start()
        assert result == True
        assert engine.is_running == True

    def test_stop(self):
        """测试停止引擎"""
        from ginkgo.trading.paper.paper_engine import PaperTradingEngine

        engine = PaperTradingEngine(portfolio_id="test")
        engine.start()
        result = engine.stop()
        assert result == True
        assert engine.is_running == False

    def test_on_daily_close(self):
        """测试日收盘事件处理"""
        from ginkgo.trading.paper.paper_engine import PaperTradingEngine

        engine = PaperTradingEngine(portfolio_id="test")
        engine.start()
        signals = engine.on_daily_close("20240101")
        assert isinstance(signals, list)
        assert engine.state.current_date == "20240101"
        engine.stop()

    def test_get_current_state(self):
        """测试获取当前状态"""
        from ginkgo.trading.paper.paper_engine import PaperTradingEngine
        from ginkgo.trading.paper.models import PaperTradingState

        engine = PaperTradingEngine(portfolio_id="test")
        state = engine.get_current_state()
        assert isinstance(state, PaperTradingState)
        assert state.portfolio_id == "test"

    def test_generate_signals(self):
        """测试信号生成"""
        from ginkgo.trading.paper.paper_engine import PaperTradingEngine

        engine = PaperTradingEngine(portfolio_id="test")
        engine.start()
        signals = engine.generate_signals("20240101")
        assert isinstance(signals, list)
        engine.stop()

    def test_compare_with_backtest(self):
        """测试与回测对比"""
        from ginkgo.trading.paper.paper_engine import PaperTradingEngine
        from ginkgo.trading.paper.models import PaperTradingResult

        engine = PaperTradingEngine(portfolio_id="test")
        result = engine.compare_with_backtest("backtest_001")
        assert isinstance(result, PaperTradingResult)
        assert result.portfolio_id == "test"

    def test_calculate_commission(self):
        """测试佣金计算"""
        from ginkgo.trading.paper.paper_engine import PaperTradingEngine
        from decimal import Decimal

        engine = PaperTradingEngine()
        # 大额交易: 10000 * 0.0003 = 3 < 5, 取最小佣金 5
        assert engine.calculate_commission(Decimal("10000")) == Decimal("5")
        # 更大额: 100000 * 0.0003 = 30 > 5
        assert engine.calculate_commission(Decimal("100000")) == Decimal("30")

    def test_apply_slippage(self):
        """测试滑点应用"""
        from ginkgo.trading.paper.paper_engine import PaperTradingEngine
        from ginkgo.enums import DIRECTION_TYPES
        from decimal import Decimal

        engine = PaperTradingEngine(slippage_model="percentage", slippage_value=Decimal("0.001"))
        adjusted = engine.apply_slippage(Decimal("10.00"), DIRECTION_TYPES.LONG)
        assert adjusted == Decimal("10.01000")


@pytest.mark.unit
class TestPaperTradingEngineIntegration:
    """PaperTradingEngine 集成测试"""

    def test_full_cycle(self):
        """测试完整周期: 初始化 -> 启动 -> 运行 -> 停止"""
        from ginkgo.trading.paper.paper_engine import PaperTradingEngine

        # 初始化
        engine = PaperTradingEngine(portfolio_id="test_portfolio")

        # 启动
        assert engine.start() == True
        assert engine.is_running == True

        # 运行
        signals = engine.on_daily_close("20240101")
        assert isinstance(signals, list)

        # 停止
        assert engine.stop() == True
        assert engine.is_running == False

    def test_to_dict(self):
        """测试序列化"""
        from ginkgo.trading.paper.paper_engine import PaperTradingEngine

        engine = PaperTradingEngine(portfolio_id="test")
        d = engine.to_dict()
        assert d["portfolio_id"] == "test"
        assert "paper_id" in d
        assert "is_running" in d
