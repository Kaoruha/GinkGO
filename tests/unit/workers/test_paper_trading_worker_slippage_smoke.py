"""epic #6851 ADR-037 Amendment 2: paper_trading_worker slippage 注入 smoke (CI gate 覆盖信号).

paper 侧成交价模型注入被 containers import 链触达 (class body executed → 非 exempt)
但 _resolve_slippage_rate/_build_fill_price_model 方法体无 smoke 调 → diff coverage gate 红.
本 smoke 用 PropertyMock patch GCONF.PAPER_SLIPPAGE_RATE 调起 _resolve_slippage_rate (3 分支)
+ _build_fill_price_model (attitude/slippage 两分支) 补覆盖信号, 锁定 A1 语义.

ADR-037 Amendment 2: slippage 改存 GCONF (共享 SimBroker 存 N 用 1 + schema 漂移根因),
不再读 MPortfolio.slippage (已回退). paper worker 是 1 worker 1 共享 broker = worker 级参数.

注: import 轻量 (仅 threading/enums/KafkaTopics, 无 Redis/Kafka 连接初始化).
"""
from unittest.mock import patch, PropertyMock

from ginkgo.libs import GCONF
from ginkgo.libs.core.config import GinkgoConfig
from ginkgo.workers.paper_trading_worker import PaperTradingWorker


class TestResolveSlippageRate:
    """_resolve_slippage_rate 读 GCONF.PAPER_SLIPPAGE_RATE (ADR-037 Amendment 2 模拟侧).

    paper worker 共享 broker 级参数: None/脏 → attitude; 有值 → slippage 确定性.
    """

    def test_none(self):
        with patch.object(GinkgoConfig, "PAPER_SLIPPAGE_RATE", new_callable=PropertyMock, return_value=None):
            assert PaperTradingWorker._resolve_slippage_rate() is None

    def test_float(self):
        with patch.object(GinkgoConfig, "PAPER_SLIPPAGE_RATE", new_callable=PropertyMock, return_value=0.002):
            assert PaperTradingWorker._resolve_slippage_rate() == 0.002

    def test_dirty_data_returns_none(self):
        """脏数据 (非数值) 回退 None, 不阻塞 worker 启动."""
        with patch.object(GinkgoConfig, "PAPER_SLIPPAGE_RATE", new_callable=PropertyMock, return_value="abc"):
            assert PaperTradingWorker._resolve_slippage_rate() is None


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
