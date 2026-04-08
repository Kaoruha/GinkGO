"""
性能: 219MB RSS, 1.94s, 31 tests [PASS]
ServiceResult 和 BaseService 单元测试

覆盖范围：
- ServiceResult: 工厂方法、属性管理、序列化、状态判断
- BaseService: 依赖注入、日志记录、结果创建、字符串表示
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

# 将项目根目录加入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../.."))

from ginkgo.data.services.base_service import ServiceResult, BaseService


# ============================================================
# ServiceResult 测试
# ============================================================


class TestServiceResultFactoryMethods:
    """ServiceResult 工厂方法测试"""

    @pytest.mark.unit
    def test_success_factory(self):
        """success() 工厂方法创建成功结果"""
        result = ServiceResult.success(data={"key": "value"}, message="操作成功")
        assert result.success is True
        assert result.error == ""
        assert result.data == {"key": "value"}
        assert result.message == "操作成功"

    @pytest.mark.unit
    def test_error_factory(self):
        """error() 工厂方法创建错误结果"""
        result = ServiceResult.error(error="数据库连接失败", data=None)
        assert result.success is False
        assert result.error == "数据库连接失败"
        assert result.message == "数据库连接失败"  # message 默认使用 error
        assert result.data is None

    @pytest.mark.unit
    def test_error_factory_with_custom_message(self):
        """error() 工厂方法支持自定义 message"""
        result = ServiceResult.error(error="DB_ERROR", message="自定义错误信息")
        assert result.error == "DB_ERROR"
        assert result.message == "自定义错误信息"

    @pytest.mark.unit
    def test_failure_factory(self):
        """failure() 工厂方法创建失败结果"""
        result = ServiceResult.failure(message="操作失败", data={"reason": "timeout"})
        assert result.success is False
        assert result.error == "操作失败"
        assert result.message == "操作失败"
        assert result.data == {"reason": "timeout"}


class TestServiceResultConstruction:
    """ServiceResult 构造和默认值测试"""

    @pytest.mark.unit
    def test_default_construction(self):
        """默认构造：success=False, data=None, warnings=[], metadata={}"""
        result = ServiceResult()
        assert result.success is False
        assert result.error == ""
        assert result.data is None
        assert result.message == ""
        assert result.warnings == []
        assert result.metadata == {}


class TestServiceResultDataManagement:
    """ServiceResult 数据管理测试"""

    @pytest.mark.unit
    def test_add_warning(self):
        """add_warning 向 warnings 列表追加警告"""
        result = ServiceResult()
        result.add_warning("低内存警告")
        result.add_warning("连接超时警告")
        assert len(result.warnings) == 2
        assert "低内存警告" in result.warnings
        assert "连接超时警告" in result.warnings

    @pytest.mark.unit
    def test_set_data(self):
        """set_data 在 data 字典中设置键值对"""
        result = ServiceResult(data={})
        result.set_data("count", 42)
        result.set_data("name", "测试")
        assert result.data["count"] == 42
        assert result.data["name"] == "测试"

    @pytest.mark.unit
    def test_set_metadata(self):
        """set_metadata 在 metadata 字典中设置键值对"""
        result = ServiceResult()
        result.set_metadata("duration", 1.23)
        result.set_metadata("source", "tushare")
        assert result.metadata["duration"] == 1.23
        assert result.metadata["source"] == "tushare"


class TestServiceResultSerialization:
    """ServiceResult 序列化测试"""

    @pytest.mark.unit
    def test_to_dict_success(self):
        """成功结果的 to_dict 结构正确"""
        result = ServiceResult.success(data={"total": 100}, message="OK")
        d = result.to_dict()
        assert d["success"] is True
        assert d["error"] == ""
        assert d["total"] == 100  # data 展开到顶层

    @pytest.mark.unit
    def test_to_dict_error(self):
        """错误结果的 to_dict 包含 error 字段"""
        result = ServiceResult.error(error="连接失败")
        d = result.to_dict()
        assert d["success"] is False
        assert d["error"] == "连接失败"

    @pytest.mark.unit
    def test_to_dict_with_warnings(self):
        """to_dict 在有 warnings 时包含该字段"""
        result = ServiceResult.success(data={"total": 10})
        result.add_warning("警告1")
        result.add_warning("警告2")
        d = result.to_dict()
        assert "warnings" in d
        assert d["warnings"] == ["警告1", "警告2"]

    @pytest.mark.unit
    def test_to_dict_with_metadata(self):
        """to_dict 在有 metadata 时包含该字段"""
        result = ServiceResult.success(data={})
        result.set_metadata("duration", 0.5)
        d = result.to_dict()
        assert "metadata" in d
        assert d["metadata"]["duration"] == 0.5

    @pytest.mark.unit
    def test_to_dict_empty_collections_excluded(self):
        """to_dict 不包含空集合"""
        result = ServiceResult()
        d = result.to_dict()
        assert "warnings" not in d
        assert "metadata" not in d


class TestServiceResultStateCheck:
    """ServiceResult 状态判断测试"""

    @pytest.mark.unit
    def test_is_success_is_failure(self):
        """is_success 和 is_failure 返回互补结果"""
        success_result = ServiceResult.success()
        failure_result = ServiceResult.failure()

        assert success_result.is_success() is True
        assert success_result.is_failure() is False
        assert failure_result.is_success() is False
        assert failure_result.is_failure() is True


class TestServiceResultStringRepresentation:
    """ServiceResult 字符串表示测试"""

    @pytest.mark.unit
    def test_str_success(self):
        """成功结果的 __str__ 包含 success=True"""
        result = ServiceResult.success(data={"count": 5})
        s = str(result)
        assert "success=True" in s
        assert "data=" in s

    @pytest.mark.unit
    def test_str_failure(self):
        """失败结果的 __str__ 包含 success=False 和 error"""
        result = ServiceResult.error(error="超时")
        s = str(result)
        assert "success=False" in s
        assert "error=超时" in s

    @pytest.mark.unit
    def test_str_no_data_no_error(self):
        """无数据无错误时 __str__ 不显示多余字段"""
        success_result = ServiceResult.success()
        assert str(success_result) == "ServiceResult(success=True)"

        failure_result = ServiceResult.failure()
        assert str(failure_result) == "ServiceResult(success=False)"


# ============================================================
# BaseService 测试
# ============================================================


class ConcreteService(BaseService):
    """BaseService 的具体实现，用于测试"""

    def _initialize_dependencies(self):
        # 调用父类默认行为
        super()._initialize_dependencies()


class TestBaseServiceDependencyInjection:
    """BaseService 依赖注入测试"""

    @pytest.mark.unit
    @patch("ginkgo.data.services.base_service.GLOG")
    def test_di_sets_private_attributes(self, mock_glog):
        """依赖注入将 'crud_repo' 设置为 self._crud_repo"""
        mock_repo = MagicMock()
        service = ConcreteService(crud_repo=mock_repo)
        assert service._crud_repo is mock_repo

    @pytest.mark.unit
    @patch("ginkgo.data.services.base_service.GLOG")
    def test_multiple_dependencies(self, mock_glog):
        """多个依赖项全部注入为私有属性"""
        mock_repo = MagicMock()
        mock_source = MagicMock()
        mock_cache = MagicMock()
        service = ConcreteService(
            crud_repo=mock_repo,
            data_source=mock_source,
            cache=mock_cache
        )
        assert service._crud_repo is mock_repo
        assert service._data_source is mock_source
        assert service._cache is mock_cache

    @pytest.mark.unit
    @patch("ginkgo.data.services.base_service.GLOG")
    def test_dependencies_stored_in_dict(self, mock_glog):
        """依赖项同时存储在 _dependencies 字典中"""
        mock_repo = MagicMock()
        service = ConcreteService(crud_repo=mock_repo)
        assert "crud_repo" in service._dependencies
        assert service._dependencies["crud_repo"] is mock_repo

    @pytest.mark.unit
    @patch("ginkgo.data.services.base_service.GLOG")
    def test_initialize_dependencies_override(self, mock_glog):
        """子类可以覆写 _initialize_dependencies 来自定义初始化逻辑"""

        class CustomService(BaseService):
            def _initialize_dependencies(self):
                # 自定义：只注入 repo，忽略其他
                setattr(self, "_repo", self._dependencies.get("crud_repo"))

        mock_repo = MagicMock()
        mock_other = MagicMock()
        service = CustomService(crud_repo=mock_repo, other=mock_other)
        assert service._repo is mock_repo
        # 确认 other 没有被默认逻辑注入
        assert not hasattr(service, "_other")


class TestBaseServiceProperties:
    """BaseService 属性测试"""

    @pytest.mark.unit
    @patch("ginkgo.data.services.base_service.GLOG")
    def test_service_name_returns_class_name(self, mock_glog):
        """service_name 返回类名"""
        service = ConcreteService()
        assert service.service_name == "ConcreteService"

    @pytest.mark.unit
    @patch("ginkgo.data.services.base_service.GLOG")
    def test_create_result_returns_service_result(self, mock_glog):
        """create_result 返回 ServiceResult 实例"""
        service = ConcreteService()
        result = service.create_result(success=True)
        assert isinstance(result, ServiceResult)
        assert result.success is True

    @pytest.mark.unit
    @patch("ginkgo.data.services.base_service.GLOG")
    def test_create_result_failure(self, mock_glog):
        """create_result 可创建失败结果"""
        service = ConcreteService()
        result = service.create_result(success=False, error="发生错误")
        assert result.success is False
        assert result.error == "发生错误"


class TestBaseServiceLogging:
    """BaseService 日志记录测试"""

    @pytest.mark.unit
    @patch("ginkgo.data.services.base_service.GLOG")
    def test_log_operation_start(self, mock_glog):
        """_log_operation_start 记录操作开始日志"""
        service = ConcreteService()
        service._log_operation_start("sync", code="000001.SZ", limit=100)
        mock_glog.DEBUG.assert_called()
        # 验证日志包含操作名和参数
        call_args = mock_glog.DEBUG.call_args[0][0]
        assert "sync" in call_args
        assert "code=000001.SZ" in call_args
        assert "limit=100" in call_args

    @pytest.mark.unit
    @patch("ginkgo.data.services.base_service.GLOG")
    def test_log_operation_end_success(self, mock_glog):
        """_log_operation_end 记录操作成功完成日志"""
        service = ConcreteService()
        service._log_operation_end("sync", success=True, duration=1.234)
        call_args = mock_glog.DEBUG.call_args[0][0]
        assert "sync" in call_args
        assert "completed" in call_args
        assert "1.234s" in call_args

    @pytest.mark.unit
    @patch("ginkgo.data.services.base_service.GLOG")
    def test_log_operation_end_failure(self, mock_glog):
        """_log_operation_end 记录操作失败日志"""
        service = ConcreteService()
        service._log_operation_end("sync", success=False, duration=0.5)
        call_args = mock_glog.DEBUG.call_args[0][0]
        assert "failed" in call_args

    @pytest.mark.unit
    @patch("ginkgo.data.services.base_service.GLOG")
    def test_log_operation_end_no_duration(self, mock_glog):
        """_log_operation_end 不传 duration 时不显示时间"""
        service = ConcreteService()
        service._log_operation_end("sync", success=True)
        call_args = mock_glog.DEBUG.call_args[0][0]
        assert "completed" in call_args
        assert "s" not in call_args.split("completed")[1][:3]  # 不包含秒数

    @pytest.mark.unit
    @patch("ginkgo.data.services.base_service.GLOG")
    def test_init_logs_dependencies(self, mock_glog):
        """初始化时记录依赖项列表"""
        mock_repo = MagicMock()
        service = ConcreteService(crud_repo=mock_repo)
        # 最后一次 DEBUG 调用应包含依赖列表
        init_call = mock_glog.DEBUG.call_args[0][0]
        assert "initialized" in init_call
        assert "crud_repo" in init_call


class TestBaseServiceStringRepresentation:
    """BaseService 字符串表示测试"""

    @pytest.mark.unit
    @patch("ginkgo.data.services.base_service.GLOG")
    def test_str(self, mock_glog):
        """__str__ 返回 <ClassName> 格式"""
        service = ConcreteService()
        assert str(service) == "<ConcreteService>"

    @pytest.mark.unit
    @patch("ginkgo.data.services.base_service.GLOG")
    def test_repr(self, mock_glog):
        """__repr__ 返回 <ClassName at 0x...> 格式"""
        service = ConcreteService()
        r = repr(service)
        assert "ConcreteService" in r
        assert "at 0x" in r
        assert hex(id(service)) in r
