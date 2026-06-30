"""
#5476: _get_user_id 应读 auth 中间件注入的 user_uuid，缺失时 fail-closed 抛 401

表象: _get_user_id fallback 到 "default_user"。
根因: auth 中间件注入 request.state.user_uuid（auth.py:128），
      但 _get_user_id 读 request.state.user_id 字段名不匹配，
      致所有 account 操作恒落 default_user。
契约: 缺失 user_uuid → HTTPException(401)；存在 → 返回该 uuid。

注: api/ 非 Python 包（无 __init__.py），经 tests/api/conftest 的 api_modules
    fixture 临时加入 sys.path，故 import 延迟到测试函数内。
"""

from unittest.mock import Mock
from types import SimpleNamespace

import pytest


def test_get_user_id_raises_401_when_user_uuid_missing(api_modules):
    """缺失 user_uuid 时必须 fail-closed 抛 401，不得 fallback default_user。"""
    from api import accounts as accounts_api
    from fastapi import HTTPException

    req = Mock()
    req.state = object()  # 无 user_uuid 属性 → AttributeError

    with pytest.raises(HTTPException) as exc:
        accounts_api._get_user_id(req)
    assert exc.value.status_code == 401


def test_get_user_id_returns_user_uuid_when_present(api_modules):
    """存在 user_uuid 时返回该值（与 auth 中间件注入字段对齐）。"""
    from api import accounts as accounts_api

    req = Mock()
    req.state = SimpleNamespace(user_uuid="user-abc-123")

    assert accounts_api._get_user_id(req) == "user-abc-123"


def test_get_user_id_never_returns_default_user(api_modules):
    """回归守护：任何缺失场景都不得静默 fallback 到 default_user。"""
    from api import accounts as accounts_api
    from fastapi import HTTPException

    req = Mock()
    req.state = object()  # 无任何用户标识

    # 必须抛 401 而非返回 default_user
    with pytest.raises(HTTPException):
        accounts_api._get_user_id(req)
