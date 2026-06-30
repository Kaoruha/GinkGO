"""#5565: API 端点 Pydantic 请求模型单元测试。

覆盖端点（验收：Create Pydantic models + field validation + tests for invalid inputs）：

- ``api/api/settings.py`` ``reset_user_password``  → ResetPasswordRequest
- ``api/api/settings.py`` ``add_group_member``     → AddGroupMemberRequest

注：``create_api_key`` / ``update_portfolio`` 的 schema 由 master 内联定义
（#5459 / #5474，``extra='ignore'``），其校验测试见
``tests/api/test_api_keys_persist.py`` 与
``tests/api/test_portfolio_update_validation.py``，本模块不再覆盖。

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
    ResetPasswordRequest,
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
