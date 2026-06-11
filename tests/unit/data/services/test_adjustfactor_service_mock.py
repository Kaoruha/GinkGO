"""
性能: 219MB RSS, 2.09s, 16 tests [PASS]
AdjustfactorService 单元测试（Mock 依赖）

通过 MagicMock 注入所有依赖，隔离测试业务逻辑。
覆盖方法：构造器, sync, get, count, validate, check_integrity, calculate
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

from ginkgo.data.services.adjustfactor_service import AdjustfactorService
from ginkgo.data.services.base_service import ServiceResult


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def mock_deps():
    """创建 mock 依赖：crud_repo, data_source, stockinfo_service"""
    return {
        "crud_repo": MagicMock(),
        "data_source": MagicMock(),
        "stockinfo_service": MagicMock(),
    }


@pytest.fixture
def service(mock_deps):
    """创建 AdjustfactorService 实例（GLOG 已 mock）"""
    with patch("ginkgo.libs.GLOG"):
        svc = AdjustfactorService(
            crud_repo=mock_deps["crud_repo"],
            data_source=mock_deps["data_source"],
            stockinfo_service=mock_deps["stockinfo_service"],
        )
        return svc


# ============================================================
# 构造器测试
# ============================================================


class TestAdjustfactorServiceConstructor:
    """构造器依赖注入测试"""

    @pytest.mark.unit
    def test_constructor_sets_dependencies(self, service, mock_deps):
        """构造器应将所有依赖设置为私有属性"""
        assert service._crud_repo is mock_deps["crud_repo"]
        assert service._data_source is mock_deps["data_source"]
        assert service._stockinfo_service is mock_deps["stockinfo_service"]


# ============================================================
# sync 方法测试
# ============================================================


class TestAdjustfactorServiceSync:
    """sync 同步方法测试"""

    @pytest.mark.unit
    def test_sync_invalid_code(self, service, mock_deps):
        """股票代码不存在时返回失败"""
        mock_deps["stockinfo_service"].exists.return_value = False

        result = service.sync(code="999999.XX")

        assert result.success is False
        assert "not in stock list" in result.message

    @pytest.mark.unit
    def test_sync_empty_data_returns_success(self, service, mock_deps):
        """数据源返回空数据时返回成功，提示无新数据"""
        mock_deps["stockinfo_service"].exists.return_value = True
        mock_deps["crud_repo"].find.return_value = []
        mock_deps["data_source"].fetch_cn_stock_adjustfactor.return_value = pd.DataFrame()

        result = service.sync(code="000001.SZ")

        assert result.success is True
        assert "No new adjustfactor data" in result.message

    @pytest.mark.unit
    def test_sync_source_exception_returns_error(self, service, mock_deps):
        """数据源抛出异常时返回失败"""
        mock_deps["stockinfo_service"].exists.return_value = True
        mock_deps["crud_repo"].find.return_value = []
        mock_deps["data_source"].fetch_cn_stock_adjustfactor.side_effect = Exception("网络超时")

        result = service.sync(code="000001.SZ")

        assert result.success is False
        assert "Failed to fetch data from source" in result.message

    @pytest.mark.unit
    def test_sync_fetches_and_persists_via_real_source_method(self, service, mock_deps):
        """sync 应通过真实方法 fetch_cn_stock_adjustfactor 拉数据并落库 (#5909 根因A/A2/A3)

        真实数据源（Tushare/Baostock）只提供 fetch_cn_stock_adjustfactor，旧代码调
        不存在的 get_adjustfactor_data → 永远 NotImplementedError → 永远落不了库。
        """
        mock_deps["stockinfo_service"].exists.return_value = True
        mock_deps["crud_repo"].find.return_value = []          # _get_fetch_start_date 走默认窗口
        mock_deps["crud_repo"].exists.return_value = False     # 记录不存在 → 走 add 分支
        df = pd.DataFrame({"trade_date": ["20240101"], "adj_factor": [1.5]})
        mock_deps["data_source"].fetch_cn_stock_adjustfactor.return_value = df

        result = service.sync(code="000001.SZ")

        # 必须调真实方法（而非 get_adjustfactor_data）
        mock_deps["data_source"].fetch_cn_stock_adjustfactor.assert_called_once()
        # 数据成功落库：success + added=1
        assert result.success is True
        assert result.data.records_added == 1

    @pytest.mark.unit
    def test_sync_models_keep_raw_factor_placeholder_foreback(self, service, mock_deps):
        """收敛契约：sync 入库只存原始 adjustfactor，fore/back 占位 1.0（交 calculate 推导）

        前后复权推导是 calculate() 的职责（task_timer/worker 在 sync 后立即调 calculate
        覆盖 fore/back）。sync 内推导属冗余的第三套逻辑，会与 calculate 漂移。
        多行数据下旧 _convert 推导 fore=latest/raw(≠1.0) → 本测试红；
        收敛为复用 mappers（fore/back 恒 1.0）后 → 本测试绿。
        """
        from decimal import Decimal

        mock_deps["stockinfo_service"].exists.return_value = True
        mock_deps["crud_repo"].find.return_value = []
        mock_deps["crud_repo"].exists.return_value = False     # 走 add 分支
        df = pd.DataFrame({
            "trade_date": ["20240101", "20240102"],
            "adj_factor": [1.5, 3.0],
        })
        mock_deps["data_source"].fetch_cn_stock_adjustfactor.return_value = df

        result = service.sync(code="000001.SZ")

        assert result.success is True
        added = [call.args[0] for call in mock_deps["crud_repo"].add.call_args_list]
        assert len(added) == 2
        raw_expected = {Decimal("1.5"), Decimal("3.0")}
        for m in added:
            # adjustfactor 保留原始因子
            assert m.adjustfactor in raw_expected
            # fore/back 占位 1.0，交 calculate 推导
            assert m.foreadjustfactor == Decimal("1.0"), \
                f"foreadjustfactor 应占位 1.0（交 calculate），实际 {m.foreadjustfactor}"
            assert m.backadjustfactor == Decimal("1.0"), \
                f"backadjustfactor 应占位 1.0（交 calculate），实际 {m.backadjustfactor}"


# ============================================================
# get 方法测试
# ============================================================


class TestAdjustfactorServiceGet:
    """get 查询方法测试"""

    @pytest.mark.unit
    def test_get_returns_data(self, service, mock_deps):
        """正常查询返回成功，data 包含记录列表"""
        mock_deps["crud_repo"].find.return_value = [MagicMock(), MagicMock()]

        result = service.get(code="000001.SZ")

        assert result.success is True
        assert len(result.data) == 2
        assert "Retrieved 2 adjustfactor records" in result.message

    @pytest.mark.unit
    def test_get_crud_exception_returns_error(self, service, mock_deps):
        """crud_repo 异常时返回失败"""
        mock_deps["crud_repo"].find.side_effect = Exception("查询失败")

        result = service.get(code="000001.SZ")

        assert result.success is False
        assert "Failed to get adjustfactor data" in result.message

    @pytest.mark.unit
    def test_get_with_date_range_filters(self, service, mock_deps):
        """传入日期范围时应构建正确的 timestamp 过滤条件"""
        mock_deps["crud_repo"].find.return_value = []

        start = datetime(2024, 1, 1)
        end = datetime(2024, 6, 30)
        result = service.get(code="000001.SZ", start_date=start, end_date=end)

        assert result.success is True
        call_kwargs = mock_deps["crud_repo"].find.call_args.kwargs
        assert call_kwargs["filters"]["code"] == "000001.SZ"
        assert "timestamp__gte" in call_kwargs["filters"]
        assert "timestamp__lte" in call_kwargs["filters"]


# ============================================================
# count 方法测试
# ============================================================


class TestAdjustfactorServiceCount:
    """count 统计方法测试"""

    @pytest.mark.unit
    def test_count_returns_success(self, service, mock_deps):
        """正常统计返回成功"""
        mock_deps["crud_repo"].count.return_value = 42

        result = service.count(code="000001.SZ")

        assert result.success is True
        assert result.data == 42

    @pytest.mark.unit
    def test_count_exception_returns_error(self, service, mock_deps):
        """crud_repo.count 异常时返回失败"""
        mock_deps["crud_repo"].count.side_effect = Exception("count 失败")

        result = service.count(code="000001.SZ")

        assert result.success is False
        assert "Failed to count adjustfactor data" in result.message


# ============================================================
# validate 方法测试
# ============================================================


class TestAdjustfactorServiceValidate:
    """validate 数据验证方法测试"""

    @pytest.mark.unit
    def test_validate_empty_list_returns_failure(self, service):
        """传入空列表时因缺少 data_quality_score 参数导致异常，返回失败"""
        result = service.validate([])

        assert result.success is False

    @pytest.mark.unit
    def test_validate_dataframe_missing_quality_score(self, service):
        """validate 内部构造 DataValidationResult 缺少 data_quality_score，抛出异常被捕获"""
        df = pd.DataFrame([
            {"code": "000001.SZ", "timestamp": datetime(2024, 1, 1),
             "adjust_type": "fore", "adjust_factor": 1.5,
             "before_price": 10.0, "after_price": 10.0,
             "dividend": 0.5, "split_ratio": 1.0},
        ])
        result = service.validate(df)

        # DataValidationResult 缺少 data_quality_score 参数导致构造失败
        assert result.success is False


# ============================================================
# check_integrity 方法测试
# ============================================================


class TestAdjustfactorServiceCheckIntegrity:
    """check_integrity 数据完整性检查测试"""

    @pytest.mark.unit
    def test_check_integrity_no_data(self, service, mock_deps):
        """无数据时完整性检查应记录 no_data 问题"""
        mock_deps["crud_repo"].find.return_value = []

        result = service.check_integrity(
            code="000001.SZ",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 6, 30),
        )

        assert result.success is True
        assert result.data.total_records == 0

    @pytest.mark.unit
    def test_check_integrity_crud_exception(self, service, mock_deps):
        """crud_repo 异常时 check_integrity 内部调用 get 失败"""
        mock_deps["crud_repo"].find.side_effect = Exception("DB error")

        result = service.check_integrity(
            code="000001.SZ",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 6, 30),
        )

        # check_integrity 内部调用 self.get()，get 失败后返回错误
        assert result.success is False
        assert "Failed to retrieve data for integrity check" in result.message


# ============================================================
# calculate 方法测试
# ============================================================


class TestAdjustfactorServiceCalculate:
    """calculate 复权因子计算测试"""

    @pytest.mark.unit
    def test_calculate_empty_code(self, service):
        """空股票代码时返回失败"""
        result = service.calculate(code="")

        assert result.success is False
        assert "股票代码不能为空" in result.message

    @pytest.mark.unit
    def test_calculate_fewer_than_2_records(self, service, mock_deps):
        """记录少于 2 条时返回成功，提示无需处理"""
        mock_deps["crud_repo"].find.return_value = [MagicMock()]

        result = service.calculate(code="000001.SZ")

        assert result.success is True
        assert "少于2条" in result.message

    @pytest.mark.unit
    def test_calculate_crud_exception(self, service, mock_deps):
        """crud_repo.find 异常时返回失败"""
        mock_deps["crud_repo"].find.side_effect = Exception("查询失败")

        result = service.calculate(code="000001.SZ")

        assert result.success is False
        assert "复权因子计算失败" in result.message


# ============================================================
# sync_batch 方法测试
# ============================================================


class TestAdjustfactorServiceSyncBatch:
    """sync_batch 批量同步方法测试（#5909 根因B：诚实传播失败）"""

    @pytest.mark.unit
    def test_sync_batch_propagates_failure_when_all_codes_fail(self, service, mock_deps):
        """所有 code 拉取都失败时，sync_batch 必须 success=False

        旧代码 L589 无条件 success=True，吞掉逐 code 失败 → handler 误报 200，
        history 写 0，无数据落库。这正是 #5909 "返回成功但无效果" 的根因。
        """
        mock_deps["stockinfo_service"].exists.return_value = True
        mock_deps["crud_repo"].find.return_value = []
        mock_deps["data_source"].fetch_cn_stock_adjustfactor.side_effect = Exception("source down")

        result = service.sync_batch(codes=["000001.SZ", "000002.SZ"])

        assert result.success is False
        assert result.metadata["total_codes"] == 2

    @pytest.mark.unit
    def test_sync_batch_success_when_at_least_one_code_persists(self, service, mock_deps):
        """至少一个 code 成功落库时，sync_batch success=True（允许部分失败）"""
        mock_deps["stockinfo_service"].exists.return_value = True
        mock_deps["crud_repo"].find.return_value = []
        mock_deps["crud_repo"].exists.return_value = False
        df = pd.DataFrame({"trade_date": ["20240101"], "adj_factor": [1.5]})

        # 逐 code 返回不同结果：第一个正常，第二个抛错
        mock_deps["data_source"].fetch_cn_stock_adjustfactor.side_effect = [df, Exception("boom")]

        result = service.sync_batch(codes=["000001.SZ", "000002.SZ"])

        assert result.success is True

    @pytest.mark.unit
    def test_sync_batch_empty_codes_returns_success(self, service, mock_deps):
        """空 code 列表不算错误，返回 success=True"""
        result = service.sync_batch(codes=[])

        assert result.success is True
        assert result.metadata["total_codes"] == 0
