"""BarService ADR-029 §Decision 1 batch 收敛 smoke（sync_range）。

F3/F4 锁 signal/position/order 的 **add path**（单 entity → crud.add）；
bar.sync_range 的 **batch path**（L198：list[Bar] → BarMapper.entity_to_model →
crud.add_batch，生产注释"ADR-029 Task 1：入站前置 mapper.entity_to_model，
不再依赖 CRUD hook 隐式转"）是兄弟盲区。本 smoke 补锁，走全入站链
（dataframe_to_bar_entities → _filter_existing_data → BarMapper → add_batch）。
"""
import datetime
from unittest.mock import MagicMock

import pandas as pd

from ginkgo.enums import FREQUENCY_TYPES
from ginkgo.data.models.model_bar import MBar
from ginkgo.data.services.bar_service import BarService


def test_bar_sync_range_batch_via_mapper():
    """sync_range：fetch daybar → Bar entities → BarMapper.entity_to_model → crud.add_batch
    （L198,ADR-029 Task 1 收敛）。

    锁 batch path mapper 收敛（F8b,F3 add-path 同形）：mock data_source 返 1 行合法
    OHLC（high>=max(open,close)、low<=min、正价，过 _validate_bar_data），mock
    stockinfo.exists→True，mock crud.find→[]（无 existing → _filter_existing_data 全保留）。
    回退 L198（跳过 mapper，裸 Bar 直送 add_batch）则 isinstance(MBar) FAIL。
    """
    data_source = MagicMock()
    data_source.fetch_cn_stock_daybar.return_value = pd.DataFrame(
        [{"trade_date": "20250102", "open": 10, "high": 11, "low": 9,
          "close": 10.5, "vol": 100, "amount": 0}]  # 含 amount 列(L134 r["amount"] 求值在 pd.notna 前)
    )
    stockinfo_svc = MagicMock()
    stockinfo_svc.exists.return_value = True
    crud = MagicMock()
    crud.find.return_value = []  # 无 existing → final_entities = 全 bar_entities

    svc = BarService(
        crud_repo=crud, data_source=data_source, stockinfo_service=stockinfo_svc
    )
    res = svc.sync_range(
        "000001",
        datetime.datetime(2025, 1, 1),
        datetime.datetime(2025, 1, 10),
        FREQUENCY_TYPES.DAY,
    )

    assert res.success, f"sync_range failed: {getattr(res, 'message', res)}"
    crud.add_batch.assert_called_once()
    batch_arg = crud.add_batch.call_args[0][0]
    assert len(batch_arg) == 1
    assert isinstance(batch_arg[0], MBar)  # 锁 mapper.entity_to_model 收敛(非裸 entity)
