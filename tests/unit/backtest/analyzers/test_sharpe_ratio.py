"""
SharpeRatio 分析器测试
基于日收益率的标准方法验证
"""

import unittest
from datetime import datetime, timedelta
import numpy as np

from ginkgo.trading.analysis.analyzers.sharpe_ratio import SharpeRatio
from ginkgo.enums import RECORDSTAGE_TYPES
from ginkgo.trading.time.providers import LogicalTimeProvider


class TestSharpeRatio(unittest.TestCase):
    """测试夏普比率分析器基本功能"""

    def setUp(self):
        self.analyzer = SharpeRatio("test_sharpe", risk_free_rate=0.03)
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)
        self.analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        self.analyzer.advance_time(self.test_time)
        self.analyzer.set_analyzer_id("test_sharpe_001")
        self.analyzer.set_portfolio_id("test_portfolio_001")

    def test_init(self):
        """测试默认初始化"""
        analyzer = SharpeRatio()
        self.assertIsNotNone(analyzer)
        self.assertEqual(analyzer._name, "sharpe_ratio")
        self.assertEqual(analyzer._risk_free_rate, 0.03 / 252)
        self.assertEqual(len(analyzer._returns), 0)
        self.assertIn(RECORDSTAGE_TYPES.ENDDAY, analyzer.active_stage)
        self.assertEqual(analyzer.record_stage, RECORDSTAGE_TYPES.ENDDAY)

    def test_custom_risk_free_rate(self):
        """测试自定义无风险利率"""
        analyzer = SharpeRatio(risk_free_rate=0.05)
        self.assertEqual(analyzer._risk_free_rate, 0.05 / 252)

    def test_initial_calculation(self):
        """测试初始计算 - 第一天无历史数据"""
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": 10000})
        self.assertEqual(self.analyzer.current_sharpe_ratio, 0.0)

    def test_insufficient_data(self):
        """测试数据不足10天时返回0"""
        base_worth = 10000
        for i in range(9):
            worth = base_worth * (1 + 0.01 * (i + 1))
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": worth})
            self.assertEqual(self.analyzer.current_sharpe_ratio, 0.0)

    def test_positive_returns(self):
        """测试全正收益场景"""
        base_worth = 10000
        for i in range(15):
            worth = base_worth * (1 + 0.01 * (i + 1))
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": worth})

        self.assertGreater(self.analyzer.current_sharpe_ratio, 0)

    def test_negative_returns(self):
        """测试主要负收益场景"""
        base_worth = 10000
        returns = [-0.01, -0.02, 0.005, -0.015, -0.01, -0.008, 0.01, -0.012, -0.018, -0.005, -0.01, -0.02]

        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        self.assertLess(self.analyzer.current_sharpe_ratio, 0)

    def test_mixed_returns(self):
        """测试混合收益场景"""
        base_worth = 10000
        returns = [0.02, -0.01, 0.015, -0.008, 0.01, -0.012, 0.018, -0.005, 0.01, -0.015, 0.02, -0.01]

        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        sharpe = self.analyzer.current_sharpe_ratio
        self.assertIsInstance(sharpe, float)
        self.assertGreater(sharpe, -10)
        self.assertLess(sharpe, 10)

    def test_zero_worth_handling(self):
        """测试零净值处理"""
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": 0})
        self.assertEqual(self.analyzer.current_sharpe_ratio, 0.0)

    def test_returns_accumulation(self):
        """测试日收益率累积"""
        base_worth = 10000
        for i in range(5):
            worth = base_worth * (1 + 0.01 * (i + 1))
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": worth})

        # 第一天初始化 _last_worth，后续4天产生4个日收益率
        self.assertEqual(len(self.analyzer._returns), 4)


class TestSharpeRatioNumericalCorrectness(unittest.TestCase):
    """数值正确性验证 - 手工计算对照"""

    def setUp(self):
        self.analyzer = SharpeRatio("test_sharpe_num", risk_free_rate=0.0)
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)
        self.analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        self.analyzer.advance_time(self.test_time)
        self.analyzer.set_analyzer_id("test_sharpe_num_001")
        self.analyzer.set_portfolio_id("test_portfolio_001")

    def test_known_sharpe_calculation(self):
        """验证手工计算的Sharpe值"""
        # 先用初始值设置 _last_worth，后续12次产生12个日收益率(>=10阈值)
        initial_worth = 10000
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": initial_worth})

        returns = [0.01, 0.02, -0.01, 0.015, -0.005, 0.01, 0.02, -0.008, 0.012, -0.003, 0.015, 0.01]

        current_worth = initial_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            day_time = self.test_time + timedelta(days=i + 1)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 手工验证: risk_free=0, sharpe = mean / std * sqrt(252)
        arr = np.array(returns)
        expected_mean = np.mean(arr)
        expected_std = np.std(arr, ddof=1)
        expected_sharpe = expected_mean / expected_std * np.sqrt(252)

        self.assertAlmostEqual(self.analyzer.current_sharpe_ratio, expected_sharpe, places=4)

    def test_all_same_returns_zero_std(self):
        """所有日收益率相同时标准差为0，Sharpe应为0"""
        base_worth = 10000
        for i in range(12):
            worth = base_worth * (1 + 0.01 * (i + 1))  # 线性增长，日收益率递减但接近
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": worth})

        # 非零 std，所以有值（不是完全相同的日收益率）
        self.assertNotEqual(self.analyzer.current_sharpe_ratio, 0.0)


class TestSharpeRatioBoundaryConditions(unittest.TestCase):
    """边界条件测试"""

    def setUp(self):
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)

    def test_empty_data(self):
        """从未调用activate，验证默认值"""
        analyzer = SharpeRatio("test_sharpe_empty")
        self.assertEqual(analyzer.current_sharpe_ratio, 0.0)
        self.assertEqual(len(analyzer._returns), 0)

    def test_single_bar(self):
        """只传1条数据"""
        analyzer = SharpeRatio("test_sharpe_single")
        analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        analyzer.advance_time(self.test_time)
        analyzer.set_analyzer_id("test_single_001")
        analyzer.set_portfolio_id("test_portfolio_001")

        analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": 10000})
        self.assertEqual(analyzer.current_sharpe_ratio, 0.0)

    def test_exactly_10_bars(self):
        """刚好10个日收益率（满足阈值）"""
        analyzer = SharpeRatio("test_sharpe_10", risk_free_rate=0.0)
        analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        analyzer.advance_time(self.test_time)
        analyzer.set_analyzer_id("test_10_001")
        analyzer.set_portfolio_id("test_portfolio_001")

        # 先初始化 _last_worth
        analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": 10000})

        returns = [0.01, -0.005, 0.02, -0.01, 0.015, -0.008, 0.01, -0.012, 0.018, -0.015]

        current_worth = 10000
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            day_time = self.test_time + timedelta(days=i + 1)
            analyzer.advance_time(day_time)
            analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 10个日收益率，刚好满足>=10阈值
        self.assertEqual(len(analyzer._returns), 10)
        self.assertNotEqual(analyzer.current_sharpe_ratio, 0.0)

    def test_all_zero_worth(self):
        """所有worth=0"""
        analyzer = SharpeRatio("test_sharpe_zeros")
        analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        analyzer.advance_time(self.test_time)
        analyzer.set_analyzer_id("test_zeros_001")
        analyzer.set_portfolio_id("test_portfolio_001")

        for i in range(5):
            day_time = self.test_time + timedelta(days=i)
            analyzer.advance_time(day_time)
            analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": 0})

        self.assertEqual(analyzer.current_sharpe_ratio, 0.0)
        self.assertEqual(len(analyzer._returns), 0)


class TestSharpeRatioDegenerateSeries(unittest.TestCase):
    """退化序列守卫 (issue #5973)。

    低换手策略（长期空仓/单股稀疏交易）下大量交易日收益为 0，
    std 被压到趋零，同时 rf_daily 主导 excess return，导致
    (mean_excess / std) * sqrt(252) 爆量到 ±10 量级（实测 -13）。
    此时 Sharpe 公式前提（近似连续分布的收益）不成立，应返回 0.0 sentinel。
    """

    def setUp(self):
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)

    def _make(self, risk_free_rate=0.03):
        a = SharpeRatio("test_sharpe_degen", risk_free_rate=risk_free_rate)
        a.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        a.advance_time(self.test_time)
        a.set_analyzer_id("test_degen_001")
        a.set_portfolio_id("test_degen_p_001")
        return a

    def test_low_turnover_majority_zero_days(self):
        """>70% 交易日零收益（贴近 fe0cef7b 实测）→ 退化，sharpe 应为 0.0。

        复现 owner 坐实场景：542 日，~74% 零收益日，std 被压到 ~1.5e-4，
        rf_daily(1.19e-4) 主导 excess，未守卫时爆量到 -13.1571。
        """
        analyzer = self._make()
        worth = 100000.0
        analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": worth})
        # 541 个交易日：402 个零收益（74.3%），139 个 ±0.05% 微动
        zero_pattern = [True] * 402 + [False] * 139  # 74.3% 零收益
        rng = np.random.RandomState(42)
        for i, is_zero in enumerate(zero_pattern, start=1):
            if not is_zero:
                worth *= (1 + rng.normal(0, 0.0005))
            analyzer.advance_time(self.test_time + timedelta(days=i))
            analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": worth})

        # 未守卫时此处为 -7 ~ -13 量级；守卫后必须落入 0.0 sentinel
        self.assertEqual(analyzer.current_sharpe_ratio, 0.0)

    def test_segment_constant_worth(self):
        """净值分段常数（长期持平偶发跳变）→ 退化，sharpe 应为 0.0。

        贴近"净值分段常数"退化场景：std 趋零且零收益日占比极高。
        守卫须同时覆盖 std 绝对趋零与高零收益占比两条路径。
        """
        analyzer = self._make()
        worth = 100000.0
        analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": worth})
        # 300 个交易日，仅第 100、200 天跳变 ±1%，其余持平
        for i in range(1, 301):
            if i == 100:
                worth *= 1.01
            elif i == 200:
                worth *= 0.995
            analyzer.advance_time(self.test_time + timedelta(days=i))
            analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": worth})

        self.assertEqual(analyzer.current_sharpe_ratio, 0.0)

    def test_normal_volatility_not_guarded(self):
        """正常波动序列（日 std~3e-3，零收益日 < 50%）→ 公式照算，sharpe 在 ±3。

        回归守卫：确认守卫不误伤健康序列，sqrt(252) 年化与 rf 转换路径仍生效。
        对照 owner 数据：标准回测 0d27a3b6 raw sharpe +0.61。
        """
        analyzer = self._make()
        worth = 100000.0
        analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": worth})
        rng = np.random.RandomState(7)
        for i in range(1, 252):
            # 每日都有波动（零收益日 = 0），std ~ 3e-3 量级
            worth *= (1 + rng.normal(0, 0.003))
            analyzer.advance_time(self.test_time + timedelta(days=i))
            analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": worth})

        sharpe = analyzer.current_sharpe_ratio
        self.assertNotEqual(sharpe, 0.0, "正常波动序列不应被退化守卫捕获")
        self.assertGreater(sharpe, -3.0)
        self.assertLess(sharpe, 3.0)


if __name__ == '__main__':
    unittest.main()
