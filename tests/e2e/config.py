"""
E2E 测试配置文件

可以通过环境变量覆盖配置:
- E2E_REMOTE_BROWSER: 远程浏览器地址
- E2E_WEB_UI_URL: Web UI 地址
- E2E_HEADLESS: 是否无头模式 (true/false)
- E2E_TIMEOUT: 超时时间 (毫秒)
"""

import os
from dataclasses import dataclass


@dataclass
class E2EConfig:
    """E2E 测试配置"""

    # 远程浏览器 CDP 地址
    remote_browser: str = "http://192.168.50.10:9222"

    # Web UI 地址
    web_ui_url: str = "http://192.168.50.12:5173"

    # 是否使用无头模式 (连接远程浏览器时无效)
    headless: bool = False

    # 默认超时时间 (毫秒)
    timeout: int = 30000

    # 慢动作延迟 (毫秒)，用于调试
    slow_mo: int = 0

    # 截图保存目录
    screenshot_dir: str = "/tmp/e2e-screenshots"

    # 测试用户
    test_username: str = "admin"
    test_password: str = "admin123"

    @classmethod
    def from_env(cls) -> "E2EConfig":
        """从环境变量加载配置"""
        return cls(
            remote_browser=os.getenv("E2E_REMOTE_BROWSER", cls.remote_browser),
            web_ui_url=os.getenv("E2E_WEB_UI_URL", cls.web_ui_url),
            headless=os.getenv("E2E_HEADLESS", "false").lower() == "true",
            timeout=int(os.getenv("E2E_TIMEOUT", str(cls.timeout))),
            slow_mo=int(os.getenv("E2E_SLOW_MO", "0")),
            screenshot_dir=os.getenv("E2E_SCREENSHOT_DIR", cls.screenshot_dir),
            test_username=os.getenv("E2E_TEST_USERNAME", cls.test_username),
            test_password=os.getenv("E2E_TEST_PASSWORD", cls.test_password),
        )


# 全局配置实例
config = E2EConfig.from_env()
