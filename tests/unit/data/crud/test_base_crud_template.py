"""
性能: 218MB RSS, 1.86s, 11 tests [PASS]
BaseCRUD 抽象类单元测试

覆盖范围：
- BaseCRUD: ABC 不可实例化、子类自动注册机制
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from abc import ABC

# ============================================================
# BaseCRUD 抽象类测试
# ============================================================


class TestBaseCRUDAbstract:
    """BaseCRUD 抽象类约束测试"""

    @pytest.mark.unit
    def test_base_crud_is_abc(self):
        """BaseCRUD 继承自 ABC，不能直接实例化"""
        from ginkgo.data.crud.base_crud import BaseCRUD
        assert issubclass(BaseCRUD, ABC)

        # BaseCRUD 有 abstractmethod，即使传入 model_class 也不能实例化
        # 因为它有 @abstractmethod 装饰的方法
        with pytest.raises(TypeError):
            BaseCRUD(MagicMock())

    @pytest.mark.unit
    @patch("ginkgo.data.crud.base_crud.GLOG")
    @patch("ginkgo.data.crud.base_crud.ModelCRUDMapping")
    def test_base_crud_subclass_auto_registration(self, mock_mapping, mock_glog):
        """子类定义 _model_class 后，__init_subclass__ 自动调用 ModelCRUDMapping.register"""
        from ginkgo.data.crud.base_crud import BaseCRUD
        from ginkgo.data.models import MBar

        # 定义一个最小子类，_model_class 指向真实模型
        class MinimalBarCRUD(BaseCRUD[MBar]):
            _model_class = MBar

            def __init__(self):
                # 跳过真实 DB 连接，直接设置属性
                self.model_class = MBar
                self._is_clickhouse = True
                self._is_mysql = False
                self._is_mongo = False

            def _get_field_config(self):
                return {}

            def _get_enum_mappings(self):
                return {}

            def _create_from_params(self, **kwargs):
                return MagicMock()

        # 验证自动注册被调用
        mock_mapping.register.assert_called_once_with(MBar, MinimalBarCRUD)

    @pytest.mark.unit
    @patch("ginkgo.data.crud.base_crud.GLOG")
    def test_base_crud_subclass_without_model_class_raises(self, mock_glog):
        """子类未设置 _model_class 时，__init_subclass__ 抛出 NotImplementedError"""
        from ginkgo.data.crud.base_crud import BaseCRUD

        with pytest.raises(NotImplementedError, match="must override '_model_class'"):
            class BadCRUD(BaseCRUD):
                pass


# ============================================================
# _do_remove 返回值契约测试（issue #6469）
#
# 契约：_do_remove 在 CH / MySQL 两方言下均须返回 int（删除行数）。
# 当前实现 CH 分支执行后丢弃 result、隐式返回 None，与 MySQL 分支
# 的 `return deleted_rows` 不对称——这是 CRUD 方言接缝的契约裂缝。
# ============================================================


@pytest.fixture
def removable_crud_class():
    """构造最小可运行的 BaseCRUD 子类，真继承 _do_remove 实现，供契约测试。

    用 MBar（MClickBase 子类）作 model_class：__init__ 据继承关系自动置
    _is_clickhouse=True。MySQL 路径测试在实例化后手动翻转方言标志。
    """
    from ginkgo.data.crud.base_crud import BaseCRUD
    from ginkgo.data.models import MBar

    # patch ModelCRUDMapping 防子类定义时 __init_subclass__ 注册污染全局映射
    with patch("ginkgo.data.crud.base_crud.ModelCRUDMapping"), \
         patch("ginkgo.data.crud.base_crud.GLOG"):
        class MinimalRemovableCRUD(BaseCRUD[MBar]):
            _model_class = MBar

            def _get_field_config(self):
                return {}

            def _get_enum_mappings(self):
                return {}

            def _create_from_params(self, **kwargs):
                return MagicMock()

        return MinimalRemovableCRUD


class TestDoRemoveReturnContract:
    """_do_remove 在两方言下返回值契约一致：均为 int（删除行数）。"""

    @pytest.mark.unit
    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_do_remove_clickhouse_returns_int_rowcount(self, removable_crud_class):
        """CH 方言：_do_remove 须返回删除行数（int），而非丢弃 result 返 None。"""
        from ginkgo.data.models import MBar
        crud = removable_crud_class(MBar)
        # MBar 继承 MClickBase → __init__ 自动 _is_clickhouse=True
        assert crud._is_clickhouse is True

        mock_session = MagicMock()
        mock_session.execute.return_value = MagicMock(rowcount=5)

        result = crud._do_remove({"code": "000001"}, session=mock_session)

        assert isinstance(result, int), f"CH 路径应返回 int，实际 {type(result)}: {result!r}"
        assert result == 5
        mock_session.execute.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_do_remove_mysql_returns_int_rowcount(self, removable_crud_class):
        """MySQL 方言：_do_remove 须返回删除行数（int），与 CH 路径契约一致。"""
        from ginkgo.data.models import MBar
        crud = removable_crud_class(MBar)
        # 手动翻转方言标志，模拟 MySQL 子类运行时
        crud._is_clickhouse = False
        crud._is_mysql = True

        mock_session = MagicMock()
        mock_session.execute.return_value = MagicMock(rowcount=3)

        result = crud._do_remove({"code": "000001"}, session=mock_session)

        assert isinstance(result, int), f"MySQL 路径应返回 int，实际 {type(result)}: {result!r}"
        assert result == 3
        mock_session.execute.assert_called_once()
