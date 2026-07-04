# Structural test: verifies bare print() replaced with GLOG
# Issue #3871 - print() → GLOG migration
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
    # GCONF startup-phase diagnostics: print(..., file=sys.stderr) runs before
    # GLOG is initialized (config load / ImportError fallback). Same spirit as
    # logger.py / core_containers.py above.
    "libs/core/config.py",
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
                # Doctest/docstring examples (>>> prefix) are documentation,
                # not executable code — AST does not treat them as Call.
                if stripped.startswith(">>>"):
                    continue
                if re.search(r"(?<!\.)print\(", stripped) and "console.print" not in stripped:
                    results.append((rel, i + 1, stripped))
    return results


class TestBarePrintReplaced:
    """Bare print() should be replaced with GLOG except in allowed files."""

    def test_find_bare_prints_skips_doctest_examples(self, tmp_path):
        """防御：扫描器应跳过 >>> docstring/doctest 示例内的 print。

        doctest 示例（>>> 开头）是文档非代码，AST 不视为 Call。扫描器若把
        >>> print(...) 当真违规会逼作者删文档示例。已跳过 ... 续行，须同样跳 >>>。
        """
        (tmp_path / "doctest_mod.py").write_text('>>> print("doctest example")\n')
        results = _find_bare_prints(str(tmp_path))
        assert results == [], f"doctest 示例不应被报为违规: {results}"

    def test_find_bare_prints_catches_real_bare_print(self, tmp_path):
        """防御：扫描器仍能抓真违规（无 file=、无 >>> 的 stdout print）。

        防止跳过逻辑过宽把真违规也漏掉（掏空测试）。
        """
        (tmp_path / "real_mod.py").write_text('print("real violation")\n')
        results = _find_bare_prints(str(tmp_path))
        assert len(results) == 1, f"应抓到 1 处真违规: {results}"
        assert "real violation" in results[0][2]

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
