"""factor_cli analyze 命令测试 -- #6794 验收3 (可读+结构化输出)

注意: typer rich 模式把 option 渲染成单杠 (见 typer-rich-markup-brackets),
      故断言命令描述/输出文本而非 option 名字面量。
"""
import pytest
from typer.testing import CliRunner

try:
    from ginkgo.client.factor_cli import app
    HAS_CLI = True
except ImportError:
    HAS_CLI = False

runner = CliRunner()


@pytest.mark.skipif(not HAS_CLI, reason="factor_cli not available")
@pytest.mark.unit
class TestFactorAnalyzeCLI:
    def test_analyze_help_lists_pit_and_metrics(self):
        """analyze --help 含 PIT 防泄漏说明 + IC 指标 (验收3)。"""
        result = runner.invoke(app, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "PIT" in result.output
        assert "IC" in result.output

    def test_analyze_requires_entity(self):
        """无 --entity 退出码 1 (参数校验, 不触发 container)。"""
        result = runner.invoke(app, [
            "analyze", "ROC", "-s", "2024-01-01", "-e", "2024-12-31",
        ])
        assert result.exit_code == 1
        assert "entity" in result.output.lower()

    def test_analyze_rejects_bad_format(self):
        """--format 非 table/csv/json 退出码 1。"""
        result = runner.invoke(app, [
            "analyze", "ROC", "-s", "2024-01-01", "-e", "2024-12-31",
            "-c", "000001.SZ", "--format", "xml",
        ])
        assert result.exit_code == 1
        assert "format" in result.output.lower()
