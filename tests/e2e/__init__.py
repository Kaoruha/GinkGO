"""
E2E 测试包

使用 Playwright Python SDK 进行端到端测试。

运行方式:
    # 运行所有 E2E 测试
    pytest tests/e2e/ -v

    # 运行单个测试文件
    pytest tests/e2e/test_login.py -v

    # 运行并显示浏览器
    E2E_HEADLESS=false pytest tests/e2e/ -v

    # 使用自定义配置
    E2E_REMOTE_BROWSER=http://localhost:9222 E2E_WEB_UI_URL=http://localhost:5173 pytest tests/e2e/ -v
"""

from .config import config, E2EConfig

__all__ = ["config", "E2EConfig"]
