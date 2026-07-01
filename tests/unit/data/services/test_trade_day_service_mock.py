"""
TradeDayService 单元测试（Mock 依赖）

通过 MagicMock 注入所有依赖，隔离测试业务逻辑。
镜像 test_stockinfo_service_mock.py 的 TestSync 结构——「加一种 data_type」
的对称扩展，trade_day 日历同步链路（#6488）。
"""

import sys
import os
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import datetime

# 将项目根目录加入路径
_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.trade_day_service import TradeDayService
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.entities import TradeDay
from ginkgo.enums import MARKET_TYPES


# ============================================================
# 辅助函数：创建带 mock 依赖的 service 实例
# ============================================================


@pytest.fixture
def mock_deps():
    """创建 mock 依赖"""
    return {
        "crud_repo": MagicMock(),
        "data_source": MagicMock(),
    }


@pytest.fixture
def service(mock_deps):
    """创建 TradeDayService 实例（GLOG 已 mock）"""
    with patch("ginkgo.libs.GLOG"):
        svc = TradeDayService(
            crud_repo=mock_deps["crud_repo"],
            data_source=mock_deps["data_source"],
        )
        return svc


# ============================================================
# sync 测试
# ============================================================


class TestSync:
    """sync 交易日历同步测试"""

    @pytest.fixture
    def raw_trade_df(self):
        """模拟 tushare pro.trade_cal() 返回（原样透传，字段 cal_date/is_open 为 int 0/1）"""
        return pd.DataFrame({
            "exchange": ["SSE", "SSE"],
            "cal_date": ["20240102", "20240103"],
            "is_open": [0, 1],
            "pretrade_date": ["20231229", "20240102"],
        })

    @pytest.mark.unit
    def test_sync_persists_trade_days(self, service, mock_deps, raw_trade_df):
        """sync 从数据源拉取日历 → 转 TradeDay → 批量落库（tracer bullet）"""
        mock_deps["data_source"].fetch_cn_stock_trade_day.return_value = raw_trade_df
        mock_deps["crud_repo"].add_batch = MagicMock()

        with patch("ginkgo.data.services.trade_day_service.RichProgress"):
            result = service.sync()

        assert result.success is True
        mock_deps["data_source"].fetch_cn_stock_trade_day.assert_called_once()
        # 批量落库被调用，传入的是 TradeDay 列表
        mock_deps["crud_repo"].add_batch.assert_called_once()
        persisted = mock_deps["crud_repo"].add_batch.call_args[0][0]
        assert len(persisted) == 2
        assert all(isinstance(td, TradeDay) for td in persisted)
        # is_open int 0/1 正确转 bool（TradeDay entity 严格要求 bool）
        assert persisted[0].is_open is False
        assert persisted[1].is_open is True
        # market 归一为 CHINA
        assert all(td.market == MARKET_TYPES.CHINA for td in persisted)

    @pytest.mark.unit
    def test_sync_empty_source(self, service, mock_deps):
        """数据源返回空 DataFrame 时同步失败"""
        mock_deps["data_source"].fetch_cn_stock_trade_day.return_value = pd.DataFrame()

        result = service.sync()
        assert result.success is False
        assert "No trade calendar data available" in result.message

    @pytest.mark.unit
    def test_sync_none_source(self, service, mock_deps):
        """数据源返回 None 时同步失败"""
        mock_deps["data_source"].fetch_cn_stock_trade_day.return_value = None

        result = service.sync()
        assert result.success is False

    @pytest.mark.unit
    def test_sync_source_exception(self, service, mock_deps):
        """数据源抛异常时同步失败（不向上传播）"""
        mock_deps["data_source"].fetch_cn_stock_trade_day.side_effect = Exception("API 超时")

        result = service.sync()
        assert result.success is False
        assert "API 超时" in result.message

    @pytest.mark.unit
    def test_sync_idempotent_removes_existing_before_add(self, service, mock_deps, raw_trade_df):
        """重复 sync 幂等：已存在的 (market,timestamp) 先 remove 再 add，不累积重复行（镜像 stockinfo，#6488 review）

        场景：DB 已含本次源返回的两个日期（第二次 sync）。sync 必须 find 出既有、
        remove 清掉它们、再 add_batch 全量——否则每次 sync 行数翻倍，
        与声明的 is_idempotent=True 自相矛盾。
        """
        mock_deps["data_source"].fetch_cn_stock_trade_day.return_value = raw_trade_df
        # 模拟 DB 已存在这两个日期（第二次 sync 场景）
        mock_deps["crud_repo"].find = MagicMock(return_value=[
            TradeDay(market=MARKET_TYPES.CHINA, is_open=False, timestamp="20240102"),
            TradeDay(market=MARKET_TYPES.CHINA, is_open=True, timestamp="20240103"),
        ])
        mock_deps["crud_repo"].remove = MagicMock()
        mock_deps["crud_repo"].add_batch = MagicMock()

        with patch("ginkgo.data.services.trade_day_service.RichProgress"):
            result = service.sync()

        assert result.success is True
        # 幂等核心 1：先 find 既有记录
        mock_deps["crud_repo"].find.assert_called_once()
        find_filters = mock_deps["crud_repo"].find.call_args.kwargs.get("filters", {})
        assert find_filters.get("market") == MARKET_TYPES.CHINA
        # 幂等核心 2：既有日期被 remove 清理（防重复累积）
        mock_deps["crud_repo"].remove.assert_called_once()
        # 落库总条数 == 源条数（new + update 都经 add_batch，但不翻倍）
        added = []
        for call in mock_deps["crud_repo"].add_batch.call_args_list:
            added.extend(call[0][0])
        assert len(added) == 2

    @pytest.mark.unit
    def test_sync_update_add_batch_failure_falls_back_per_item(self, service, mock_deps, raw_trade_df):
        """update 分支 add_batch 失败 → 逐条 add_batch([item]) 回退，已 remove 的 update_items 不丢失（#6488 review 第3轮 blocking）

        场景：DB 已含本次源日期（第二次 sync，触发 update 路径）。remove 成功清掉
        旧行后，add_batch(update_items) 抛异常。若无逐条 fallback，update_items
        旧行已删、新行未写 → 永久丢失且静默 success。镜像 stockinfo sync update
        段逐条 add_batch([item]) 容错。
        """
        mock_deps["data_source"].fetch_cn_stock_trade_day.return_value = raw_trade_df
        mock_deps["crud_repo"].find = MagicMock(return_value=[
            TradeDay(market=MARKET_TYPES.CHINA, is_open=False, timestamp="20240102"),
            TradeDay(market=MARKET_TYPES.CHINA, is_open=True, timestamp="20240103"),
        ])
        mock_deps["crud_repo"].remove = MagicMock()
        # 批量 add 第1次抛异常（模拟 MySQL batch 死锁），后续逐条调用成功
        mock_deps["crud_repo"].add_batch = MagicMock(
            side_effect=[Exception("batch deadlock"), None, None]
        )

        with patch("ginkgo.data.services.trade_day_service.RichProgress"):
            result = service.sync()

        # 逐条回退：2 条 update 各经 add_batch([item]) 单条写入 → 数据不丢
        per_item_calls = [
            c for c in mock_deps["crud_repo"].add_batch.call_args_list
            if len(c[0][0]) == 1
        ]
        assert len(per_item_calls) == 2, (
            "add_batch 失败后须逐条回退，2 条 update 各一次单条调用；"
            f"实际单条调用 {len(per_item_calls)} 次"
        )
        # 逐条成功 → success_count 完整，数据未丢
        assert result.success is True
        assert result.data.records_added == 2
        assert result.data.records_failed == 0

    @pytest.mark.unit
    def test_sync_new_add_batch_failure_falls_back_per_item(self, service, mock_deps, raw_trade_df):
        """new 分支 add_batch 失败 → 逐条 add_batch([item]) 回退（对称镜像 stockinfo，#6488 review 第3轮）

        场景：find 返回空（首次 sync，全 new）。new_items 批量 add 抛异常，
        须逐条回退写入，否则全量数据丢失。
        """
        mock_deps["data_source"].fetch_cn_stock_trade_day.return_value = raw_trade_df
        mock_deps["crud_repo"].find = MagicMock(return_value=[])
        mock_deps["crud_repo"].add_batch = MagicMock(
            side_effect=[Exception("batch deadlock"), None, None]
        )

        with patch("ginkgo.data.services.trade_day_service.RichProgress"):
            result = service.sync()

        per_item_calls = [
            c for c in mock_deps["crud_repo"].add_batch.call_args_list
            if len(c[0][0]) == 1
        ]
        assert len(per_item_calls) == 2
        assert result.success is True
        assert result.data.records_added == 2

    @pytest.mark.unit
    def test_sync_update_batch_and_per_item_both_fail_records_failure(self, service, mock_deps, raw_trade_df):
        """update 批量+逐条均失败 → failed_count 计入，不静默 success 掩盖丢失（#6488 review 第3轮）

        场景：add_batch 持续抛异常（批量 + 逐条全失败）。须如实计入 records_failed，
        不能假装全成功。镜像 stockinfo 逐条失败 failed_count += 1 语义。
        """
        mock_deps["data_source"].fetch_cn_stock_trade_day.return_value = raw_trade_df
        mock_deps["crud_repo"].find = MagicMock(return_value=[
            TradeDay(market=MARKET_TYPES.CHINA, is_open=False, timestamp="20240102"),
            TradeDay(market=MARKET_TYPES.CHINA, is_open=True, timestamp="20240103"),
        ])
        mock_deps["crud_repo"].remove = MagicMock()
        # 所有 add_batch 调用（批量 + 逐条）全失败
        mock_deps["crud_repo"].add_batch = MagicMock(side_effect=Exception("DB down"))

        with patch("ginkgo.data.services.trade_day_service.RichProgress"):
            result = service.sync()

        # 不静默：2 条 update 全失败计入 records_failed
        assert result.data.records_failed == 2
        assert result.data.records_added == 0


# ============================================================
# container 装配测试（DI wiring）
# ============================================================


class TestContainerWiring:
    """验证 data container 正确注册 trade_day_service provider（#6488 wiring）"""

    @pytest.mark.unit
    def test_container_resolves_trade_day_service(self):
        """container.trade_day_service() 可解析为 TradeDayService 实例"""
        from ginkgo.data.containers import container

        svc = container.trade_day_service()
        assert isinstance(svc, TradeDayService)
