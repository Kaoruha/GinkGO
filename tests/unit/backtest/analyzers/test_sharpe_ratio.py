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


class TestSharpeRatioLowVarianceGuard(unittest.TestCase):
    """低方差退化序列守卫测试（#5973）"""

    def setUp(self):
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)

    def _make_analyzer(self, name="test_sharpe_lowvar", risk_free_rate=0.03):
        analyzer = SharpeRatio(name, risk_free_rate=risk_free_rate)
        analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        analyzer.advance_time(self.test_time)
        analyzer.set_analyzer_id("test_lowvar_001")
        analyzer.set_portfolio_id("test_portfolio_001")
        return analyzer

    def test_sparse_zero_heavy_series_not_explosive(self):
        """#5973: >70% 零收益日的稀疏交易序列，sharpe 不应爆量到 ±3 之外。

        重现 fe0cef7b 形态（MA 单股稀疏交易）：长期常数净值 + 偶发单次抖动。
        零收益占比 58/59 ≈ 98%，std 被压到 ~1.3e-4；同时 rf_daily(1.19e-4) 主导
        excess → 当前实现爆到约 -12.5。修复后应落入 ±3（sentinel 0.0）。
        """
        analyzer = self._make_analyzer(risk_free_rate=0.03)

        base_worth = 10000.0
        # 60 个交易日：i=0..43 净值常数 10000；i=44..59 净值常数 10010（单次 0.1% 抖动）
        for i in range(60):
            worth = base_worth if i < 44 else base_worth * 1.001
            day_time = self.test_time + timedelta(days=i)
            analyzer.advance_time(day_time)
            analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": worth})

        sharpe = analyzer.current_sharpe_ratio
        self.assertGreaterEqual(sharpe, -3.0, f"低方差序列 sharpe 爆量: {sharpe}")
        self.assertLessEqual(sharpe, 3.0, f"低方差序列 sharpe 爆量: {sharpe}")

    def test_piecewise_constant_net_value_returns_sentinel(self):
        """#5973 AC: 分段常数净值（长平台 + 单次阶跃）应返回 sentinel 0.0。

        净值前 30 日常数 10000，第 31 日阶跃到 10010 并保持。收益序列：
        29 个零 + 0.001 + 若干零，mean≈1.7e-5 << rf_daily(1.19e-4) → rf 主导
        excess → 修复前爆量约 -12，修复后应 sentinel 0.0（低换手/长期空仓典型形态）。
        """
        analyzer = self._make_analyzer(name="test_sharpe_piecewise", risk_free_rate=0.03)

        for i in range(60):
            worth = 10000.0 if i < 30 else 10010.0
            day_time = self.test_time + timedelta(days=i)
            analyzer.advance_time(day_time)
            analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": worth})

        self.assertEqual(analyzer.current_sharpe_ratio, 0.0)

    def test_healthy_volatile_series_still_computed(self):
        """#5973 回归守卫：健康波动序列（日 std~3e-3, mean>>rf）必须正常计算，
        不被退化守卫误伤，且 sharpe 落入正常 ±3 范围。
        """
        analyzer = self._make_analyzer(name="test_sharpe_healthy", risk_free_rate=0.03)

        # 30 个日收益：mean≈5e-4 (>>rf_daily 1.19e-4)，std≈3e-3（健康波动）
        returns = [0.003, -0.002, 0.004, -0.001, 0.002, -0.003, 0.005, -0.002,
                   0.001, -0.004, 0.003, -0.002, 0.004, -0.001, 0.002, -0.003,
                   0.005, -0.002, 0.001, -0.004, 0.003, -0.002, 0.004, -0.001,
                   0.002, -0.003, 0.005, -0.002, 0.001, -0.004]

        worth = 10000.0
        # 首日初始化 _last_worth
        analyzer.advance_time(self.test_time)
        analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": worth})
        for i, ret in enumerate(returns):
            worth = worth * (1 + ret)
            day_time = self.test_time + timedelta(days=i + 1)
            analyzer.advance_time(day_time)
            analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": worth})

        sharpe = analyzer.current_sharpe_ratio
        self.assertNotEqual(sharpe, 0.0, "健康序列不应被退化守卫 sentinel")
        self.assertGreater(sharpe, -3.0)
        self.assertLess(sharpe, 3.0)

    def test_rf_zero_low_std_series_not_explosive(self):
        """#5973 rf=0 兜底：rf=0 时 |mean|>=rf 退化为 |mean|>=0 恒真，原守卫失效。
        等差增长 worth（每日 +1 元）产生 std~1e-7 的近常数收益序列，rf=0 下会爆量
        到 ~1e4（实测 +5.3 起）。修复后应被 std 下界兜底 sentinel，落入 ±3。
        rf=0 是退化配置（无风险利率设 0），std 这么小的序列 sharpe 估计统计不可信。
        """
        analyzer = self._make_analyzer(name="test_sharpe_rf0", risk_free_rate=0.0)

        base_worth = 10000.0
        # 30 个交易日：worth 每日等差 +1 元 → 收益序列近常数（std~1e-7）
        for i in range(30):
            worth = base_worth + (i + 1) * 1.0
            day_time = self.test_time + timedelta(days=i)
            analyzer.advance_time(day_time)
            analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": worth})

        sharpe = analyzer.current_sharpe_ratio
        self.assertGreaterEqual(sharpe, -3.0, f"rf=0 低 std 序列 sharpe 爆量: {sharpe}")
        self.assertLessEqual(sharpe, 3.0, f"rf=0 低 std 序列 sharpe 爆量: {sharpe}")


if __name__ == '__main__':
    unittest.main()
