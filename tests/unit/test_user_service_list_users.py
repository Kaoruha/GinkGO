# See #4948: list_users(limit=N) 必须把 limit + 过滤下推到 DB 层
# (page_size=LIMIT + filters DSL __or__/__like)，不能取全量后 Python 切片。
# 反模式点名见 base_crud.py:find docstring（issue #6572 / PR #6561 决策历史）。

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ginkgo.data.services.base_service import ServiceResult


pytestmark = pytest.mark.unit


def _make_user(uuid, username="u", display_name=None, user_type=1):
    """构造 mock user（user_type=1 → PERSON，USER_TYPES.from_int 可用）"""
    return SimpleNamespace(
        uuid=uuid,
        username=username,
        display_name=display_name,
        description="",
        user_type=user_type,
        is_active=True,
        create_at=None,
    )


def _mock_user_service():
    from ginkgo.user.services.user_service import UserService
    with patch.object(UserService, '__init__', lambda self: None):
        svc = UserService()
    svc.user_crud = MagicMock()
    svc.user_contact_crud = MagicMock()
    svc.user_contact_crud.find.return_value = []
    svc.get_all_credentials = MagicMock(return_value={})
    return svc


class TestListUsersLimitPushdown:
    """limit 必须下推为 find 的 page_size（DB 层 LIMIT），不做 Python 切片。"""

    def test_limit_pushed_as_page_size(self):
        """limit=5 → find 收到 page_size=5（DB 层 LIMIT，非 Python [:5] 切片）"""
        svc = _mock_user_service()
        svc.user_crud.find.return_value = [_make_user(i) for i in range(2)]

        svc.list_users(limit=5)

        _, kwargs = svc.user_crud.find.call_args
        assert kwargs.get("page_size") == 5, "limit 必须下推为 page_size"

    def test_default_limit_100_pushed(self):
        """默认 limit=100 → find 收到 page_size=100"""
        svc = _mock_user_service()
        svc.user_crud.find.return_value = [_make_user(i) for i in range(2)]

        svc.list_users()

        _, kwargs = svc.user_crud.find.call_args
        assert kwargs.get("page_size") == 100

    def test_no_python_truncation_after_find(self):
        """守护：service 不得对 find 返回值做 [:limit] 切片。

        find 返 10 条（mock 忽略 page_size），limit=3 —— service 应原样返回 10 条
        （真实场景由 DB LIMIT 保证只返 3 条；此测试守护"不要回归 #6561 的 Python 切片"）。
        """
        svc = _mock_user_service()
        svc.user_crud.find.return_value = [_make_user(i) for i in range(10)]

        result = svc.list_users(limit=3)

        assert result.success is True
        assert result.data["count"] == 10, "service 不应对 find 结果做 Python [:limit]"


class TestListUsersNameFilterPushdown:
    """name 模糊过滤下推为 __or__ + __like（DB 层），不再 Python 端 .lower() 循环。"""

    def test_name_filter_pushed_as_or_like(self):
        """name='ali' → filters['__or__'] 含 username__like 与 display_name__like"""
        svc = _mock_user_service()
        svc.user_crud.find.return_value = [_make_user(0, username="alice")]

        svc.list_users(name="ali")

        _, kwargs = svc.user_crud.find.call_args
        filters = kwargs.get("filters", {})
        assert "__or__" in filters, "name 必须下推为 __or__ 跨字段 OR"
        or_clauses = filters["__or__"]
        assert {"username__like": "ali"} in or_clauses
        assert {"display_name__like": "ali"} in or_clauses

    def test_name_filter_no_python_lower_loop(self):
        """守护：service 不得在 Python 端按 .lower() 二次过滤。

        find 返 [alice, charlie]，name='ali' —— DB 层已过滤，service 应原样返回 2 条。
        若 service 仍 Python 端过滤会丢掉 charlie（charlie 不含 ali）。
        """
        svc = _mock_user_service()
        svc.user_crud.find.return_value = [
            _make_user(0, username="alice"),
            _make_user(1, username="charlie"),
        ]

        result = svc.list_users(name="ali")

        assert result.success is True
        assert result.data["count"] == 2, "service 不应 Python 端二次过滤 find 结果"


class TestListUsersUsernameFilterPushdown:
    """username 精确匹配下推为等值（DB 层），不再 Python 端 == 循环。"""

    def test_username_filter_pushed_as_equality(self):
        """username='alice' → filters['username'] == 'alice'（等值下推）"""
        svc = _mock_user_service()
        svc.user_crud.find.return_value = [_make_user(0, username="alice")]

        svc.list_users(username="alice")

        _, kwargs = svc.user_crud.find.call_args
        filters = kwargs.get("filters", {})
        assert filters.get("username") == "alice"

    def test_username_and_name_both_pushed(self):
        """同时传 username + name → 等值 AND __or__ 同时进 filters（语义：精确 AND 模糊）"""
        svc = _mock_user_service()
        svc.user_crud.find.return_value = [_make_user(0, username="alice")]

        svc.list_users(username="alice", name="ali")

        _, kwargs = svc.user_crud.find.call_args
        filters = kwargs.get("filters", {})
        assert filters.get("username") == "alice"
        assert "__or__" in filters

    def test_is_del_default_false_pushed(self):
        """既有契约守护：is_del 默认 False 仍下推（防重构丢默认值）"""
        svc = _mock_user_service()
        svc.user_crud.find.return_value = []

        svc.list_users()

        _, kwargs = svc.user_crud.find.call_args
        assert kwargs["filters"].get("is_del") is False
