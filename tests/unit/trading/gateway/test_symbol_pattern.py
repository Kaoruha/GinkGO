"""
Test TradeGateway symbol pattern matching

This test suite validates dynamic regex pattern matching for detecting
market types from symbol codes (A-shares, Crypto, HK stocks, Futures, US stocks).
"""

import pytest
from ginkgo.trading.gateway.trade_gateway import TradeGateway
from ginkgo.trading.brokers.sim_broker import SimBroker


class TestSymbolPatternMatching:
    """测试动态符号模式匹配功能"""

    def _make_brokers(self):
        """创建测试用的Broker实例"""
        sim = SimBroker()
        sim.market = "SIM"
        return [sim]

    def test_a_share_pattern_sz(self):
        """测试深圳A股代码识别 (6位数字.SZ)"""
        gw = TradeGateway(brokers=self._make_brokers())
        assert gw._get_market_by_code("000001.SZ") == "A股"
        assert gw._get_market_by_code("300001.SZ") == "A股"
        assert gw._get_market_by_code("002594.SZ") == "A股"

    def test_a_share_pattern_sh(self):
        """测试上海A股代码识别 (6位数字.SH)"""
        gw = TradeGateway(brokers=self._make_brokers())
        assert gw._get_market_by_code("600000.SH") == "A股"
        assert gw._get_market_by_code("000001.SH") == "A股"

    def test_crypto_pattern(self):
        """测试加密货币代码识别 (字母/USDT格式)"""
        gw = TradeGateway(brokers=self._make_brokers())
        assert gw._get_market_by_code("BTC/USDT") == "Crypto"
        assert gw._get_market_by_code("ETH/USDT") == "Crypto"
        assert gw._get_market_by_code("SOL/USDT") == "Crypto"

    def test_hk_stock_pattern(self):
        """测试港股代码识别 (5位数字.HK)"""
        gw = TradeGateway(brokers=self._make_brokers())
        assert gw._get_market_by_code("00700.HK") == "港股"
        assert gw._get_market_by_code("00941.HK") == "港股"
        assert gw._get_market_by_code("03690.HK") == "港股"

    def test_futures_pattern(self):
        """测试期货代码识别 (IF/IC/IH/IM/MO + 4位数字)"""
        gw = TradeGateway(brokers=self._make_brokers())
        assert gw._get_market_by_code("IF2312") == "期货"
        assert gw._get_market_by_code("IC2312") == "期货"
        assert gw._get_market_by_code("IH2312") == "期货"
        assert gw._get_market_by_code("IM2403") == "期货"
        assert gw._get_market_by_code("MO2403") == "期货"

    def test_us_stock_pattern(self):
        """测试美股代码识别 (1-5位纯字母)"""
        gw = TradeGateway(brokers=self._make_brokers())
        assert gw._get_market_by_code("AAPL") == "美股"
        assert gw._get_market_by_code("TSLA") == "美股"
        assert gw._get_market_by_code("MSFT") == "美股"
        assert gw._get_market_by_code("GOOG") == "美股"

    def test_unknown_symbol_no_crash(self):
        """测试未知符号不崩溃，返回默认市场"""
        gw = TradeGateway(brokers=self._make_brokers())
        result = gw._get_market_by_code("UNKNOWN123")
        assert result is not None
        # 未知符号应返回默认市场（A股）
        assert result == "A股"

    def test_empty_code_returns_default(self):
        """测试空代码返回默认市场"""
        gw = TradeGateway(brokers=self._make_brokers())
        result = gw._get_market_by_code("")
        assert result == "A股"
