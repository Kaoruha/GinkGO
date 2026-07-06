import importlib.util
from pathlib import Path


def _load_module():
    script = Path(__file__).resolve().parents[3] / "scripts" / "check_diff_coverage.py"
    spec = importlib.util.spec_from_file_location("check_diff_coverage", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_unified_diff_tracks_added_python_lines_under_src_and_api():
    module = _load_module()
    diff = """diff --git a/src/ginkgo/foo.py b/src/ginkgo/foo.py
--- a/src/ginkgo/foo.py
+++ b/src/ginkgo/foo.py
@@ -10,0 +11,3 @@
+covered()
+# comment
+missing()
diff --git a/docs/readme.md b/docs/readme.md
--- a/docs/readme.md
+++ b/docs/readme.md
@@ -1,0 +2,1 @@
+ignored
diff --git a/api/bar.py b/api/bar.py
--- a/api/bar.py
+++ b/api/bar.py
@@ -4,2 +4,2 @@
-old()
+new()
 context()
"""

    assert module.parse_unified_diff(diff) == {
        "src/ginkgo/foo.py": {11, 12, 13},
        "api/bar.py": {4},
    }


def test_calculate_diff_coverage_ignores_non_executable_lines():
    module = _load_module()
    changed = {"src/ginkgo/foo.py": {11, 12, 13}}
    coverage = {
        "files": {
            "src/ginkgo/foo.py": {
                "executed_lines": [11],
                "missing_lines": [13],
            }
        }
    }

    result = module.calculate_diff_coverage(changed, coverage)

    assert result.total == 2
    assert result.covered == 1
    assert result.uncovered == {"src/ginkgo/foo.py": [13]}
    assert result.percent == 50.0


def test_calculate_diff_coverage_reports_no_source_changes():
    module = _load_module()

    result = module.calculate_diff_coverage({}, {"files": {}})

    assert result.total == 0
    assert result.covered == 0
    assert result.percent == 100.0


def test_calculate_diff_coverage_exempts_files_absent_from_coverage_report():
    """Files the smoke subset never imported are exempt, not 0%-covered.

    Mirrors diff_cover: a file absent from the coverage report is "unknown
    coverage", not "uncovered". Otherwise a PR touching any file outside the
    3-test smoke subset fails at 0% even when it ships dedicated tests, and
    comments/blank lines in the diff get counted as uncovered executable
    lines — contradicting the module docstring.
    """
    module = _load_module()
    changed = {
        "src/ginkgo/foo.py": {11, 12, 13},  # measured below
        "src/ginkgo/unmeasured.py": {5, 6, 7},  # absent from coverage.json
    }
    coverage = {
        "files": {
            "src/ginkgo/foo.py": {
                "executed_lines": [11, 12],
                "missing_lines": [13],
            }
        }
    }

    result = module.calculate_diff_coverage(changed, coverage)

    # unmeasured.py must not pollute the totals or show up as uncovered.
    assert result.total == 3
    assert result.covered == 2
    assert result.uncovered == {"src/ginkgo/foo.py": [13]}
    assert "src/ginkgo/unmeasured.py" not in result.uncovered
    # And it must be surfaced so CI can warn the author their file wasn't measured.
    assert result.exempt == {"src/ginkgo/unmeasured.py": [5, 6, 7]}
