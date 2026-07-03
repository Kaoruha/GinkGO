# #6020 — dev test/lint 引用错误目录 test/ 应为 tests/
# #5366 — dev chat 非 TTY / 无 Ollama 时应友好退出而非崩溃
"""
验证 ginkgo dev test / dev lint 命令指向真实存在的 tests/ 目录，
而非不存在的 test/（项目测试目录统一为 tests/，见 CLAUDE.md）。
另验证 dev chat 在非交互终端或 Ollama 不可用时给出友好提示退出（#5366）。
"""
import pytest
import typer
from unittest.mock import patch, MagicMock


class TestDevTestCommandTargetsTestsDir:
    """dev test 应把 tests/ 作为 pytest 目标"""

    @patch("subprocess.run")
    @patch("ginkgo.libs.GCONF")
    def test_dev_test_cmd_targets_tests_dir(self, mock_gconf, mock_run):
        mock_gconf.DEBUGMODE = True
        mock_gconf.WORKING_PATH = "/tmp"

        from ginkgo.client.dev_cli import dev_test
        dev_test()

        assert mock_run.called, "dev_test 未调用 subprocess.run"
        cmd = mock_run.call_args[0][0]
        assert "tests/" in cmd, f"#6020: dev test 未指向 tests/, cmd={cmd}"
        assert "test/" not in cmd, f"#6020: dev test 仍指向 test/, cmd={cmd}"

    @patch("subprocess.run")
    @patch("ginkgo.libs.GCONF")
    def test_dev_test_verbose_pattern_still_targets_tests_dir(self, mock_gconf, mock_run):
        """组合参数时 tests/ 仍应在 cmd 末尾"""
        mock_gconf.DEBUGMODE = True
        mock_gconf.WORKING_PATH = "/tmp"

        from ginkgo.client.dev_cli import dev_test
        dev_test(verbose=True, pattern="smoke")

        cmd = mock_run.call_args[0][0]
        assert "tests/" in cmd, f"cmd={cmd}"
        assert "test/" not in cmd, f"cmd={cmd}"


class TestDevLintCommandTargetsTestsDir:
    """dev lint / lint --fix 应把 tests/ 纳入 black/isort/flake8 范围"""

    @patch("subprocess.run")
    def test_dev_lint_fix_targets_tests_dir(self, mock_run):
        from ginkgo.client.dev_cli import dev_lint
        dev_lint(fix=True)

        # 收集所有 black/isort/flake8 调用的参数（排除 --version 探测）
        all_args = [c[0][0] for c in mock_run.call_args_list]
        tool_calls = [
            a for a in all_args
            if a and a[0] in ("black", "isort", "flake8")
            and not (len(a) == 2 and a[1] == "--version")
        ]
        assert tool_calls, f"未找到 lint 工具调用: {all_args}"
        for call in tool_calls:
            assert "tests/" in call, f"#6020: {call[0]} 未含 tests/: {call}"
            assert "test/" not in call, f"#6020: {call[0]} 仍含 test/: {call}"


class TestDevChatNonTTYGuard:
    """#5366: 非 TTY 环境应友好提示退出，不进入交互循环"""

    def test_non_tty_exits_without_cmdloop(self):
        """非交互终端调用 dev_chat 应 raise typer.Exit 且不进入 cmdloop"""
        from ginkgo.client.dev_cli import dev_chat

        with patch("sys.stdin.isatty", return_value=False), \
             patch("ginkgo.client.interactive_cli.MyPrompt") as mock_prompt:
            with pytest.raises(typer.Exit):
                dev_chat()

        # 守卫触发后绝不能构造 MyPrompt / 进入 cmdloop
        assert not mock_prompt.called, "非 TTY 不应构造 MyPrompt"


class TestDevChatOllamaUnreachableGuard:
    """#5366: Ollama 不可用时应给出安装/启动提示而非 ConnectionError 堆栈"""

    def test_ollama_unreachable_exits_without_cmdloop(self):
        """TTY 正常但连不上 Ollama 应 raise typer.Exit 且不进入 cmdloop"""
        import requests
        from ginkgo.client.dev_cli import dev_chat

        with patch("sys.stdin.isatty", return_value=True), \
             patch("requests.get", side_effect=requests.exceptions.ConnectionError), \
             patch("ginkgo.client.interactive_cli.MyPrompt") as mock_prompt:
            with pytest.raises(typer.Exit):
                dev_chat()

        assert not mock_prompt.called, "Ollama 不可用时不应构造 MyPrompt"


class TestDevChatHappyPathPreserved:
    """#5366: TTY + Ollama 可用时，原有 cmdloop 行为必须保留"""

    def test_tty_and_ollama_ok_enters_cmdloop(self):
        """守卫不应误伤正常交互场景"""
        from ginkgo.client.dev_cli import dev_chat

        ok_resp = MagicMock(status_code=200)
        with patch("sys.stdin.isatty", return_value=True), \
             patch("requests.get", return_value=ok_resp) as mock_get, \
             patch("ginkgo.client.interactive_cli.MyPrompt") as mock_prompt, \
             patch("os.system") as mock_system:
            dev_chat()

        assert mock_prompt.called, "正常路径应构造 MyPrompt"
        mock_prompt.return_value.cmdloop.assert_called_once(), "正常路径应进入 cmdloop"
        # clear 仍在守卫之后执行
        mock_system.assert_called_with("clear")
        # #5366 review: 校验传给 requests.get 的 URL 含 scheme
        # （原 happy-path 用 MagicMock 整体替换 get，schema bug 测试不可见）
        called_url = mock_get.call_args[0][0]
        assert called_url.startswith(("http://", "https://")), \
            f"URL 缺 scheme，默认配置会触发 InvalidSchema: {called_url}"
        assert called_url.endswith("/api/tags"), f"URL 应指向 /api/tags: {called_url}"


class TestCheckOllamaReachableSchemaException:
    """#5366 review: except 收窄，schema 类异常（InvalidSchema/MissingSchema/InvalidURL）
    必须原样抛出。宽 except RequestException 会把它们当「连不上」吞掉，
    把配置 bug 伪装成「Ollama 没启动」，违背归因纪律。"""

    def test_invalid_schema_propagates_not_swallowed(self):
        """requests.get 抛 InvalidSchema 时应原样抛，不返 False"""
        import requests
        from ginkgo.client.dev_cli import _check_ollama_reachable

        with patch("requests.get", side_effect=requests.exceptions.InvalidSchema("No connection adapters")):
            with pytest.raises(requests.exceptions.InvalidSchema):
                _check_ollama_reachable()

    def test_connection_error_still_swallowed_friendly(self):
        """真·连接错误仍应友好吞掉返 False（保留原 #5366 守卫语义）"""
        import requests
        from ginkgo.client.dev_cli import _check_ollama_reachable

        with patch("requests.get", side_effect=requests.exceptions.ConnectionError):
            assert _check_ollama_reachable() is False

    def test_timeout_still_swallowed_friendly(self):
        """超时仍应友好吞掉返 False"""
        import requests
        from ginkgo.client.dev_cli import _check_ollama_reachable

        with patch("requests.get", side_effect=requests.exceptions.Timeout):
            assert _check_ollama_reachable() is False


class TestAskOllamaUsesNormalizedUrl:
    """#5366 review: interactive_cli.ask_ollama 同款裸 URL（{OLLAMA_HOST}:{PORT}/api/generate），
    守卫侥幸过了进 REPL 仍崩。必须复用归一化 helper。"""

    def test_ask_ollama_url_contains_scheme(self):
        """ask_ollama 传给 requests.post 的 URL 必须含 scheme"""
        import ginkgo.client.interactive_cli as ic

        with patch.object(ic, "mem", ""), \
             patch.object(ic, "requests") as mock_requests, \
             patch.object(ic, "chunk_print"):
            ic.ask_ollama("hello")

        called_url = mock_requests.post.call_args[0][0]
        assert called_url.startswith(("http://", "https://")), \
            f"ask_ollama URL 缺 scheme，进 REPL 仍会 InvalidSchema: {called_url}"
        assert called_url.endswith("/api/generate"), \
            f"URL 应指向 /api/generate: {called_url}"


class TestNormalizeOllamaUrl:
    """#5366 review: OLLAMA_HOST 默认裸 host（localhost），URL 必须归一化补 scheme，
    否则 requests.get 抛 InvalidSchema 被宽 except 吞 → 守卫恒 False。"""

    def test_bare_host_gets_http_scheme(self):
        """裸 host（默认 localhost）应补 http:// 前缀"""
        from ginkgo.client.interactive_cli import _normalize_ollama_url

        url = _normalize_ollama_url("localhost", "11434", "/api/tags")
        assert url == "http://localhost:11434/api/tags"

    def test_host_with_scheme_preserved(self):
        """用户显式配置 http:// 或 https:// 时不重复补 scheme"""
        from ginkgo.client.interactive_cli import _normalize_ollama_url

        assert _normalize_ollama_url("http://localhost", "11434", "/api/tags") == "http://localhost:11434/api/tags"
        assert _normalize_ollama_url("https://ollama.example.com", "11434", "/api/tags") == "https://ollama.example.com:11434/api/tags"
