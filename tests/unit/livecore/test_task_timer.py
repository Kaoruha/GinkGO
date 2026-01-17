"""TaskTimer单元测试"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from apscheduler.schedulers.background import BackgroundScheduler

from ginkgo.livecore.task_timer import TaskTimer


@pytest.mark.tdd
class TestTaskTimer:
    """TaskTimer单元测试"""

    def test_init_with_default_config(self):
        """测试：使用默认配置初始化TaskTimer"""
        timer = TaskTimer()
        assert timer is not None
        assert timer.config_path == os.path.expanduser("~/.ginkgo/task_timer.yml")
        assert isinstance(timer.scheduler, BackgroundScheduler)
        assert timer._producer is None
        assert timer._jobs == []

    def test_init_with_custom_config_path(self):
        """测试：使用自定义配置路径初始化"""
        custom_path = "/tmp/custom_task_timer.yml"
        timer = TaskTimer(config_path=custom_path)
        assert timer.config_path == custom_path

    @patch('ginkgo.livecore.task_timer.GinkgoProducer')
    @patch('ginkgo.livecore.task_timer.GCONF')
    def test_start_method(self, mock_gconf, mock_producer):
        """测试：start方法启动APScheduler并添加定时任务"""
        # 设置mock
        mock_gconf.get.return_value = "localhost:9092"
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance

        timer = TaskTimer()
        success = timer.start()

        assert success is True
        assert timer.scheduler.running
        assert timer._producer is not None

        # 清理
        timer.stop()

    @patch('ginkgo.livecore.task_timer.GinkgoProducer')
    @patch('ginkgo.livecore.task_timer.GCONF')
    def test_stop_method(self, mock_gconf, mock_producer):
        """测试：stop方法正确shutdown APScheduler"""
        mock_gconf.get.return_value = "localhost:9092"
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance

        timer = TaskTimer()
        timer.start()
        assert timer.scheduler.running

        success = timer.stop()
        assert success is True
        assert not timer.scheduler.running

    def test_load_config_from_file(self):
        """测试：从task_timer.yml加载配置"""
        # 创建临时配置文件
        config_content = """
scheduled_tasks:
  - name: "test_task"
    cron: "0 * * * *"
    command: "bar_snapshot"
    enabled: true
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            timer = TaskTimer(config_path=temp_path)
            timer._load_config()

            assert "scheduled_tasks" in timer._config
            assert len(timer._config["scheduled_tasks"]) == 1
            assert timer._config["scheduled_tasks"][0]["name"] == "test_task"
        finally:
            os.unlink(temp_path)

    def test_load_config_default_when_file_not_exists(self):
        """测试：配置文件不存在时使用默认配置"""
        timer = TaskTimer(config_path="/nonexistent/path.yml")
        timer._load_config()

        assert "scheduled_tasks" in timer._config
        assert len(timer._config["scheduled_tasks"]) == 2  # bar_snapshot和update_selector

    @patch('ginkgo.livecore.task_timer.GinkgoProducer')
    @patch('ginkgo.livecore.task_timer.GCONF')
    def test_add_jobs_with_cron_trigger(self, mock_gconf, mock_producer):
        """测试：使用CronTrigger添加定时任务"""
        mock_gconf.get.return_value = "localhost:9092"
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance

        # 创建测试配置
        timer = TaskTimer()
        timer._config = {
            "scheduled_tasks": [
                {
                    "name": "test_job",
                    "cron": "0 * * * *",
                    "command": "bar_snapshot",
                    "enabled": True
                }
            ]
        }

        timer._producer = mock_producer_instance
        timer._add_jobs()

        assert len(timer._jobs) == 1
        assert "test_job" in timer._jobs

        # 清理
        if timer.scheduler.running:
            timer.scheduler.shutdown(wait=False)

    @patch('ginkgo.livecore.task_timer.GinkgoProducer')
    @patch('ginkgo.livecore.task_timer.GCONF')
    def test_bar_snapshot_job(self, mock_gconf, mock_producer):
        """测试：_bar_snapshot_job发送bar_snapshot控制命令"""
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance
        mock_gconf.get.return_value = "localhost:9092"

        timer = TaskTimer()
        timer._producer = mock_producer_instance

        # 执行任务
        timer._bar_snapshot_job()

        # 验证Kafka发送被调用
        mock_producer_instance.send.assert_called_once()
        call_args = mock_producer_instance.send.call_args
        assert "bar_snapshot" in call_args[1]["message"]

    @patch('ginkgo.livecore.task_timer.GinkgoProducer')
    @patch('ginkgo.livecore.task_timer.GCONF')
    def test_selector_update_job(self, mock_gconf, mock_producer):
        """测试：_selector_update_job发送update_selector控制命令"""
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance
        mock_gconf.get.return_value = "localhost:9092"

        timer = TaskTimer()
        timer._producer = mock_producer_instance

        # 执行任务
        timer._selector_update_job()

        # 验证Kafka发送被调用
        mock_producer_instance.send.assert_called_once()
        call_args = mock_producer_instance.send.call_args
        assert "update_selector" in call_args[1]["message"]

    @patch('ginkgo.livecore.task_timer.GinkgoProducer')
    @patch('ginkgo.livecore.task_timer.GCONF')
    def test_data_update_job(self, mock_gconf, mock_producer):
        """测试：_data_update_job发送update_data控制命令"""
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance
        mock_gconf.get.return_value = "localhost:9092"

        timer = TaskTimer()
        timer._producer = mock_producer_instance

        # 执行任务
        timer._data_update_job()

        # 验证Kafka发送被调用
        mock_producer_instance.send.assert_called_once()
        call_args = mock_producer_instance.send.call_args
        assert "update_data" in call_args[1]["message"]

    def test_validate_config_valid(self):
        """测试：validate_config验证有效配置"""
        config_content = """
scheduled_tasks:
  - name: "test_task"
    cron: "0 * * * *"
    command: "bar_snapshot"
    enabled: true
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            timer = TaskTimer(config_path=temp_path)
            result = timer.validate_config()
            assert result is True
        finally:
            os.unlink(temp_path)

    def test_validate_config_file_not_exists(self):
        """测试：validate_config处理文件不存在"""
        timer = TaskTimer(config_path="/nonexistent/path.yml")
        result = timer.validate_config()
        assert result is False

    def test_validate_config_invalid_command(self):
        """测试：validate_config处理无效命令"""
        config_content = """
scheduled_tasks:
  - name: "test_task"
    cron: "0 * * * *"
    command: "invalid_command"
    enabled: true
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            timer = TaskTimer(config_path=temp_path)
            result = timer.validate_config()
            assert result is False
        finally:
            os.unlink(temp_path)

    @patch('ginkgo.livecore.task_timer.GinkgoProducer')
    @patch('ginkgo.livecore.task_timer.GCONF')
    def test_disabled_job_not_added(self, mock_gconf, mock_producer):
        """测试：禁用的任务不会被添加"""
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance
        mock_gconf.get.return_value = "localhost:9092"

        timer = TaskTimer()
        timer._config = {
            "scheduled_tasks": [
                {
                    "name": "disabled_job",
                    "cron": "0 * * * *",
                    "command": "bar_snapshot",
                    "enabled": False
                }
            ]
        }

        timer._producer = mock_producer_instance
        timer._add_jobs()

        assert len(timer._jobs) == 0

        # 清理
        if timer.scheduler.running:
            timer.scheduler.shutdown(wait=False)

    @patch('ginkgo.livecore.task_timer.GinkgoProducer')
    @patch('ginkgo.livecore.task_timer.GCONF')
    def test_invalid_cron_expression_skipped(self, mock_gconf, mock_producer):
        """测试：无效的cron表达式任务被跳过"""
        mock_producer_instance = Mock()
        mock_producer.return_value = mock_producer_instance
        mock_gconf.get.return_value = "localhost:9092"

        timer = TaskTimer()
        timer._config = {
            "scheduled_tasks": [
                {
                    "name": "invalid_cron_job",
                    "cron": "invalid_cron",
                    "command": "bar_snapshot",
                    "enabled": True
                }
            ]
        }

        timer._producer = mock_producer_instance
        timer._add_jobs()

        # 无效cron的任务应该被跳过
        assert len(timer._jobs) == 0

        # 清理
        if timer.scheduler.running:
            timer.scheduler.shutdown(wait=False)
