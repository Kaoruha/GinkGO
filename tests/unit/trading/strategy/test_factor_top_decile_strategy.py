"""FactorTopDecileStrategy 测试 -- #6796 验收 (截面排名 + PIT + 多因子 + 走步 OOS)

fixture: 5 code universe, factor ROC5 值 A<B<C<D<E (与未来收益正相关);
         decile=5 → top 5//5=1 → 仅最高分 E 做多。
"""
import pytest
from datetime import datetime
from types import SimpleNamespace

try:
    from ginkgo.trading.strategies.factor_top_decile import FactorTopDecileStrategy
    HAS_STRAT = True
except ImportError:
    HAS_STRAT = False


class _FakeReader:
    """模拟 factor_reader (PIT 契约: values = {(code, factor): (value, timestamp)})。"""
    def __init__(self, values):
        self._v = values

    def get_factor_value(self, code, factor_name, at_time=None):
        entry = self._v.get((code, factor_name))
        if entry is None:
            return None
        val, ts = entry
        # PIT: at_time 已知时, 因子 timestamp 必 <= at_time
        if at_time is not None and ts is not None and ts > at_time:
            return None  # 未来值, 不返回
        return val


class _FakeSelector:
    def __init__(self, codes):
        self._c = list(codes)

    def pick(self, time=None):
        return list(self._c)


@pytest.mark.skipif(not HAS_STRAT, reason="FactorTopDecileStrategy not available")
@pytest.mark.unit
class TestFactorTopDecileStrategy:
    def _strategy(self, values, decile=5, factors=None):
        s = FactorTopDecileStrategy(
            factors=factors or {"ROC5": 1.0}, decile=decile)
        # create_signal 构造 Signal 需 _context (engine/portfolio/task_id)
        s._context = SimpleNamespace(engine_id="e", portfolio_id="p", task_id="t")
        s.bind_factor_reader(_FakeReader(values))
        return s

    def test_top_decile_issues_long_signal(self):
        """截面排名 top 分位 → LONG; 非 top → 无信号 (验收1)。"""
        now = datetime(2024, 1, 1)
        values = {
            ("A", "ROC5"): (1.0, now), ("B", "ROC5"): (2.0, now),
            ("C", "ROC5"): (3.0, now), ("D", "ROC5"): (4.0, now),
            ("E", "ROC5"): (5.0, now),
        }
        s = self._strategy(values, decile=5)  # 5//5=1 → top1 = E
        info = {"now": now, "selector": [_FakeSelector(["A", "B", "C", "D", "E"])]}

        sigs_e = s.cal(info, SimpleNamespace(code="E", timestamp=now))
        assert len(sigs_e) == 1
        # E 最高分 → top1 → LONG

        sigs_a = s.cal(info, SimpleNamespace(code="A", timestamp=now))
        assert sigs_a == []  # A 最低 → 非 top → 无信号

    def test_pit_does_not_read_future_factor(self):
        """验收3: 排名只用 <= now 的因子值, 未来因子不读。"""
        now = datetime(2024, 1, 1)
        future = datetime(2024, 1, 2)
        # E 的因子值 timestamp 在未来 (future > now) → reader 返回 None → E 不入选
        values = {
            ("A", "ROC5"): (1.0, now),
            ("E", "ROC5"): (5.0, future),  # 未来值
        }
        s = self._strategy(values, decile=2)  # 2//2=1 top1
        info = {"now": now, "selector": [_FakeSelector(["A", "E"])]}

        # E 因子是未来值 → reader 返 None → E 剔除 → 仅 A 有分 → A=top1
        sigs_a = s.cal(info, SimpleNamespace(code="A", timestamp=now))
        assert len(sigs_a) == 1  # A 成为 top1 (E 被剔除)
        sigs_e = s.cal(info, SimpleNamespace(code="E", timestamp=now))
        assert sigs_e == []  # E 无因子值 (未来) → 不发信号

    def test_multi_factor_weighted_score_ranks_correctly(self):
        """多因子加权: VOL5 权重高 → 改变排名 (验收1 多因子组合)。"""
        factors = {"ROC5": 1.0, "VOL5": 2.0}
        # A: ROC5=1, VOL5=10 → 1 + 20 = 21
        # B: ROC5=5, VOL5=1  → 5 + 2  = 7
        # 单看 ROC5 是 B>A; 加权后 A(21) > B(7) → A 在 top
        now = datetime(2024, 1, 1)
        values = {
            ("A", "ROC5"): (1.0, now), ("A", "VOL5"): (10.0, now),
            ("B", "ROC5"): (5.0, now), ("B", "VOL5"): (1.0, now),
        }
        s = self._strategy(values, decile=2, factors=factors)  # 2//2=1 top1
        info = {"now": now, "selector": [_FakeSelector(["A", "B"])]}

        assert len(s.cal(info, SimpleNamespace(code="A", timestamp=now))) == 1
        assert s.cal(info, SimpleNamespace(code="B", timestamp=now)) == []
