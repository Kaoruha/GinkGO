"""
数据库驱动测试共享fixtures

提供跨驱动测试文件共享的pytest fixtures
"""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_logger():
    """模拟日志器"""
    logger = MagicMock()
    logger.logger_name = "test_logger"
    # log() 方法使用 level.upper() 访问属性，需要同时支持大小写
    for level in ["info", "INFO", "error", "ERROR", "warning", "WARNING", "debug", "DEBUG"]:
        setattr(logger, level, MagicMock())
    logger.log = MagicMock()
    return logger
