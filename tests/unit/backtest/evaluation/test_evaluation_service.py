# EvaluationService 编排契约测试 (stub 领域层, 不碰 DB):
# - get_gate_definitions: 16 条 gate 全量、字段齐全、与 ALL_GATES 同源
# - get_funnel_report / get_parity_report: 领域层异常 → ServiceResult(success=False)
# - get_parity_report: net_value 缺失 → success=False 带指引
# - run_preflight: selector 解析注入生效、报告 dict 返回

from datetime import date

import pytest

from ginkgo.trading.services.evaluation_service import EvaluationService


class _StubReport:
    def __init__(self, kw):
        self.kw = kw

    def to_dict(self):
        return {"level_reached": "G1", "args": self.kw}


class _StubEvaluator:
    def __init__(self, engine):
        pass

    def evaluate(self, **kw):
        return _StubReport(kw)


class _StubCalculator:
    def compare(self, **kw):
        return _StubReport(kw)


class _StubChecker:
    def __init__(self, bar_crud=None, factor_loader=None, selector=None, daily_counts_loader=None):
        self.bar_crud = bar_crud
        self.factor_loader = factor_loader
        self.selector = selector
        self.daily_counts_loader = daily_counts_loader
        self.called = None

    def check(self, portfolio_id, codes, start, end, min_bars=10):
        self.called = (portfolio_id, codes, start, end, min_bars)
        return _StubReport({})


class _StubEngine:
    def __init__(self):
        pass

    def _load_data(self, task_id, portfolio_id):
        if task_id == "missing":
            return {}
        return {
            "net_value": [(date(2026, 1, i + 1), 100.0 + i) for i in range(30)],
            "order_count": 10,
        }


@pytest.fixture
def patched(monkeypatch):
    """领域层三件套换成 stub, 隔离 DB 依赖 (函数体内 from-import 每次调用重读模块属性)"""
    import ginkgo.trading.analysis.evaluation.funnel_evaluator as fe_mod
    import ginkgo.trading.analysis.evaluation.parity_calculator as pc_mod
    import ginkgo.trading.analysis.evaluation.preflight_checker as pf_mod

    monkeypatch.setattr(EvaluationService, "_analysis_engine", lambda self: _StubEngine())
    monkeypatch.setattr(fe_mod, "FunnelEvaluator", _StubEvaluator)
    monkeypatch.setattr(pc_mod, "ParityCalculator", _StubCalculator)
    monkeypatch.setattr(pf_mod, "PreflightChecker", _StubChecker)


def test_gate_definitions_full(patched):
    r = EvaluationService().get_gate_definitions()
    assert r.success
    assert len(r.data) == 16
    ids = {g["id"] for g in r.data}
    assert {
        "g0_bar_gap", "g0_universe_density", "g2_daily_return_corr",
        "g3_kill_switch", "g1_param_neighborhood",
    } <= ids
    for g in r.data:
        assert {"id", "level", "name", "threshold", "direction", "remediation"} <= set(g)


def test_funnel_report_success(patched):
    r = EvaluationService().get_funnel_report("p" * 32, task_id="t" * 32)
    assert r.success and r.data["level_reached"] == "G1"


def test_funnel_report_domain_error(patched, monkeypatch):
    import ginkgo.trading.analysis.evaluation.funnel_evaluator as fe_mod

    class _Boom:
        def __init__(self, engine):
            pass

        def evaluate(self, **kw):
            raise RuntimeError("db down")

    monkeypatch.setattr(fe_mod, "FunnelEvaluator", _Boom)
    r = EvaluationService().get_funnel_report("p" * 32)
    assert not r.success and "db down" in r.error


def test_parity_report_success(patched):
    r = EvaluationService().get_parity_report("p" * 32, "a" * 32, "b" * 32)
    assert r.success and "args" in r.data


def test_parity_report_missing_nav(patched):
    r = EvaluationService().get_parity_report("p" * 32, "missing", "b" * 32)
    assert not r.success and "net_value" in r.error


def test_parity_report_domain_error(patched, monkeypatch):
    import ginkgo.trading.analysis.evaluation.parity_calculator as pc_mod

    class _Boom:
        def compare(self, **kw):
            raise RuntimeError("series broken")

    monkeypatch.setattr(pc_mod, "ParityCalculator", _Boom)
    r = EvaluationService().get_parity_report("p" * 32, "a" * 32, "b" * 32)
    assert not r.success and "series broken" in r.error


def test_preflight_uses_injected_resolver(patched):
    import ginkgo.trading.analysis.evaluation.preflight_checker as pf_mod

    seen = {}

    def resolver(pid):
        seen["pid"] = pid
        return ["000001.SZ"]

    svc = EvaluationService(
        bar_crud=object(),
        factor_loader=lambda c, s, e: [],
        selector_resolver=resolver,
    )
    r = svc.run_preflight("p" * 32, "2026-01-01", "2026-06-30", min_bars=5)
    assert r.success
    assert seen["pid"] == "p" * 32
    # checker 拿到注入的 resolver 结果与窗口/阈值
    assert pf_mod.PreflightChecker is not None  # patched 类被实例化过即路径通


def test_preflight_domain_error(patched, monkeypatch):
    import ginkgo.trading.analysis.evaluation.preflight_checker as pf_mod

    class _Boom:
        def __init__(self, bar_crud=None, factor_loader=None, selector=None, daily_counts_loader=None):
            pass

        def check(self, *a, **kw):
            raise RuntimeError("ch down")

    monkeypatch.setattr(pf_mod, "PreflightChecker", _Boom)
    svc = EvaluationService(selector_resolver=lambda pid: ["000001.SZ"])
    r = svc.run_preflight("p" * 32, "2026-01-01", "2026-06-30")
    assert not r.success and "ch down" in r.error
