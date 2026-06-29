# Upstream: api.api.data.sync_data (POST /api/v1/data/sync)
# Role: 验证无效 type 错误提示列出所有有效值 (#5390)
"""
sync_data 无效 type 错误提示测试

#5390: type=bar 等无效值返回 'Unsupported data type: bar'，
未告诉用户合法值（stockinfo/bars/ticks/adjustfactor）。
本测试锁定：错误提示应列出全部有效 type。
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock

from fastapi import HTTPException


def run_async(coro):
    return asyncio.run(coro)


def make_sync_record_mock():
    """构造 DataSyncRecordService + record_start 返回值的替身"""
    svc = MagicMock()
    rec = MagicMock()
    rec.is_success.return_value = True
    rec.data = {"uuid": "rec-uuid-1"}
    svc.record_start.return_value = rec
    return svc


@pytest.mark.unit
class TestSyncDataUnsupportedType:
    """#5390: 无效 type 错误提示列出有效值"""

    def test_unsupported_type_lists_all_valid_values(self):
        """type=bar 无效时，400 错误提示含全部有效 type

        RED: 当前 detail='Unsupported data type: bar' 未列有效值。
        """
        from api.data import sync_data, DataUpdateRequest

        request = DataUpdateRequest(type="bar", codes=["000001.SZ"])

        with patch("api.data.get_sync_record_service", return_value=make_sync_record_mock()):
            with pytest.raises(HTTPException) as exc:
                run_async(sync_data(request))

        assert exc.value.status_code == 400
        detail = str(exc.value.detail)
        assert "Unsupported data type: bar" in detail
        # 列出全部有效值
        assert "stockinfo" in detail
        assert "bars" in detail
        assert "ticks" in detail
        assert "adjustfactor" in detail
