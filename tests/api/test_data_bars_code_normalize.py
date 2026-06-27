# Issue: #5760 — GET /api/v1/data/bars 需精确代码格式 + 缺 code 返回空
# Upstream: api.api.data.get_bars
# Downstream: BarService.get(code=...) — DB code 列存 000001.SZ
# Role: 验证 get_bars 入口校验 code 必填(422) + 归一化交易所后缀(000001→000001.SZ)

"""
data/bars code 归一化 + 必填校验测试 (#5760 验收 1 + 3)。

根因：
1. get_bars code 参数 Optional[str]=None，缺失时静默走 None 查询返回空（验收3）
2. code 无交易所后缀归一化，裸 000001 查不到 DB 的 000001.SZ（验收1）

修复：get_bars 入口调 _normalize_bar_code(code)：
- None/空 → HTTPException(422)
- 6 位数字按首位推断交易所后缀 (.SH/.SZ/.BJ)
- 已含后缀原样返回
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from fastapi import HTTPException


def run_async(coro):
    return asyncio.run(coro)


def make_mock_result(data=None, success=True):
    result = MagicMock()
    result.is_success.return_value = success
    result.data = data
    return result


class TestGetBarsCodeNormalization:
    """#5760: get_bars code 必填(422) + 交易所后缀归一化。"""

    def test_plain_sz_code_normalized_to_sz_suffix(self):
        """验收1: code=000001 应归一化为 000001.SZ 传给 bar_service（DB 存 .SZ）。"""
        mock_service = MagicMock()
        mock_service.get.return_value = make_mock_result(data=[])

        from api.data import get_bars

        with patch("api.data.get_bar_service", return_value=mock_service):
            run_async(get_bars(code="000001"))

        called_code = mock_service.get.call_args.kwargs.get("code")
        assert called_code == "000001.SZ", (
            f"#5760: 000001 未补全深交所后缀, bar_service.get 收到 code={called_code!r}"
        )

    def test_plain_sh_code_normalized_to_sh_suffix(self):
        """验收1: 上证代码 600000 → 600000.SH。"""
        mock_service = MagicMock()
        mock_service.get.return_value = make_mock_result(data=[])

        from api.data import get_bars

        with patch("api.data.get_bar_service", return_value=mock_service):
            run_async(get_bars(code="600000"))

        called_code = mock_service.get.call_args.kwargs.get("code")
        assert called_code == "600000.SH", (
            f"#5760: 600000 未补全上证后缀, got {called_code!r}"
        )

    def test_already_suffixed_code_unchanged(self):
        """已含后缀的 code 不被二次处理（000001.SZ 原样传入）。"""
        mock_service = MagicMock()
        mock_service.get.return_value = make_mock_result(data=[])

        from api.data import get_bars

        with patch("api.data.get_bar_service", return_value=mock_service):
            run_async(get_bars(code="000001.SZ"))

        called_code = mock_service.get.call_args.kwargs.get("code")
        assert called_code == "000001.SZ"

    def test_missing_code_raises_422(self):
        """验收3: 缺少 code 参数应返回 422 而非空数据。"""
        from api.data import get_bars

        with pytest.raises(HTTPException) as exc:
            run_async(get_bars())

        assert exc.value.status_code == 422, (
            f"#5760: 缺 code 应 422, got {exc.value.status_code}"
        )

    def test_empty_code_raises_422(self):
        """验收3: 空 code（空串/空白）同样 422。"""
        from api.data import get_bars

        with pytest.raises(HTTPException) as exc:
            run_async(get_bars(code="   "))

        assert exc.value.status_code == 422

    def test_sz_etf_code_159_normalized_to_sz(self):
        """#5760 review: 深 ETF 159xxx (首位1) → .SZ。对齐 mootdx '15'→sz。

        旧规则首位 1 无分支 → 原样返回查空 (DB 存 159915.SZ)。
        """
        mock_service = MagicMock()
        mock_service.get.return_value = make_mock_result(data=[])

        from api.data import get_bars

        with patch("api.data.get_bar_service", return_value=mock_service):
            run_async(get_bars(code="159915"))

        called_code = mock_service.get.call_args.kwargs.get("code")
        assert called_code == "159915.SZ", (
            f"#5760: 深ETF首位1应补 .SZ, got {called_code!r}"
        )

    def test_sh_b_code_900_normalized_to_sh(self):
        """#5760 review: 沪 B 900xxx (首位9) → .SH 非 .BJ。对齐 mootdx 首位9→sh。

        旧规则首位 9→.BJ 错标 (沪 B 实属上交所)。
        """
        mock_service = MagicMock()
        mock_service.get.return_value = make_mock_result(data=[])

        from api.data import get_bars

        with patch("api.data.get_bar_service", return_value=mock_service):
            run_async(get_bars(code="900901"))

        called_code = mock_service.get.call_args.kwargs.get("code")
        assert called_code == "900901.SH", (
            f"#5760: 沪B首位9应补 .SH 非 .BJ, got {called_code!r}"
        )
