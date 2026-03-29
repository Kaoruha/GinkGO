"""
Serve CLI 单元测试

测试 ginkgo.client.serve_cli 的所有命令：
- api: 启动 API 服务器 (FastAPI + Uvicorn)
- webui: 启动 Web UI 开发服务器 (Vue 3 + Vite)
- all: 同时启动 API + Web UI
- livecore: 启动 LiveCore 实盘交易容器
- execution: 启动 ExecutionNode 执行节点
- scheduler: 启动 Scheduler 调度器
- tasktimer: 启动 TaskTimer 定时任务
- worker-data: 启动 DataWorker 数据工作器
- worker-backtest: 启动 BacktestWorker 回测工作器
- mcp: 启动 MCP Server

测试重点：帮助信息、参数传递、路径检查、依赖缺失处理。
"""

import os
import sys

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from ginkgo.client import serve_cli


@pytest.fixture
def runner():
    return CliRunner()


# ============================================================================
# 1. Help 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestServeHelp:
    """serve 命令帮助信息"""

    def test_serve_root_help_shows_all_commands(self, runner):
        """serve --help 列出所有可用子命令"""
        result = runner.invoke(serve_cli.app, ["--help"])
        assert result.exit_code == 0
        assert "api" in result.output
        assert "webui" in result.output
        assert "all" in result.output
        assert "livecore" in result.output
        assert "execution" in result.output
        assert "scheduler" in result.output
        assert "tasktimer" in result.output
        assert "worker-data" in result.output
        assert "worker-backtest" in result.output
        assert "mcp" in result.output

    def test_serve_api_help_shows_options(self, runner):
        """serve api --help 显示 host/port/reload 选项"""
        result = runner.invoke(serve_cli.app, ["api", "--help"])
        assert result.exit_code == 0
        assert "--host" in result.output or "-h" in result.output
        assert "--port" in result.output or "-p" in result.output
        assert "--reload" in result.output or "-r" in result.output

    def test_serve_webui_help_shows_options(self, runner):
        """serve webui --help 显示 host/port/open 选项"""
        result = runner.invoke(serve_cli.app, ["webui", "--help"])
        assert result.exit_code == 0
        assert "--host" in result.output or "-h" in result.output
        assert "--port" in result.output or "-p" in result.output
        assert "--open" in result.output or "-o" in result.output


# ============================================================================
# 2. API 命令
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestServeApi:
    """serve api 命令测试"""

    @staticmethod
    def _make_fake_uvicorn():
        fake = MagicMock()
        fake.run = MagicMock()
        return fake

    @patch("os.path.exists", return_value=True)
    def test_api_default_invocation(self, mock_exists, runner):
        """默认参数调用 api 命令，传递正确的 host/port/reload"""
        fake_uvicorn = self._make_fake_uvicorn()
        with patch.dict("sys.modules", {"uvicorn": fake_uvicorn}):
            result = runner.invoke(serve_cli.app, ["api"])
        assert result.exit_code == 0
        assert "API Server" in result.output
        assert "8000" in result.output
        fake_uvicorn.run.assert_called_once()
        call_kwargs = fake_uvicorn.run.call_args
        assert call_kwargs.kwargs["host"] == "0.0.0.0"
        assert call_kwargs.kwargs["port"] == 8000
        assert call_kwargs.kwargs["reload"] is True

    @patch("os.path.exists", return_value=True)
    def test_api_custom_port(self, mock_exists, runner):
        """--port 参数传递自定义端口号"""
        fake_uvicorn = self._make_fake_uvicorn()
        with patch.dict("sys.modules", {"uvicorn": fake_uvicorn}):
            result = runner.invoke(serve_cli.app, ["api", "--port", "9000"])
        assert result.exit_code == 0
        assert "9000" in result.output
        call_kwargs = fake_uvicorn.run.call_args
        assert call_kwargs.kwargs["port"] == 9000

    @patch("os.path.exists", return_value=True)
    def test_api_explicit_reload_flag(self, mock_exists, runner):
        """显式传递 --reload 标志时启用 reload 并设置 reload_dirs"""
        fake_uvicorn = self._make_fake_uvicorn()
        with patch.dict("sys.modules", {"uvicorn": fake_uvicorn}):
            result = runner.invoke(serve_cli.app, ["api", "--reload"])
        assert result.exit_code == 0
        assert "On" in result.output
        call_kwargs = fake_uvicorn.run.call_args
        assert call_kwargs.kwargs["reload"] is True
        assert "reload_dirs" in call_kwargs.kwargs


# ============================================================================
# 3. WebUI 命令
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestServeWebui:
    """serve webui 命令测试"""

    @patch("os.path.exists", return_value=True)
    @patch("shutil.which", return_value="/usr/bin/npm")
    @patch("subprocess.run")
    def test_webui_default_invocation(self, mock_run, mock_which, mock_exists, runner):
        """默认参数调用 webui 命令"""
        result = runner.invoke(serve_cli.app, ["webui"])
        assert result.exit_code == 0
        assert "Web UI" in result.output
        assert "5173" in result.output
        # subprocess.run should be called for npm run dev
        mock_run.assert_called_once()
        cmd_list = mock_run.call_args.args[0]
        assert "npm" in cmd_list[0]
        assert "dev" in cmd_list

    @patch("os.path.exists", return_value=True)
    @patch("shutil.which", return_value="/usr/bin/npm")
    @patch("subprocess.run")
    def test_webui_open_browser_flag(self, mock_run, mock_which, mock_exists, runner):
        """--open 标志被传递到环境变量"""
        result = runner.invoke(serve_cli.app, ["webui", "--open"])
        assert result.exit_code == 0
        # 验证命令被调用
        mock_run.assert_called_once()
        cmd_list = mock_run.call_args.args[0]
        assert "npm" in cmd_list[0]


# ============================================================================
# 4. 错误处理
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestServeErrorHandling:
    """serve 命令错误处理测试"""

    @patch("os.path.exists", return_value=False)
    def test_api_path_not_found(self, mock_exists, runner):
        """API 路径不存在时退出码为 1"""
        result = runner.invoke(serve_cli.app, ["api"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    @patch("os.path.exists", return_value=False)
    def test_webui_path_not_found(self, mock_exists, runner):
        """Web UI 路径不存在时退出码为 1"""
        result = runner.invoke(serve_cli.app, ["webui"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    @patch("os.path.exists", return_value=True)
    def test_api_missing_uvicorn_dependency(self, mock_exists, runner):
        """uvicorn 未安装时显示安装提示并退出"""
        import ginkgo.client.serve_cli as serve_module

        # 让 import uvicorn 抛出 ImportError
        with patch.dict("sys.modules", {"uvicorn": None}):
            result = runner.invoke(serve_cli.app, ["api"])
        assert result.exit_code == 1
        assert "uvicorn" in result.output.lower()

    @patch("os.path.exists", return_value=True)
    @patch("shutil.which", return_value=None)
    def test_webui_npm_not_found(self, mock_which, mock_exists, runner):
        """npm 不存在时显示安装提示并退出"""
        result = runner.invoke(serve_cli.app, ["webui"])
        assert result.exit_code == 1
        assert "npm" in result.output.lower()
        assert "Node.js" in result.output
