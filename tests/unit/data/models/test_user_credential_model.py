# #3895 MUserCredential.update() TDD tests
import datetime

import pytest

from ginkgo.data.models.model_user_credential import MUserCredential


class TestMUserCredentialUpdate:
    """MUserCredential.update() 行为测试 — #3895"""

    def _make(self, **overrides):
        defaults = dict(user_id="user-001", password_hash="h1")
        defaults.update(overrides)
        return MUserCredential(**defaults)

    # --- kwargs 更新 ---

    def test_update_password_hash_via_kwargs(self):
        cred = self._make()
        cred.update(password_hash="new_hash")
        assert cred.password_hash == "new_hash"

    def test_update_is_active_via_kwargs(self):
        cred = self._make()
        cred.update(is_active=False)
        assert cred.is_active is False

    def test_update_is_admin_via_kwargs(self):
        cred = self._make()
        cred.update(is_admin=True)
        assert cred.is_admin is True

    def test_update_multiple_fields_via_kwargs(self):
        cred = self._make()
        cred.update(password_hash="h2", is_active=False, is_admin=True)
        assert cred.password_hash == "h2"
        assert cred.is_active is False
        assert cred.is_admin is True

    # --- update_at 刷新 ---

    def test_update_refreshes_update_at(self):
        cred = self._make()
        before = cred.update_at
        cred.update(password_hash="h3")
        assert cred.update_at > before

    # --- pd.Series 更新 ---

    def test_update_from_series(self):
        import pandas as pd

        cred = self._make()
        series = pd.Series({
            "password_hash": "series_hash",
            "is_active": False,
            "is_admin": True,
        })
        cred.update(series)
        assert cred.password_hash == "series_hash"
        assert cred.is_active is False
        assert cred.is_admin is True

    # --- 错误处理 ---

    def test_update_no_args_raises(self):
        cred = self._make()
        with pytest.raises(NotImplementedError):
            cred.update()

    def test_update_unsupported_type_raises(self):
        cred = self._make()
        with pytest.raises(NotImplementedError):
            cred.update(12345)
