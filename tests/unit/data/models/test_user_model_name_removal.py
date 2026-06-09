"""
TDD 测试：验证 MUser.name 冗余字段已移除

关联 issue: #4659

验证行为：
1. MUser 没有 name 映射列（SQLAlchemy mapper）
2. _update_from_series 不再用 name 回退 display_name
3. 构造正常工作（回归保护）
"""

import pytest
import pandas as pd
from sqlalchemy import inspect as sa_inspect

from ginkgo.data.models.model_user import MUser


# ============================================================
# Behavior 1: MUser 没有 name 映射列
# ============================================================


class TestMUserNameColumnRemoved:
    """验证 name 列已从 MUser 的 SQLAlchemy mapper 中移除"""

    @pytest.mark.unit
    def test_name_not_in_mapper_columns(self):
        """MUser 的 SQLAlchemy mapper columns 中不应包含 name"""
        mapper = sa_inspect(MUser)
        column_names = [c.key for c in mapper.columns]
        assert "name" not in column_names, (
            f"'name' should not be a mapped column. "
            f"Current columns: {column_names}"
        )

    @pytest.mark.unit
    def test_username_still_exists(self):
        """回归：username 列仍存在"""
        mapper = sa_inspect(MUser)
        column_names = [c.key for c in mapper.columns]
        assert "username" in column_names

    @pytest.mark.unit
    def test_display_name_still_exists(self):
        """回归：display_name 列仍存在"""
        mapper = sa_inspect(MUser)
        column_names = [c.key for c in mapper.columns]
        assert "display_name" in column_names


# ============================================================
# Behavior 2: _update_from_series 不再用 name 回退
# ============================================================


class TestMUserUpdateFromSeriesNoNameFallback:
    """验证 _update_from_series 不再用 name 字段回退 display_name"""

    @pytest.mark.unit
    def test_series_with_name_no_fallback(self):
        """Series 只有 name 列时，display_name 不应被设置"""
        user = MUser(username="alice", display_name="Alice Original")
        series = pd.Series({"name": "From Name Column"})

        user._update_from_series(series)

        # name 不应回退到 display_name
        assert user.display_name == "Alice Original"

    @pytest.mark.unit
    def test_series_with_display_name_takes_precedence(self):
        """回归：Series 有 display_name 时正常设置"""
        user = MUser(username="alice", display_name="Old")
        series = pd.Series({"display_name": "New Display"})

        user._update_from_series(series)

        assert user.display_name == "New Display"

    @pytest.mark.unit
    def test_series_with_both_display_name_wins(self):
        """回归：同时有 name 和 display_name 时，display_name 生效"""
        user = MUser(username="alice")
        series = pd.Series({"name": "From Name", "display_name": "From Display"})

        user._update_from_series(series)

        assert user.display_name == "From Display"


# ============================================================
# Behavior 3: 构造正常工作（回归）
# ============================================================


class TestMUserConstructionRegression:
    """回归测试：移除 name 后构造仍正常"""

    @pytest.mark.unit
    def test_constructor_sets_username_and_display_name(self):
        """构造时 username 和 display_name 正确设置"""
        user = MUser(username="bob")

        assert user.username == "bob"
        assert user.display_name == "bob"  # 默认回退到 username

    @pytest.mark.unit
    def test_constructor_with_explicit_display_name(self):
        """显式设置 display_name"""
        user = MUser(username="bob", display_name="Robert")

        assert user.username == "bob"
        assert user.display_name == "Robert"

    @pytest.mark.unit
    def test_no_name_attribute_from_init(self):
        """__init__ 不应设置 self.name 属性"""
        user = MUser(username="charlie")

        assert not hasattr(user, "name") or user.name != user.username
