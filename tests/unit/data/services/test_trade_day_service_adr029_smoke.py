"""TradeDayService ADR-029 §Decision 1 batch 收敛 smoke（sync）。

F3/F4 已锁 signal/position.add/order.upsert 的 **add path**；trade_day.sync 的
**batch path**（L163：list[TradeDay] → TradeDayMapper.entity_to_model → crud.add_batch，
生产注释明确"ADR-029 Task 4：不再依赖 CRUD hook 隐式转"）是兄弟盲区。本 smoke 补锁。
"""
from unittest.mock import MagicMock

import pandas as pd

from ginkgo.data.models.model_trade_day import MTradeDay
from ginkgo.data.services.trade_day_service import TradeDayService


def test_trade_day_sync_batch_via_mapper():
    """sync：fetch trade_cal → TradeDay entities → TradeDayMapper.entity_to_model →
    crud.add_batch（L163,ADR-029 Task 4 收敛）。

    锁 batch path mapper 收敛（F8d,F3 add-path 同形）：mock 数据源返 1 行日历，
    mock crud.find 返空（无 existing → 全走 new 段）。回退 L163（跳过 mapper，
    裸 TradeDay 直送 add_batch）则 isinstance(MTradeDay) FAIL。
    """
    data_source = MagicMock()
    data_source.fetch_cn_stock_trade_day.return_value = pd.DataFrame(
        {"cal_date": ["2025-01-02"], "is_open": [1]}
    )
    crud = MagicMock()
    crud.find.return_value = []  # 无 existing → 全 new

    svc = TradeDayService(crud_repo=crud, data_source=data_source)
    res = svc.sync()

    assert res.success, f"sync failed: {res.message if hasattr(res, 'message') else res}"
    crud.add_batch.assert_called_once()
    batch_arg = crud.add_batch.call_args[0][0]
    assert len(batch_arg) == 1
    assert isinstance(batch_arg[0], MTradeDay)  # 锁 mapper.entity_to_model 收敛(非裸 entity)
