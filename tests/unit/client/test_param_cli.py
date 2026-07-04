"""
param delete 的 TTY 守卫测试 (ADR-021 E3, #6578).

3 场景：
  - 非 TTY 无 --force → exit 1，delete_by_uuid 未调用（不再静默取消）
  - 非 TTY + --force → 正常删除
  - 确认通过（mock safe_confirm=True）→ 正常删除

断言走 isinstance(result.exception, ...) 通道，非 output 字面量
（CliRunner catch_exceptions=True 把退出异常吞进 result.exception，
呼应 feedback_test_cli_assertion_channel）。

注：CliRunner isolation 替换 sys.stdin 无法模拟真实 TTY，故 TTY 交互本身
由 test_cli_utils_confirm 覆盖；命令层场景 3 mock safe_confirm 返回值，
验证"确认通过后命令正确执行业务"。
"""
import pytest
import typer
from unittest.mock import MagicMock, patch

from ginkgo.client import param_cli


PARAM_ID = "abcdefgh-1234-5678-9abc-def012345678"


@pytest.mark.unit
@pytest.mark.cli
class TestParamDeleteConfirm:
    """param delete 危险操作的 TTY 守卫。"""

    def test_non_tty_without_force_exits1_and_skips_delete(self, cli_runner):
        """非 TTY 无 --force → Exit(1)，CRUD 未被调用（不再静默 no-op）。"""
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_crud = MagicMock()
            mock_container.cruds.param.return_value = mock_crud
            result = cli_runner.invoke(param_cli.app, ["delete", "--param", PARAM_ID])

        # CliRunner 默认非 TTY → safe_confirm raise CliConfirmError
        # → confirm_or_exit raise typer.Exit(1)；standalone_mode 转 SystemExit
        assert result.exit_code == 1
        assert isinstance(result.exception, (typer.Exit, SystemExit))
        mock_crud.delete_by_uuid.assert_not_called()

    def test_non_tty_with_force_deletes(self, cli_runner):
        """非 TTY + --force → CRUD 正常删除。"""
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_crud = MagicMock()
            mock_container.cruds.param.return_value = mock_crud
            result = cli_runner.invoke(
                param_cli.app, ["delete", "--param", PARAM_ID, "--force"]
            )

        assert result.exit_code == 0, result.output
        mock_crud.delete_by_uuid.assert_called_once_with(PARAM_ID)

    def test_confirmed_proceeds_with_delete(self, cli_runner):
        """确认通过（用户在 TTY 同意）→ CRUD 正常删除。

        safe_confirm 的 TTY 交互已由 test_cli_utils_confirm 覆盖；
        此处 mock safe_confirm 返回 True，验证命令集成路径。
        """
        with patch("ginkgo.client.cli_utils.safe_confirm", return_value=True), \
             patch("ginkgo.data.containers.container") as mock_container:
            mock_crud = MagicMock()
            mock_container.cruds.param.return_value = mock_crud
            result = cli_runner.invoke(param_cli.app, ["delete", "--param", PARAM_ID])

        assert result.exit_code == 0, result.output
        mock_crud.delete_by_uuid.assert_called_once_with(PARAM_ID)
