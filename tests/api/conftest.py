# Issue #3849 + #4080: 移除 api/ 的 sys.path.insert
# 原实现将 api/ 目录加入 sys.path，导致 api/core/ 和 api/services/
# 与 tests/unit/core/、tests/integration/data/services/ 产生命名空间冲突
# （28 个 collection errors）。需要 api 模块的测试应使用 conftest fixture 延迟导入。
import os
import sys
from pathlib import Path

import pytest


_API_DIR = str(Path(__file__).parent.parent.parent / "api")

# #5464: 确保测试环境有合法 SECRET_KEY，避免 config.py 全局 Settings() 报错
if not os.environ.get("SECRET_KEY") or os.environ.get("SECRET_KEY") == "your-secret-key-change-in-production":
    os.environ["SECRET_KEY"] = "test-secret-key-for-jwt-security-tests"


@pytest.fixture(autouse=True, scope="session")
def api_modules():
    """仅在测试执行时将 api/ 临时加入 sys.path，完成后移除。

    使用方式:
        def test_something(api_modules):
            from services.saga_transaction import SagaTransaction
    """
    if _API_DIR not in sys.path:
        sys.path.insert(0, _API_DIR)
    yield
    if _API_DIR in sys.path:
        sys.path.remove(_API_DIR)
