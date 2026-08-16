# Issue: 前端 research/* 三端点 404——后端无路由（前端模块零引用，契约按库语义定）
# Upstream: api.api.research（ic / layering / decay）
# Downstream: FactorAnalysisService.analyze_factor（features.services，#6794）
# Role: 端点契约——报告键映射、entity 合并去重、上限校验、ServiceResult 失败转 BusinessError

"""
research 端点测试

验证：
1. 三端点把 analyze_factor 的 ServiceResult.data 映射到响应键（不伪造库内没有的字段）
2. entity_ids + codes 合并去重、去空串
3. 校验：无 entity → ValidationError；>50 → ValidationError；日期倒序 → ValidationError
4. analyze_factor 失败（success=False）→ BusinessError
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest


def run_async(coro):
    return asyncio.run(coro)


def _req(**overrides):
    from api.research import FactorAnalysisRequest

    defaults = dict(
        factor_name="ma_cross",
        start_date="2025-01-01",
        end_date="2025-06-30",
        entity_ids=["000001.SZ"],
    )
    defaults.update(overrides)
    return FactorAnalysisRequest(**defaults)


def _report(**overrides):
    """analyze_factor 真实返回形态（factor_analysis_service.py set_data 键）"""
    d = {
        "ic": 0.05,
        "ir": 1.2,
        "ic_by_period": {"1": 0.05, "5": 0.04},
        "ir_by_period": {"1": 1.2, "5": 1.0},
        "decay": {"factor_name": "ma_cross", "lag_ic": {1: 0.05, 2: 0.03},
                  "half_life": 4.5, "decay_rate": 0.12, "optimal_lag": 3,
                  "created_at": "2026-01-01T00:00:00", "metadata": {}},
        "turnover": 0.25,
        "layering_spread": 0.018,
        "layering": {"group_spread": "0.018"},
    }
    d.update(overrides)
    return SimpleNamespace(success=True, data=d, error=None)


def _analysis_service(report):
    svc = MagicMock()
    svc.analyze_factor.return_value = report
    return svc


def _patched(svc):
    return patch("ginkgo.features.services.factor_analysis_service.FactorAnalysisService",
                 return_value=svc)


class TestICEndpoint:
    def test_maps_report_keys(self):
        from api.research import analyze_ic

        svc = _analysis_service(_report())
        with _patched(svc):
            result = run_async(analyze_ic(_req()))

        d = result["data"]
        assert d["ic_mean"] == 0.05 and d["icir"] == 1.2
        assert d["ic_by_period"] == {"1": 0.05, "5": 0.04}
        assert d["turnover"] == 0.25 and d["method"] == "spearman"
        assert "half_life" not in d  # IC 视图不带衰减字段

        kwargs = svc.analyze_factor.call_args.kwargs
        assert kwargs["factor_name"] == "ma_cross"
        assert kwargs["start_date"] == "2025-01-01"


class TestLayeringEndpoint:
    def test_maps_report_keys(self):
        from api.research import analyze_layering

        svc = _analysis_service(_report())
        with _patched(svc):
            result = run_async(analyze_layering(_req(n_groups=10)))

        d = result["data"]
        assert d["spread"] == 0.018
        assert d["statistics"] == {"group_spread": "0.018"}
        assert d["n_groups"] == 10
        assert "layers" not in d  # 库内无 per-group 明细，不虚构


class TestDecayEndpoint:
    def test_maps_report_keys(self):
        from api.research import analyze_decay

        svc = _analysis_service(_report())
        with _patched(svc):
            result = run_async(analyze_decay(_req(max_lag=30)))

        d = result["data"]
        assert d["half_life"] == 4.5 and d["decay_rate"] == 0.12
        assert d["optimal_lag"] == 3 and d["lag_ic"] == {1: 0.05, 2: 0.03}
        assert d["max_lag"] == 30
        assert "created_at" not in d and "metadata" not in d  # 内部字段丢弃


class TestRequestValidation:
    def test_entity_merge_dedupe_and_strip(self):
        from api.research import analyze_ic

        svc = _analysis_service(_report())
        with _patched(svc):
            run_async(analyze_ic(_req(
                entity_ids=["000001.SZ", " 000002.SZ ", ""],
                codes=["000001.SZ", "600000.SH"],
            )))

        ids = svc.analyze_factor.call_args.kwargs["entity_ids"]
        assert ids == ["000001.SZ", "000002.SZ", "600000.SH"]  # 去重保序 + 去空

    def test_no_entity_rejected(self):
        from api.research import analyze_ic
        from core.exceptions import ValidationError

        svc = _analysis_service(_report())
        with _patched(svc), pytest.raises(ValidationError):
            run_async(analyze_ic(_req(entity_ids=None, codes=None)))
        svc.analyze_factor.assert_not_called()

    def test_over_limit_rejected(self):
        from api.research import analyze_ic
        from core.exceptions import ValidationError

        svc = _analysis_service(_report())
        with _patched(svc), pytest.raises(ValidationError):
            run_async(analyze_ic(_req(entity_ids=[f"{i:06d}.SZ" for i in range(51)])))
        svc.analyze_factor.assert_not_called()

    def test_reversed_dates_rejected(self):
        from api.research import analyze_ic
        from core.exceptions import ValidationError

        svc = _analysis_service(_report())
        with _patched(svc), pytest.raises(ValidationError):
            run_async(analyze_ic(_req(start_date="2025-06-30", end_date="2025-01-01")))

    def test_bad_date_format_rejected_at_model(self):
        from api.research import FactorAnalysisRequest
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            FactorAnalysisRequest(
                factor_name="x", start_date="2025/01/01",
                end_date="2025-06-30", entity_ids=["000001.SZ"],
            )


class TestFailurePaths:
    def test_analysis_failure_raises_business_error(self):
        from api.research import analyze_ic
        from core.exceptions import BusinessError

        svc = _analysis_service(SimpleNamespace(success=False, data={}, error="no factor data"))
        with _patched(svc), pytest.raises(BusinessError) as exc_info:
            run_async(analyze_ic(_req()))
        assert "no factor data" in str(exc_info.value)
