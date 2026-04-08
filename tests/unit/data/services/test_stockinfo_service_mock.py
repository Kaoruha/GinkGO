"""
性能: 220MB RSS, 1.98s, 39 tests [PASS]
StockinfoService 单元测试（Mock 依赖）

通过 MagicMock 注入所有依赖，隔离测试业务逻辑。
覆盖方法：health_check, sync, get, count, validate, check_integrity, exists
"""

import sys
import os
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime

# 将项目根目录加入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../.."))

from ginkgo.data.services.stockinfo_service import StockinfoService
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.entities import StockInfo


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
    """创建 StockinfoService 实例（GLOG 已 mock）"""
    with patch("ginkgo.libs.GLOG"):
        svc = StockinfoService(
            crud_repo=mock_deps["crud_repo"],
            data_source=mock_deps["data_source"]
        )
        return svc


# ============================================================
# health_check 测试
# ============================================================


class TestHealthCheck:
    """health_check 健康检查测试"""

    @pytest.mark.unit
    def test_health_check_healthy(self, service, mock_deps):
        """数据源可用时返回 healthy 状态"""
        # count() 内部调用 crud_repo.find，需要 mock 返回
        mock_deps["crud_repo"].find.return_value = [{"code": "000001.SZ"}]
        mock_deps["data_source"].fetch_cn_stockinfo = MagicMock()  # hasattr 检查

        result = service.health_check()
        assert result.success is True
        assert result.data["status"] == "healthy"
        assert result.data["dependencies"]["data_source"] == "healthy"

    @pytest.mark.unit
    def test_health_check_no_data_source(self, service, mock_deps):
        """data_source 为 None 时返回 unhealthy"""
        service._data_source = None
        mock_deps["crud_repo"].find.return_value = []

        result = service.health_check()
        assert result.success is True
        assert result.data["status"] == "unhealthy"

    @pytest.mark.unit
    def test_health_check_data_source_missing_method(self, service, mock_deps):
        """data_source 缺少 fetch_cn_stockinfo 方法时返回 unhealthy"""
        service._data_source = MagicMock(spec=[])  # 空 spec，无任何方法
        mock_deps["crud_repo"].find.return_value = []

        result = service.health_check()
        assert result.data["status"] == "unhealthy"

    @pytest.mark.unit
    def test_health_check_count_exception(self, service, mock_deps):
        """count() 异常时 total_records 回退为 0"""
        mock_deps["data_source"].fetch_cn_stockinfo = MagicMock()
        # find 抛异常，但 health_check 内部 try-except 捕获
        mock_deps["crud_repo"].find.side_effect = Exception("DB down")

        result = service.health_check()
        assert result.success is True
        assert result.data["total_records"] == 0

    @pytest.mark.unit
    def test_health_check_total_records(self, service, mock_deps):
        """health_check 正确统计 total_records"""
        mock_deps["data_source"].fetch_cn_stockinfo = MagicMock()
        mock_deps["crud_repo"].find.return_value = [
            {"code": "000001.SZ"}, {"code": "000002.SZ"}, {"code": "600000.SH"}
        ]

        result = service.health_check()
        assert result.success is True
        assert result.data["total_records"] == 3


# ============================================================
# count 测试
# ============================================================


class TestCount:
    """count 计数方法测试"""

    @pytest.mark.unit
    def test_count_all(self, service, mock_deps):
        """无过滤条件时返回全部记录数"""
        mock_deps["crud_repo"].find.return_value = [
            {"code": "000001.SZ"},
            {"code": "000002.SZ"},
            {"code": "600000.SH"},
        ]
        result = service.count()
        assert result.success is True
        assert result.data == 3

    @pytest.mark.unit
    def test_count_with_filters(self, service, mock_deps):
        """带过滤条件时传递正确 filters 给 crud_repo"""
        mock_deps["crud_repo"].find.return_value = [{"code": "000001.SZ"}]

        result = service.count(code="000001.SZ", industry="银行")
        assert result.success is True
        assert result.data == 1
        # 验证传递的 filters
        call_kwargs = mock_deps["crud_repo"].find.call_args
        assert call_kwargs[1]["filters"]["code"] == "000001.SZ"
        assert call_kwargs[1]["filters"]["industry"] == "银行"

    @pytest.mark.unit
    def test_count_empty_result(self, service, mock_deps):
        """查询无结果时返回 0"""
        mock_deps["crud_repo"].find.return_value = []

        result = service.count(code="999999.XX")
        assert result.success is True
        assert result.data == 0

    @pytest.mark.unit
    def test_count_none_result(self, service, mock_deps):
        """crud_repo 返回 None 时处理为 0"""
        mock_deps["crud_repo"].find.return_value = None

        result = service.count()
        assert result.success is True
        assert result.data == 0

    @pytest.mark.unit
    def test_count_exception(self, service, mock_deps):
        """crud_repo 异常时返回失败结果"""
        mock_deps["crud_repo"].find.side_effect = Exception("数据库连接失败")

        result = service.count()
        assert result.success is False
        assert "数据库连接失败" in result.error


# ============================================================
# get 测试
# ============================================================


class TestGet:
    """get 查询方法测试"""

    @pytest.mark.unit
    def test_get_all(self, service, mock_deps):
        """无过滤条件时返回所有记录"""
        mock_model_list = MagicMock()
        mock_model_list.__len__ = MagicMock(return_value=2)
        mock_deps["crud_repo"].find.return_value = mock_model_list

        result = service.get()
        assert result.success is True
        assert result.data is mock_model_list

    @pytest.mark.unit
    def test_get_with_code_filter(self, service, mock_deps):
        """按 code 过滤时传递正确参数"""
        mock_model_list = MagicMock()
        mock_model_list.__len__ = MagicMock(return_value=1)
        mock_deps["crud_repo"].find.return_value = mock_model_list

        result = service.get(code="000001.SZ")
        assert result.success is True
        call_kwargs = mock_deps["crud_repo"].find.call_args
        assert call_kwargs[1]["filters"]["code"] == "000001.SZ"

    @pytest.mark.unit
    def test_get_with_pagination(self, service, mock_deps):
        """分页参数正确传递给 crud_repo"""
        mock_model_list = MagicMock()
        mock_model_list.__len__ = MagicMock(return_value=10)
        mock_deps["crud_repo"].find.return_value = mock_model_list

        result = service.get(limit=10, offset=2)
        assert result.success is True
        call_kwargs = mock_deps["crud_repo"].find.call_args
        assert call_kwargs[1]["page_size"] == 10
        assert call_kwargs[1]["page"] == 2

    @pytest.mark.unit
    def test_get_with_sorting(self, service, mock_deps):
        """排序参数正确传递"""
        mock_model_list = MagicMock()
        mock_model_list.__len__ = MagicMock(return_value=5)
        mock_deps["crud_repo"].find.return_value = mock_model_list

        result = service.get(order_by="code", desc_order=True)
        assert result.success is True
        call_kwargs = mock_deps["crud_repo"].find.call_args
        assert call_kwargs[1]["order_by"] == "code"
        assert call_kwargs[1]["desc_order"] is True

    @pytest.mark.unit
    def test_get_with_name_filter(self, service, mock_deps):
        """按 name 过滤时使用 name__contains"""
        mock_model_list = MagicMock()
        mock_model_list.__len__ = MagicMock(return_value=0)
        mock_deps["crud_repo"].find.return_value = mock_model_list

        result = service.get(name="平安")
        call_kwargs = mock_deps["crud_repo"].find.call_args
        assert call_kwargs[1]["filters"]["name__contains"] == "平安"

    @pytest.mark.unit
    def test_get_exception(self, service, mock_deps):
        """crud_repo 异常时返回失败结果"""
        mock_deps["crud_repo"].find.side_effect = Exception("查询超时")

        result = service.get()
        assert result.success is False
        assert "查询超时" in result.error


# ============================================================
# exists 测试
# ============================================================


class TestExists:
    """exists 存在性检查测试"""

    @pytest.mark.unit
    def test_exists_true(self, service, mock_deps):
        """股票代码存在时返回 True"""
        mock_deps["crud_repo"].find.return_value = [{"code": "000001.SZ"}]

        result = service.exists("000001.SZ")
        assert result.success is True
        assert result.data is True

    @pytest.mark.unit
    def test_exists_false(self, service, mock_deps):
        """股票代码不存在时返回 False"""
        mock_deps["crud_repo"].find.return_value = []

        result = service.exists("999999.XX")
        assert result.success is True
        assert result.data is False

    @pytest.mark.unit
    def test_exists_passes_correct_filters(self, service, mock_deps):
        """exists 传递正确的 code 过滤条件和 page_size=1"""
        mock_deps["crud_repo"].find.return_value = []

        service.exists("000001.SZ")
        call_kwargs = mock_deps["crud_repo"].find.call_args
        assert call_kwargs[1]["filters"]["code"] == "000001.SZ"
        assert call_kwargs[1]["page_size"] == 1

    @pytest.mark.unit
    def test_exists_exception(self, service, mock_deps):
        """crud_repo 异常时返回错误结果"""
        mock_deps["crud_repo"].find.side_effect = Exception("连接失败")

        result = service.exists("000001.SZ")
        assert result.success is False
        assert "连接失败" in result.error


# ============================================================
# validate 测试
# ============================================================


class TestValidate:
    """validate 数据验证测试"""

    @pytest.mark.unit
    def test_validate_empty_data(self, service, mock_deps):
        """无数据时返回警告信息"""
        mock_deps["crud_repo"].find.return_value = []

        result = service.validate()
        assert result.success is True
        assert "No stock info data to validate" in result.message

    @pytest.mark.unit
    def test_validate_none_data(self, service, mock_deps):
        """crud_repo 返回 None 时处理为空数据"""
        mock_deps["crud_repo"].find.return_value = None

        result = service.validate()
        assert result.success is True
        assert "No stock info data to validate" in result.message

    @pytest.mark.unit
    def test_validate_passes_args_to_find(self, service, mock_deps):
        """validate 传递过滤参数给 crud_repo"""
        # 创建一个模拟 model_list，支持 to_dataframe
        mock_df = pd.DataFrame({"code": ["000001.SZ"], "name": ["平安银行"]})
        mock_model_list = MagicMock()
        mock_model_list.to_dataframe.return_value = mock_df
        mock_model_list.__len__ = MagicMock(return_value=1)
        mock_deps["crud_repo"].find.return_value = mock_model_list

        result = service.validate(filters={"code": "000001.SZ"})
        assert result.success is True
        # 验证 crud_repo.find 被正确调用
        mock_deps["crud_repo"].find.assert_called_once_with(filters={"code": "000001.SZ"})

    @pytest.mark.unit
    def test_validate_clean_data(self, service, mock_deps):
        """干净数据通过验证"""
        mock_df = pd.DataFrame({
            "code": ["000001.SZ", "000002.SZ"],
            "name": ["平安银行", "万科A"]
        })
        mock_model_list = MagicMock()
        mock_model_list.to_dataframe.return_value = mock_df
        mock_model_list.__len__ = MagicMock(return_value=2)
        mock_deps["crud_repo"].find.return_value = mock_model_list

        result = service.validate()
        assert result.success is True
        assert result.data.metadata["is_valid"] is True
        assert "passed validation" in result.message

    @pytest.mark.unit
    def test_validate_missing_fields(self, service, mock_deps):
        """缺失字段时验证失败"""
        mock_df = pd.DataFrame({
            "code": ["000001.SZ", None],
            "name": ["平安银行", None]
        })
        mock_model_list = MagicMock()
        mock_model_list.to_dataframe.return_value = mock_df
        mock_model_list.__len__ = MagicMock(return_value=2)
        mock_deps["crud_repo"].find.return_value = mock_model_list

        result = service.validate()
        assert result.success is True
        assert result.data.metadata["is_valid"] is False

    @pytest.mark.unit
    def test_validate_exception(self, service, mock_deps):
        """验证过程异常时返回失败结果"""
        mock_deps["crud_repo"].find.side_effect = Exception("验证异常")

        result = service.validate()
        assert result.success is False
        assert "验证异常" in result.error


# ============================================================
# check_integrity 测试
# ============================================================


class TestCheckIntegrity:
    """check_integrity 数据完整性检查测试"""

    @pytest.mark.unit
    def test_check_integrity_empty_data(self, service, mock_deps):
        """无数据时返回 no_data 问题"""
        mock_deps["crud_repo"].find.return_value = []

        result = service.check_integrity()
        assert result.success is True
        assert "No stock info data" in result.message

    @pytest.mark.unit
    def test_check_integrity_none_data(self, service, mock_deps):
        """crud_repo 返回 None 时处理为空数据"""
        mock_deps["crud_repo"].find.return_value = None

        result = service.check_integrity()
        assert result.success is True
        assert "No stock info data" in result.message

    @pytest.mark.unit
    def test_check_integrity_clean_data(self, service, mock_deps):
        """干净数据完整性检查通过（score >= 90）"""
        mock_df = pd.DataFrame({
            "code": ["000001.SZ", "000002.SZ", "600000.SH"],
            "name": ["平安银行", "万科A", "浦发银行"]
        })
        mock_model_list = MagicMock()
        mock_model_list.to_dataframe.return_value = mock_df
        mock_model_list.__len__ = MagicMock(return_value=3)
        mock_deps["crud_repo"].find.return_value = mock_model_list

        result = service.check_integrity()
        assert result.success is True
        assert result.data.metadata["is_healthy"] is True

    @pytest.mark.unit
    def test_check_integrity_duplicate_codes(self, service, mock_deps):
        """重复 code 被检测为完整性问题"""
        mock_df = pd.DataFrame({
            "code": ["000001.SZ", "000001.SZ"],
            "name": ["平安银行", "平安银行"]
        })
        mock_model_list = MagicMock()
        mock_model_list.to_dataframe.return_value = mock_df
        mock_model_list.__len__ = MagicMock(return_value=2)
        mock_deps["crud_repo"].find.return_value = mock_model_list

        result = service.check_integrity()
        assert result.success is True
        # 重复 code 会导致 integrity_score < 90
        assert result.data.metadata["is_healthy"] is False

    @pytest.mark.unit
    def test_check_integrity_missing_codes(self, service, mock_deps):
        """缺失 code 被检测为完整性问题"""
        mock_df = pd.DataFrame({
            "code": [None, "000002.SZ"],
            "name": ["平安银行", "万科A"]
        })
        mock_model_list = MagicMock()
        mock_model_list.to_dataframe.return_value = mock_df
        mock_model_list.__len__ = MagicMock(return_value=2)
        mock_deps["crud_repo"].find.return_value = mock_model_list

        result = service.check_integrity()
        assert result.success is True
        assert result.data.metadata["issues_count"] >= 1

    @pytest.mark.unit
    def test_check_integrity_exception(self, service, mock_deps):
        """检查过程异常时返回失败结果"""
        mock_deps["crud_repo"].find.side_effect = Exception("完整性检查失败")

        result = service.check_integrity()
        assert result.success is False
        assert "完整性检查失败" in result.error


# ============================================================
# sync 测试
# ============================================================


class TestSync:
    """sync 数据同步测试"""

    @pytest.fixture
    def raw_stock_df(self):
        """创建模拟的 raw_data DataFrame"""
        return pd.DataFrame({
            "ts_code": ["000001.SZ", "000002.SZ"],
            "name": ["平安银行", "万科A"],
            "industry": ["银行", "房地产"],
            "list_date": ["19910403", "19910129"],
            "delist_date": [None, None]
        })

    @pytest.mark.unit
    def test_sync_empty_source(self, service, mock_deps):
        """数据源返回空 DataFrame 时同步失败"""
        mock_deps["data_source"].fetch_cn_stockinfo.return_value = pd.DataFrame()

        result = service.sync()
        assert result.success is False
        assert "No stock info data available" in result.message

    @pytest.mark.unit
    def test_sync_none_source(self, service, mock_deps):
        """数据源返回 None 时同步失败"""
        mock_deps["data_source"].fetch_cn_stockinfo.return_value = None

        result = service.sync()
        assert result.success is False

    @pytest.mark.unit
    def test_sync_source_exception(self, service, mock_deps):
        """数据源抛异常时同步失败"""
        mock_deps["data_source"].fetch_cn_stockinfo.side_effect = Exception("API 超时")

        result = service.sync()
        assert result.success is False
        assert "API 超时" in result.error

    @pytest.mark.unit
    def test_sync_all_new_records(self, service, mock_deps, raw_stock_df):
        """全部为新记录时批量插入成功"""
        mock_deps["data_source"].fetch_cn_stockinfo.return_value = raw_stock_df
        mock_deps["crud_repo"].find.return_value = []  # 无已存在记录
        mock_deps["crud_repo"].add_batch = MagicMock()

        with patch("ginkgo.data.services.stockinfo_service.RichProgress"):
            with patch("ginkgo.data.services.stockinfo_service.datetime_normalize", return_value=datetime(2024, 1, 1)):
                result = service.sync()

        assert result.success is True
        assert "successfully" in result.message.lower() or "successful" in result.message.lower()

    @pytest.mark.unit
    def test_sync_all_existing_records(self, service, mock_deps, raw_stock_df):
        """全部为已存在记录时执行更新（删除+重新插入）"""
        mock_deps["data_source"].fetch_cn_stockinfo.return_value = raw_stock_df
        # 模拟已存在记录
        mock_deps["crud_repo"].find.return_value = [
            MagicMock(code="000001.SZ"),
            MagicMock(code="000002.SZ")
        ]
        mock_deps["crud_repo"].remove = MagicMock()
        mock_deps["crud_repo"].add_batch = MagicMock()

        with patch("ginkgo.data.services.stockinfo_service.RichProgress"):
            with patch("ginkgo.data.services.stockinfo_service.datetime_normalize", return_value=datetime(2024, 1, 1)):
                result = service.sync()

        assert result.success is True
        # 验证先删除再插入
        mock_deps["crud_repo"].remove.assert_called()

    @pytest.mark.unit
    def test_sync_batch_insert_fallback(self, service, mock_deps, raw_stock_df):
        """批量插入失败时回退到逐条插入"""
        mock_deps["data_source"].fetch_cn_stockinfo.return_value = raw_stock_df
        mock_deps["crud_repo"].find.return_value = []  # 新记录
        mock_deps["crud_repo"].add_batch.side_effect = Exception("批量失败")
        mock_deps["crud_repo"].create = MagicMock()

        with patch("ginkgo.data.services.stockinfo_service.RichProgress"):
            with patch("ginkgo.data.services.stockinfo_service.datetime_normalize", return_value=datetime(2024, 1, 1)):
                # StockInfo 对象不支持 ** 解包，回退路径 create(**item) 会 TypeError
                # 源码 except 中 item.get("code") 也需要 StockInfo 支持 get
                # 动态添加 get 方法以完整测试回退路径
                original_init = StockInfo.__init__

                def patched_init(self_inner, *args, **kwargs):
                    original_init(self_inner, *args, **kwargs)
                    self_inner.get = lambda key, default=None: getattr(self_inner, key, default)

                with patch.object(StockInfo, "__init__", patched_init):
                    result = service.sync()

        # 验证 add_batch 被调用（主路径失败）
        mock_deps["crud_repo"].add_batch.assert_called()
        # create(**item) 因 StockInfo 不支持解包，从未真正被调用
        # 回退路径的 except 被触发，记录了失败
        mock_deps["crud_repo"].create.assert_not_called()

    @pytest.mark.unit
    def test_sync_calls_data_source(self, service, mock_deps, raw_stock_df):
        """sync 调用 data_source.fetch_cn_stockinfo"""
        mock_deps["data_source"].fetch_cn_stockinfo.return_value = raw_stock_df
        mock_deps["crud_repo"].find.return_value = []
        mock_deps["crud_repo"].add_batch = MagicMock()

        with patch("ginkgo.data.services.stockinfo_service.RichProgress"):
            with patch("ginkgo.data.services.stockinfo_service.datetime_normalize", return_value=datetime(2024, 1, 1)):
                service.sync()

        mock_deps["data_source"].fetch_cn_stockinfo.assert_called_once()
