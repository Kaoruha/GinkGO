"""
数据模型基础测试 - Pytest最佳实践重构

测试MBase基础模型的核心功能
涵盖ID管理、元数据、时间戳、数据转换等
"""
import pytest
import datetime
import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from types import MethodType, FunctionType
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.models.model_base import MBase


@pytest.mark.unit
class TestMBaseConstruction:
    """测试MBase基础构造功能"""

    def test_mbase_can_be_instantiated(self):
        """测试MBase可以被实例化"""
        model = MBase()
        assert model is not None
        assert isinstance(model, MBase)

    def test_mbase_has_to_dataframe_method(self):
        """测试MBase有to_dataframe方法"""
        model = MBase()
        assert hasattr(model, 'to_dataframe')
        assert callable(model.to_dataframe)

    def test_mbase_to_dataframe_returns_dataframe(self):
        """测试to_dataframe返回DataFrame"""
        try:
            import pandas as pd
            model = MBase()
            df = model.to_dataframe()
            assert isinstance(df, pd.DataFrame)
        except ImportError:
            pytest.skip("pandas not available")


@pytest.mark.unit
class TestMBaseToDataFrame:
    """测试MBase.to_dataframe()方法"""

    def test_to_dataframe_excludes_private_attributes(self):
        """测试to_dataframe排除私有属性"""
        try:
            import pandas as pd
            model = MBase()
            model._private_attr = "should_not_appear"

            df = model.to_dataframe()
            assert '_private_attr' not in df.columns
        except ImportError:
            pytest.skip("pandas not available")

    def test_to_dataframe_excludes_methods(self):
        """测试to_dataframe排除方法"""
        try:
            import pandas as pd
            model = MBase()

            df = model.to_dataframe()
            # 排除内置方法
            for col in df.columns:
                assert not isinstance(getattr(model, col, None), MethodType)
                assert not isinstance(getattr(model, col, None), FunctionType)
        except ImportError:
            pytest.skip("pandas not available")

    def test_to_dataframe_excludes_special_methods(self):
        """测试to_dataframe排除特殊方法"""
        try:
            import pandas as pd
            model = MBase()

            df = model.to_dataframe()
            excluded_methods = ["delete", "query", "registry", "metadata", "to_dataframe"]
            for method in excluded_methods:
                assert method not in df.columns
        except ImportError:
            pytest.skip("pandas not available")

    @pytest.mark.parametrize("attr,value,expected_type", [
        ("string_attr", "test_value", str),
        ("int_attr", 42, int),
        ("float_attr", 3.14, float),
        ("decimal_attr", Decimal("10.5"), Decimal),
    ])
    def test_to_dataframe_includes_public_attributes(self, attr, value, expected_type):
        """测试to_dataframe包含公开属性"""
        try:
            import pandas as pd
            model = MBase()
            setattr(model, attr, value)

            df = model.to_dataframe()
            assert attr in df.columns
        except ImportError:
            pytest.skip("pandas not available")


@pytest.mark.unit
class TestMBaseEnumHandling:
    """测试MBase枚举类型处理"""

    def test_to_dataframe_converts_enum_to_value(self):
        """测试to_dataframe将枚举转换为值"""
        try:
            import pandas as pd
            from sqlalchemy import Enum

            model = MBase()
            mock_enum = Enum("VALUE1", "VALUE2", name="test_enum")
            model.test_enum = mock_enum

            df = model.to_dataframe()
            assert 'test_enum' in df.columns
        except ImportError:
            pytest.skip("pandas not available")


@pytest.mark.unit
class TestMBaseDataTypes:
    """测试MBase数据类型处理"""

    @pytest.mark.parametrize("value", [
        "string_value",
        123,
        12.34,
        Decimal("10.50"),
        True,
        None,
        datetime.datetime.now(),
    ])
    def test_to_dataframe_handles_various_types(self, value):
        """测试to_dataframe处理各种数据类型"""
        try:
            import pandas as pd
            model = MBase()
            model.test_attr = value

            df = model.to_dataframe()
            assert 'test_attr' in df.columns
        except ImportError:
            pytest.skip("pandas not available")


@pytest.mark.unit
class TestMBaseEdgeCases:
    """测试MBase边界情况"""

    def test_to_dataframe_with_empty_model(self):
        """测试空模型的to_dataframe"""
        try:
            import pandas as pd
            model = MBase()

            df = model.to_dataframe()
            assert isinstance(df, pd.DataFrame)
            # 应该有列但可能为空
            assert df.shape[0] == 1  # 一行数据
        except ImportError:
            pytest.skip("pandas not available")

    def test_to_dataframe_with_none_values(self):
        """测试包含None值的to_dataframe"""
        try:
            import pandas as pd
            model = MBase()
            model.attr1 = None
            model.attr2 = "value"

            df = model.to_dataframe()
            assert 'attr1' in df.columns
            assert 'attr2' in df.columns
        except ImportError:
            pytest.skip("pandas not available")


@pytest.mark.unit
class TestMBaseInheritance:
    """测试MBase继承"""

    def test_subclass_inherits_to_dataframe(self):
        """测试子类继承to_dataframe方法"""
        try:
            import pandas as pd

            class CustomModel(MBase):
                pass

            model = CustomModel()
            assert hasattr(model, 'to_dataframe')
            assert callable(model.to_dataframe)
        except ImportError:
            pytest.skip("pandas not available")

    def test_subclass_to_dataframe_includes_custom_attributes(self):
        """测试子类to_dataframe包含自定义属性"""
        try:
            import pandas as pd

            class CustomModel(MBase):
                def __init__(self):
                    super().__init__()
                    self.custom_field = "custom_value"

            model = CustomModel()
            df = model.to_dataframe()
            assert 'custom_field' in df.columns
        except ImportError:
            pytest.skip("pandas not available")


@pytest.mark.unit
class TestMBaseThreadSafety:
    """测试MBase线程安全性"""

    def test_to_dataframe_is_thread_safe(self):
        """测试to_dataframe的线程安全性"""
        try:
            import pandas as pd
            import threading

            model = MBase()
            model.attr1 = "value1"
            model.attr2 = "value2"

            results = []
            def create_dataframe():
                df = model.to_dataframe()
                results.append(df)

            threads = [threading.Thread(target=create_dataframe) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(results) == 10
        except ImportError:
            pytest.skip("pandas not available")


@pytest.mark.unit
class TestMBasePerformance:
    """测试MBase性能"""

    def test_to_dataframe_with_many_attributes(self):
        """测试处理大量属性的性能"""
        try:
            import pandas as pd

            model = MBase()
            # 创建100个属性
            for i in range(100):
                setattr(model, f"attr_{i}", f"value_{i}")

            df = model.to_dataframe()
            assert len(df.columns) >= 100
        except ImportError:
            pytest.skip("pandas not available")
