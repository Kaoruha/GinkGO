"""Client 模式 JWT 凭证存储 (ADR-024).

存 ``$GINKGO_DIR/auth.json`` (chmod 600)：``api_base / token / expires_at / user``。

设计要点：
- **密码不落盘**——login 执行时内存持有，POST 完即丢；此处只存 bearer token。
- token 到期前可撤销 (``logout`` 清本地 + JWT 过期失效)；续期走 ``/auth/refresh``
  (凭近过期 JWT 换新)，非存密码自动重登。
- 启动期校验 auth.json 权限位 (0600)，防 group/other 可读。
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

AuthRecord = Dict[str, Any]


def auth_path() -> str:
    """auth.json 绝对路径：``$GINKGO_DIR/auth.json``。"""
    from ginkgo.libs import GCONF

    return os.path.join(GCONF.get_conf_dir(), "auth.json")


def _parse_iso_z(value: str) -> Optional[datetime]:
    """解析 ISO8601 字符串 (含 ``Z`` 后缀) 为 aware UTC datetime；失败返 None。"""
    if not value:
        return None
    try:
        s = value
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def load() -> Optional[AuthRecord]:
    """读取 auth.json；不存在/损坏返 None (不抛)。"""
    p = auth_path()
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return None
    except Exception:
        return None


def save(record: AuthRecord) -> None:
    """写 auth.json，强制 0600 (先建再 chmod 兜底 umask)。"""
    from ginkgo.libs import GCONF

    conf_dir = GCONF.get_conf_dir()
    GCONF.ensure_dir(conf_dir)
    p = os.path.join(conf_dir, "auth.json")
    # O_CREAT mode 受 umask 影响，故 open 后再显式 chmod 0600 兜底。
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
    finally:
        os.chmod(p, 0o600)


def clear() -> None:
    """删除 auth.json (logout)。文件不存在静默。"""
    p = auth_path()
    if os.path.exists(p):
        try:
            os.remove(p)
        except OSError:
            pass


def get_token() -> Optional[str]:
    """便捷取 token；未登录返 None。"""
    record = load()
    if record is None:
        return None
    token = record.get("token")
    return str(token) if token else None


def is_expired(record: AuthRecord, slack_seconds: int = 0) -> bool:
    """token 是否已过期 (含 slack 提前量)；无 expires_at 视为已过期。"""
    exp = _parse_iso_z(str(record.get("expires_at", "")))
    if exp is None:
        return True
    return datetime.now(timezone.utc) >= (exp - timedelta(seconds=slack_seconds))


def ensure_secure_perms() -> bool:
    """
    校验 auth.json 权限位为 0600；不符则修正并返 False (调用方可告警)。

    返回 True=权限本来就 OK；False=已修正或文件不存在。
    """
    p = auth_path()
    if not os.path.exists(p):
        return True
    try:
        st = Path(p).stat()
        mode = st.st_mode & 0o777
        if mode != 0o600:
            os.chmod(p, 0o600)
            return False
        return True
    except OSError:
        return False
