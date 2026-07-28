# Upstream: c1 试点验证（MOrder/MySQL）
# Downstream: MOrder（MySQL/SA 模型）、_conversion._Conversion（反射钩子）
# Role: 验证删 order_crud._get_enum_mappings override 后，默认反射从 MOrder 字段 info 还原四映射


"""c1 试点(MySQL):MOrder enum 映射下沉 model 字段 info 反射验证。

验证删 ``order_crud._get_enum_mappings`` override 后，默认反射逻辑从
MOrder(MySQL/SA)字段 ``info={'enum': ...}`` 还原与原 override 同构的
``{direction, order_type, status, source}`` 四映射。覆盖 MySQL(MMysqlBase)
路径，与 signal(CH/MClickBase)试点互补，证明 SA info 反射 CH+MySQL 两库通用。
``source`` 继承自 ``MMysqlBase``(MySQL 公共基类)，反射 ``__table__.columns``
含其 info（对称 signal 的 source 继承 MClickBase）。

Run: pytest tests/unit/data/test_order_enum_reflection_c1.py -v -o addopts=""
"""

import pytest

from ginkgo.data.models import MOrder
from ginkgo.enums import (
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    SOURCE_TYPES,
)
from ginkgo.data.crud.mixins._conversion import _Conversion


@pytest.mark.unit
class TestOrderEnumReflectionC1:
    """c1：删 order_crud override 后，反射 MOrder model info 还原完整四映射。"""

    def test_direction_info_declared_on_order(self):
        """direction 字段声明 enum 元信息。"""
        col = MOrder.__table__.columns["direction"]
        assert col.info.get("enum") is DIRECTION_TYPES

    def test_order_type_info_declared_on_order(self):
        """order_type 字段声明 enum 元信息。"""
        col = MOrder.__table__.columns["order_type"]
        assert col.info.get("enum") is ORDER_TYPES

    def test_status_info_declared_on_order(self):
        """status 字段声明 enum 元信息。"""
        col = MOrder.__table__.columns["status"]
        assert col.info.get("enum") is ORDERSTATUS_TYPES

    def test_source_info_inherited_from_mysqlbase(self):
        """source 继承自 MMysqlBase(MySQL 公共基类)，反射 __table__.columns 含其 info。"""
        col = MOrder.__table__.columns["source"]
        assert col.info.get("enum") is SOURCE_TYPES

    def test_reflection_returns_full_mapping(self):
        """_Conversion._get_enum_mappings 反射 MOrder 还原四映射，与原 override 同构。

        stub 仅给 model_class（避免实例化 CRUD 连库）；反射逻辑与
        OrderCRUD（删 override 后继承默认实现）等价。原 override 返回
        ``{'direction': DIRECTION_TYPES, 'order_type': ORDER_TYPES,
        'status': ORDERSTATUS_TYPES, 'source': SOURCE_TYPES}``。
        """

        class Stub(_Conversion):
            model_class = MOrder

        mappings = Stub()._get_enum_mappings()
        assert mappings == {
            "direction": DIRECTION_TYPES,
            "order_type": ORDER_TYPES,
            "status": ORDERSTATUS_TYPES,
            "source": SOURCE_TYPES,
        }

    def test_columns_without_info_not_collected(self):
        """无 info 声明的列不进映射——防空列误报。"""

        class Stub(_Conversion):
            model_class = MOrder

        mappings = Stub()._get_enum_mappings()
        assert "code" not in mappings
        assert "portfolio_id" not in mappings
        assert "volume" not in mappings
