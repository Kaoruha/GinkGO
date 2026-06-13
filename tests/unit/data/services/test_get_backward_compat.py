"""ADR-010 Phase 4.2 P0 回归测试：get() 返 List[StockInfo] 的向后兼容契约。

防 c7f64489 的 P0 回归（get 被错委托到 DF 出口，kafka_service 的
`for stock in data: stock.code` 迭代 DataFrame 得列名崩溃）再发。

覆盖 3 个真实生产调用方的消费契约：
- kafka_service:969/991/1013  -> for stock in data: stock.code; len(data)
- seeding.py:183              -> len(data); truthy
- tick_service:939            -> 已迁 get_stockinfos_df(); data 是 DataFrame
"""

import sys
import os
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.stockinfo_service import StockinfoService
from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.entities import StockInfo


@pytest.fixture
def service():
    """创建带 mock 依赖的 StockinfoService（GLOG 已 mock）。"""
    with patch("ginkgo.libs.GLOG"):
        svc = StockinfoService(crud_repo=MagicMock(), data_source=MagicMock())
        return svc


def _make_entities(n=3):
    """构造 n 个真实 StockInfo（绕过 mapper，直接 patch from_models）。"""
    return [
        StockInfo(code=f"00000{i}.SZ", code_name=f"股票{i}", industry="银行")
        for i in range(n)
    ]


class TestGetBackwardCompat:
    """get() 返 List[StockInfo]，兼容 kafka/seeding 的迭代/.code/len 消费。"""

    @pytest.mark.unit
    def test_get_returns_list_of_stockinfo(self, service):
        """get() data 是 list 且元素是 StockInfo（不是 ModelList/DataFrame）。"""
        entities = _make_entities(3)
        service._crud_repo.find.return_value = MagicMock()  # truthy 触发 from_models
        with patch("ginkgo.data.services.stockinfo_service.StockInfoMapper.from_models",
                   return_value=entities):
            result = service.get()

        assert result.success is True
        # 契约：List[StockInfo]
        assert isinstance(result.data, list)
        assert all(isinstance(x, StockInfo) for x in result.data)
        # 关键：既不是 ModelList 也不是 DataFrame（P0 回归点）
        assert not isinstance(result.data, ModelList)
        assert not isinstance(result.data, pd.DataFrame)

    @pytest.mark.unit
    def test_get_iterable_with_code_attr(self, service):
        """kafka_service 消费契约：for stock in data: stock.code 必须能跑通。

        回归点：c7f64489 错委托 DF 出口时，迭代 DataFrame 得列名字符串，
        ``.code`` 访问崩溃，导致 send_tick/bar/adjustfactor_all_signal 失效。
        """
        entities = _make_entities(3)
        service._crud_repo.find.return_value = MagicMock()
        with patch("ginkgo.data.services.stockinfo_service.StockInfoMapper.from_models",
                   return_value=entities):
            result = service.get()

        # 复刻 kafka_service:975-985 的消费逻辑
        codes_from_iteration = [stock.code for stock in result.data]
        assert len(codes_from_iteration) == 3
        assert all(c.endswith(".SZ") for c in codes_from_iteration)
        # kafka_service:985 用 len(data) 做成功数比对
        assert len(result.data) == 3

    @pytest.mark.unit
    def test_get_empty_returns_empty_list(self, service):
        """seeding.py:185 消费契约：空结果返空 list（len==0, falsy）。

        回归点：c7f64489 错委托 DF 出口时，空 DataFrame 的 len 是列数（语义错位）。
        """
        # crud_repo.find 返回 falsy（None 或空）-> get_stockinfos 返 []
        service._crud_repo.find.return_value = None
        result = service.get()

        assert result.success is True
        assert isinstance(result.data, list)
        assert len(result.data) == 0
        # seeding.py:185 用 `not result.data` 判空
        assert not result.data

    @pytest.mark.unit
    def test_get_does_not_transmit_modellist(self, service):
        """get() 不透传裸 ModelList（V11 重灾区，ADR-010 核心目标）。

        即使 crud_repo.find 返回真实 ModelList 实例，get() 也应经 mapper 转 List[StockInfo]，
        data 绝不是 ModelList。
        """
        # 构造真实 ModelList（需 crud_instance 形参）
        from ginkgo.data.models import MStockInfo
        crud_stub = MagicMock()
        ml = ModelList([], crud_stub)
        service._crud_repo.find.return_value = ml
        with patch("ginkgo.data.services.stockinfo_service.StockInfoMapper.from_models",
                   return_value=_make_entities(1)):
            result = service.get()

        assert result.success is True
        assert isinstance(result.data, list)
        assert not isinstance(result.data, ModelList)


class TestTickServiceDfExit:
    """tick_service 已迁 get_stockinfos_df()，data 是 DataFrame（取 iloc[0]['list_date']）。"""

    @pytest.mark.unit
    def test_get_stockinfos_df_returns_dataframe(self, service):
        """get_stockinfos_df().data 是 pandas.DataFrame，支持 .empty / iloc。"""
        mock_df = pd.DataFrame([{"code": "000001.SZ", "list_date": "19910403"}])
        mock_model_list = MagicMock()
        mock_model_list.to_dataframe.return_value = mock_df
        service._crud_repo.find.return_value = mock_model_list

        result = service.get_stockinfos_df(code="000001.SZ")

        assert result.success is True
        assert isinstance(result.data, pd.DataFrame)
        assert not result.data.empty
        # 复刻 tick_service:945 的 iloc[0]['list_date'] 消费
        listing_date_raw = result.data.iloc[0]['list_date']
        assert listing_date_raw == "19910403"

    @pytest.mark.unit
    def test_get_stockinfos_df_empty_returns_empty_dataframe(self, service):
        """空查询返空 DataFrame（.empty 为 True），tick_service 走 WARN 兜底分支。"""
        mock_model_list = MagicMock()
        mock_model_list.to_dataframe.return_value = pd.DataFrame()
        service._crud_repo.find.return_value = mock_model_list

        result = service.get_stockinfos_df(code="NONEXISTENT.SZ")

        assert result.success is True
        assert isinstance(result.data, pd.DataFrame)
        assert result.data.empty
