"""#6906: CI 分层 import 门禁 — client/api 禁止直连 crud。

守护分层规则 `API/CLI → Service → CRUD → DB`（ADR-002）：client 与 api 层
只能经 `*_service` 触达数据层，禁止直接 import `ginkgo.data.crud`。
两处 scheduler 启动期构造 `RedisCRUD` 注入 livecore.Scheduler 的 DI 边界
（#6300 评估为合法）作为白名单，按站点收口。

静态断言（零 import，绕过命名空间/容器启动副作用）+ 行为断言（实跑
`lint-imports`，与 CI 同入口）双保险。
"""

import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).parents[2]  # tests/unit/xxx.py → 仓库根
PYPROJECT = REPO / "pyproject.toml"

# 两处合法 DI 边界：scheduler 启动期构造 RedisCRUD 注入 livecore.Scheduler
WHITELISTED_SITES = {
    "ginkgo.client.scheduler_cli -> ginkgo.data.crud",
    "ginkgo.client.serve_cli -> ginkgo.data.crud",
}

pytestmark = pytest.mark.refactor


def _importlinter_config() -> dict:
    cfg = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return cfg.get("tool", {}).get("importlinter", {})


def test_forbidden_contract_declared() -> None:
    """[tool.importlinter] 必须声明 forbidden 契约：client+api → crud。

    无配置时 `lint-imports` 会空过（退出 0 "Could not read any configuration"），
    故配置存在性本身必须被断言，否则门禁形同虚设。
    """
    il = _importlinter_config()
    assert il, "[tool.importlinter] 配置缺失，门禁未配置"

    contracts = il.get("contracts", [])
    forbidden = [c for c in contracts if c.get("type") == "forbidden"]
    assert forbidden, "未声明 type=forbidden 契约"

    c = forbidden[0]
    sources = set(c.get("source_modules", []))
    forbidden_mods = set(c.get("forbidden_modules", []))

    # 两层入口都要覆盖：CLI 层（ginkgo.client）与 API 层（api）
    assert "ginkgo.client" in sources, "forbidden 契约未覆盖 CLI 层 ginkgo.client"
    assert "api" in sources, "forbidden 契约未覆盖 API 层 api"
    # 数据层 crud 必须是被禁目标
    assert "ginkgo.data.crud" in forbidden_mods, "未禁止 ginkgo.data.crud"
    # 关键：仅拦直接 import。默认 false=检查传递可达，会把 client→service→crud 的
    # 合法路径也判违例（每个经 DI 容器的模块都传递触达 crud），契约形同虚设。
    # 必须显式 allow_indirect_imports=true 才只拦直接 import。
    assert str(c.get("allow_indirect_imports", "")).lower() == "true", (
        "allow_indirect_imports 必须 true（仅拦直接 import）；缺失或 false 会退化成传递可达检查"
    )


def test_whitelist_covers_scheduler_di_sites() -> None:
    """两处 scheduler 启动期 RedisCRUD DI 必须在白名单内。

    防止有人误删白名单后 lint-imports 转为报违例（而非通过）。
    """
    il = _importlinter_config()
    contracts = il.get("contracts", [])
    forbidden = next((c for c in contracts if c.get("type") == "forbidden"), None)
    assert forbidden is not None, "forbidden 契约缺失"

    ignores = set(forbidden.get("ignore_imports", []))
    missing = WHITELISTED_SITES - ignores
    assert not missing, f"白名单漏掉 scheduler DI 站点: {missing}"


def test_lint_imports_gate_passes() -> None:
    """实跑 `lint-imports`（与 CI 同入口），契约必须在 master 上通过。

    import-linter 仅装于项目 .venv（dev optional-dep）；ginkgo 运行 venv 未装时
    跳过，CI（uv run）侧由 .github/workflows/ci.yml 的 lint-imports step 强制。
    """
    # shutil.which 走 PATH 搜索（uv run 已激活项目 venv，lint-imports 在 PATH 上）；
    # sys.executable 在 uv/pytest 子进程里可能漂移到 uv 管理的 cpython toolchain，
    # 故不以它为锚。ginkgo 运行 venv 未装 lint-imports → which 返回 None → 跳过。
    lint_bin = shutil.which("lint-imports") or str(Path(sys.executable).resolve().parent / "lint-imports")
    if not Path(lint_bin).exists():
        pytest.skip("lint-imports 未安装于当前环境（dev optional-dep，CI 侧强制）")

    result = subprocess.run(
        [lint_bin],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"lint-imports 失败 (rc={result.returncode}):\n{result.stdout}\n{result.stderr}"
    )
