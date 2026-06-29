"""
MLiveAccount model 列类型测试（#5629）。

性能: <1s, 单元测试 [PASS]
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

import pytest
from sqlalchemy import inspect, Text

from ginkgo.data.models.model_live_account import MLiveAccount


class TestLiveAccountValidationStatusColumn:
    """#5629: validation_status 列长度不足，验证错误无法持久化。"""

    @pytest.mark.unit
    def test_validation_status_is_text_not_short_varchar(self):
        """validation_status 应为 Text，容纳米超长验证错误信息（如 OKX 详细错误）。

        原 String(100) 致 MySQL 报 `Data too long for column
        'validation_status'`，验证结果（success/failed: <msg>）无法持久化，
        列始终 NULL。同表 description 已用 Text，此列对齐。
        """
        col = inspect(MLiveAccount).columns["validation_status"]
        assert isinstance(col.type, Text), (
            f"validation_status 应为 Text（容纳米超长错误信息），"
            f"实际 {type(col.type).__name__}(length={getattr(col.type, 'length', None)})"
        )

    @pytest.mark.unit
    def test_validation_status_accepts_long_message(self):
        """构造 >100 字符的验证错误消息赋给 validation_status，model 层应接受。

        #5629 复现：OKX testnet 无真实 API key，验证错误消息远超 100 字符。
        列改 Text 后，model 实例可承载任意长消息（DB 层不再截断）。
        """
        long_message = "failed: " + "x" * 200  # 208 字符，远超 String(100)
        account = MLiveAccount(
            user_id="u1",
            exchange="okx",
            environment="testnet",
            name="test",
            api_key="k",
            api_secret="s",
        )
        # model 层赋值不应因长度报错（DB 层类型决定是否截断）
        account.validation_status = long_message
        assert account.validation_status == long_message
        assert len(account.validation_status) > 100
