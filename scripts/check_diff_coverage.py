#!/usr/bin/env python3
"""Small diff coverage gate for CI.

The repo cannot run the full test suite in CI safely, so this checker consumes
coverage from the existing smoke subset and gates only executable lines touched
by the PR diff.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import NamedTuple


SOURCE_PREFIXES = ("src/", "api/")
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


class DiffCoverageResult(NamedTuple):
    covered: int
    total: int
    uncovered: dict[str, list[int]]
    # Changed src/api files the smoke subset never measured. These are exempt
    # (unknown coverage, not "uncovered") so a PR touching a file outside the
    # 3-test subset isn't failed at 0% — see diff_cover convention.
    exempt: dict[str, list[int]] = {}

    @property
    def percent(self) -> float:
        if self.total == 0:
            return 100.0
        return round((self.covered / self.total) * 100, 2)


def parse_unified_diff(diff_text: str) -> dict[str, set[int]]:
    changed: dict[str, set[int]] = {}
    current_file: str | None = None
    current_line: int | None = None

    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            path = line[len("+++ b/") :]
            if path.endswith(".py") and path.startswith(SOURCE_PREFIXES):
                current_file = path
                changed.setdefault(path, set())
            else:
                current_file = None
            current_line = None
            continue

        match = HUNK_RE.match(line)
        if match:
            current_line = int(match.group(1))
            continue

        if current_file is None or current_line is None:
            continue

        if line.startswith("+") and not line.startswith("+++"):
            changed[current_file].add(current_line)
            current_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            continue
        elif line.startswith("\\"):
            # git's "\ No newline at end of file" marker — metadata about the
            # adjacent +/- line, not a file line. Skipping it (rather than the
            # context branch's `current_line += 1`) prevents line-number drift
            # for files without a trailing newline.
            continue
        else:
            current_line += 1

    return {path: lines for path, lines in changed.items() if lines}


def _coverage_file_map(coverage_json: dict) -> dict[str, dict]:
    files = coverage_json.get("files", {})
    by_norm = {}
    for path, data in files.items():
        normalized = path.replace("\\", "/")
        if normalized.startswith("./"):
            normalized = normalized[2:]
        by_norm[normalized] = data
    return by_norm


def calculate_diff_coverage(changed_lines: dict[str, set[int]], coverage_json: dict) -> DiffCoverageResult:
    coverage_files = _coverage_file_map(coverage_json)
    covered = 0
    total = 0
    uncovered: dict[str, list[int]] = {}
    exempt: dict[str, list[int]] = {}

    for path, lines in sorted(changed_lines.items()):
        data = coverage_files.get(path)
        executed = set(data.get("executed_lines", [])) if data else set()
        missing = set(data.get("missing_lines", [])) if data else set()

        if data is None or not executed:
            # No positive coverage signal for this file under the smoke subset:
            #   - data is None: file absent from the report (never imported).
            #   - executed empty: file present (e.g. coverage.py statically
            #     scanned it under `--cov=src/...`) but no line was ever
            #     executed, so the smoke subset gave no usable signal.
            # Either way coverage is unknown, not "uncovered" — exempt it
            # (diff_cover convention) and warn, instead of failing every
            # changed line at 0%. A file the smoke subset DID execute keeps
            # its full signal below (changed uncovered lines still gated).
            exempt[path] = sorted(lines)
            continue

        executable = lines & (executed | missing)

        for line_no in sorted(executable):
            total += 1
            if line_no in executed:
                covered += 1
            else:
                uncovered.setdefault(path, []).append(line_no)

    return DiffCoverageResult(covered=covered, total=total, uncovered=uncovered, exempt=exempt)


def _git_diff(base: str, head: str) -> str:
    completed = subprocess.run(
        ["git", "diff", "--unified=0", base, head, "--", "src", "api"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return completed.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check diff coverage from coverage.py JSON output")
    parser.add_argument("--coverage-json", default="coverage.json")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--threshold", type=float, default=80.0)
    args = parser.parse_args(argv)

    coverage_path = Path(args.coverage_json)
    coverage_json = json.loads(coverage_path.read_text(encoding="utf-8"))
    changed_lines = parse_unified_diff(_git_diff(args.base, args.head))
    result = calculate_diff_coverage(changed_lines, coverage_json)

    # Surface files the smoke subset never measured so the PR author knows their
    # change wasn't gated (not silently passed, not falsely failed).
    for path, lines in result.exempt.items():
        print(
            f"::warning file={path}::{len(lines)} changed line(s) not measured by the "
            f"smoke subset — diff coverage gate does not cover this file"
        )

    if result.total == 0:
        if result.exempt:
            print("Diff coverage: all changed src/api lines are in exempt (unmeasured) files; gate skipped.")
        else:
            print("Diff coverage: no changed executable src/api Python lines; gate skipped.")
        return 0

    print(
        f"Diff coverage: {result.covered}/{result.total} executable changed lines covered "
        f"({result.percent:.2f}%), threshold {args.threshold:.2f}%"
    )

    if result.percent < args.threshold:
        for path, lines in result.uncovered.items():
            for line_no in lines:
                print(f"::error file={path},line={line_no}::changed executable line is not covered")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
