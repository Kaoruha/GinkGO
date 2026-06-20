"""
#5782: POST /accounts/{id}/validate 不应无限挂起(HTTP 000)。

表象: 网络不可达时 OKX SDK 无 timeout 调用阻塞,handler 同步等待 → HTTP 000;
      账户 validation_status / last_validated_at 恒 None。
根因: validate_account handler 直接同步调 service.validate_account,
      下游 _validate_okx_account 调用 SDK 无 timeout,且无超时落库。
契约:
  - handler 在有限时间内返回(默认 30s),超时则返回 valid=False;
  - 超时不落库:后台 @retry 线程的最终结果为准(成功→ENABLED / 全失败→ERROR)。
    handler 若在超时分支写 ERROR,会与后台成功分支(update_status ENABLED)竞态,
    造成"客户端 valid=False 但库最终 ENABLED"的响应/持久态分裂(见 review #6213)。

注: api/ 非 Python 包(无 __init__.py),经 tests/api/conftest 的 api_modules
    fixture 临时加入 sys.path,故 import 须延迟到测试函数内。
"""

import asyncio
import time
from unittest.mock import Mock


def test_validate_handler_times_out_instead_of_hanging(api_modules, monkeypatch):
    """handler 必须在超时阈值内返回 valid=False,而非等到 service 阻塞完成。"""
    from api import accounts as accounts_api

    # 超时阈值调小,避免测试等待 30s
    monkeypatch.setattr(accounts_api, "VALIDATE_TIMEOUT_SECONDS", 0.2)

    mock_service = Mock()

    def slow_validate(*a, **kw):
        time.sleep(0.6)  # 模拟网络阻塞(超过超时阈值)
        return {"success": True, "valid": True}

    mock_service.validate_account.side_effect = slow_validate
    monkeypatch.setattr(accounts_api, "get_live_account_service", lambda: mock_service)

    start = time.monotonic()
    resp = asyncio.run(accounts_api.validate_account("test-uuid"))
    elapsed = time.monotonic() - start

    data = resp["data"]
    # 超时路径返回失败(否则会拿到 mock 的 valid=True)
    assert data["valid"] is False
    assert "timeout" in str(data.get("error", "")).lower() or "timed out" in str(
        data.get("message", "")
    ).lower()
    # 未无限挂起(后台线程 ~0.6s + 退出等待,远小于 30s 默认)
    assert elapsed < 5
    # 关键: 超时分支禁止写库。后台 @retry 线程仍在跑,其最终结果(ENABLED/ERROR)
    # 才是权威;若 handler 在此写 ERROR,会与后台成功分支竞态覆盖。
    mock_service.record_validation_failure.assert_not_called()


def test_validate_handler_returns_success_when_service_succeeds(api_modules, monkeypatch):
    """正常路径: service 验证成功时 handler 透传 valid=True(回归保护)。"""
    from api import accounts as accounts_api

    mock_service = Mock()
    mock_service.validate_account.return_value = {
        "success": True,
        "valid": True,
        "message": "API validation successful",
        "account_info": {"balance": "100"},
    }
    monkeypatch.setattr(accounts_api, "get_live_account_service", lambda: mock_service)

    resp = asyncio.run(accounts_api.validate_account("test-uuid"))

    assert resp["data"]["valid"] is True
    # 成功路径不应触发失败落库
    mock_service.record_validation_failure.assert_not_called()
