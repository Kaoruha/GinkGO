"""#5482: login brute-force 防护——RedisService per-username 失败计数/throttle/lockout。

纯 mock 测试（不依赖真 Redis），验证原子 pipeline 调用与 fail-open 语义。
对应 auth.py login 端点的节流入口检查与失败记录。
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.redis_service import RedisService


def _make_service():
    """构造 RedisService（跳 __init__ 避真 Redis），mock 底层 client + logger。"""
    svc = RedisService.__new__(RedisService)
    svc.redis = MagicMock()
    svc._logger = MagicMock()
    return svc


# ---------- 1. tracer：incr 原子递增 + 设 TTL 窗口 ----------
def test_incr_login_failures_counts_up_and_sets_window_ttl():
    svc = _make_service()
    pipe = MagicMock()
    pipe.execute.return_value = (1, True)
    svc.redis.pipeline.return_value = pipe

    count = svc.incr_login_failures("alice")

    assert count == 1
    pipe.incr.assert_called_once_with("auth:login_fail:alice")
    pipe.expire.assert_called_once_with("auth:login_fail:alice", 600)
    svc.redis.pipeline.assert_called_once()


def test_incr_login_failures_returns_incrementing_count():
    svc = _make_service()
    pipe = MagicMock()
    pipe.execute.return_value = (5, True)
    svc.redis.pipeline.return_value = pipe

    assert svc.incr_login_failures("bob") == 5


# ---------- 2. fail-open：Redis 异常返 0（不阻塞登录） ----------
def test_incr_login_failures_fail_open_on_redis_error():
    svc = _make_service()
    svc.redis.pipeline.side_effect = Exception("redis down")

    assert svc.incr_login_failures("alice") == 0  # 不抛，返安全默认
    svc._logger.ERROR.assert_called_once()


# ---------- 3. get/set throttle 与 lockout ----------
def test_set_login_throttle_sets_key_with_ttl():
    svc = _make_service()
    svc.set_login_throttle("alice", 8)
    svc.redis.setex.assert_called_once_with("auth:login_throttle:alice", 8, 1)


def test_set_login_lockout_defaults_5_minutes():
    svc = _make_service()
    svc.set_login_lockout("alice")
    svc.redis.setex.assert_called_once_with("auth:login_lockout:alice", 300, 1)


# ---------- 4. TTL 查询（节流入口判断） ----------
def test_get_login_throttle_ttl_returns_remaining_seconds():
    svc = _make_service()
    svc.redis.ttl.return_value = 6
    assert svc.get_login_throttle_ttl("alice") == 6
    svc.redis.ttl.assert_called_once_with("auth:login_throttle:alice")


def test_get_login_throttle_ttl_zero_when_no_key():
    svc = _make_service()
    svc.redis.ttl.return_value = -2  # redis: key 不存在
    assert svc.get_login_throttle_ttl("alice") == 0


def test_get_login_lockout_ttl_returns_remaining_seconds():
    svc = _make_service()
    svc.redis.ttl.return_value = 280
    assert svc.get_login_lockout_ttl("alice") == 280


# ---------- 5. reset：成功登录清所有节流键 ----------
def test_reset_login_state_deletes_all_three_keys():
    svc = _make_service()
    svc.reset_login_state("alice")
    deleted = {call.args[0] for call in svc.redis.delete.call_args_list}
    assert deleted == {
        "auth:login_fail:alice",
        "auth:login_throttle:alice",
        "auth:login_lockout:alice",
    }
