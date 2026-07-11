"""LiveCore CLI tests."""

import pytest
from typer.testing import CliRunner

from ginkgo.client import livecore_cli


@pytest.mark.unit
@pytest.mark.cli
class TestLiveCoreStatus:
    def test_status_reports_not_running_without_phase_placeholder(self):
        result = CliRunner().invoke(livecore_cli.app, ["status"])

        assert result.exit_code == 0
        assert "Phase 4" not in result.output
        assert "Not running" in result.output
        assert "ginkgo livecore start" in result.output
