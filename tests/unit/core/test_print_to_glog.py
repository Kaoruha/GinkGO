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
