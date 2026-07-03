"""
#4751: ginkgo test validate 不应崩 ModuleNotFoundError。

根因：test_cli.py:233 ``from test.database.test_isolation import ...`` 用了过时的
顶层 ``test`` 包路径（仓库已重构为 ``tests/unit/``），Python 找不到 ``test`` 包
→ ModuleNotFoundError。同样过时的 import 还存在于 ``run --database`` 分支（:381）。

测试策略：
  - CliRunner.invoke catch_exceptions=True 会把异常吞进 result.exception
    （见 feedback_test_cli_assertion_channel），故断言走 isinstance(result.exception)
    而非 output 字面量
  - validate_test_database_config 内部 try/except 兜底，不会因缺 DB 配置崩，
    只会返回 issues，所以 validate 命令能跑完
"""
from typer.testing import CliRunner

from ginkgo.client.test_cli import app


def test_validate_does_not_raise_module_not_found():
    """validate 命令不再因 ``from test.database...`` 过时 import 崩 ModuleNotFoundError。"""
    runner = CliRunner()
    result = runner.invoke(app, ["validate"], catch_exceptions=True)
    # catch_exceptions=True 吞异常进 result.exception；不抛 ModuleNotFoundError 是关键
    assert not isinstance(result.exception, ModuleNotFoundError), (
        f"validate 不应崩 ModuleNotFoundError，got: {result.exception!r}"
    )
    assert result.exit_code == 0
    # 命令真正执行（不是被 import 错挡在第一行）
    assert "Test Environment Validation" in result.output


def test_run_database_does_not_raise_module_not_found():
    """``run --database``（无 --force）触发同源 import（:381），同样不应崩。

    import 修好后，``validate_test_database_config`` 在测试环境（debug 未开）返回
    ``(False, issues)``，命令早退 return，不会调 pytest.main，无副作用。
    """
    runner = CliRunner()
    result = runner.invoke(app, ["run", "--database"], catch_exceptions=True)
    assert not isinstance(result.exception, ModuleNotFoundError), (
        f"run --database 不应崩 ModuleNotFoundError，got: {result.exception!r}"
    )
