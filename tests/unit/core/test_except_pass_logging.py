# Structural test: verifies that except...pass blocks have logging
# Issue #3868 - silent exception swallowing
import os
import re
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


def _has_logging_before_pass(filepath, pass_line):
    """Check if there's a GLOG/logging call between except and pass."""
    with open(filepath) as f:
        lines = f.readlines()
    for i in range(pass_line, pass_line + 1):
        if i < len(lines):
            line_content = lines[i]
            if "GLOG." in line_content or "logging.getLogger" in line_content:
                return True
    return False


class TestExceptPassHasLogging:
    """Every except...pass should have at least a GLOG call for observability."""

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
