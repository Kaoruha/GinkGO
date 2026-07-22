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
from typing import Any, Optional

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

    补齐 CLI 直接访问的字段：``initial_capital``/``current_capital``/``cash``/``is_live``。
    """
    if not isinstance(data, dict):
        return _to_ns(data) if data is not None else None

    initial_cash = data.get("initial_cash")
    current_cash = data.get("current_cash")
    mode_str = data.get("mode")
    merged = dict(data)
    # CLI get/status 读 initial_capital / current_capital / cash
    if "initial_capital" not in merged and initial_cash is not None:
        merged["initial_capital"] = initial_cash
    if "current_capital" not in merged and current_cash is not None:
        merged["current_capital"] = current_cash
    if "cash" not in merged and current_cash is not None:
        merged["cash"] = current_cash
    # CLI status 读 is_live（REST 用 mode 字符串推导）
    if "is_live" not in merged:
        merged["is_live"] = str(mode_str).lower() == "live"
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
