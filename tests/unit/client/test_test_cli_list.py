"""
#6017: ginkgo test list/run 在 GCONF.WORKING_PATH 为 None 时不应崩溃。

根因：config.py WORKING_PATH property 无 None 保护，配置缺 working_directory
键时返 None → test_cli.py Path(None) 抛 TypeError。list(:60) 与 run(:313) 同源。

测试策略：
  - patch GCONF.WORKING_PATH property 为 None（PropertyMock）
  - CliRunner.invoke catch_exceptions=True 会把异常吞进 result.exception
    （见 feedback_test_cli_assertion_channel），故断言走 isinstance(result.exception)
    而非 output 字面量
"""
from unittest.mock import PropertyMock, patch

from typer.testing import CliRunner

from ginkgo.client.test_cli import app
from ginkgo.libs.core.config import GCONF


def test_list_with_none_working_path_does_not_crash():
    """WORKING_PATH=None 时 list 命令回退到 cwd，不抛 TypeError。"""
    runner = CliRunner()
    with patch.object(type(GCONF), "WORKING_PATH", new_callable=PropertyMock) as mock_wp:
        mock_wp.return_value = None
        result = runner.invoke(app, ["list"], catch_exceptions=True)
    # catch_exceptions=True 吞异常进 result.exception；不抛 TypeError 是关键
    assert not isinstance(result.exception, TypeError), (
        f"WORKING_PATH=None 不应抛 TypeError，got: {result.exception!r}"
    )
    assert result.exit_code == 0


def test_list_normal_path_displays_layers():
    """AC2: 正常 WORKING_PATH 时 list 正常显示分层信息（不回归）。"""
    runner = CliRunner()
    result = runner.invoke(app, ["list"], catch_exceptions=True)
    assert result.exit_code == 0
    assert "Ginkgo Test Suite" in result.output
    assert result.exception is None or not isinstance(result.exception, TypeError)


def test_run_with_none_working_path_does_not_crash():
    """WORKING_PATH=None 时 run 命令同样回退到 cwd，不抛 TypeError。

    run :313 与 list :60 同源（#6408 一并加 ``or "."`` 兜底）。run 兜底后 cwd
    无 ``test/`` 目录 → test_paths 空 → 早退 return，不会调 pytest.main，测试无副作用。
    """
    runner = CliRunner()
    with patch.object(type(GCONF), "WORKING_PATH", new_callable=PropertyMock) as mock_wp:
        mock_wp.return_value = None
        result = runner.invoke(app, ["run"], catch_exceptions=True)
    # catch_exceptions=True 吞异常进 result.exception；不抛 TypeError 是关键
    assert not isinstance(result.exception, TypeError), (
        f"WORKING_PATH=None 不应抛 TypeError，got: {result.exception!r}"
    )
