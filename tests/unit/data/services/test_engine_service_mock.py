"""
EngineService 单元测试（Mock 依赖）

通过 MagicMock 注入所有依赖，隔离测试业务逻辑。
覆盖方法：构造器、health_check、add、get、count、exists、update、
set_status、delete、validate、check_integrity、fuzzy_search
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from contextlib import contextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../.."))

from ginkgo.data.services.engine_service import EngineService
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.enums import ENGINESTATUS_TYPES, SOURCE_TYPES


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
        "engine_portfolio_mapping_crud": MagicMock(),
        "param_crud": MagicMock(),
    }


@pytest.fixture
def service(mock_deps):
    """创建 EngineService 实例（GLOG 已 mock）"""
    with patch("ginkgo.libs.GLOG"):
        svc = EngineService(
            crud_repo=mock_deps["crud_repo"],
            engine_portfolio_mapping_crud=mock_deps["engine_portfolio_mapping_crud"],
            param_crud=mock_deps["param_crud"],
        )
        return svc


def _make_engine(name="test-engine", uuid="engine-001", is_live=False,
                 status=ENGINESTATUS_TYPES.IDLE):
    """创建模拟引擎对象"""
    e = MagicMock()
    e.name = name
    e.uuid = uuid
    e.is_live = is_live
    e.status = status
    e.desc = f"{'实盘' if is_live else '回测'}引擎: {name}"
    return e


# ============================================================
# 构造器测试
# ============================================================


class TestConstructor:
    """构造器测试"""

    @pytest.mark.unit
    def test_constructor_stores_dependencies(self, service, mock_deps):
        """构造器正确存储所有依赖"""
        assert service._crud_repo is mock_deps["crud_repo"]
        assert service._mapping_repo is mock_deps["engine_portfolio_mapping_crud"]
        assert service._param_crud is mock_deps["param_crud"]

    @pytest.mark.unit
    def test_constructor_mapping_repo_alias(self, service, mock_deps):
        """_mapping_repo 是 _engine_portfolio_mapping_crud 的别名"""
        assert service._mapping_repo is service._engine_portfolio_mapping_crud


# ============================================================
# health_check 测试
# ============================================================


class TestHealthCheck:
    """健康检查测试"""

    @pytest.mark.unit
    def test_health_check_healthy(self, service, mock_deps):
        """所有依赖正常时返回成功"""
        mock_deps["crud_repo"].count.return_value = 5
        mock_deps["engine_portfolio_mapping_crud"].count.return_value = 3
        mock_deps["param_crud"].count.return_value = 10

        result = service.health_check()
        assert result.success is True
        assert result.data["database_connection"] == "ok"
        assert result.data["engine_count"] == 5
        assert result.data["mapping_count"] == 3

    @pytest.mark.unit
    def test_health_check_db_exception(self, service, mock_deps):
        """数据库连接异常时返回错误"""
        mock_deps["crud_repo"].count.side_effect = Exception("DB down")

        result = service.health_check()
        assert result.success is False
        assert "DB down" in result.error


# ============================================================
# add 测试
# ============================================================


class TestAdd:
    """创建引擎测试"""

    @pytest.mark.unit
    def test_add_backtest_engine(self, service, mock_deps):
        """创建回测引擎成功"""
        mock_deps["crud_repo"].exists.return_value = False
        mock_deps["crud_repo"].create.return_value = _make_engine("bt-1", "e-001")

        result = service.add(name="bt-1", is_live=False)
        assert result.success is True
        assert result.data["engine_info"]["name"] == "bt-1"
        assert result.data["engine_info"]["is_live"] is False
        mock_deps["crud_repo"].create.assert_called_once()

    @pytest.mark.unit
    def test_add_live_engine(self, service, mock_deps):
        """创建实盘引擎成功"""
        mock_deps["crud_repo"].exists.return_value = False
        mock_deps["crud_repo"].create.return_value = _make_engine("live-1", "e-002", is_live=True)

        result = service.add(name="live-1", is_live=True)
        assert result.success is True
        assert result.data["engine_info"]["is_live"] is True

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

        result = service.add(name="dup")
        assert result.success is False
        assert "已存在" in result.error

    @pytest.mark.unit
    def test_add_name_truncation_warning(self, service, mock_deps):
        """名称超长时截断并产生警告"""
        mock_deps["crud_repo"].exists.return_value = False
        mock_deps["crud_repo"].create.return_value = _make_engine("a" * 50)

        result = service.add(name="a" * 100)
        assert result.success is True
        assert len(result.warnings) > 0

    @pytest.mark.unit
    def test_add_exception(self, service, mock_deps):
        """创建过程异常时返回错误"""
        mock_deps["crud_repo"].exists.side_effect = Exception("create failed")

        result = service.add(name="err")
        assert result.success is False
        assert "create failed" in result.error


# ============================================================
# get 测试
# ============================================================


class TestGet:
    """查询引擎测试"""

    @pytest.mark.unit
    def test_get_by_id(self, service, mock_deps):
        """按 engine_id 查询"""
        mock_deps["crud_repo"].find.return_value = [_make_engine("e1", "id-1")]

        result = service.get(engine_id="id-1")
        assert result.success is True
        call_kwargs = mock_deps["crud_repo"].find.call_args
        assert call_kwargs[1]["filters"]["uuid"] == "id-1"
        assert call_kwargs[1]["filters"]["is_del"] is False

    @pytest.mark.unit
    def test_get_by_name(self, service, mock_deps):
        """按名称查询"""
        mock_deps["crud_repo"].find.return_value = [_make_engine("my-engine")]

        result = service.get(name="my-engine")
        assert result.success is True

    @pytest.mark.unit
    def test_get_exception(self, service, mock_deps):
        """查询异常时返回错误"""
        mock_deps["crud_repo"].find.side_effect = Exception("query failed")

        result = service.get(engine_id="e1")
        assert result.success is False
        assert "query failed" in result.error


# ============================================================
# count 测试
# ============================================================


class TestCount:
    """计数方法测试"""

    @pytest.mark.unit
    def test_count_all(self, service, mock_deps):
        """无过滤条件时返回全部计数"""
        mock_deps["crud_repo"].count.return_value = 10

        result = service.count()
        assert result.success is True
        assert result.data["count"] == 10

    @pytest.mark.unit
    def test_count_with_name(self, service, mock_deps):
        """按名称过滤计数"""
        mock_deps["crud_repo"].count.return_value = 1

        result = service.count(name="my-engine")
        assert result.success is True
        assert result.data["count"] == 1

    @pytest.mark.unit
    def test_count_exception(self, service, mock_deps):
        """计数异常时返回错误"""
        mock_deps["crud_repo"].count.side_effect = Exception("count err")

        result = service.count()
        assert result.success is False
        assert "count err" in result.error


# ============================================================
# exists 测试
# ============================================================


class TestExists:
    """存在性检查测试"""

    @pytest.mark.unit
    def test_exists_true(self, service, mock_deps):
        """引擎存在时返回 exists=True"""
        mock_deps["crud_repo"].count.return_value = 1

        result = service.exists(engine_id="e1")
        assert result.success is True
        assert result.data["exists"] is True

    @pytest.mark.unit
    def test_exists_false(self, service, mock_deps):
        """引擎不存在时返回 exists=False"""
        mock_deps["crud_repo"].count.return_value = 0

        result = service.exists(engine_id="not-exist")
        assert result.success is True
        assert result.data["exists"] is False

    @pytest.mark.unit
    def test_exists_by_name(self, service, mock_deps):
        """按名称检查存在性"""
        mock_deps["crud_repo"].count.return_value = 2

        result = service.exists(name="my-engine")
        assert result.success is True
        assert result.data["count"] == 2

    @pytest.mark.unit
    def test_exists_exception(self, service, mock_deps):
        """检查过程异常时返回错误"""
        mock_deps["crud_repo"].count.side_effect = Exception("exists err")

        result = service.exists(engine_id="e1")
        assert result.success is False
        assert "exists err" in result.error


# ============================================================
# update 测试
# ============================================================


class TestUpdate:
    """更新引擎测试"""

    @pytest.mark.unit
    def test_update_name(self, service, mock_deps):
        """更新引擎名称"""
        # find 第一次调用：检查名称冲突；第二次调用：获取更新后数据
        mock_deps["crud_repo"].find.side_effect = [[], [_make_engine("new-name")]]
        mock_deps["crud_repo"].modify.return_value = 1

        result = service.update(engine_id="e1", name="new-name")
        assert result.success is True
        assert "name" in result.data["updates_applied"]

    @pytest.mark.unit
    def test_update_empty_id(self, service, mock_deps):
        """engine_id 为空时返回错误"""
        result = service.update(engine_id="", name="new")
        assert result.success is False
        assert "不能为空" in result.error

    @pytest.mark.unit
    def test_update_no_params(self, service, mock_deps):
        """不提供任何更新参数时返回空更新"""
        result = service.update(engine_id="e1")
        assert result.success is True
        assert result.data["updates_applied"] == []

    @pytest.mark.unit
    def test_update_name_conflict(self, service, mock_deps):
        """名称与其他引擎冲突时返回错误"""
        other_engine = _make_engine("conflict-name", "other-uuid")
        mock_deps["crud_repo"].find.return_value = [other_engine]

        result = service.update(engine_id="e1", name="conflict-name")
        assert result.success is False
        assert "已存在" in result.error


# ============================================================
# set_status 测试
# ============================================================


class TestSetStatus:
    """引擎状态更新测试"""

    @pytest.mark.unit
    def test_set_status_with_enum(self, service, mock_deps):
        """使用枚举值设置状态"""
        mock_deps["crud_repo"].count.return_value = 1
        mock_deps["crud_repo"].get_session.return_value = _mock_session()
        mock_deps["crud_repo"].modify.return_value = 1

        result = service.set_status(engine_id="e1", status=ENGINESTATUS_TYPES.RUNNING)
        assert result.success is True
        assert result.data["new_status"] == "RUNNING"

    @pytest.mark.unit
    def test_set_status_with_int(self, service, mock_deps):
        """使用整数值设置状态"""
        mock_deps["crud_repo"].count.return_value = 1
        mock_deps["crud_repo"].get_session.return_value = _mock_session()
        mock_deps["crud_repo"].modify.return_value = 1

        result = service.set_status(engine_id="e1", status=ENGINESTATUS_TYPES.RUNNING.value)
        assert result.success is True

    @pytest.mark.unit
    def test_set_status_invalid_int(self, service, mock_deps):
        """使用无效整数值时返回错误"""
        mock_deps["crud_repo"].count.return_value = 1

        result = service.set_status(engine_id="e1", status=9999)
        assert result.success is False
        assert "无效" in result.error

    @pytest.mark.unit
    def test_set_status_engine_not_exist(self, service, mock_deps):
        """引擎不存在时返回错误"""
        mock_deps["crud_repo"].count.return_value = 0

        result = service.set_status(engine_id="not-exist", status=ENGINESTATUS_TYPES.RUNNING)
        assert result.success is False
        assert "不存在" in result.error


# ============================================================
# delete 测试
# ============================================================


class TestDelete:
    """删除引擎测试"""

    @pytest.mark.unit
    def test_delete_success(self, service, mock_deps):
        """正常删除引擎"""
        mock_deps["crud_repo"].get_session.return_value = _mock_session()
        mock_deps["engine_portfolio_mapping_crud"].remove.return_value = 0
        mock_deps["crud_repo"].soft_remove.return_value = 1
        mock_deps["crud_repo"].find.return_value = []

        result = service.delete(engine_id="e1")
        assert result.success is True
        assert result.data["engine_id"] == "e1"

    @pytest.mark.unit
    def test_delete_empty_id(self, service, mock_deps):
        """engine_id 为空时返回错误"""
        result = service.delete(engine_id="")
        assert result.success is False
        assert "不能为空" in result.error

    @pytest.mark.unit
    def test_delete_exception(self, service, mock_deps):
        """删除过程异常时返回错误"""
        mock_deps["crud_repo"].get_session.return_value = _mock_session()
        mock_deps["crud_repo"].soft_remove.side_effect = Exception("delete err")

        result = service.delete(engine_id="e1")
        assert result.success is False
        assert "delete err" in result.error


# ============================================================
# validate 测试
# ============================================================


class TestValidate:
    """数据验证测试"""

    @pytest.mark.unit
    def test_validate_pass(self, service, mock_deps):
        """有效数据通过验证"""
        result = service.validate(engine_data={"name": "valid-engine"})
        assert result.success is True
        assert "passed" in result.message.lower()

    @pytest.mark.unit
    def test_validate_empty_name(self, service, mock_deps):
        """名称为空时验证失败"""
        result = service.validate(engine_data={"name": ""})
        assert result.success is False
        assert "empty" in result.data["errors"][0].lower() or "不能为空" in result.error

    @pytest.mark.unit
    def test_validate_name_too_long(self, service, mock_deps):
        """名称超长时验证失败"""
        result = service.validate(engine_data={"name": "A" * 51})
        assert result.success is False
        assert result.data["errors"]

    @pytest.mark.unit
    def test_validate_invalid_status(self, service, mock_deps):
        """无效状态值时验证失败"""
        result = service.validate(engine_data={"status": 9999})
        assert result.success is False
        assert "Invalid" in result.data["errors"][0] or "无效" in result.error

    @pytest.mark.unit
    def test_validate_exception(self, service, mock_deps):
        """验证过程异常时返回错误"""
        mock_deps["crud_repo"].find.side_effect = Exception("val err")

        result = service.validate(engine_id="e1")
        assert result.success is False
        assert "val err" in result.error


# ============================================================
# fuzzy_search 测试
# ============================================================


class TestFuzzySearch:
    """模糊搜索测试"""

    @pytest.mark.unit
    def test_fuzzy_search_results(self, service, mock_deps):
        """搜索返回匹配结果"""
        mock_result = MagicMock()
        mock_deps["crud_repo"].fuzzy_search.return_value = mock_result

        result = service.fuzzy_search(query="test")
        assert result.success is True
        assert result.data is mock_result

    @pytest.mark.unit
    def test_fuzzy_search_empty_query(self, service, mock_deps):
        """空查询字符串返回空结果"""
        result = service.fuzzy_search(query="")
        assert result.success is True

    @pytest.mark.unit
    def test_fuzzy_search_exception(self, service, mock_deps):
        """搜索异常时返回错误"""
        mock_deps["crud_repo"].fuzzy_search.side_effect = Exception("search err")

        result = service.fuzzy_search(query="test")
        assert result.success is False
        assert "search err" in result.error
