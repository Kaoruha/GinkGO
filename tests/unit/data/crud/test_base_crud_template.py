"""
性能: 218MB RSS, 1.86s, 11 tests [PASS]
CRUDResult 包装器 + BaseCRUD 抽象类单元测试

覆盖范围：
- CRUDResult: 空结果、有数据结果、filter/map、迭代、索引、__repr__
- BaseCRUD: ABC 不可实例化、子类自动注册机制
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from abc import ABC

from ginkgo.data.crud.base_crud import CRUDResult


# ============================================================
# CRUDResult 测试
# ============================================================


class TestCRUDResult:
    """CRUDResult 查询结果包装器测试"""

    @pytest.mark.unit
    def test_crud_result_empty_models(self):
        """空结果：count=0, is_empty=True, first()=None, bool=False"""
        crud_instance = MagicMock()
        result = CRUDResult([], crud_instance)

        assert result.count() == 0
        assert result.is_empty() is True
        assert result.first() is None
        assert bool(result) is False
        assert len(result) == 0

    @pytest.mark.unit
    def test_crud_result_with_models(self):
        """有数据结果：count、first、__len__、__bool__ 正常工作"""
        crud_instance = MagicMock()

        mock_model_a = MagicMock(name="ModelA")
        mock_model_b = MagicMock(name="ModelB")
        mock_model_c = MagicMock(name="ModelC")
        models = [mock_model_a, mock_model_b, mock_model_c]

        result = CRUDResult(models, crud_instance)

        assert result.count() == 3
        assert result.first() is mock_model_a
        assert len(result) == 3
        assert bool(result) is True

    @pytest.mark.unit
    def test_crud_result_filter(self):
        """filter 方法：按条件过滤模型列表"""
        crud_instance = MagicMock()

        model_a = MagicMock()
        model_a.value = 1
        model_b = MagicMock()
        model_b.value = 5
        model_c = MagicMock()
        model_c.value = 10
        models = [model_a, model_b, model_c]

        result = CRUDResult(models, crud_instance)

        # 过滤 value > 3 的模型
        filtered = result.filter(lambda m: m.value > 3)

        assert filtered.count() == 2
        assert model_b in filtered
        assert model_c in filtered
        assert model_a not in filtered
        # filter 返回新 CRUDResult，原始不受影响
        assert result.count() == 3

    @pytest.mark.unit
    def test_crud_result_map(self):
        """map 方法：对每个模型应用映射函数"""
        crud_instance = MagicMock()

        model_a = MagicMock()
        model_a.code = "000001.SZ"
        model_b = MagicMock()
        model_b.code = "000002.SZ"
        models = [model_a, model_b]

        result = CRUDResult(models, crud_instance)

        codes = result.map(lambda m: m.code)
        assert codes == ["000001.SZ", "000002.SZ"]

    @pytest.mark.unit
    def test_crud_result_iteration(self):
        """支持 for 循环迭代"""
        crud_instance = MagicMock()

        models = [MagicMock(name=f"M{i}") for i in range(3)]
        result = CRUDResult(models, crud_instance)

        collected = []
        for model in result:
            collected.append(model)

        assert collected == models

    @pytest.mark.unit
    def test_crud_result_indexing(self):
        """支持索引访问 __getitem__"""
        crud_instance = MagicMock()

        model_a = MagicMock(name="M0")
        model_b = MagicMock(name="M1")
        model_c = MagicMock(name="M2")
        models = [model_a, model_b, model_c]

        result = CRUDResult(models, crud_instance)

        assert result[0] is model_a
        assert result[1] is model_b
        assert result[-1] is model_c

    @pytest.mark.unit
    def test_crud_result_repr(self):
        """__repr__ 返回包含 count 和模型类型名称的字符串"""
        crud_instance = MagicMock()

        # 有数据
        model = MagicMock()
        model.__class__.__name__ = "MBar"
        result = CRUDResult([model], crud_instance)
        r = repr(result)
        assert "count=1" in r
        assert "MBar" in r

        # 空结果
        empty = CRUDResult([], crud_instance)
        r_empty = repr(empty)
        assert "count=0" in r_empty
        assert "No models" in r_empty

    @pytest.mark.unit
    def test_crud_result_to_business_objects_caching(self):
        """to_business_objects 调用 crud_instance 的转换方法并缓存结果"""
        crud_instance = MagicMock()
        models = [MagicMock(), MagicMock()]
        result = CRUDResult(models, crud_instance)

        # 第一次调用
        business = result.to_business_objects()
        assert crud_instance._convert_to_business_objects.call_count == 1
        crud_instance._convert_to_business_objects.assert_called_once_with(models)

        # 第二次调用应该使用缓存
        business2 = result.to_business_objects()
        assert crud_instance._convert_to_business_objects.call_count == 1
        assert business is business2


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
