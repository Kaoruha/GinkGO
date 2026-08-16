"""
Import 回归: api Settings.env_file 必须锚定仓库根绝对路径

ginkgo CLI 是全局命令, 可从任意 CWD 启动 (ginkgo serve api)。
pydantic-settings 的 env_file 若为相对路径 ".env" 则按 CWD 解析:
从非仓库根目录启动时读不到根 .env 的 SECRET_KEY → 回落不安全默认值 →
DEBUG 未设(=False)时硬拒绝启动 (2026-08-16 从 frontend/ 启动时实况崩溃)。
"""

import os
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]
_API_DIR = _REPO_ROOT / "api"

# 与 tests/api/conftest.py 同策略: 先保证合法 SECRET_KEY 再 import config
# (config.py 模块级实例化 Settings, import 即校验)
if not os.environ.get("SECRET_KEY") or os.environ.get("SECRET_KEY") == "your-secret-key-change-in-production":
    os.environ["SECRET_KEY"] = "test-secret-key-for-jwt-anchor-tests"

sys.path.insert(0, str(_API_DIR))

from core.config import Settings  # noqa: E402


def _env_file_candidates() -> list:
    env_file = Settings.model_config.get("env_file")
    if env_file is None:
        return []
    if isinstance(env_file, (str, Path)):
        return [Path(env_file)]
    return [Path(p) for p in env_file]


class TestEnvFileAnchoredToRepoRoot:
    def test_env_file_contains_repo_root_absolute_path(self):
        """env_file 必须含指向仓库根 .env 的绝对路径, 不随 CWD 漂移。"""
        candidates = _env_file_candidates()
        assert candidates, "env_file 未配置"
        assert any(
            p.is_absolute() and p.resolve() == (_REPO_ROOT / ".env")
            for p in candidates
        ), f"env_file 未锚定仓库根 .env: {candidates}"

    @pytest.mark.skipif(
        not (_REPO_ROOT / ".env").exists() or "SECRET_KEY=" not in (_REPO_ROOT / ".env").read_text(),
        reason="本机仓库根 .env 含 SECRET_KEY 时才跑 (CI 无 .env 跳过)",
    )
    def test_settings_loads_from_foreign_cwd(self, tmp_path, monkeypatch):
        """CWD 在无 .env 的目录时, 仍应读到仓库根 .env 的 SECRET_KEY。"""
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.chdir(tmp_path)
        s = Settings()  # 不传参, 走类默认 env_file 链
        assert s.SECRET_KEY not in ("", "your-secret-key-change-in-production")
