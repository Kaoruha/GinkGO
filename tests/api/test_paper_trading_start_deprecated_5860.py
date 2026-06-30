# Issue: #5860
# Upstream: api.api.trading, api.core.exceptions
# Downstream: pytest
# Role: Paper Trading start 端点废弃治理 — 410 Gone + 迁移指引 + 移除无效 Kafka 投递

"""
Paper Trading start 端点废弃测试

根因：POST /api/v1/paper-trading/{account_id}/start 标 @deprecated 仍暴露 OpenAPI，
发 Kafka ControlCommand.deploy 到 CONTROL_COMMANDS topic，但 worker.py:31 只消费
DATA_COMMANDS（数据采集专用），topic 不匹配无消费者 → 命令发出后无人处理，账户状态
永不变。端点返回 200/{success:true} 误导用户。

修复（A 方案，#5860 验收）：废弃端点改 raise BusinessError(code=410)，移除无效 Kafka
投递，message 含迁移指引（POST /api/v1/portfolios/{uuid}/start）。「真启动引擎」需
worker 改消费 CONTROL_COMMANDS（基础设施改造，新旧端点同受影响，超本端点范围）。
"""

import pytest
from unittest.mock import MagicMock


@pytest.mark.asyncio
async def test_start_is_deprecated_returns_410_no_kafka_with_migration(monkeypatch):
    """#5860 AC1+AC2: 废弃 start 端点必须 (1) 返 410 Gone 非 200/success:true,
    (2) 不再发无效 Kafka 投递（CONTROL_COMMANDS 无消费者）, (3) message 含迁移指引。
    """
    from api.trading import start_paper_trading
    from core.exceptions import BusinessError

    # 即便 _get_kafka_producer 被调用（废弃后不应被调用），也注入 mock 以断言不发
    fake_producer = MagicMock()
    monkeypatch.setattr("api.trading._get_kafka_producer", lambda: fake_producer)

    with pytest.raises(BusinessError) as exc_info:
        await start_paper_trading("acct-deprecated-1")

    # AC1: 410 Gone（不再 200/success:true 误导）
    assert exc_info.value.code == 410
    assert exc_info.value.status_code == 410

    # 废弃端点不再发无效 Kafka 投递（CONTROL_COMMANDS 无 worker 消费）
    fake_producer.send.assert_not_called()

    # AC2: message 含迁移指引（新端点路径）
    msg = str(exc_info.value.message)
    assert "/portfolios/" in msg, "410 响应必须指向新端点 /portfolios/{uuid}/start"
    assert "start" in msg
