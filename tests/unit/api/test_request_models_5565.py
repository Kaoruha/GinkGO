"""#5565: 4 API 端点 Pydantic 请求模型单元测试。

覆盖端点（验收：Create Pydantic models for all 4 endpoints + field validation
+ tests for invalid inputs）：

- ``api/api/settings.py`` ``reset_user_password``  → ResetPasswordRequest
- ``api/api/settings.py`` ``add_group_member``     → AddGroupMemberRequest
- ``api/api/settings.py`` ``create_api_key``       → CreateApiKeyRequest
- ``api/api/portfolio.py`` ``update_portfolio``    → UpdatePortfolioRequest

schema 定义在独立模块 ``api/request_models.py``（零 ginkgo 依赖），
测试直接导入该模块，不触发 settings.py 的 container 初始化，亦绕开
仓库根 main.py 遮蔽（arch_api_test_root_main_shadow）。
"""

import sys
from pathlib import Path

# 自带 sys.path：api/ 在 path 时 request_models 作顶层模块解析
# （与 settings.py 内 `from core.logging import logger` 同一假设：
#   运行时 uvicorn 从 api/ 启动，api/ 已在 sys.path）。
_API_DIR = str(Path(__file__).parent.parent.parent.parent / "api")
if _API_DIR not in sys.path:
    sys.path.insert(0, _API_DIR)

import pytest
from pydantic import ValidationError

from request_models import (  # noqa: E402
    AddGroupMemberRequest,
    CreateApiKeyRequest,
    ResetPasswordRequest,
    UpdatePortfolioRequest,
)


class TestResetPasswordRequest:
    """#5565: reset_user_password 请求模型。"""

    def test_valid_password(self):
        r = ResetPasswordRequest(new_password="StrongPass1")
        assert r.new_password == "StrongPass1"

    def test_missing_password_rejected(self):
        with pytest.raises(ValidationError):
            ResetPasswordRequest()

    def test_extra_field_rejected_mass_assignment_guard(self):
        # mass assignment 防护：注入 is_admin 必须失败
        with pytest.raises(ValidationError):
            ResetPasswordRequest(new_password="StrongPass1", is_admin=True)

    def test_short_password_rejected_complexity(self):
        # 密码复杂度基线：最少 8 字符
        with pytest.raises(ValidationError):
            ResetPasswordRequest(new_password="Ab1")


class TestAddGroupMemberRequest:
    def test_valid(self):
        r = AddGroupMemberRequest(user_uuid="abc123")
        assert r.user_uuid == "abc123"

    def test_missing_user_uuid(self):
        with pytest.raises(ValidationError):
            AddGroupMemberRequest()

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            AddGroupMemberRequest(user_uuid="abc", role="admin")


class TestCreateApiKeyRequest:
    def test_name_optional(self):
        r = CreateApiKeyRequest()
        assert r.name is None

    def test_valid_name(self):
        r = CreateApiKeyRequest(name="my-key")
        assert r.name == "my-key"

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            CreateApiKeyRequest(name="x", is_admin=True)


class TestUpdatePortfolioRequest:
    """#5565 核心：防任意 key 流入 saga（mass assignment）。"""

    def test_empty_body_valid_partial_update(self):
        # PUT 部分更新：所有字段 Optional，空 body 合法
        r = UpdatePortfolioRequest()
        assert r.name is None

    def test_valid_fields(self):
        r = UpdatePortfolioRequest(
            name="p",
            initial_cash=100000,
            selectors=[{"file_id": "x"}],
            sizer_uuid="s",
            sizer_config={"k": 1},
            strategies=[{"file_id": "s1"}],
            risk_managers=[],
            analyzers=[],
        )
        assert r.name == "p"
        assert r.initial_cash == 100000

    def test_arbitrary_key_rejected_mass_assignment_guard(self):
        # saga mass assignment 防护：未知字段流入 saga 必须失败
        with pytest.raises(ValidationError):
            UpdatePortfolioRequest(name="p", is_admin=True)

    def test_nested_lists_passthrough(self):
        # 嵌套结构透传：saga 内部解析，schema 不深校验
        r = UpdatePortfolioRequest(strategies=[{"file_id": "s", "params": {}}])
        assert r.strategies == [{"file_id": "s", "params": {}}]
