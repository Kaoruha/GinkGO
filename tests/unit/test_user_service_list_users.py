# See #4948: list_users(limit=N) 必须截断到 N 条，不能 dead parameter

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


class TestListUsersLimit:
    def test_limit_truncates_results(self):
        """list_users(limit=2) 当 DB 返回 5 用户时，只返回 2 条（#4948 核心）"""
        svc = _mock_user_service()
        svc.user_crud.find.return_value = [_make_user(i) for i in range(5)]

        result = svc.list_users(limit=2)

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert len(result.data["users"]) == 2
        assert result.data["count"] == 2

    def test_limit_applies_after_name_filter(self):
        """先 name 过滤再 limit 截断——不能先截断后过滤（否则丢匹配）"""
        svc = _mock_user_service()
        svc.user_crud.find.return_value = [
            _make_user(0, username="bob0"),
            _make_user(1, username="alice1"),
            _make_user(2, username="bob2"),
            _make_user(3, username="alice3"),
            _make_user(4, username="alice4"),
        ]

        result = svc.list_users(name="alice", limit=2)

        assert result.success is True
        # name=alice 匹配 3 个，limit=2 截断到 2 个（若先截断 2 再过滤只得 1 个，错）
        assert len(result.data["users"]) == 2
        usernames = [u["username"] for u in result.data["users"]]
        assert all("alice" in u for u in usernames)

    def test_default_limit_100(self):
        """limit 默认 100，DB 返回 150 用户时只返回 100 条"""
        svc = _mock_user_service()
        svc.user_crud.find.return_value = [_make_user(i) for i in range(150)]

        result = svc.list_users()  # 不传 limit，用默认 100

        assert result.success is True
        assert len(result.data["users"]) == 100
