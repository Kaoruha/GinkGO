"""
Selector 时间窗口参数校验：momentum.window / popularity.span 必须为 [1, 365] 内 int。

防御：过大的窗口会让 bar 批量查询一次取全表（master 库 5423 code × 35 年 ≈ 1568 万行）
导致 OOM/卡死。源头 __init__ 拒绝非法值，fail-fast 早于回测运行期崩溃。
"""

import unittest

from ginkgo.trading.selectors.momentum_selector import MomentumSelector
from ginkgo.trading.selectors.popularity_selector import PopularitySelector


class MomentumSelectorWindowValidationTest(unittest.TestCase):
    def test_accepts_default_and_boundary_values(self):
        """window ∈ {1, 20(默认), 365(上限)} 均应正常实例化并落属性。"""
        for w in (1, 20, 365):
            with self.subTest(window=w):
                s = MomentumSelector(name="t", window=w)
                self.assertEqual(s.window, w)

    def test_rejects_zero(self):
        """window=0 → 窗口为空，无意义，拒。"""
        with self.assertRaises(ValueError):
            MomentumSelector(name="t", window=0)

    def test_rejects_negative(self):
        """负 window → start>end 空集，静默失败，拒。"""
        with self.assertRaises(ValueError):
            MomentumSelector(name="t", window=-5)

    def test_rejects_above_max(self):
        """window>365 → 批量取数 OOM 风险，拒。"""
        with self.assertRaises(ValueError):
            MomentumSelector(name="t", window=366)

    def test_rejects_non_int(self):
        """str/float/None → timedelta(days=) 语义错误，拒。bool 亦拒（是 int 子类）。"""
        for bad in ("20", 20.0, None, True):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    MomentumSelector(name="t", window=bad)


class PopularitySelectorSpanValidationTest(unittest.TestCase):
    def test_accepts_default_and_boundary_values(self):
        """span ∈ {1, 30(默认), 365(上限)} 均应正常实例化并落属性。"""
        for sp in (1, 30, 365):
            with self.subTest(span=sp):
                s = PopularitySelector(name="t", span=sp)
                self.assertEqual(s.span, sp)

    def test_rejects_zero(self):
        with self.assertRaises(ValueError):
            PopularitySelector(name="t", span=0)

    def test_rejects_negative(self):
        with self.assertRaises(ValueError):
            PopularitySelector(name="t", span=-5)

    def test_rejects_above_max(self):
        with self.assertRaises(ValueError):
            PopularitySelector(name="t", span=366)

    def test_rejects_non_int(self):
        for bad in ("30", 30.0, None, True):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    PopularitySelector(name="t", span=bad)


if __name__ == "__main__":
    unittest.main()
