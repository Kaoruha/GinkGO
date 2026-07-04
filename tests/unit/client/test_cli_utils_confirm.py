"""
confirm_or_exit helper 单测 (ADR-021 E3, #6578).

覆盖 3 场景：
  - 非 TTY 无 --yes → typer.Exit(1)（不再静默走 default）
  - 非 TTY + --yes(yes_flag=True) → 直接放行
  - TTY → 走 typer.confirm
"""
import pytest
import typer
from unittest.mock import patch

from ginkgo.client.cli_utils import confirm_or_exit


@pytest.mark.unit
@pytest.mark.cli
class TestConfirmOrExit:
    def test_non_tty_without_yes_raises_exit1(self):
        """非 TTY + 无 --yes → typer.Exit(1)，不再静默走 default=False。"""
        with patch("sys.stdin.isatty", return_value=False):
            with pytest.raises(typer.Exit) as exc_info:
                confirm_or_exit("dangerous op")
        assert exc_info.value.exit_code == 1

    def test_non_tty_with_yes_flag_passes(self):
        """非 TTY + yes_flag=True → 不 raise（safe_confirm 内部短路返 True）。"""
        with patch("sys.stdin.isatty", return_value=False):
            # 不应 raise
            confirm_or_exit("dangerous op", yes_flag=True)

    def test_tty_invokes_typer_confirm(self):
        """TTY → 调用 typer.confirm，由其返回值决定（mock True 放行）。"""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("ginkgo.client.cli_utils.typer.confirm", return_value=True) as m:
                confirm_or_exit("dangerous op")
            m.assert_called_once()
