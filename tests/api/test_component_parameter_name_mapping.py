# #5408 — 组件参数端点名称映射断裂（类名 vs 文件名）
"""
表象：GET /components/parameters/{component_name} 永远 404。
根因：COMPONENT_PARAMETER_DEFINITIONS 的 key 是 Python 类名（PascalCase，
      如 PositionRatioRisk），但 API 调用方传组件文件名（snake_case，
      如 position_ratio_risk）；service.get_component_parameters 直接
      dict.get(component_name) 无归一化 → 永不匹配。
契约（service 层 ComponentParameterService.get_component_parameters）：
  - snake_case 文件名查询 → 返回对应参数（归一化到 PascalCase key）
  - PascalCase 类名查询 → 仍返回参数（向后兼容，防回归）
  - 未知组件 → 返回空列表
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-routing-test")


def _svc():
    # lazy import：conftest api_modules fixture 在测试执行时才把 api/ 加入 sys.path
    from services.component_parameter_service import ComponentParameterService
    return ComponentParameterService()


class TestComponentParameterNameMapping:
    """组件参数查询必须兼容 snake_case 文件名与 PascalCase 类名"""

    def test_snake_case_filename_returns_params(self):
        """position_ratio_risk (文件名) 应返回 PositionRatioRisk 的参数"""
        svc = _svc()
        params = svc.get_component_parameters("position_ratio_risk")
        assert len(params) > 0, "文件名查询应返回参数（当前映射断裂返回空）"
        names = [p.name for p in params]
        assert "max_position_ratio" in names

    def test_pascal_case_classname_still_works(self):
        """PositionRatioRisk (类名) 查询必须继续工作（防回归）"""
        svc = _svc()
        params = svc.get_component_parameters("PositionRatioRisk")
        assert len(params) > 0, "类名查询应返回参数"
        assert "max_position_ratio" in [p.name for p in params]

    def test_snake_and_pascal_return_same_params(self):
        """同一组件的文件名与类名查询必须返回等价参数"""
        svc = _svc()
        by_file = svc.get_component_parameters("loss_limit_risk")
        by_class = svc.get_component_parameters("LossLimitRisk")
        assert len(by_file) > 0
        assert [p.name for p in by_file] == [p.name for p in by_class]

    def test_unknown_component_returns_empty(self):
        """未知组件返回空列表（策略 moving_average_crossover 当前无定义）"""
        svc = _svc()
        params = svc.get_component_parameters("moving_average_crossover")
        assert params == [], "未知组件应返回空列表而非报错"

    def test_get_all_definitions_returns_dict(self):
        """get_all_component_definitions 返回非空字典（供 GET /parameters 使用）"""
        svc = _svc()
        all_defs = svc.get_all_component_definitions()
        assert isinstance(all_defs, dict)
        assert len(all_defs) > 0
        assert "PositionRatioRisk" in all_defs


class TestParametersRouteOrdering:
    """GET /parameters 不能被 /{uuid} 路由截获 (#5408 acceptance #2)

    FastAPI 按声明顺序匹配路由：/{uuid} 若声明在 /parameters 之前，会把
    GET /parameters 当成 uuid="parameters" 截获。
    """

    def _client(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api.components import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1/components")
        return TestClient(app)

    def test_get_all_parameters_not_intercepted_by_uuid_route(self):
        """GET /parameters 应返回全部定义字典，而非被 /{uuid} 当 uuid 截获"""
        c = self._client()
        r = c.get("/api/v1/components/parameters")
        assert r.status_code == 200, f"应走 get_all 路由(200)，实际 {r.status_code}: {r.text[:120]}"
        data = r.json().get("data")
        assert isinstance(data, dict), f"data 应为字典，实际 {type(data)}"
        assert "PositionRatioRisk" in data

    def test_filename_param_query_returns_200(self):
        """GET /parameters/position_ratio_risk 应 200（映射修复 + 路由顺序正确）"""
        c = self._client()
        r = c.get("/api/v1/components/parameters/position_ratio_risk")
        assert r.status_code == 200, f"文件名查询应 200，实际 {r.status_code}: {r.text[:120]}"
        data = r.json().get("data")
        assert isinstance(data, list) and len(data) > 0
        assert "max_position_ratio" in [p["name"] for p in data]
