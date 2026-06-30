"""#5565: API 请求 Pydantic 模型

为原本接受 ``data: dict`` 的端点提供字段白名单 + 类型校验，防止
mass assignment（任意 key 流入 service/saga）。

约定：全部 ``extra='forbid'``（与 ``RegisterRequest`` #5458 一致）。
本模块顶层只依赖 pydantic，不触发 ginkgo container 初始化，
便于单元测试直接导入。

注：``create_api_key`` / ``update_portfolio`` 的请求 schema 由 master
内联定义于 ``api/api/settings.py`` / ``api/api/portfolio.py``
（#5459 / #5474，``extra='ignore'`` 策略）；本模块仅收纳 master 仍为
``data: dict`` 的 ``reset_user_password`` / ``add_group_member`` 两端点。
"""

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
