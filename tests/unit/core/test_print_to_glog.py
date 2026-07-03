# Structural test: verifies bare print() replaced with GLOG
# Issue #3871 - print() → GLOG migration
import ast
import os
import re
import pytest


# Files where bare print() is acceptable (CLI output, demo/example results)
_ALLOWED_PRINT_FILES = {
    # CLI modules - terminal output is intentional
    "client/interactive_cli.py",
    "client/dev_cli.py",
    # Demo/example result display
    "libs/data/statistics.py",
    "validation/monte_carlo.py",
    "validation/sensitivity.py",
    "validation/walk_forward.py",
    "research/layering.py",
    "research/factor_comparison.py",
    "research/decay_analysis.py",
    "research/ic_analysis.py",
    "trading/optimization/bayesian_optimizer.py",
    "trading/optimization/genetic_optimizer.py",
    "trading/optimization/grid_search.py",
    "trading/comparison/backtest_comparator.py",
    # Console notification channel - its job IS printing
    "notifier/channels/console_channel.py",
    # Logging infrastructure - can't use GLOG
    "libs/core/logger.py",
    # GLOG fallback - print() used when GLOG is unavailable (ImportError branch)
    "core/core_containers.py",  # MockLoggerService in except ImportError
    "trading/strategies/random_signal_strategy.py",  # log_error() ImportError fallback
}


def _find_bare_prints(src_dir="src/ginkgo"):
    """Find bare print() calls (not console.print)."""
    results = []
    for root, dirs, files in os.walk(src_dir):
        if "__pycache__" in root or ".ipynb_checkpoints" in root:
            continue
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            rel = path.replace(src_dir + "/", "")
            if rel.startswith("client/"):
                continue

            lines = open(path).readlines()
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("..."):
                    continue
                if re.search(r"(?<!\.)print\(", stripped) and "console.print" not in stripped:
                    results.append((rel, i + 1, stripped))
    return results


def _check_syntax(path):
    """Return SyntaxError if ``path`` fails to parse, else None.

    Issue #5433: grep 级检查抓不到 print→GLOG 坏替换引入的语法错误。
    此 helper 用 ast.parse 兜底，正/反测试共用。
    """
    with open(path) as fh:
        source = fh.read()
    try:
        ast.parse(source, filename=path)
    except SyntaxError as exc:
        return exc
    return None


class TestBarePrintReplaced:
    """Bare print() should be replaced with GLOG except in allowed files."""

    def test_bare_print_replaced_with_glog(self):
        prints = _find_bare_prints()
        violations = []
        for rel, linenum, content in prints:
            if rel not in _ALLOWED_PRINT_FILES:
                violations.append(f"{rel}:{linenum}  {content[:80]}")

        assert len(violations) == 0, (
            f"{len(violations)} bare print() calls should use GLOG:\n"
            + "\n".join(f"  {v}" for v in violations[:30])
        )


class TestReplacedFilesHaveValidSyntax:
    """print→GLOG 替换后文件必须仍是合法 Python 语法（Issue #5433）。

    grep 级检查只能确认 ``print(`` 消失，无法发现替换引入的 SyntaxError
    （历史 commit 5a69aadf 把 ``def print(string):`` 误替换为
    ``GLOG.INFO(string):)`` 多冒号，8 个测试全绿）。这里用 ast.parse 兜底。
    """

    def test_syntax_check_catches_injected_syntaxerror(self, tmp_path):
        """反向：注入坏替换产生的 SyntaxError，helper 必须检出。

        样本复刻 issue 真实坏替换 ``GLOG.INFO(...):)``（多余右括号/冒号）。
        helper 返回 SyntaxError 实例 → 非 None；证明校验非空转。
        """
        bad = tmp_path / "bad_replace.py"
        bad.write_text('GLOG.INFO("colon"):)\n')  # 多余 ): 致 SyntaxError
        result = _check_syntax(str(bad))
        assert result is not None, "注入 SyntaxError 的文件应被检出"
        assert isinstance(result, SyntaxError)

    def test_scanned_source_files_parse_cleanly(self):
        """正向：所有被 print→GLOG 迁移覆盖的源文件必须 ast.parse 通过。

        扫描范围与 ``_find_bare_prints`` 一致（src/ginkgo 下 *.py，排除
        client/ 与 __pycache__）。任一文件 SyntaxError 立即失败，并报文件
        名+行号，定位到坏替换。
        """
        src_dir = "src/ginkgo"
        broken = []
        for root, dirs, files in os.walk(src_dir):
            if "__pycache__" in root or ".ipynb_checkpoints" in root:
                continue
            for f in files:
                if not f.endswith(".py"):
                    continue
                path = os.path.join(root, f)
                rel = path.replace(src_dir + "/", "")
                if rel.startswith("client/"):
                    continue
                exc = _check_syntax(path)
                if exc is not None:
                    broken.append(f"{rel}:{exc.lineno}  {exc.msg}")
        assert broken == [], (
            f"{len(broken)} 个源文件含 SyntaxError（疑似迁移坏替换）：\n"
            + "\n".join(f"  {b}" for b in broken[:30])
        )
