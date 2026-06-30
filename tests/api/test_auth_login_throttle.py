"""#5482: login 端点 brute-force 防护——auth.py helper 与端点接线测试。

验证 _check_login_throttle（入口 lockout/throttle 拦截）与 _record_login_failure
（失败计数 + progressive delay 3/5/7/9→1/2/4/8s + 10 失败 lockout 5min）。
patch container.redis_service 隔离真 Redis。
"""
import pytest
from fastapi import HTTPException


# ---------- _check_login_throttle：入口节流检查 ----------

def test_check_login_throttle_raises_429_when_locked(api_modules):
    from unittest.mock import MagicMock, patch
    from api.auth import _check_login_throttle

    rsvc = MagicMock()
    rsvc.get_login_lockout_ttl.return_value = 280
    rsvc.get_login_throttle_ttl.return_value = 0
    with patch("ginkgo.data.containers.container.redis_service", return_value=rsvc):
        with pytest.raises(HTTPException) as exc:
            _check_login_throttle("alice")
    assert exc.value.status_code == 429
    assert "locked" in exc.value.detail.lower()


def test_check_login_throttle_raises_429_when_throttled(api_modules):
    from unittest.mock import MagicMock, patch
    from api.auth import _check_login_throttle

    rsvc = MagicMock()
    rsvc.get_login_lockout_ttl.return_value = 0
    rsvc.get_login_throttle_ttl.return_value = 6
    with patch("ginkgo.data.containers.container.redis_service", return_value=rsvc):
        with pytest.raises(HTTPException) as exc:
            _check_login_throttle("alice")
    assert exc.value.status_code == 429


def test_check_login_throttle_passes_when_clear(api_modules):
    from unittest.mock import MagicMock, patch
    from api.auth import _check_login_throttle

    rsvc = MagicMock()
    rsvc.get_login_lockout_ttl.return_value = 0
    rsvc.get_login_throttle_ttl.return_value = 0
    with patch("ginkgo.data.containers.container.redis_service", return_value=rsvc):
        _check_login_throttle("alice")  # 不抛即通过


# ---------- _record_login_failure：progressive delay + lockout ----------

def test_record_login_failure_locks_out_at_10(api_modules):
    from unittest.mock import MagicMock, patch
    from api.auth import _record_login_failure

    rsvc = MagicMock()
    rsvc.incr_login_failures.return_value = 10
    with patch("ginkgo.data.containers.container.redis_service", return_value=rsvc):
        with pytest.raises(HTTPException) as exc:
            _record_login_failure("alice")
    assert exc.value.status_code == 429
    rsvc.set_login_lockout.assert_called_once_with("alice", 300)


def test_record_login_failure_sets_progressive_delay(api_modules):
    from unittest.mock import MagicMock, patch
    from api.auth import _record_login_failure

    # count → delay 映射：3→1s, 5→2s, 7→4s, 9→8s
    for count, expected_delay in [(3, 1), (5, 2), (7, 4), (9, 8)]:
        rsvc = MagicMock()
        rsvc.incr_login_failures.return_value = count
        with patch("ginkgo.data.containers.container.redis_service", return_value=rsvc):
            _record_login_failure("alice")  # 阈值内不抛
        rsvc.set_login_throttle.assert_called_once_with("alice", expected_delay)
        rsvc.set_login_lockout.assert_not_called()


def test_record_login_failure_no_delay_below_threshold(api_modules):
    from unittest.mock import MagicMock, patch
    from api.auth import _record_login_failure

    rsvc = MagicMock()
    rsvc.incr_login_failures.return_value = 2  # 未达 3 失败阈值
    with patch("ginkgo.data.containers.container.redis_service", return_value=rsvc):
        _record_login_failure("alice")
    rsvc.set_login_throttle.assert_not_called()
    rsvc.set_login_lockout.assert_not_called()
