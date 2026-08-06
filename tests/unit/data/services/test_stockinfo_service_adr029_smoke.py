"""StockinfoService ADR-029 §Decision 1 batch 收敛 smoke（sync）。

F3/F4 已锁 signal/position.add/order.upsert 的 **add path**；stockinfo.sync 的
**batch path**（L227：list[StockInfo] → StockInfoMapper.entity_to_model → crud.add_batch，
生产注释"ADR-029 Task 3：入站前置 mapper（Entity→Model），CRUD 不再做转换"）是兄弟盲区。
本 smoke 补锁，使 §Decision 1 在 stockinfo 同步路径也有锚点。
"""
from unittest.mock import MagicMock

import pandas as pd

from ginkgo.data.models.model_stock_info import MStockInfo
from ginkgo.data.services.stockinfo_service import StockinfoService


def test_stockinfo_sync_batch_via_mapper():
    """sync：fetch_cn_stockinfo → StockInfo entities → StockInfoMapper.entity_to_model →
    crud.add_batch（L227,ADR-029 Task 3 收敛）。

    锁 batch path mapper 收敛（F8c,F3 add-path 同形）：mock 数据源返 1 行 stockinfo，
    mock crud.find 返空（无 existing → 全走 new 段）。回退 L227（跳过 mapper，
    裸 StockInfo 直送 add_batch）则 isinstance(MStockInfo) FAIL。
    """
    data_source = MagicMock()
    data_source.fetch_cn_stockinfo.return_value = pd.DataFrame(
        [{"ts_code": "000001.SZ", "name": "test", "industry": "bank",
          "list_date": "20250102", "delist_date": None}]
    )
    crud = MagicMock()
    crud.find.return_value = []  # 无 existing → 全 new

    svc = StockinfoService(crud_repo=crud, data_source=data_source)
    res = svc.sync()

    assert res.success, f"sync failed: {getattr(res, 'message', res)}"
    crud.add_batch.assert_called_once()
    batch_arg = crud.add_batch.call_args[0][0]
    assert len(batch_arg) == 1
    assert isinstance(batch_arg[0], MStockInfo)  # 锁 mapper.entity_to_model 收敛(非裸 entity)
