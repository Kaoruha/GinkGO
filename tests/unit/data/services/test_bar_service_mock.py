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
_path = os.path.join(os.path.dirname(__file__
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
