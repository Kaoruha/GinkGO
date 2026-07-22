"""瘦客户端 HTTP 客户端 (ADR-024)。

封装与远端 Ginkgo API 的交互：
- ``base_url`` 取自 ``GCONF.API_BASE``；
- 自动附 ``Authorization: Bearer <jwt>``；
- 临过期 (5min slack) **主动** refresh；收到 401 **被动** refresh 一次；
- 解包统一响应 ``{code, data, ...}``，``code != 0`` 抛 ``ApiError``。

异常分级：
- ``NotLoggedInError``：未登录（无 auth.json）。
- ``TokenExpiredError``：token 已过期且 refresh 失败 → 需重新 ``ginkgo user login``。
- ``ApiError``：其它业务/传输错误。
"""

from typing import Any, Optional

import httpx

from ginkgo.libs import GCONF
from ginkgo.client.remote import auth_store

# 临过期提前量：token 剩余 < 5min 时主动 refresh（仍在有效期内，refresh 必成功）。
REFRESH_SLACK_SECONDS = 300

# API 路由前缀（与 api/main.py 挂载一致）。
API_PREFIX = "/api/v1"


class ApiError(Exception):
    """远端 API 业务/传输错误。"""

    def __init__(self, message: str, status_code: int = 0, code: int = -1):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class NotLoggedInError(ApiError):
    """client 模式未登录。"""


class TokenExpiredError(ApiError):
    """token 已过期且 refresh 失败，需重新 login。"""


class ApiClient:
    """瘦客户端 HTTP 客户端单例。"""

    def _base_url(self) -> str:
        return GCONF.API_BASE

    def _headers(self, token: str) -> dict:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _ensure_token(self) -> str:
        """取一个可用 token；临过期先 refresh。"""
        record = auth_store.load()
        if record is None or not record.get("token"):
            raise NotLoggedInError("未登录，请先 `ginkgo user login`")
        if auth_store.is_expired(record, slack_seconds=REFRESH_SLACK_SECONDS):
            self._refresh()
            record = auth_store.load()
            if record is None or not record.get("token"):
                raise TokenExpiredError("登录已过期，请 `ginkgo user login`")
        return record["token"]

    def _refresh(self) -> None:
        """调 /auth/refresh 换新 token 并写回 auth.json。"""
        record = auth_store.load()
        if record is None or not record.get("token"):
            raise NotLoggedInError("未登录，请先 `ginkgo user login`")
        try:
            resp = httpx.post(
                f"{self._base_url()}{API_PREFIX}/auth/refresh",
                headers=self._headers(record["token"]),
                timeout=10,
            )
        except httpx.HTTPError as e:
            raise ApiError(f"refresh 请求失败：{e}")
        if resp.status_code == 401:
            # token 过期超 leeway 或被撤销 → 清除，需重登
            auth_store.clear()
            raise TokenExpiredError("登录已过期，请 `ginkgo user login`")
        if resp.status_code != 200:
            raise ApiError(f"refresh 失败：HTTP {resp.status_code}")
        try:
            body = resp.json()
        except ValueError:
            raise ApiError("refresh 响应非 JSON")
        if body.get("code") != 0:
            raise ApiError(f"refresh 失败：{body.get('message')}")
        data = body.get("data") or {}
        record.update(
            {
                "token": data["token"],
                "expires_at": data["expires_at"],
                "user": data.get("user", record.get("user", {})),
            }
        )
        auth_store.save(record)

    def _request_raw(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: Optional[dict] = None,
        timeout: float = 30,
        _retry: bool = True,
    ) -> "tuple[Any, Optional[dict]]":
        """发请求，返回 ``(data, meta)``（信封 code 字段 + meta 字段）。

        - ``path`` 为相对 ``API_PREFIX`` 的路径（如 ``/portfolio/<id>``）；
        - ``code != 0`` 抛 ``ApiError``；
        - 401 先 refresh 一次再重试（``_retry`` 防递归），仍 401 清凭证抛 ``TokenExpiredError``。
        """
        token = self._ensure_token()
        url = f"{self._base_url()}{API_PREFIX}{path}"
        try:
            resp = httpx.request(
                method,
                url,
                headers=self._headers(token),
                json=json_body,
                params=params,
                timeout=timeout,
            )
        except httpx.HTTPError as e:
            raise ApiError(f"请求失败：{e}")

        if resp.status_code == 401:
            if _retry:
                try:
                    self._refresh()
                    return self._request_raw(
                        method,
                        path,
                        json_body=json_body,
                        params=params,
                        timeout=timeout,
                        _retry=False,
                    )
                except TokenExpiredError:
                    raise
            auth_store.clear()
            raise TokenExpiredError("登录已过期，请 `ginkgo user login`")

        if resp.status_code >= 400:
            raise ApiError(
                f"HTTP {resp.status_code}: {resp.text[:200]}",
                status_code=resp.status_code,
            )

        try:
            body = resp.json()
        except ValueError:
            raise ApiError(f"HTTP {resp.status_code}: 响应非 JSON")

        if body.get("code") != 0:
            raise ApiError(
                body.get("message", "unknown error"),
                status_code=resp.status_code,
                code=body.get("code", -1),
            )
        return body.get("data"), body.get("meta")

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: Optional[dict] = None,
        timeout: float = 30,
    ) -> Any:
        """发请求，返回 ``data``（丢 meta）。分页总数请用 ``request_with_meta``。"""
        data, _meta = self._request_raw(
            method, path, json_body=json_body, params=params, timeout=timeout
        )
        return data

    def request_with_meta(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: Optional[dict] = None,
        timeout: float = 30,
    ) -> "tuple[Any, Optional[dict]]":
        """同 ``request``，但额外返回信封 ``meta``（分页 ``total`` 等）。

        远端 list 端点的总数在 ``meta.total``，``data`` 只是当前页 → ``count()``
        读总数必须走此方法。
        """
        return self._request_raw(
            method, path, json_body=json_body, params=params, timeout=timeout
        )

    def get(self, path: str, **kw) -> Any:
        return self.request("GET", path, **kw)

    def post(self, path: str, **kw) -> Any:
        return self.request("POST", path, **kw)

    def put(self, path: str, **kw) -> Any:
        return self.request("PUT", path, **kw)

    def delete(self, path: str, **kw) -> Any:
        return self.request("DELETE", path, **kw)


_client: Optional[ApiClient] = None


def get_client() -> ApiClient:
    """模块级单例（同进程复用连接上下文由 httpx 管理）。"""
    global _client
    if _client is None:
        _client = ApiClient()
    return _client
