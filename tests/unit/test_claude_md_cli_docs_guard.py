"""CLAUDE.md CLI 文档一致性守护 (#6203)。

断言 CLAUDE.md 中的 debug 命令与组件名清单与 ginkgo 0.8.1 实际行为一致，
防止 CLI 重构/组件命名演进后文档再次漂移。

验收锚点 (issue #6203 AC):
- debug 命令为 `ginkgo debug on`（非已删除的 `system config set --debug on`）
- Selector/Sizer 组件名带后缀（与 `ginkgo component list` 实际一致）
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _read_claude_md() -> str:
    # tests/unit/ → repo root (worktree root holds CLAUDE.md)
    repo_root = Path(__file__).resolve().parents[2]
    claude_md = repo_root / "CLAUDE.md"
    assert claude_md.exists(), f"CLAUDE.md not found at {claude_md}"
    return claude_md.read_text(encoding="utf-8")


def test_debug_command_uses_top_level_debug_not_system_config():
    """AC1: debug 命令应为 `ginkgo debug on`，而非已删除的 `system config set --debug on`。"""
    content = _read_claude_md()
    assert "ginkgo system config set --debug" not in content, (
        "CLAUDE.md 仍含已删除的 `ginkgo system config set --debug` 命令；"
        "0.8.1 起 debug 是顶层命令，应为 `ginkgo debug on`。"
    )
    assert "ginkgo debug on" in content, (
        "CLAUDE.md 缺少 `ginkgo debug on` 命令。"
    )


def _component_line(content: str, label: str) -> str:
    for line in content.splitlines():
        if line.lstrip().startswith(f"- **{label}**"):
            return line
    pytest.fail(f"未找到 {label} 组件清单行")


def test_selector_names_have_suffix_and_no_phantom():
    """AC2: Selector 组件名带 `_selector` 后缀，且不含未实现的 multi_params 幽灵组件。"""
    line = _component_line(_read_claude_md(), "Selector")
    for real in ("fixed_selector", "cn_all_selector", "momentum_selector", "popularity_selector"):
        assert real in line, f"Selector 清单缺少实际组件 {real}"
    # multi_params 仅存在于 fixed_selector.py 注释愿景，无文件/类/seed 实现
    assert "multi_params" not in line, (
        "Selector 清单含 multi_params——该组件未实现（无文件/类/seed），属文档幽灵。"
    )


def test_sizer_names_have_suffix():
    """AC2: Sizer 组件名带 `_sizer` 后缀。"""
    line = _component_line(_read_claude_md(), "Sizer")
    for real in ("fixed_sizer", "atr_sizer", "ratio_sizer"):
        assert real in line, f"Sizer 清单缺少实际组件 {real}"
