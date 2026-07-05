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

            def _convert_input_item(self, item):
                return None

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
