"""Verify no risk_managementss typo in production code.

# Issue #4555
"""
import subprocess


def test_no_double_s_in_source():
    """risk_managementss (double-s) must not appear in src/."""
    result = subprocess.run(
        ["grep", "-rn", "risk_managementss", "src/"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        f"Found typo in source:\n{result.stdout}"
    )
