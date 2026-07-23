"""远端 service 代理 (ADR-024)。

client 模式下，``container.portfolio_service()`` 等 provider 经 Selector 返回这里的
代理（而非本地 service）。代理走 :class:`ApiClient` 调远端 REST，把 JSON 映射回本地
service 的 ``ServiceResult`` 契约（DataFrame / 可属性访问对象），让 CLI 命令**零改动**。

阻抗说明（重要）
----------------
远端 REST 面向 web-ui，字段集合 ≠ 本地 service 面向 CLI 的字段集合：

- ``GET /portfolio`` list 不含 ``initial_capital`` / ``is_live`` / ``status``；
- ``GET /portfolio/{uuid}`` detail 用 ``initial_cash``/``current_cash``，而 CLI 期望
  ``initial_capital``/``current_capital``/``cash``，且无 ``desc``、无 ``is_live``。

本模块做**显式字段映射**补齐 CLI 期望的属性名；映射不到的字段为 ``None``，CLI 容错展示
（capital 列空、status 显示 Unknown 等）。完整保真字段映射是后续工作，MVP 保证 seam 通透。
"""

from types import SimpleNamespace
from typing import Any, List, Optional

import pandas as pd

from ginkgo.data.services.base_service import ServiceResult
from ginkgo.client.remote.api_client import ApiClient, ApiError, get_client


def _to_ns(obj: Any) -> Any:
    """递归 dict→SimpleNamespace，让 CLI 的 ``portfolio.uuid`` 属性访问可用。"""
    if isinstance(obj, dict):
        return SimpleNamespace(**{k: _to_ns(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_to_ns(x) for x in obj]
    return obj


class _ModelList(list):
    """模拟本地 ModelList：可索引 / ``len`` / ``to_dataframe``，元素为 SimpleNamespace。

    本地 ``PortfolioService.get`` 出口 data 是 ``ModelList[MPortfolio]``，CLI 用
    ``result.data[0]``、``portfolio.uuid``；远端无 ORM Model，用 namespace 兜形。
    """

    def to_dataframe(self) -> pd.DataFrame:
        rows = []
        for item in self:
            if isinstance(item, SimpleNamespace):
                rows.append(vars(item))
            elif isinstance(item, dict):
                rows.append(item)
        return pd.DataFrame(rows)


def _map_detail_to_namespace(data: Any) -> Optional[SimpleNamespace]:
    """REST ``GET /portfolio/{uuid}`` detail dict → CLI 期望属性的 namespace。

    强制补齐 CLI 直接访问的字段 ``initial_capital``/``current_capital``/``cash``/``desc``/``is_live``：
    缺值给安全默认（数值 0.0 / 空串），避免 ``portfolio.desc`` / ``portfolio.initial_capital``
    访问不存在属性致 ``AttributeError``（CLI ``get``/``status`` 一跑即崩）。REST 用
    ``initial_cash``/``current_cash`` 命名，list 端点 items 全无这些字段且无 desc →
    uuid 与 name 两路径都可能缺，统一 ``setdefault`` 兜底。
    """
    if not isinstance(data, dict):
        return _to_ns(data) if data is not None else None

    initial_cash = data.get("initial_cash")
    current_cash = data.get("current_cash")
    mode_str = data.get("mode")
    merged = dict(data)
    # CLI get/status 格式串 ``:,.2f`` 拒 None（TypeError），故数值缺值默认 0.0。
    merged.setdefault("initial_capital", float(initial_cash) if initial_cash is not None else 0.0)
    merged.setdefault("current_capital", float(current_cash) if current_cash is not None else 0.0)
    merged.setdefault("cash", float(current_cash) if current_cash is not None else 0.0)
    # CLI get 读 desc：REST detail/list 均不返 desc/description → 默认空串（容错展示）。
    merged.setdefault("desc", merged.get("description") or "")
    # CLI status 读 is_live（REST 用 mode 字符串推导）
    merged.setdefault("is_live", str(mode_str).lower() == "live")
    return _to_ns(merged)


class RemoteService:
    """远端代理基类：持 :class:`ApiClient`，统一把异常包成 ``ServiceResult.failure``。

    ``client`` 可注入，便于单测用 fake client（无 live HTTP）。
    """

    #: 远端资源前缀，子类覆写（如 ``"/portfolio"``）
    resource: str = ""

    def __init__(self, client: Optional[ApiClient] = None):
        self._client = client or get_client()

    def _ok(self, data: Any, message: str = "") -> ServiceResult:
        return ServiceResult.success(data=data, message=message)

    def _fail(self, err: Exception) -> ServiceResult:
        if isinstance(err, ApiError):
            return ServiceResult.failure(
                message=str(err), code=str(err.status_code or err.code)
            )
        return ServiceResult.failure(message=f"远端请求失败：{err}")


class RemotePortfolioService(RemoteService):
    """``PortfolioService`` 的远端代理（list / get / add / delete / count）。"""

    resource = "/portfolio"

    def get_portfolios_df(
        self,
        portfolio_id: str = None,
        name: str = None,
        mode: Any = None,
        state: Any = None,
        page: int = None,
        page_size: int = None,
    ) -> ServiceResult:
        """出口为 DataFrame（与本地 ``get_portfolios_df`` 同契约）。

        REST list 不含 ``initial_capital``/``is_live``/``status`` → 这些列为缺失；
        CLI list 容错展示（capital 显示 ¥0.00、type 全 Backtest、status Unknown）。
        """
        try:
            params: dict = {}
            if name:
                params["keyword"] = name
            if page is not None:
                params["page"] = page
            if page_size is not None and page_size > 0:
                params["page_size"] = page_size
            items, _meta = self._client.request_with_meta(
                "GET", self.resource, params=params or None
            )
            df = pd.DataFrame(items or [])
            return self._ok(df, f"Retrieved {len(df)} portfolios (remote)")
        except Exception as e:
            return self._fail(e)

    def count(
        self, name: str = None, mode: Any = None, state: Any = None, **kwargs
    ) -> ServiceResult:
        """读 list 端点 ``meta.total``（data 只是当前页）。"""
        try:
            params: dict = {"page": 0, "page_size": 1}
            if name:
                params["keyword"] = name
            _data, meta = self._client.request_with_meta(
                "GET", self.resource, params=params
            )
            total = (meta or {}).get("total", 0)
            return self._ok({"count": total}, f"{total} portfolios (remote)")
        except Exception as e:
            return self._fail(e)

    def get(
        self,
        portfolio_id: str = None,
        name: str = None,
        mode: Any = None,
        state: Any = None,
        **kwargs,
    ) -> ServiceResult:
        """按 uuid 取详情；按 name 走 list keyword 取首条。出口为 ``_ModelList``。"""
        try:
            if portfolio_id:
                data = self._client.get(f"{self.resource}/{portfolio_id}")
                ns = _map_detail_to_namespace(data)
                return self._ok(
                    _ModelList([ns]) if ns is not None else None,
                    "Portfolio retrieved (remote)",
                )
            if name:
                items, _ = self._client.request_with_meta(
                    "GET", self.resource, params={"keyword": name, "page_size": 100}
                )
                ns_list = [_map_detail_to_namespace(i) for i in (items or [])]
                return self._ok(_ModelList(ns_list), "Portfolio retrieved (remote)")
            return ServiceResult.failure(message="portfolio_id 或 name 必须提供其一")
        except Exception as e:
            return self._fail(e)

    def add(
        self,
        name: str = None,
        description: str = None,
        initial_capital: Any = None,
        **kwargs,
    ) -> ServiceResult:
        """``POST /portfolio``，出口 data 为 ``{"uuid": ...}``（与本地 add 同契约）。"""
        try:
            body: dict = {}
            if name is not None:
                body["name"] = name
            if description is not None:
                body["description"] = description
            if initial_capital is not None:
                body["initial_capital"] = initial_capital
            data = self._client.post(self.resource, json_body=body)
            uuid = data.get("uuid") if isinstance(data, dict) else None
            return self._ok({"uuid": uuid}, "Portfolio created (remote)")
        except Exception as e:
            return self._fail(e)

    def delete(self, portfolio_id: str, **kwargs) -> ServiceResult:
        """``DELETE /portfolio/{uuid}``（REST 返 204 无 body，成功即 data=None）。"""
        try:
            self._client.delete(f"{self.resource}/{portfolio_id}")
            return self._ok(None, "Portfolio deleted (remote)")
        except Exception as e:
            return self._fail(e)

    def fuzzy_search(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        **kwargs,
    ) -> ServiceResult:
        """``PortfolioService.fuzzy_search`` (#5995) 的远端代理。

        REST ``GET /portfolio?keyword=`` 当前是 **精确 name 匹配**（``filters["name"]=keyword``），
        非 LIKE 片段；故本代理仅覆盖「精确名称命中」，UUID 片段 / 名称部分模糊需 server 端
        keyword 改 LIKE（后续工作）。补此方法让命令体（如 ``resolve_portfolio_uuid``）在
        client 模式不再 ``AttributeError``，名称解析可用。出口为 ``_ModelList``（元素含 ``uuid``）。
        """
        try:
            if not query or not str(query).strip():
                return self._ok(_ModelList([]), "Empty query (remote)")
            items, _ = self._client.request_with_meta(
                "GET", self.resource, params={"keyword": str(query), "page_size": 100}
            )
            ns_list = [_map_detail_to_namespace(i) for i in (items or [])]
            return self._ok(_ModelList(ns_list), f"{len(ns_list)} match(es) (remote)")
        except Exception as e:
            return self._fail(e)

    def collect_portfolio_components(self, portfolio_id: str, **kwargs) -> ServiceResult:
        """``PortfolioService.collect_portfolio_components`` 的远端代理。

        REST ``GET /portfolio/{uuid}`` detail 响应已内含组件装配（strategies/selectors/sizers/
        risk_managers/analyzers 五数组，见 ``api/api/portfolio.py::get_portfolio``），直接抽取
        映射回本地 service 的 dict 契约。元素 shape 对齐 ``display_component_tree`` 的字段访问
        （``name`` / ``file_id`` 字符串 / ``parameters=[{index, value}]``）；REST 用 ``uuid``/
        ``config``，做一层归一。
        """
        try:
            detail = self._client.get(f"{self.resource}/{portfolio_id}")
            if not isinstance(detail, dict):
                return self._ok(
                    {"strategies": [], "selectors": [], "sizers": [], "risk_managers": [], "analyzers": []},
                    "No component data (remote)",
                )

            def _shape(items):
                shaped = []
                for elem in (items or []):
                    if not isinstance(elem, dict):
                        continue
                    config = elem.get("config") or {}
                    params = [
                        {"index": idx, "value": val, "raw_value": val}
                        for idx, (_k, val) in enumerate(config.items())
                    ]
                    shaped.append(
                        {
                            "name": str(elem.get("name") or ""),
                            "file_id": str(elem.get("uuid") or ""),
                            "type": elem.get("type"),
                            "mapping_uuid": elem.get("mapping_uuid"),
                            "parameters": params,
                        }
                    )
                return shaped

            component_data = {
                "strategies": _shape(detail.get("strategies")),
                "selectors": _shape(detail.get("selectors")),
                "sizers": _shape(detail.get("sizers")),
                "risk_managers": _shape(detail.get("risk_managers")),
                "analyzers": _shape(detail.get("analyzers")),
            }
            return self._ok(component_data, "Components collected (remote)")
        except Exception as e:
            return self._fail(e)


class RemoteBacktestRunner:
    """client 模式 backtest run：提交 + 轮询（ADR-024 命令级分支）。

    与本地 ``BacktestOrchestrator.run_from_task`` 对偶：本地同步阻塞跑引擎，本类把任务
    **提交到远端 BacktestWorker**（``POST /backtest/{uuid}/start``）后轮询
    ``GET /backtest/{uuid}`` 的 ``status`` 字段到终态。**零本地计算**。

    ``status`` 取值（``model_backtest_task.py:67``）：created/pending/running/
    completed/failed/stopped；终态 = completed/failed/stopped。

    注：``POST /{uuid}/start`` 返回的 ``{state: "PENDING"}`` 只是即时 ack，真正要轮询的
    是 detail 的 ``status`` 字段（小写、由 worker 落库驱动）。
    """

    #: 轮询终态（小写，对齐 DB status 字段）
    TERMINAL_STATES = ("completed", "failed", "stopped")
    #: 默认轮询间隔（秒）
    POLL_INTERVAL = 1.0

    def __init__(self, client: Optional[ApiClient] = None, poll_interval: Optional[float] = None):
        self._client = client or get_client()
        self.poll_interval = (
            poll_interval if poll_interval is not None else self.POLL_INTERVAL
        )

    def submit(self, uuid: str) -> Any:
        """``POST /backtest/{uuid}/start``：触发远端 worker。"""
        return self._client.post(f"/backtest/{uuid}/start")

    def get_status(self, uuid: str) -> Any:
        """``GET /backtest/{uuid}``：task detail dict（含 ``status``）。"""
        return self._client.get(f"/backtest/{uuid}")

    def get_results(self, uuid: str) -> Any:
        """``GET /backtest/{uuid}/results``：结果摘要（completed 才有意义，可能 None）。"""
        return self._client.get(f"/backtest/{uuid}/results")

    @staticmethod
    def _status_of(detail: Any) -> Optional[str]:
        """从 detail dict 取 status（兼容 ``state`` 别名），归一小写。"""
        if isinstance(detail, dict):
            return str(detail.get("status") or detail.get("state") or "").lower()
        return None

    def run(
        self,
        uuid: str,
        on_progress=None,
        timeout: Optional[float] = None,
    ) -> "tuple[str, Any, Any]":
        """提交并轮询到终态，返回 ``(final_status, detail, results)``。

        - ``on_progress(status, detail)`` 在 ``status`` 变化时回调（CLI 用于印状态行）；
        - ``timeout``（秒）超时则返回当前非终态 status，CLI 据此提示仍在跑；
        - ``completed`` 时额外拉一次 ``results``（失败静默为 None）。
        """
        import time

        self.submit(uuid)
        last: Optional[str] = None
        start = time.monotonic()
        while True:
            detail = self.get_status(uuid)
            status = self._status_of(detail)
            if status != last:
                if on_progress is not None:
                    on_progress(status, detail)
                last = status
            if status in self.TERMINAL_STATES:
                results = None
                if status == "completed":
                    try:
                        results = self.get_results(uuid)
                    except Exception:
                        results = None
                return status, detail, results
            time.sleep(self.poll_interval)
            if timeout is not None and (time.monotonic() - start) > timeout:
                return status or "unknown", detail, None
