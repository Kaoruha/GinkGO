"""epic #6851 ADR-037 D2: paper_trading_worker slippage 注入 smoke (CI gate 覆盖信号).

paper 侧成交价模型注入被 containers import 链触达 (class body executed → 非 exempt)
但 assemble_engine 重方法无 smoke 调其方法体 → diff coverage gate 红 (check_diff_coverage).
本 smoke 调起 _resolve_slippage_from_portfolios (4 分支) + _build_fill_price_model
(attitude/slippage 两分支) 补覆盖信号, 锁定 A1 语义 (slippage_rate 推导 policy).

注: import 轻量 (仅 threading/enums/KafkaTopics, 无 Redis/Kafka 连接初始化).
"""
from unittest.mock import MagicMock

from ginkgo.workers.paper_trading_worker import PaperTradingWorker


def _pf(slippage):
    """构造带 .slippage 属性的假 portfolio (免连 DB)."""
    m = MagicMock()
    m.slippage = slippage
    return m


class TestResolveSlippageFromPortfolios:
    """_resolve_slippage_from_portfolios 4 分支 (ADR-037 D2 模拟侧取值)."""

    def test_empty_returns_none(self):
        assert PaperTradingWorker._resolve_slippage_from_portfolios([]) is None

    def test_none_slippage_returns_none(self):
        assert PaperTradingWorker._resolve_slippage_from_portfolios([_pf(None)]) is None

    def test_float_value(self):
        assert PaperTradingWorker._resolve_slippage_from_portfolios([_pf(0.001)]) == 0.001

    def test_dirty_data_returns_none(self):
        """脏数据 (非数值) 回退 None, 不阻塞 worker 启动."""
        assert PaperTradingWorker._resolve_slippage_from_portfolios([_pf("abc")]) is None


class TestBuildFillPriceModel:
    """_build_fill_price_model attitude/slippage 两分支 (A1 语义)."""

    def test_none_rate_attitude(self):
        from ginkgo.trading.brokers.fill_price_model import AttitudePricing
        m = PaperTradingWorker._build_fill_price_model(None)
        assert isinstance(m, AttitudePricing), "None rate → attitude 零回归回退"

    def test_rate_slippage(self):
        from ginkgo.trading.brokers.fill_price_model import DeterministicSlippage
        m = PaperTradingWorker._build_fill_price_model(0.002)
        assert isinstance(m, DeterministicSlippage), "rate → slippage 确定性"
