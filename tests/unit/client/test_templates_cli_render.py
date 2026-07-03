"""templates_cli render 命令的端到端友好错误测试（issue #4760）。

验证 TemplateEngine 层的友好错误（含 template_id + 位置）能透传到
用户在终端看到的命令输出，而非裸 Jinja2 traceback。
"""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from ginkgo.client.templates_cli import app
from ginkgo.data.models.model_notification_template import MNotificationTemplate


@pytest.mark.unit
class TestTemplatesCliRenderFriendlyError:
    """render 命令在模板含语法错时输出含 template_id 的可读错误。"""

    def _make_bad_template(self) -> MNotificationTemplate:
        return MNotificationTemplate(
            template_id="live_signal",
            template_name="Live Signal",
            content="# {{ title }\nSymbol: {{ symbol }}",  # 第一行缺闭合 → 语法错
            is_active=True,
        )

    def test_render_preview_syntax_error_shows_template_id(self):
        """--preview 路径：错误输出含 template_id（issue #4760 验收点）"""
        runner = CliRunner()
        mock_crud = MagicMock()
        mock_crud.get_by_template_id.return_value = self._make_bad_template()

        with patch(
            "ginkgo.data.containers.container.notification_template_crud",
            return_value=mock_crud,
        ):
            result = runner.invoke(app, ["render", "--id", "live_signal", "--preview"])

        # 友好错误：exit_code=1，stdout 含 template_id，非裸 traceback
        assert result.exit_code == 1
        assert "live_signal" in result.output
        # 不应把 Python traceback 暴露给用户
        assert "Traceback" not in result.output

    def test_render_full_syntax_error_shows_template_id(self):
        """完整渲染路径：错误输出含 template_id"""
        runner = CliRunner()
        mock_crud = MagicMock()
        mock_crud.get_by_template_id.return_value = self._make_bad_template()

        with patch(
            "ginkgo.data.containers.container.notification_template_crud",
            return_value=mock_crud,
        ):
            result = runner.invoke(
                app,
                ["render", "--id", "live_signal", "--var", "title=X", "--var", "symbol=AAPL"],
            )

        assert result.exit_code == 1
        assert "live_signal" in result.output
        assert "Traceback" not in result.output
