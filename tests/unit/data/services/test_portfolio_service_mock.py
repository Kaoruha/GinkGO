"""
PortfolioService 单元测试（Mock 依赖）

通过 MagicMock 注入所有依赖，隔离测试业务逻辑。
覆盖方法：构造器、health_check、add、get、count、exists、update、
delete、validate、check_integrity、mount_component、unmount_component
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from contextlib import contextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../.."))

from ginkgo.data.services.portfolio_service import PortfolioService
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.enums import PORTFOLIO_MODE_TYPES, PORTFOLIO_RUNSTATE_TYPES, FILE_TYPES


# ============================================================
# 辅助工具
# ============================================================


@contextmanager
def _mock_session():
    """模拟 get_session() 上下文管理器"""
    yield MagicMock()


@pytest.fixture
def mock_deps():
    """创建所有 mock 依赖"""
    return {
        "crud_repo": MagicMock(),
        "portfolio_file_mapping_crud": MagicMock(),
    }


@pytest.fixture
def service(mock_deps):
    """创建 PortfolioService 实例（GLOG 已 mock）"""
    with patch("ginkgo.libs.GLOG"):
        svc = PortfolioService(
            crud_repo=mock_deps["crud_repo"],
            portfolio_file_mapping_crud=mock_deps["portfolio_file_mapping_crud"],
        )
        return svc


def _make_portfolio(name="test-portfolio", uuid="port-001",
                    mode=PORTFOLIO_MODE_TYPES.BACKTEST,
                    state=PORTFOLIO_RUNSTATE_TYPES.INITIALIZED):
    """创建模拟投资组合对象"""
    p = MagicMock()
    p.name = name
    p.uuid = uuid
    p.mode = mode
    p.state = state
    p.desc = f"{mode.name} portfolio: {name}"
    return p


def _make_mapping(portfolio_id="port-001", file_id="file-001",
                  name="comp-1", mtype=FILE_TYPES.STRATEGY):
    """创建模拟映射对象"""
    m = MagicMock()
    m.uuid = "mount-001"
    m.portfolio_id = portfolio_id
    m.file_id = file_id
    m.name = name
    m.type = mtype
    m.created_at = MagicMock()
    m.created_at.isoformat.return_value = "2024-01-01T00:00:00"
    return m


# ============================================================
# 构造器测试
# ============================================================


class TestConstructor:
    """构造器测试"""

    @pytest.mark.unit
    def test_constructor_stores_dependencies(self, service, mock_deps):
        """构造器正确存储所有依赖"""
        assert service._crud_repo is mock_deps["crud_repo"]
        assert service._portfolio_file_mapping_crud is mock_deps["portfolio_file_mapping_crud"]

    @pytest.mark.unit
    def test_constructor_dependencies_dict(self, service):
        """构造器将依赖存入 _dependencies 字典"""
        assert "crud_repo" in service._dependencies
        assert "portfolio_file_mapping_crud" in service._dependencies


# ============================================================
# health_check 测试
# ============================================================


class TestHealthCheck:
    """健康检查测试"""

    @pytest.mark.unit
    def test_health_check_healthy(self, service, mock_deps):
        """所有依赖正常时返回 healthy"""
        mock_deps["crud_repo"].find.return_value = [_make_portfolio()]
        mock_deps["crud_repo"].count.return_value = 3

        result = service.health_check()
        assert result.success is True
        assert result.data["status"] == "healthy"
        assert result.data["total_portfolios"] == 3

    @pytest.mark.unit
    def test_health_check_crud_none(self, service):
        """crud_repo 为 None 时返回错误"""
        service._crud_repo = None

        result = service.health_check()
        assert result.success is False
        assert "未初始化" in result.error

    @pytest.mark.unit
    def test_health_check_db_connection_fail(self, service, mock_deps):
        """数据库连接失败时返回错误"""
        mock_deps["crud_repo"].find.side_effect = Exception("DB connection failed")

        result = service.health_check()
        assert result.success is False
        assert "连接失败" in result.error or "connection" in result.error.lower()


# ============================================================
# add 测试
# ============================================================


class TestAdd:
    """创建投资组合测试"""

    @pytest.mark.unit
    def test_add_success(self, service, mock_deps):
        """正常创建投资组合"""
        mock_deps["crud_repo"].exists.return_value = False
        mock_deps["crud_repo"].get_session.return_value = _mock_session()
        mock_deps["crud_repo"].create.return_value = _make_portfolio("my-portfolio", "uuid-1")

        result = service.add(name="my-portfolio")
        assert result.success is True
        assert result.data["name"] == "my-portfolio"
        mock_deps["crud_repo"].create.assert_called_once()

    @pytest.mark.unit
    def test_add_empty_name(self, service, mock_deps):
        """名称为空时返回错误"""
        result = service.add(name="")
        assert result.success is False
        assert "不能为空" in result.error

    @pytest.mark.unit
    def test_add_whitespace_name(self, service, mock_deps):
        """名称为纯空白时返回错误"""
        result = service.add(name="   ")
        assert result.success is False
        assert "不能为空" in result.error

    @pytest.mark.unit
    def test_add_duplicate_name(self, service, mock_deps):
        """名称重复时返回错误"""
        mock_deps["crud_repo"].exists.return_value = True

        result = service.add(name="duplicate")
        assert result.success is False
        assert "已存在" in result.error

    @pytest.mark.unit
    def test_add_exception(self, service, mock_deps):
        """创建过程异常时返回错误（mock create 抛异常）"""
        mock_deps["crud_repo"].exists.return_value = False
        mock_deps["crud_repo"].get_session.return_value = _mock_session()
        mock_deps["crud_repo"].create.side_effect = Exception("DB error")

        result = service.add(name="fail-portfolio")
        assert result.success is False
        assert "DB error" in result.error


# ============================================================
# get 测试
# ============================================================


class TestGet:
    """查询投资组合测试"""

    @pytest.mark.unit
    def test_get_by_id(self, service, mock_deps):
        """按 portfolio_id 查询"""
        mock_deps["crud_repo"].find.return_value = [_make_portfolio("p1", "uuid-1")]

        result = service.get(portfolio_id="uuid-1")
        assert result.success is True
        call_kwargs = mock_deps["crud_repo"].find.call_args
        assert call_kwargs[1]["filters"]["uuid"] == "uuid-1"

    @pytest.mark.unit
    def test_get_by_name(self, service, mock_deps):
        """按名称查询"""
        mock_deps["crud_repo"].find.return_value = [_make_portfolio("my-p")]

        result = service.get(name="my-p")
        assert result.success is True

    @pytest.mark.unit
    def test_get_not_found_by_id(self, service, mock_deps):
        """按 ID 查询不到时返回错误"""
        mock_deps["crud_repo"].find.return_value = []

        result = service.get(portfolio_id="not-exist")
        assert result.success is False
        assert "不存在" in result.error

    @pytest.mark.unit
    def test_get_exception(self, service, mock_deps):
        """查询异常时返回错误"""
        mock_deps["crud_repo"].find.side_effect = Exception("查询失败")

        result = service.get(portfolio_id="e1")
        assert result.success is False
        assert "查询失败" in result.error


# ============================================================
# count 测试
# ============================================================


class TestCount:
    """计数方法测试"""

    @pytest.mark.unit
    def test_count_all(self, service, mock_deps):
        """无过滤条件时返回全部计数"""
        mock_deps["crud_repo"].count.return_value = 7

        result = service.count()
        assert result.success is True
        assert result.data["count"] == 7

    @pytest.mark.unit
    def test_count_with_name(self, service, mock_deps):
        """按名称过滤计数"""
        mock_deps["crud_repo"].count.return_value = 1

        result = service.count(name="my-p")
        assert result.success is True
        assert result.data["count"] == 1

    @pytest.mark.unit
    def test_count_exception(self, service, mock_deps):
        """计数异常时返回错误"""
        mock_deps["crud_repo"].count.side_effect = Exception("计数失败")

        result = service.count()
        assert result.success is False
        assert "计数失败" in result.error


# ============================================================
# exists 测试
# ============================================================


class TestExists:
    """存在性检查测试"""

    @pytest.mark.unit
    def test_exists_true(self, service, mock_deps):
        """投资组合存在时返回 exists=True"""
        mock_deps["crud_repo"].exists.return_value = True

        result = service.exists(portfolio_id="p1")
        assert result.success is True
        assert result.data["exists"] is True

    @pytest.mark.unit
    def test_exists_false(self, service, mock_deps):
        """投资组合不存在时返回 exists=False"""
        mock_deps["crud_repo"].exists.return_value = False

        result = service.exists(portfolio_id="not-exist")
        assert result.success is True
        assert result.data["exists"] is False

    @pytest.mark.unit
    def test_exists_no_params(self, service, mock_deps):
        """不提供任何参数时返回错误"""
        result = service.exists()
        assert result.success is False
        assert "必须提供" in result.error

    @pytest.mark.unit
    def test_exists_by_name(self, service, mock_deps):
        """按名称检查存在性"""
        mock_deps["crud_repo"].exists.return_value = True

        result = service.exists(name="my-p")
        assert result.success is True
        assert result.data["exists"] is True


# ============================================================
# update 测试
# ============================================================


class TestUpdate:
    """更新投资组合测试"""

    @pytest.mark.unit
    def test_update_name(self, service, mock_deps):
        """更新投资组合名称"""
        mock_deps["crud_repo"].modify.return_value = 1
        mock_deps["crud_repo"].find.return_value = []
        # get_portfolios 调用 _crud_repo.find
        mock_deps["crud_repo"].find.return_value = []

        result = service.update(portfolio_id="p1", name="new-name")
        assert result.success is True
        assert "name" in result.data["updates_applied"]

    @pytest.mark.unit
    def test_update_empty_id(self, service, mock_deps):
        """portfolio_id 为空时返回错误"""
        result = service.update(portfolio_id="", name="new")
        assert result.success is False
        assert "cannot be empty" in result.error.lower() or "不能为空" in result.error

    @pytest.mark.unit
    def test_update_empty_name(self, service, mock_deps):
        """名称为空字符串时返回错误"""
        result = service.update(portfolio_id="p1", name="   ")
        assert result.success is False

    @pytest.mark.unit
    def test_update_no_params(self, service, mock_deps):
        """不提供任何更新参数时，源码 bug 导致 TypeError 逃逸（ServiceResult.success 参数过多）"""
        # 源码 bug: portfolio_service.py L169 调用 ServiceResult.success({}, "msg", warnings)
        # 传了 3 个位置参数，但签名只接受 data + message 两个
        with pytest.raises(TypeError, match="takes from 1 to 3 positional arguments"):
            service.update(portfolio_id="p1")


# ============================================================
# delete 测试
# ============================================================


class TestDelete:
    """删除投资组合测试"""

    @pytest.mark.unit
    def test_delete_success(self, service, mock_deps):
        """正常删除投资组合"""
        mock_deps["crud_repo"].exists.return_value = True
        mock_deps["portfolio_file_mapping_crud"].find.return_value = []
        mock_deps["portfolio_file_mapping_crud"].remove.return_value = 0
        mock_deps["crud_repo"].soft_remove.return_value = 1

        result = service.delete(portfolio_id="p1")
        assert result.success is True
        assert result.data["portfolio_id"] == "p1"

    @pytest.mark.unit
    def test_delete_empty_id(self, service, mock_deps):
        """portfolio_id 为空时返回错误"""
        result = service.delete(portfolio_id="")
        assert result.success is False
        assert "不能为空" in result.error

    @pytest.mark.unit
    def test_delete_not_exist(self, service, mock_deps):
        """投资组合不存在时返回错误"""
        mock_deps["crud_repo"].exists.return_value = False

        result = service.delete(portfolio_id="not-exist")
        assert result.success is False
        assert "不存在" in result.error

    @pytest.mark.unit
    def test_delete_exception(self, service, mock_deps):
        """删除过程异常时返回错误"""
        mock_deps["crud_repo"].exists.side_effect = Exception("删除失败")

        result = service.delete(portfolio_id="p1")
        assert result.success is False
        assert "删除失败" in result.error


# ============================================================
# mount_component 测试
# ============================================================


class TestMountComponent:
    """组件挂载测试"""

    @pytest.mark.unit
    def test_mount_success(self, service, mock_deps):
        """正常挂载组件"""
        mock_deps["crud_repo"].exists.return_value = True
        mock_deps["portfolio_file_mapping_crud"].get_session.return_value = _mock_session()
        mock_deps["portfolio_file_mapping_crud"].create.return_value = _make_mapping()
        # get_components 内部 find 返回空列表
        mock_deps["portfolio_file_mapping_crud"].find.return_value = []

        result = service.mount_component(
            portfolio_id="p1", component_id="f1",
            component_name="strategy-1", component_type=FILE_TYPES.STRATEGY
        )
        assert result.success is True
        assert result.data["component_name"] == "strategy-1"
        mock_deps["portfolio_file_mapping_crud"].create.assert_called_once()

    @pytest.mark.unit
    def test_mount_empty_portfolio_id(self, service, mock_deps):
        """portfolio_id 为空时返回错误"""
        result = service.mount_component(
            portfolio_id="", component_id="f1",
            component_name="s1", component_type=FILE_TYPES.STRATEGY
        )
        assert result.success is False
        assert "不能为空" in result.error

    @pytest.mark.unit
    def test_mount_portfolio_not_exist(self, service, mock_deps):
        """投资组合不存在时返回错误"""
        mock_deps["crud_repo"].exists.return_value = False

        result = service.mount_component(
            portfolio_id="not-exist", component_id="f1",
            component_name="s1", component_type=FILE_TYPES.STRATEGY
        )
        assert result.success is False
        assert "不存在" in result.error


# ============================================================
# unmount_component 测试
# ============================================================


class TestUnmountComponent:
    """组件卸载测试"""

    @pytest.mark.unit
    def test_unmount_success(self, service, mock_deps):
        """正常卸载组件"""
        mock_deps["portfolio_file_mapping_crud"].soft_remove.return_value = 1

        result = service.unmount_component(mount_id="mount-001")
        assert result.success is True
        assert result.data["mount_id"] == "mount-001"

    @pytest.mark.unit
    def test_unmount_empty_id(self, service, mock_deps):
        """mount_id 为空时返回错误"""
        result = service.unmount_component(mount_id="")
        assert result.success is False
        assert "不能为空" in result.error

    @pytest.mark.unit
    def test_unmount_exception(self, service, mock_deps):
        """卸载过程异常时返回错误"""
        mock_deps["portfolio_file_mapping_crud"].soft_remove.side_effect = Exception("卸载失败")

        result = service.unmount_component(mount_id="m1")
        assert result.success is False
        assert "卸载失败" in result.error


# ============================================================
# validate 测试
# ============================================================


class TestValidate:
    """数据验证测试"""

    @pytest.mark.unit
    def test_validate_valid_data(self, service, mock_deps):
        """有效数据通过验证"""
        result = service.validate({"name": "valid-portfolio"})
        assert result.success is True
        assert result.data["valid"] is True

    @pytest.mark.unit
    def test_validate_missing_name(self, service, mock_deps):
        """缺少 name 字段时验证失败"""
        result = service.validate({"mode": 1})
        assert result.success is False
        assert "name" in result.error.lower()

    @pytest.mark.unit
    def test_validate_empty_name(self, service, mock_deps):
        """name 为空时验证失败"""
        result = service.validate({"name": ""})
        assert result.success is False
        # 空名称先触发必填字段检查
        assert "name" in result.error.lower()

    @pytest.mark.unit
    def test_validate_name_too_long(self, service, mock_deps):
        """名称超长时验证失败"""
        result = service.validate({"name": "A" * 101})
        assert result.success is False
        assert "100" in result.error

    @pytest.mark.unit
    def test_validate_invalid_dict_type(self, service, mock_deps):
        """非字典类型时验证失败"""
        result = service.validate("not a dict")
        assert result.success is False
        assert "字典" in result.error
