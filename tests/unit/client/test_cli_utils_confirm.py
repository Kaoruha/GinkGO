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

    def test_tty_user_rejects_raises_exit0(self):
        """TTY + 用户拒绝（typer.confirm 返 False）→ typer.Exit(0)。

        master 原契约：用户主动取消 = 正常退出（exit 0），且不能继续
        执行危险操作。typer.confirm 默认 abort=False，拒绝返 False 不
        raise，故 confirm_or_exit 必须显式检查 safe_confirm 返回值
        （#6578 review #1 抓到的 regression：原实现忽略返回值，用户拒绝
        仍执行 destructive op，等于把 master 守卫整个删了）。
        """
        with patch("sys.stdin.isatty", return_value=True):
            with patch("ginkgo.client.cli_utils.typer.confirm", return_value=False):
                with pytest.raises(typer.Exit) as exc_info:
                    confirm_or_exit("dangerous op")
        assert exc_info.value.exit_code == 0
