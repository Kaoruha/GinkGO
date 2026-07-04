# Structural test: verifies that except...pass blocks have logging
# Issue #3868 - silent exception swallowing
import os
import re
import textwrap
import pytest


def _find_except_pass_locations(src_dir="src/ginkgo"):
    """Find all except...pass blocks in source."""
    locations = []
    for root, dirs, files in os.walk(src_dir):
        if "__pycache__" in root or ".ipynb_checkpoints" in root:
            continue
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            lines = open(path).readlines()
            for i, line in enumerate(lines):
                stripped = line.rstrip()
                if re.match(r"\s*except\b", stripped) and stripped.endswith(":"):
                    if i + 1 < len(lines):
                        next_stripped = lines[i + 1].strip()
                        if next_stripped == "pass":
                            locations.append((path, i + 1))
    return locations


def _has_logging_before_pass(filepath, except_line):
    """Check if there's a GLOG/logging call in the except block.

    ``except_line`` is the 1-based line number of the ``except`` statement
    (as produced by ``_find_except_pass_locations``). Scan downward through the
    block body; return True if a logging call appears before ``pass`` or the
    end of the block, False otherwise. Avoids the dead-code trap of checking
    only a single line (which lands on ``pass`` itself for the common
    except-immediately-followed-by-pass shape).
    """
    with open(filepath) as f:
        lines = f.readlines()
    idx = except_line - 1  # 0-based index of the except line
    if idx < 0 or idx >= len(lines):
        return False
    except_indent = len(lines[idx]) - len(lines[idx].lstrip())
    for i in range(idx + 1, len(lines)):
        line_content = lines[i]
        if not line_content.strip():
            continue  # blank line
        cur_indent = len(line_content) - len(line_content.lstrip())
        if cur_indent <= except_indent:
            return False  # dedented out of the except block
        body = line_content.strip()
        if body.startswith("#"):
            continue
        if body == "pass":
            return False
        if "GLOG." in line_content or "logging.getLogger" in line_content or re.search(r"\blogging\.", line_content):
            return True
    return False


class TestExceptPassHasLogging:
    """Every except...pass should have at least a GLOG call for observability."""

    def test_has_logging_before_pass_detects_logging_in_block(self, tmp_path):
        """防御：helper 应识别 except 块内已有 logging 的样本（非死代码）。

        样本里 except 后跟一行业务降级语句、再跟 logging、最后 pass。
        helper 接收 except 行号（1-based），应向下扫描整个块，命中 logging → True。
        防止扫描器退化成"只看 except 下一行"的死代码（locator 传 except 行号时，
        lines[except_1based] 恰为 pass 行 → 永远 False）。
        """
        sample = textwrap.dedent("""\
            try:
                x()
            except Exception:
                fallback = None
                logging.getLogger(__name__).warning("fail", exc_info=True)
                pass
            """)
        f = tmp_path / "has_log.py"
        f.write_text(sample)
        # except 在第 3 行（1-based）；logging 在第 5 行
        assert _has_logging_before_pass(str(f), 3) is True

    def test_has_logging_before_pass_returns_false_when_no_logging(self, tmp_path):
        """防御：except 紧接 pass（块内无 logging）仍返回 False。"""
        sample = textwrap.dedent("""\
            try:
                x()
            except Exception:
                pass
            """)
        f = tmp_path / "no_log.py"
        f.write_text(sample)
        assert _has_logging_before_pass(str(f), 3) is False

    def test_all_except_pass_have_logging(self):
        locations = _find_except_pass_locations()
        unlogged = []
        for path, line in locations:
            if not _has_logging_before_pass(path, line):
                unlogged.append(f"{path}:{line + 1}")

        # Allow a small tolerance for legitimate cases (e.g., ImportError for optional deps)
        assert len(unlogged) == 0, (
            f"{len(unlogged)} except...pass blocks without logging:\n"
            + "\n".join(f"  {u}" for u in unlogged[:20])
        )
