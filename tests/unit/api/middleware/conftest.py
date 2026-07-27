import os

# #5464/#6784: api.core import 链触发 config.py 全局 Settings()，需合法 SECRET_KEY。
# conftest 在测试模块 import 前加载，此处 setdefault 先于 middleware.error_handler →
# core.logging → core/__init__ → config.Settings() 生效。
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-security-tests")
