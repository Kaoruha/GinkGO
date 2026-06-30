# Upstream: src/ginkgo/libs/data/statistics.py
# Context: #5521 — t_test/chi2_test 用 print() 污染 stdout，且 t_test 丢失 t_critical；
#          chi2_test 注释/文本与 p 值逻辑相反。库函数应返回结构化结果，无副作用输出。
import numpy as np
import pytest

scipy = pytest.importorskip("scipy")  # 无 scipy 环境跳过统计检验测试

from ginkgo.libs.data.statistics import t_test  # noqa: E402


class TestTTest:
    """t_test 不再 print，返回含 t_critical 的结构化结果。"""

    def test_does_not_print_to_stdout(self, capsys):
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        b = [2.0, 3.0, 4.0, 5.0, 6.0]
        t_test(a, b)
        out = capsys.readouterr()
        assert out.out == ""
        assert out.err == ""

    def test_returns_structured_with_critical_value(self):
        # 原实现 return result（TtestResult）丢失 t_critical 计算结果
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        b = [2.0, 3.0, 4.0, 5.0, 6.0]
        result = t_test(a, b)
        assert hasattr(result, "t_critical")
        assert hasattr(result, "pvalue")
        assert hasattr(result, "statistic")
        assert hasattr(result, "degree_of_freedom")

    def test_pvalue_finite_for_different_samples(self):
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        b = [10.0, 11.0, 12.0, 13.0, 14.0]
        result = t_test(a, b)
        assert np.isfinite(result.pvalue)
        assert np.isfinite(result.t_critical)


from ginkgo.libs.data.statistics import chi2_test  # noqa: E402


class TestChi2Test:
    """chi2_test 不再 print，返回 namedtuple（原实现注释/文本与 p 值逻辑相反）。"""

    def test_does_not_print_to_stdout(self, capsys):
        a = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        b = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        chi2_test(a, b)
        out = capsys.readouterr()
        assert out.out == ""
        assert out.err == ""

    def test_returns_structured_namedtuple(self):
        a = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        b = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        result = chi2_test(a, b)
        assert hasattr(result, "chi2")
        assert hasattr(result, "p")
        assert hasattr(result, "degree_of_freedom")
        assert hasattr(result, "expected")
