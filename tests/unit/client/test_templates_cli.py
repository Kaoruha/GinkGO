"""#5033: templates list 不应截断 template_id/UUID

背景: templates_cli.py list 命令 UUID 列 max_width=12 + 主动 uuid[:8]+"..."，
ID 列 max_width=15，致 live_signal_alert(16 字符) 等被截断，下游 templates get <id>
无法获取完整 ID。

收敛: 去除 ID 列 max_width（核心修复）+ UUID 列主动截断 + Created 列 max_width。
验收: ginkgo templates list 显示完整 template_id 与完整 UUID。
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from datetime import datetime

from ginkgo.client import templates_cli as templates_cli_module
from ginkgo.client.templates_cli import app

runner = CliRunner()


@pytest.fixture
def wide_terminal():
    """设 console._width 模拟真实终端宽度（200 列）。

    CliRunner 把 stdout 重定向为非 tty，Rich 回退到默认 80 列，致 7 列表格被压缩
    硬截断——并非代码 bug。真实终端宽度足够时完整显示。此 fixture 模拟真实终端。
    手动管理 _width（Rich Console.width 是 read-only property，patch.object 会
    在 teardown 撞 'no deleter' 错；_width 是可读写的内部缓存，size property 优先用它）。
    """
    console = templates_cli_module.console
    original = console._width
    console._width = 200
    try:
        yield
    finally:
        console._width = original


def _make_template(template_id="live_signal_alert", uuid="9d3da292704e46b5a3ec4e0b3da5a296"):
    """构造 mock template 对象，覆盖 list 表格读取的全部属性/方法。

    用 MagicMock 而非真实 MNotificationTemplate，避免 DB 连接依赖；
    显式 set 每个属性防 MagicMock auto-truthy 掩盖 bug
    (见 feedback_magicmock_method_attr_mask 教训)。
    """
    t = MagicMock()
    t.template_id = template_id
    t.template_name = "Live Signal Alert"
    t.uuid = uuid
    t.is_active = True
    t.tags = ["alert", "trading"]
    t.create_at = datetime(2026, 7, 4, 12, 34, 56)
    type_enum = MagicMock()
    type_enum.name = "MARKDOWN"
    t.get_template_type_enum.return_value = type_enum
    return t


class TestTemplatesListNoTruncation:
    """#5033: templates list 不应截断 template_id/UUID。"""

    @pytest.mark.unit
    def test_list_shows_full_template_id(self, wide_terminal):
        """list 应显示完整 template_id（16 字符的 live_signal_alert 不被 max_width=15 截断）。

        RED: 当前 ID 列 max_width=15 → live_signal_alert(16) 被 Rich 截断。
        """
        mock_crud = MagicMock()
        mock_crud.get_all.return_value = [_make_template(template_id="live_signal_alert")]

        with patch("ginkgo.data.containers.container.notification_template_crud",
                   return_value=mock_crud):
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0, \
            f"CLI 崩溃 (exit={result.exit_code}): {result.output}\nexc={result.exception}"
        assert "live_signal_alert" in result.output, \
            f"template_id 被截断，期望完整 'live_signal_alert':\n{result.output}"

    @pytest.mark.unit
    def test_list_shows_full_uuid(self, wide_terminal):
        """list 应显示完整 UUID（去掉 uuid[:8]+'...' 主动截断 + max_width=12）。

        RED: 当前 line 166 uuid_short = uuid[:8]+'...' → 只显示 9d3da292...
        """
        full_uuid = "9d3da292704e46b5a3ec4e0b3da5a296"
        mock_crud = MagicMock()
        mock_crud.get_all.return_value = [_make_template(uuid=full_uuid)]

        with patch("ginkgo.data.containers.container.notification_template_crud",
                   return_value=mock_crud):
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0, \
            f"CLI 崩溃 (exit={result.exit_code}): {result.output}\nexc={result.exception}"
        assert full_uuid in result.output, \
            f"UUID 被截断，期望完整 '{full_uuid}':\n{result.output}"

    @pytest.mark.unit
    def test_list_shows_full_timestamp(self, wide_terminal):
        """list 的 Created 列应显示完整时间戳（去掉 max_width=16 防截断）。

        RED: 当前 Created 列 max_width=16 → '2026-07-04 12:34'(16 字符) 边界，
        含秒的 '2026-07-04 12:34:56'(19 字符) 被截断。
        """
        mock_crud = MagicMock()
        mock_crud.get_all.return_value = [_make_template()]

        with patch("ginkgo.data.containers.container.notification_template_crud",
                   return_value=mock_crud):
            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        # 完整时间戳（含秒）必须出现
        assert "2026-07-04 12:34:56" in result.output, \
            f"Created 时间戳被截断:\n{result.output}"
