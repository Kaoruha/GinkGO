"""
性能: 273MB RSS, 2.5s, 27 tests [PASS]
"""

# tests/unit/client/test_paper_trading_cli.py
"""
Tests for deploy/unload paper trading CLI commands.

Tests cover:
- deploy command: DB creation + Kafka notification
- unload command: Kafka notification to worker
- _deploy_paper_trading: portfolio creation and mapping copy
- _send_deploy_notification: Kafka send
- _send_unload_command: Kafka send
"""
import os
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from typer.testing import CliRunner

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"


class TestDeployCommandRegistration:
    """deploy 命令注册测试"""

    def test_deploy_command_exists(self):
        """deploy 命令应在 CLI 中注册"""
        from ginkgo.client.portfolio_cli import app

        registered = [cmd for cmd in app.registered_commands if cmd.name == "deploy"]
        assert len(registered) > 0, "deploy command should be registered"

    def test_unload_command_exists(self):
        """unload 命令应在 CLI 中注册"""
        from ginkgo.client.portfolio_cli import app

        registered = [cmd for cmd in app.registered_commands if cmd.name == "unload"]
        assert len(registered) > 0, "unload command should be registered"

    def test_stop_command_removed(self):
        """旧的 stop 命令应不再存在"""
        from ginkgo.client.portfolio_cli import app

        registered = [cmd for cmd in app.registered_commands if cmd.name == "stop"]
        assert len(registered) == 0, "old stop command should be removed"


class TestDeployCommandInvocation:
    """deploy 命令调用测试"""

    @patch("ginkgo.client.portfolio_cli.GLOG")
    @patch("ginkgo.client.portfolio_cli.console")
    @patch("ginkgo.client.portfolio_cli._deploy_paper_trading")
    def test_deploy_calls_internal_function(self, mock_deploy, mock_console, mock_glog):
        """deploy 命令应调用 _deploy_paper_trading"""
        mock_deploy.return_value = "new_paper_portfolio_uuid"

        from ginkgo.client.portfolio_cli import app
        runner = CliRunner()
        result = runner.invoke(app, [
            "deploy",
            "--source", "source_portfolio_id",
            "--name", "my_paper",
        ])

        assert result.exit_code == 0
        mock_deploy.assert_called_once_with(
            source_portfolio_id="source_portfolio_id",
            name="my_paper",
        )

    @patch("ginkgo.client.portfolio_cli.GLOG")
    @patch("ginkgo.client.portfolio_cli.console")
    @patch("ginkgo.client.portfolio_cli._deploy_paper_trading")
    def test_deploy_without_name(self, mock_deploy, mock_console, mock_glog):
        """deploy 不传 --name 时 name 应为 None"""
        mock_deploy.return_value = "paper_uuid_123"

        from ginkgo.client.portfolio_cli import app
        runner = CliRunner()
        result = runner.invoke(app, [
            "deploy",
            "--source", "source_portfolio_id",
        ])

        assert result.exit_code == 0
        mock_deploy.assert_called_once_with(
            source_portfolio_id="source_portfolio_id",
            name=None,
        )

    @patch("ginkgo.client.portfolio_cli.GLOG")
    @patch("ginkgo.client.portfolio_cli.console")
    @patch("ginkgo.client.portfolio_cli._deploy_paper_trading")
    def test_deploy_failure_shows_error(self, mock_deploy, mock_console, mock_glog):
        """deploy 失败时应显示错误信息"""
        mock_deploy.side_effect = ValueError("Source portfolio not found")

        from ginkgo.client.portfolio_cli import app
        runner = CliRunner()
        result = runner.invoke(app, [
            "deploy",
            "--source", "bad_source",
        ])

        assert result.exit_code == 1
        mock_console.print.assert_called()
        call_args = str(mock_console.print.call_args)
        assert "Deploy failed" in call_args


class TestUnloadCommandInvocation:
    """unload 命令调用测试"""

    @patch("ginkgo.client.portfolio_cli.GLOG")
    @patch("ginkgo.client.portfolio_cli.console")
    @patch("ginkgo.client.portfolio_cli._send_unload_command")
    def test_unload_calls_send_unload(self, mock_unload, mock_console, mock_glog):
        """unload 命令应调用 _send_unload_command"""
        mock_unload.return_value = True

        from ginkgo.client.portfolio_cli import app
        runner = CliRunner()
        result = runner.invoke(app, [
            "unload",
            "paper_portfolio_id",
        ])

        assert result.exit_code == 0
        mock_unload.assert_called_once_with("paper_portfolio_id")

    @patch("ginkgo.client.portfolio_cli.GLOG")
    @patch("ginkgo.client.portfolio_cli.console")
    @patch("ginkgo.client.portfolio_cli._send_unload_command")
    def test_unload_failure_exits_with_error(self, mock_unload, mock_console, mock_glog):
        """unload Kafka 发送失败时应报错退出"""
        mock_unload.return_value = False

        from ginkgo.client.portfolio_cli import app
        runner = CliRunner()
        result = runner.invoke(app, [
            "unload",
            "paper_portfolio_id",
        ])

        assert result.exit_code == 1
        # Verify at least one error message was printed
        all_calls = [str(c) for c in mock_console.print.call_args_list]
        has_error = any("Failed to send unload command" in c or "Unload failed" in c for c in all_calls)
        assert has_error, f"Expected error message in calls: {all_calls}"

    @patch("ginkgo.client.portfolio_cli.GLOG")
    @patch("ginkgo.client.portfolio_cli.console")
    @patch("ginkgo.client.portfolio_cli._send_unload_command")
    def test_unload_exception_shows_error(self, mock_unload, mock_console, mock_glog):
        """unload 异常时应报错退出"""
        mock_unload.side_effect = Exception("Kafka connection failed")

        from ginkgo.client.portfolio_cli import app
        runner = CliRunner()
        result = runner.invoke(app, [
            "unload",
            "paper_portfolio_id",
        ])

        assert result.exit_code == 1
        call_args = str(mock_console.print.call_args)
        assert "Unload failed" in call_args


class TestDeployPaperTrading:
    """_deploy_paper_trading 核心逻辑测试"""

    def _make_mock_source_portfolio(self):
        """创建 mock 源 Portfolio"""
        source = MagicMock()
        source.name = "backtest_portfolio"
        source.uuid = "source_uuid"
        return source

    def _make_mock_service_result(self, data, success=True):
        """创建 mock ServiceResult"""
        result = MagicMock()
        result.success = success
        result.error = None if success else "error"
        result.data = data
        return result

    def _setup_mock_data(self, source_result, create_result, mappings=None):
        """设置 mock data container"""
        mock_ps = MagicMock()
        mock_ps.get.return_value = source_result
        mock_ps.add.return_value = create_result

        mock_crud = MagicMock()
        mock_crud.find.return_value = mappings or []

        mock_data = MagicMock()
        mock_data.portfolio_service.return_value = mock_ps
        mock_data.cruds.portfolio_file_mapping.return_value = mock_crud
        return mock_data, mock_ps, mock_crud

    @patch("ginkgo.client.portfolio_cli._send_deploy_notification")
    @patch("ginkgo.services")
    def test_deploy_creates_paper_portfolio(self, mock_services, mock_send):
        """应创建 PAPER 模式的 Portfolio"""
        source_portfolio = self._make_mock_source_portfolio()
        source_result = self._make_mock_service_result([source_portfolio])
        create_result_data = {"uuid": "new_paper_uuid", "name": "paper_backtest_portfolio"}
        create_result = self._make_mock_service_result(create_result_data)

        mock_data, mock_ps, mock_crud = self._setup_mock_data(source_result, create_result)
        mock_services.data = mock_data

        from ginkgo.client.portfolio_cli import _deploy_paper_trading
        result_id = _deploy_paper_trading(
            source_portfolio_id="source_uuid",
            name="paper_backtest_portfolio",
        )

        assert result_id == "new_paper_uuid"
        mock_ps.add.assert_called_once()
        call_kwargs = mock_ps.add.call_args[1]
        assert call_kwargs["mode"].name == "PAPER"
        assert call_kwargs["name"] == "paper_backtest_portfolio"

    @patch("ginkgo.client.portfolio_cli._send_deploy_notification")
    @patch("ginkgo.services")
    def test_deploy_copies_mappings(self, mock_services, mock_send):
        """应复制源 Portfolio 的组件映射"""
        source_portfolio = self._make_mock_source_portfolio()
        source_result = self._make_mock_service_result([source_portfolio])
        create_result_data = {"uuid": "new_paper_uuid", "name": "paper_backtest_portfolio"}
        create_result = self._make_mock_service_result(create_result_data)

        mock_mapping = MagicMock()
        mock_mapping.file_id = "file_001"
        mock_mapping.name = "strategy_ma"
        mock_mapping.type.value = "strategy"

        mock_data, mock_ps, mock_crud = self._setup_mock_data(source_result, create_result, [mock_mapping])
        mock_services.data = mock_data

        from ginkgo.client.portfolio_cli import _deploy_paper_trading
        _deploy_paper_trading(
            source_portfolio_id="source_uuid",
            name="paper_backtest_portfolio",
        )

        mock_crud.add.assert_called_once()
        call_kwargs = mock_crud.add.call_args[1]
        assert call_kwargs["portfolio_id"] == "new_paper_uuid"
        assert call_kwargs["file_id"] == "file_001"
        assert call_kwargs["type"] == "strategy"

    @patch("ginkgo.client.portfolio_cli._send_deploy_notification")
    @patch("ginkgo.services")
    def test_deploy_sends_kafka_notification(self, mock_services, mock_send):
        """应发送 Kafka deploy 通知"""
        source_portfolio = self._make_mock_source_portfolio()
        source_result = self._make_mock_service_result([source_portfolio])
        create_result_data = {"uuid": "new_paper_uuid", "name": "paper_backtest_portfolio"}
        create_result = self._make_mock_service_result(create_result_data)

        mock_data, mock_ps, mock_crud = self._setup_mock_data(source_result, create_result)
        mock_services.data = mock_data

        from ginkgo.client.portfolio_cli import _deploy_paper_trading
        _deploy_paper_trading(source_portfolio_id="source_uuid")

        mock_send.assert_called_once_with("new_paper_uuid")

    @patch("ginkgo.services")
    def test_deploy_source_not_found_raises(self, mock_services):
        """源 Portfolio 不存在时应抛出 ValueError"""
        source_result = self._make_mock_service_result(None, success=False)
        mock_data, mock_ps, mock_crud = self._setup_mock_data(source_result, None)
        mock_services.data = mock_data

        from ginkgo.client.portfolio_cli import _deploy_paper_trading
        with pytest.raises(ValueError, match="Source portfolio not found"):
            _deploy_paper_trading(source_portfolio_id="bad_source")

    @patch("ginkgo.client.portfolio_cli._send_deploy_notification")
    @patch("ginkgo.services")
    def test_deploy_create_fails_raises(self, mock_services, mock_send):
        """创建 Portfolio 失败时应抛出 ValueError"""
        source_portfolio = self._make_mock_source_portfolio()
        source_result = self._make_mock_service_result([source_portfolio])

        create_result = self._make_mock_service_result(None, success=False)
        create_result.error = "Name already exists"

        mock_data, mock_ps, mock_crud = self._setup_mock_data(source_result, create_result)
        mock_services.data = mock_data

        from ginkgo.client.portfolio_cli import _deploy_paper_trading
        with pytest.raises(ValueError, match="Failed to create paper portfolio"):
            _deploy_paper_trading(source_portfolio_id="source_uuid")

    @patch("ginkgo.client.portfolio_cli._send_deploy_notification")
    @patch("ginkgo.services")
    def test_deploy_default_name_generation(self, mock_services, mock_send):
        """不传 name 时应自动生成名称"""
        source_portfolio = self._make_mock_source_portfolio()
        source_result = self._make_mock_service_result([source_portfolio])
        create_result_data = {"uuid": "new_paper_uuid", "name": "paper_backtest_portfolio"}
        create_result = self._make_mock_service_result(create_result_data)

        mock_data, mock_ps, mock_crud = self._setup_mock_data(source_result, create_result)
        mock_services.data = mock_data

        from ginkgo.client.portfolio_cli import _deploy_paper_trading
        _deploy_paper_trading(source_portfolio_id="source_uuid", name=None)

        call_kwargs = mock_ps.add.call_args[1]
        assert call_kwargs["name"] == "paper_backtest_portfolio"


class TestSendDeployNotification:
    """_send_deploy_notification 测试"""

    @patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer")
    def test_sends_deploy_command_to_kafka(self, mock_producer_cls):
        """应发送 deploy 命令到 CONTROL_COMMANDS topic"""
        mock_producer = MagicMock()
        mock_producer.send.return_value = True
        mock_producer_cls.return_value = mock_producer

        from ginkgo.client.portfolio_cli import _send_deploy_notification

        _send_deploy_notification("portfolio_123")

        mock_producer.send.assert_called_once()
        topic = mock_producer.send.call_args[0][0]
        msg = mock_producer.send.call_args[0][1]
        assert topic == "ginkgo.live.control.commands"
        assert msg["command"] == "deploy"
        assert msg["portfolio_id"] == "portfolio_123"
        assert "timestamp" in msg


class TestSendUnloadCommand:
    """_send_unload_command 测试"""

    @patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer")
    def test_sends_unload_command_to_kafka(self, mock_producer_cls):
        """应发送 unload 命令到 CONTROL_COMMANDS topic"""
        mock_producer = MagicMock()
        mock_producer.send.return_value = True
        mock_producer_cls.return_value = mock_producer

        from ginkgo.client.portfolio_cli import _send_unload_command

        result = _send_unload_command("portfolio_456")

        assert result is True
        mock_producer.send.assert_called_once()
        topic = mock_producer.send.call_args[0][0]
        msg = mock_producer.send.call_args[0][1]
        assert topic == "ginkgo.live.control.commands"
        assert msg["command"] == "unload"
        assert msg["portfolio_id"] == "portfolio_456"

    @patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer")
    def test_returns_false_on_kafka_failure(self, mock_producer_cls):
        """Kafka 发送失败应返回 False"""
        mock_producer = MagicMock()
        mock_producer.send.return_value = False
        mock_producer_cls.return_value = mock_producer

        from ginkgo.client.portfolio_cli import _send_unload_command

        result = _send_unload_command("portfolio_456")

        assert result is False


class TestStoreDeploySource:
    """_store_deploy_source 测试"""

    @patch("ginkgo.client.portfolio_cli.GLOG")
    def test_stores_source_in_redis(self, mock_glog):
        """应将 source_portfolio_id 存入 Redis"""
        mock_redis = MagicMock()

        with patch("ginkgo.services") as mock_services:
            mock_services.data.redis_service.return_value = mock_redis

            from ginkgo.client.portfolio_cli import _store_deploy_source
            _store_deploy_source("paper_001", "source_001")

        mock_redis.set.assert_called_once_with("deviation:source:paper_001", "source_001")

    @patch("ginkgo.client.portfolio_cli.GLOG")
    def test_handles_redis_failure_gracefully(self, mock_glog):
        """Redis 失败时应 WARN 而非抛异常"""
        mock_redis = MagicMock()
        mock_redis.set.side_effect = Exception("connection refused")

        with patch("ginkgo.services") as mock_services:
            mock_services.data.redis_service.return_value = mock_redis

            from ginkgo.client.portfolio_cli import _store_deploy_source
            # 不应抛异常
            _store_deploy_source("paper_001", "source_001")

        mock_glog.WARN.assert_called_once()


class TestGenerateBaseline:
    """_generate_baseline_if_possible 测试"""

    @patch("ginkgo.client.portfolio_cli.GLOG")
    def test_skips_when_no_completed_backtest(self, mock_glog):
        """无已完成回测时应跳过"""
        mock_redis = MagicMock()
        mock_task_svc = MagicMock()
        mock_task_svc.list.return_value = MagicMock(is_success=True, data=[])

        with patch("ginkgo.services", create=True) as mock_services:
            mock_services.data.redis_service.return_value = mock_redis
            mock_services.data.backtest_task_service.return_value = mock_task_svc

            from ginkgo.client.portfolio_cli import _generate_baseline_if_possible
            _generate_baseline_if_possible("paper_001", "source_001")

        mock_glog.WARN.assert_called_once()

    @patch("ginkgo.client.portfolio_cli.GLOG")
    def test_computes_and_caches_baseline(self, mock_glog):
        """有已完成回测时应调用 backtest_task_service 并尝试缓存"""
        mock_redis = MagicMock()

        mock_task = MagicMock()
        mock_task.run_id = "task-001"
        mock_task.engine_id = "engine-001"

        mock_task_svc = MagicMock()
        mock_task_svc.list.return_value = MagicMock(
            is_success=True,
            data=[mock_task],
        )

        mock_services = MagicMock()
        mock_services.data.redis_service.return_value = mock_redis
        mock_services.data.backtest_task_service.return_value = mock_task_svc

        with patch("ginkgo.services", mock_services):
            from ginkgo.client.portfolio_cli import _generate_baseline_if_possible
            _generate_baseline_if_possible("paper_001", "source_001")

        mock_task_svc.list.assert_called_once()
        call_kwargs = mock_task_svc.list.call_args[1]
        assert call_kwargs.get("portfolio_id") == "source_001"
        assert call_kwargs.get("status") == "completed"

    @patch("ginkgo.client.portfolio_cli.GLOG")
    def test_skips_when_evaluation_fails(self, mock_glog):
        """baseline 评估失败时应跳过"""
        mock_redis = MagicMock()

        mock_task = MagicMock()
        mock_task.run_id = "task-001"
        mock_task.engine_id = "engine-001"

        mock_task_svc = MagicMock()
        mock_task_svc.list.return_value = MagicMock(
            is_success=True,
            data=[mock_task],
        )

        mock_services = MagicMock()
        mock_services.data.redis_service.return_value = mock_redis
        mock_services.data.backtest_task_service.return_value = mock_task_svc

        with patch("ginkgo.services", mock_services):
            from ginkgo.client.portfolio_cli import _generate_baseline_if_possible
            _generate_baseline_if_possible("paper_001", "source_001")

        # Should not crash
        mock_task_svc.list.assert_called_once()


class TestBaselineCommand:
    """baseline CLI 命令测试"""

    def test_baseline_command_exists(self):
        """baseline 命令应在 CLI 中注册"""
        from ginkgo.client.portfolio_cli import app

        registered = [cmd for cmd in app.registered_commands if cmd.name == "baseline"]
        assert len(registered) > 0, "baseline command should be registered"

    @patch("ginkgo.client.portfolio_cli._generate_baseline_if_possible")
    @patch("ginkgo.client.portfolio_cli._store_deploy_source")
    @patch("ginkgo.client.portfolio_cli.GLOG")
    @patch("ginkgo.client.portfolio_cli.console")
    def test_baseline_uses_redis_source(self, mock_console, mock_glog,
                                        mock_store, mock_generate):
        """baseline 命令应使用 Redis 中的 source 映射"""
        mock_redis = MagicMock()
        mock_redis.get.return_value = "source_from_redis"

        mock_services = MagicMock()
        mock_services.data.redis_service.return_value = mock_redis

        with patch("ginkgo.services", mock_services):
            from ginkgo.client.portfolio_cli import app
            runner = CliRunner()
            result = runner.invoke(app, ["baseline", "paper_001"])

        assert result.exit_code == 0
        mock_generate.assert_called_once_with("paper_001", "source_from_redis")
        mock_store.assert_not_called()  # 不需要更新映射

    @patch("ginkgo.client.portfolio_cli._generate_baseline_if_possible")
    @patch("ginkgo.client.portfolio_cli.GLOG")
    @patch("ginkgo.client.portfolio_cli.console")
    def test_baseline_uses_source_option(self, mock_console, mock_glog,
                                         mock_generate):
        """baseline 命令传 --source 时应先更新 Redis 再用新值生成 baseline"""
        # Simulate Redis storage: set() writes, get() reads from same dict
        redis_store = {}
        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda key: redis_store.get(key)
        mock_redis.set.side_effect = lambda key, val: redis_store.update({key: val})
        redis_store["deviation:source:paper_001"] = "old_source"

        mock_services = MagicMock()
        mock_services.data.redis_service.return_value = mock_redis

        with patch("ginkgo.services", mock_services):
            from ginkgo.client.portfolio_cli import app
            runner = CliRunner()
            result = runner.invoke(app, ["baseline", "paper_001", "--source", "new_source"])

        assert result.exit_code == 0
        # _store_deploy_source should have written "new_source" to Redis
        assert redis_store["deviation:source:paper_001"] == "new_source"
        # _generate_baseline_if_possible is called with the updated value from Redis
        mock_generate.assert_called_once_with("paper_001", "new_source")

    @patch("ginkgo.client.portfolio_cli._store_deploy_source")
    @patch("ginkgo.client.portfolio_cli.GLOG")
    @patch("ginkgo.client.portfolio_cli.console")
    def test_baseline_fails_without_source(self, mock_console, mock_glog, mock_store):
        """无 source 时应报错退出"""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        mock_services = MagicMock()
        mock_services.data.redis_service.return_value = mock_redis

        with patch("ginkgo.services", mock_services):
            from ginkgo.client.portfolio_cli import app
            runner = CliRunner()
            result = runner.invoke(app, ["baseline", "paper_001"])

        assert result.exit_code == 1
