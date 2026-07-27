"""c1 试点：enum 映射下沉 model 字段 info 反射验证。

验证 ``_conversion._get_enum_mappings`` 默认反射逻辑能从 model 字段
``mapped_column(..., info={'enum': XxxTypes})`` 还原 ``{字段: Enum类}`` 映射，
与原 ``signal_crud._get_enum_mappings`` override 返回值同构。
覆盖 CH(MSignal)路径；direction 为 signal 专属，source 继承自 MClickBase。

Run: pytest tests/unit/data/test_signal_enum_reflection_c1.py -v -o addopts=""
"""

import pytest

from ginkgo.data.models import MSignal
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.data.crud.mixins._conversion import _Conversion


@pytest.mark.unit
class TestSignalEnumReflectionC1:
    """c1：删 signal_crud override 后，反射 model info 须还原完整映射。"""

    def test_direction_info_declared_on_signal(self):
        """direction 字段（signal 专属）声明了 enum 元信息。"""
        col = MSignal.__table__.columns["direction"]
        assert col.info.get("enum") is DIRECTION_TYPES

    def test_source_info_inherited_from_clickbase(self):
        """source 继承自 MClickBase，反射 __table__.columns 含其 info。"""
        col = MSignal.__table__.columns["source"]
        assert col.info.get("enum") is SOURCE_TYPES

    def test_reflection_returns_full_mapping(self):
        """_Conversion._get_enum_mappings 反射 model_class 还原 direction+source。

        stub 仅给 model_class（避免实例化 CRUD 连库）；反射逻辑与
        SignalCRUD（删 override 后继承默认实现）等价。断言与原 override
        ``{'direction': DIRECTION_TYPES, 'source': SOURCE_TYPES}`` 同构。
        """

        class Stub(_Conversion):
            model_class = MSignal

        mappings = Stub()._get_enum_mappings()
        assert mappings == {"direction": DIRECTION_TYPES, "source": SOURCE_TYPES}

    def test_columns_without_info_not_collected(self):
        """无 info 声明的列（如 code/portfolio_id）不进映射——防空列误报。"""

        class Stub(_Conversion):
            model_class = MSignal

        mappings = Stub()._get_enum_mappings()
        assert "code" not in mappings
        assert "portfolio_id" not in mappings

    def test_model_without_table_returns_empty(self):
        """无 __table__ 的 model_class（如 Mongo Pydantic）反射返回 {}，不抛。"""

        class NoTableModel:
            pass

        class Stub(_Conversion):
            model_class = NoTableModel

        assert Stub()._get_enum_mappings() == {}
