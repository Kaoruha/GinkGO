"""Structural guard for the CI diff-coverage gate wiring.

The gate is a separate concern from the checker script: even a correct
`check_diff_coverage.py` fails in CI if the workflow that runs it checks out
a shallow clone. These tests pin the workflow shape so the gate stays runnable.
"""

from pathlib import Path

import yaml


def _ci_workflow():
    ci_path = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "ci.yml"
    return yaml.safe_load(ci_path.read_text(encoding="utf-8"))


def _job_running_gate(workflow):
    for name, job in workflow.get("jobs", {}).items():
        for step in job.get("steps", []):
            if "Diff coverage gate" in (step.get("name") or ""):
                return name, job
    return None, None


def test_diff_coverage_gate_job_checks_out_full_history():
    """The gate runs `git diff <base.sha> <head>`, which needs the PR base
    commit. A depth-1 checkout omits it, so `git diff` raises "unknown
    revision" on every PR. The checkout in the job that runs the gate must
    therefore set fetch-depth: 0 (full history).
    """
    workflow = _ci_workflow()
    gate_job_name, gate_job = _job_running_gate(workflow)
    assert gate_job is not None, "no step named 'Diff coverage gate' found in ci.yml"

    checkouts = [
        s
        for s in gate_job.get("steps", [])
        if isinstance(s.get("uses"), str) and s["uses"].startswith("actions/checkout")
    ]
    assert checkouts, f"'{gate_job_name}' job has no actions/checkout step"

    depths = [c.get("with", {}).get("fetch-depth") for c in checkouts]
    assert 0 in depths, (
        f"'{gate_job_name}' job runs the diff coverage gate (git diff base head) but "
        f"its checkout(s) have fetch-depth={depths}; the base commit is absent in a "
        f"shallow clone, so the gate fails on every PR"
    )
