"""RemotePortfolioService 单测 (ADR-024)。

纯单测：注入 fake ApiClient，不触 HTTP/DB，验证远端代理把 REST JSON 映射回
本地 service 的 ServiceResult 契约（DataFrame / 可属性访问 / uuid dict）。
"""
import pandas as pd

from ginkgo.client.remote.api_client import ApiError, TokenExpiredError
from ginkgo.client.remote.services import RemotePortfolioService, _ModelList
from ginkgo.data.containers import _remote_portfolio_service_factory


class FakeClient:
    """记录调用 + 可注入响应的 fake ApiClient。"""

    def __init__(self, *, list_items=None, list_total=0, detail=None, created=None,
                 raise_on=None):
        self.calls = []
        self._list_items = list_items or []
        self._list_total = list_total
        self._detail = detail
        self._created = created or {"uuid": "new-uuid"}
        self._raise_on = raise_on or {}  # method -> Exception

    def request_with_meta(self, method, path, *, json_body=None, params=None, timeout=30):
        self.calls.append((method, path, params))
        if self._raise_on.get("request_with_meta"):
            raise self._raise_on["request_with_meta"]
        return list(self._list_items), {"total": self._list_total}

    def get(self, path, **kw):
        self.calls.append(("GET", path, None))
        if self._raise_on.get("get"):
            raise self._raise_on["get"]
        return self._detail

    def post(self, path, **kw):
        self.calls.append(("POST", path, kw.get("json_body")))
        if self._raise_on.get("post"):
            raise self._raise_on["post"]
        return self._created

    def delete(self, path, **kw):
        self.calls.append(("DELETE", path, None))
        if self._raise_on.get("delete"):
            raise self._raise_on["delete"]
        return None


def _detail_dict():
    return {
        "uuid": "u1", "name": "p1", "mode": "live", "state": "running",
        "initial_cash": 1000000.0, "current_cash": 980000.0,
    }


def test_list_returns_dataframe():
    fc = FakeClient(list_items=[{"uuid": "u1", "name": "p1", "mode": "live"}], list_total=1)
    res = RemotePortfolioService(client=fc).get_portfolios_df(page=0, page_size=20)
    assert res.success
    assert isinstance(res.data, pd.DataFrame)
    assert len(res.data) == 1
    assert list(res.data.columns) == ["uuid", "name", "mode"]


def test_count_reads_meta_total():
    fc = FakeClient(list_total=42)
    res = RemotePortfolioService(client=fc).count()
    assert res.success
    assert res.data == {"count": 42}


def test_get_by_uuid_maps_impedance_fields():
    fc = FakeClient(detail=_detail_dict())
    res = RemotePortfolioService(client=fc).get(portfolio_id="u1")
    assert res.success
    assert isinstance(res.data, _ModelList)
    p = res.data[0]
    # REST initial_cash/current_cash → CLI initial_capital/cash
    assert p.uuid == "u1"
    assert p.initial_capital == 1000000.0
    assert p.current_capital == 980000.0
    assert p.cash == 980000.0
    # is_live 由 mode 字符串推导
    assert p.is_live is True


def test_get_by_name_uses_keyword():
    fc = FakeClient(list_items=[_detail_dict()], list_total=1)
    res = RemotePortfolioService(client=fc).get(name="p1")
    assert res.success
    assert len(res.data) == 1
    # 确认走了 keyword 参数
    assert any(c[0] == "GET" and (c[2] or {}).get("keyword") == "p1" for c in fc.calls)


def test_add_returns_uuid_dict():
    fc = FakeClient(created={"uuid": "abc"})
    res = RemotePortfolioService(client=fc).add(
        name="x", description="d", initial_capital=100000
    )
    assert res.success
    assert res.data == {"uuid": "abc"}
    # body 透传
    post_call = [c for c in fc.calls if c[0] == "POST"][0]
    assert post_call[2]["name"] == "x"
    assert post_call[2]["initial_capital"] == 100000


def test_delete_succeeds():
    fc = FakeClient()
    res = RemotePortfolioService(client=fc).delete("u1")
    assert res.success
    assert any(c[0] == "DELETE" for c in fc.calls)


def test_api_error_maps_to_failure():
    fc = FakeClient(raise_on={"get": ApiError("boom", status_code=500)})
    res = RemotePortfolioService(client=fc).get(portfolio_id="u1")
    assert not res.success
    assert "boom" in (res.error or "")


def test_token_expired_maps_to_failure():
    fc = FakeClient(raise_on={"get": TokenExpiredError("expired")})
    res = RemotePortfolioService(client=fc).get(portfolio_id="u1")
    assert not res.success


def test_remote_factory_returns_service():
    svc = _remote_portfolio_service_factory()
    assert isinstance(svc, RemotePortfolioService)


def test_fuzzy_search_passes_keyword_returns_modellist():
    """fuzzy_search 走 list keyword（REST 精确 name 匹配），出口 _ModelList。"""
    fc = FakeClient(list_items=[_detail_dict()], list_total=1)
    res = RemotePortfolioService(client=fc).fuzzy_search("p1")
    assert res.success
    assert isinstance(res.data, _ModelList)
    assert res.data[0].uuid == "u1"
    assert any(c[2] and c[2].get("keyword") == "p1" for c in fc.calls)


def test_fuzzy_search_empty_query_returns_empty_no_call():
    """空 query 不打远端，直接返空 _ModelList。"""
    fc = FakeClient(list_total=99)
    res = RemotePortfolioService(client=fc).fuzzy_search("   ")
    assert res.success
    assert len(res.data) == 0
    assert fc.calls == []  # 未触 request_with_meta


def test_collect_portfolio_components_maps_detail_arrays():
    """collect_portfolio_components 从 detail 抽五组件数组，shape 对齐 display_component_tree。"""
    detail = {
        "uuid": "u1",
        "strategies": [{"uuid": "s-uuid-1234", "name": "MA", "type": "strategy", "config": {"fast": 5, "slow": 20}}],
        "selectors": [],
        "sizers": [{"uuid": "sz1", "name": "fixed", "config": {"volume": 100}}],
        "risk_managers": [],
        "analyzers": [],
    }
    fc = FakeClient(detail=detail)
    res = RemotePortfolioService(client=fc).collect_portfolio_components("u1")
    assert res.success
    data = res.data
    assert set(data.keys()) == {"strategies", "selectors", "sizers", "risk_managers", "analyzers"}
    strat = data["strategies"][0]
    # display_component_tree 访问 name / file_id[:8] / parameters[].index|value
    assert strat["name"] == "MA"
    assert strat["file_id"] == "s-uuid-1234"
    assert strat["file_id"][:8] == "s-uuid-1"
    assert [(p["index"], p["value"]) for p in strat["parameters"]] == [(0, 5), (1, 20)]
    assert any(c[0] == "GET" and c[1] == "/portfolio/u1" for c in fc.calls)


def test_collect_portfolio_components_non_dict_returns_empty_contract():
    """detail 非 dict（如 None）时返五空数组契约，不崩。"""
    fc = FakeClient(detail=None)
    res = RemotePortfolioService(client=fc).collect_portfolio_components("u1")
    assert res.success
    assert res.data == {"strategies": [], "selectors": [], "sizers": [], "risk_managers": [], "analyzers": []}
