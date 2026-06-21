"""
性能: 218MB RSS, 1.98s, 15 tests [PASS]
BarService 单元测试（Mock 依赖）

通过 MagicMock 注入所有依赖，隔离测试业务逻辑。
覆盖方法：构造器, get, count, get_available_codes, get_latest_timestamp, sync_range
"""

import sys
import os
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime, timedelta

# 将项目根目录加入路径
_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.bar_service import BarService
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.enums import FREQUENCY_TYPES, ADJUSTMENT_TYPES


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def mock_deps():
    """创建 mock 依赖：crud_repo, data_source, stockinfo_service, adjustfactor_service"""
    return {
        "crud_repo": MagicMock(),
        "data_source": MagicMock(),
        "stockinfo_service": MagicMock(),
        "adjustfactor_service": MagicMock(),
    }


@pytest.fixture
def service(mock_deps):
    """创建 BarService 实例（GLOG 已 mock，adjustfactor_service 显式注入避免真实初始化）"""
    with patch("ginkgo.libs.GLOG"):
        svc = BarService(
            crud_repo=mock_deps["crud_repo"],
            data_source=mock_deps["data_source"],
            stockinfo_service=mock_deps["stockinfo_service"],
            adjustfactor_service=mock_deps["adjustfactor_service"],
        )
        return svc


# ============================================================
# 构造器测试
# ============================================================


class TestBarServiceConstructor:
    """构造器依赖注入测试"""

    @pytest.mark.unit
    def test_constructor_sets_dependencies(self, service, mock_deps):
        """构造器应将所有依赖设置为私有属性"""
        assert service._crud_repo is mock_deps["crud_repo"]
        assert service._data_source is mock_deps["data_source"]
        assert service._stockinfo_service is mock_deps["stockinfo_service"]
        assert service._adjustfactor_service is mock_deps["adjustfactor_service"]

    @pytest.mark.unit
    def test_constructor_without_adjustfactor_service(self, mock_deps):
        """不传 adjustfactor_service 时应自动创建默认实例"""
        with patch("ginkgo.libs.GLOG"):
            with patch("ginkgo.data.services.adjustfactor_service.AdjustfactorService") as MockAF:
                svc = BarService(
                    crud_repo=mock_deps["crud_repo"],
                    data_source=mock_deps["data_source"],
                    stockinfo_service=mock_deps["stockinfo_service"],
                )
                MockAF.assert_called_once()
                assert svc._adjustfactor_service is MockAF.return_value


# ============================================================
# get 方法测试
# ============================================================


class TestBarServiceGet:
    """get 查询方法测试"""

    @pytest.mark.unit
    def test_get_no_params_returns_error(self, service):
        """不传任何查询参数时返回错误"""
        result = service.get()
        assert result.success is False
        assert "查询参数不能为空" in result.error

    @pytest.mark.unit
    def test_get_with_code_calls_find(self, service, mock_deps):
        """传入 code 时调用 crud_repo.find 并返回成功"""
        mock_model_list = MagicMock()
        mock_model_list.__len__ = MagicMock(return_value=3)
        mock_deps["crud_repo"].find.return_value = mock_model_list

        result = service.get(code="000001.SZ", adjustment_type=ADJUSTMENT_TYPES.NONE)

        assert result.success is True
        mock_deps["crud_repo"].find.assert_called_once()
        call_kwargs = mock_deps["crud_repo"].find.call_args
        assert call_kwargs.kwargs["filters"]["code"] == "000001.SZ"

    @pytest.mark.unit
    def test_get_crud_exception_returns_error(self, service, mock_deps):
        """crud_repo.find 抛出异常时返回 ServiceResult.error"""
        mock_deps["crud_repo"].find.side_effect = Exception("数据库连接失败")

        result = service.get(code="000001.SZ")

        assert result.success is False
        assert "Database operation failed" in result.error

    @pytest.mark.unit
    def test_get_with_date_range_builds_correct_filters(self, service, mock_deps):
        """传入日期范围时应正确构建 timestamp 过滤条件"""
        mock_model_list = MagicMock()
        mock_model_list.__len__ = MagicMock(return_value=0)
        mock_deps["crud_repo"].find.return_value = mock_model_list

        start = datetime(2024, 1, 1)
        end = datetime(2024, 6, 30)
        result = service.get(code="000001.SZ", start_date=start, end_date=end, adjustment_type=ADJUSTMENT_TYPES.NONE)

        assert result.success is True
        call_kwargs = mock_deps["crud_repo"].find.call_args.kwargs
        assert "timestamp__gte" in call_kwargs["filters"]
        assert "timestamp__lte" in call_kwargs["filters"]


# ============================================================
# count 方法测试
# ============================================================


class TestBarServiceCount:
    """count 统计方法测试"""

    @pytest.mark.unit
    def test_count_returns_success(self, service, mock_deps):
        """正常统计时返回 ServiceResult.success"""
        mock_deps["crud_repo"].count.return_value = 100

        result = service.count(code="000001.SZ")

        assert result.success is True
        assert result.data == 100
        assert "100 bar records" in result.message

    @pytest.mark.unit
    def test_count_exception_returns_error(self, service, mock_deps):
        """crud_repo.count 抛出异常时返回错误"""
        mock_deps["crud_repo"].count.side_effect = Exception("count 失败")

        result = service.count(code="000001.SZ")

        assert result.success is False
        assert "Database query failed" in result.error


# ============================================================
# get_available_codes 测试
# ============================================================


class TestBarServiceGetAvailableCodes:
    """get_available_codes 方法测试"""

    @pytest.mark.unit
    def test_get_available_codes_returns_sorted_list(self, service, mock_deps):
        """应返回排序后的代码列表"""
        mock_deps["crud_repo"].find.return_value = ["600000.SH", "000001.SZ"]

        result = service.get_available_codes()

        assert result.success is True
        assert result.data == ["000001.SZ", "600000.SH"]

    @pytest.mark.unit
    def test_get_available_codes_crud_exception(self, service, mock_deps):
        """crud_repo 异常时返回错误"""
        mock_deps["crud_repo"].find.side_effect = Exception("查询失败")

        result = service.get_available_codes()

        assert result.success is False
        assert "Database query failed" in result.error


# ============================================================
# get_latest_timestamp 测试
# ============================================================


class TestBarServiceGetLatestTimestamp:
    """get_latest_timestamp 方法测试"""

    @pytest.mark.unit
    def test_get_latest_timestamp_found(self, service, mock_deps):
        """有数据时返回最新时间戳"""
        mock_record = MagicMock()
        mock_record.timestamp = datetime(2024, 12, 31)
        mock_deps["crud_repo"].find.return_value = [mock_record]

        result = service.get_latest_timestamp(code="000001.SZ")

        assert result.success is True
        assert result.data == datetime(2024, 12, 31)

    @pytest.mark.unit
    def test_get_latest_timestamp_no_data(self, service, mock_deps):
        """无数据时返回默认开始日期"""
        mock_deps["crud_repo"].find.return_value = []

        with patch("ginkgo.data.services.bar_service.GCONF") as mock_gconf:
            mock_gconf.DEFAULTSTART = "20200101"
            with patch("ginkgo.data.services.bar_service.datetime_normalize") as mock_normalize:
                mock_normalize.return_value = datetime(2020, 1, 1)
                result = service.get_latest_timestamp(code="000001.SZ")

        assert result.success is True
        assert "default start date" in result.message

    @pytest.mark.unit
    def test_get_latest_timestamp_exception(self, service, mock_deps):
        """crud_repo 异常时返回错误"""
        mock_deps["crud_repo"].find.side_effect = Exception("DB error")

        result = service.get_latest_timestamp(code="000001.SZ")

        assert result.success is False
        assert "Database query failed" in result.error


# ============================================================
# sync_range 测试
# ============================================================


class TestBarServiceSyncRange:
    """sync_range 同步方法测试"""

    @pytest.mark.unit
    def test_sync_range_invalid_code(self, service, mock_deps):
        """股票代码不在 stockinfo 列表中时返回错误"""
        mock_deps["stockinfo_service"].exists.return_value = False

        result = service.sync_range(code="999999.XX")

        assert result.success is False
        assert "not in stock list" in result.message

    @pytest.mark.unit
    def test_sync_range_empty_source_data(self, service, mock_deps):
        """数据源返回空数据时返回成功但提示无新数据"""
        mock_deps["stockinfo_service"].exists.return_value = True
        mock_deps["data_source"].fetch_cn_stock_daybar.return_value = pd.DataFrame()

        with patch("ginkgo.data.services.bar_service.datetime_normalize", side_effect=lambda x: x):
            with patch("ginkgo.data.services.bar_service.GCONF") as mock_gconf:
                mock_gconf.DEFAULTSTART = datetime(2020, 1, 1)
                result = service.sync_range(code="000001.SZ")

        assert result.success is True
        assert "No new data available" in result.message

    @pytest.mark.unit
    def test_sync_range_normal_path_records_processed_gt_zero(self, service, mock_deps):
        """#5584: 正常同步路径 records_processed 应 = raw_data 行数 > 0（证伪"恒 0"）

        正常路径(bar_service.py:206-210): 数据源有数据 → 转实体 → 过滤后仍有新数据 →
        落库，records_processed = len(raw_data)。旧代码此处恒 0，现应正确统计。
        """
        mock_deps["stockinfo_service"].exists.return_value = True
        df = pd.DataFrame({
            "open": [10.0, 11.0, 12.0],
            "high": [11.0, 12.0, 13.0],
            "low": [9.0, 10.0, 11.0],
            "close": [10.5, 11.5, 12.5],
        })
        mock_deps["data_source"].fetch_cn_stock_daybar.return_value = df
        entities = [MagicMock(timestamp=datetime(2024, 1, 1 + i)) for i in range(3)]
        mock_deps["crud_repo"].find.return_value = []  # 无已存在记录 → 全部视为新数据
        mock_deps["crud_repo"].add_batch.return_value = entities

        with patch("ginkgo.data.services.bar_service.datetime_normalize", side_effect=lambda x: x), \
                patch("ginkgo.data.services.bar_service.mappers") as mock_mappers:
            mock_mappers.dataframe_to_bar_entities.return_value = entities
            result = service.sync_range(
                code="000001.SZ",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 3),
            )

        assert result.success is True
        assert result.data.records_processed == 3  # 证伪 #5584 "恒 0"

    @pytest.mark.unit
    def test_sync_range_idempotent_path_records_processed_gt_zero(self, service, mock_deps):
        """#5584: 幂等路径(数据已全部存在) records_processed 仍应 = len(raw_data) > 0

        幂等路径(bar_service.py:161-175): _filter_existing_data 返空(全部已存在)，
        但 records_processed 仍 = len(raw_data)、records_skipped 同步、is_idempotent=True。
        旧代码此处恒 0，现应正确统计。
        """
        mock_deps["stockinfo_service"].exists.return_value = True
        df = pd.DataFrame({
            "open": [10.0, 11.0, 12.0],
            "high": [11.0, 12.0, 13.0],
            "low": [9.0, 10.0, 11.0],
            "close": [10.5, 11.5, 12.5],
        })
        mock_deps["data_source"].fetch_cn_stock_daybar.return_value = df

        # 3 个实体 + 3 条已存在记录，timestamp 完全一致 → new_models=[] 走幂等分支
        ts = [datetime(2024, 1, 1 + i) for i in range(3)]
        entities = [MagicMock(timestamp=ts[i]) for i in range(3)]
        existing = [MagicMock(timestamp=ts[i]) for i in range(3)]
        mock_deps["crud_repo"].find.return_value = existing  # 全部已存在

        with patch("ginkgo.data.services.bar_service.datetime_normalize", side_effect=lambda x: x), \
                patch("ginkgo.data.services.bar_service.mappers") as mock_mappers:
            mock_mappers.dataframe_to_bar_entities.return_value = entities
            result = service.sync_range(
                code="000001.SZ",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 3),
            )

        assert result.success is True
        assert result.data.records_processed == 3  # 幂等路径也非 0
        assert result.data.records_skipped == 3
        assert result.data.is_idempotent is True


# ============================================================
# sync_smart 测试
# ============================================================

class TestBarServiceSyncSmart:
    """sync_smart 方法测试"""

    @pytest.mark.unit
    def test_fast_mode_data_up_to_date_returns_already_latest(self, service, mock_deps):
        """
        #5450: fast_mode 下库中最新数据已是今天时，sync_smart 应返回 success +
        '已是最新'说明，而非让 start>end 的 ValueError 被 _validate_and_set_date_range
        抛出后吞成失败 proc=0。

        复现：000001.SZ 最新 bars timestamp=今天 → _get_fetch_date_range 算出
        start=明天 > end=今天 → 旧代码 sync_range 抛 ValueError → sync_smart except
        返回 error，sync_history 记 proc=0 无说明。
        """
        # 库中最新 bars 已是今天 → start_date = 明天 > end_date = 今天
        mock_record = MagicMock()
        mock_record.timestamp = datetime.now()
        mock_deps["crud_repo"].find.return_value = [mock_record]

        result = service.sync_smart("000001.SZ", fast_mode=True)

        # 验收标准2: 数据已最新时明确说明为何 0 records
        assert result.success is True, f"应成功返回'已是最新'，实际 error: {getattr(result, 'error', None)}"
        assert "最新" in (result.message or ""), f"message 应说明已最新，实际: {result.message}"
        # 守卫提前返回，不应进 sync_range 调数据源
        mock_deps["data_source"].fetch_cn_stock_daybar.assert_not_called()
        # data 是 DataSyncResult，records_processed=0（已最新无新数据）
        assert result.data is not None
        assert result.data.records_processed == 0

    @pytest.mark.unit
    def test_fast_mode_data_up_to_date_metadata_reason(self, service, mock_deps):
        """#5450: '已是最新'结果应带 metadata(reason=already_up_to_date) 供调用方区分"""
        mock_record = MagicMock()
        mock_record.timestamp = datetime.now()
        mock_deps["crud_repo"].find.return_value = [mock_record]

        result = service.sync_smart("000001.SZ", fast_mode=True)

        assert result.success is True
        assert result.data.metadata.get("reason") == "already_up_to_date"
