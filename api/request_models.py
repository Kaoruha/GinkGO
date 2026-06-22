"""#5565: API 请求 Pydantic 模型

为原本接受 ``data: dict`` 的端点提供字段白名单 + 类型校验，防止
mass assignment（任意 key 流入 service/saga）。

约定：全部 ``extra='forbid'``（与 ``RegisterRequest`` #5458 一致）。
本模块顶层只依赖 pydantic/typing，不触发 ginkgo container 初始化，
便于单元测试直接导入。
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ResetPasswordRequest(BaseModel):
    """``POST /users/{uuid}/reset-password`` 请求体（settings.py）。

    #5465 已要求 new_password 必传（移除旧的 "123456" 默认弱密码）；
    本模型额外加最低长度（密码复杂度基线）与 extra='forbid'。
    """

    model_config = ConfigDict(extra="forbid")

    new_password: str = Field(..., min_length=8, description="新密码（最少 8 字符）")


class AddGroupMemberRequest(BaseModel):
    """``POST /user-groups/{group_uuid}/members`` 请求体（settings.py）。"""

    model_config = ConfigDict(extra="forbid")

    user_uuid: str


class CreateApiKeyRequest(BaseModel):
    """``POST /api-keys`` 请求体（settings.py）。

    注意：端点当前为 TODO 桩（返回硬编码占位），本模型为将来实现
    预留字段白名单，避免桩被绕过时 mass assignment。
    """

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None


class UpdatePortfolioRequest(BaseModel):
    """``PUT /portfolios/{uuid}`` 请求体（portfolio.py）。

    顶层字段白名单防 mass assignment（任意 key 流入 saga）。
    嵌套 selectors/strategies/risk_managers/analyzers 为 ``List[dict]``
    透传——saga 内部自行解析组件结构，schema 层不深校验，避免与 saga
    内部字段类型强耦合导致 schema 漂移。
    """

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    initial_cash: Optional[float] = None
    selectors: Optional[List[dict]] = None
    sizer_uuid: Optional[str] = None
    sizer_config: Optional[dict] = None
    strategies: Optional[List[dict]] = None
    risk_managers: Optional[List[dict]] = None
    analyzers: Optional[List[dict]] = None
