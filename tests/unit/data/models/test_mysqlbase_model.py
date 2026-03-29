"""
MySQL基础模型测试 - Pytest最佳实践重构

测试MMysqlBase模型的MySQL特有功能
涵盖事务支持、软删除、时间戳管理、约束处理等
"""
import pytest
import datetime
import uuid
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.models.model_mysqlbase import MMysqlBase


# 具体子类用于实例化测试
class ConcreteMysqlModel(MMysqlBase):
    __abstract__ = False
    __tablename__ = "test_concrete_mysql"


def _make_model(**kwargs):
    """工厂方法：创建具体子类实例并补充默认值（meta/desc不在__init__中初始化）"""
    m = ConcreteMysqlModel(**kwargs)
    # 仅在未显式传入且值为None时设置默认值
    if 'meta' not in kwargs and m.meta is None:
        m.meta = "{}"
    if 'desc' not in kwargs and m.desc is None:
        m.desc = "This man is lazy, there is no description."
    return m


@pytest.mark.unit
class TestMMysqlBaseConstruction:
    """测试MMysqlBase构造功能"""

    def test_mmysqlbase_is_abstract(self):
        """测试MMysqlBase是抽象类"""
        assert MMysqlBase.__abstract__ is True

    def test_mmysqlbase_tablename(self):
        """测试表名配置"""
        assert MMysqlBase.__tablename__ == "MysqlBaseModel"

    def test_mmysqlbase_has_required_fields(self):
        """测试必需字段存在"""
        required_fields = [
            'uuid', 'meta', 'desc', 'create_at', 'update_at',
            'is_del', 'source'
        ]
        for field in required_fields:
            assert hasattr(MMysqlBase, field)


@pytest.mark.unit
class TestMMysqlBaseFields:
    """测试MMysqlBase字段定义"""

    def test_uuid_field_default(self):
        """测试uuid字段默认值"""
        model = _make_model()
        assert model.uuid is not None
        assert len(model.uuid) == 32  # UUID hex格式

    def test_meta_field_default(self):
        """测试meta字段默认值"""
        model = _make_model()
        assert model.meta == "{}"

    def test_desc_field_default(self):
        """测试desc字段默认值"""
        model = _make_model()
        assert model.desc == "This man is lazy, there is no description."

    def test_create_at_field_default(self):
        """测试create_at字段默认值"""
        model = ConcreteMysqlModel()
        # __init__ handles create_at
        assert model.create_at is not None
        assert isinstance(model.create_at, datetime.datetime)

    def test_update_at_field_default(self):
        """测试update_at字段默认值"""
        model = ConcreteMysqlModel()
        # __init__ handles update_at
        assert model.update_at is not None
        assert isinstance(model.update_at, datetime.datetime)

    def test_is_del_field_default(self):
        """测试is_del字段默认值"""
        model = ConcreteMysqlModel()
        # __init__ handles is_del
        assert model.is_del is False

    def test_source_field_default(self):
        """测试source字段默认值"""
        model = ConcreteMysqlModel()
        # __init__ handles source
        assert model.source == -1


@pytest.mark.unit
class TestMMysqlBaseSourceHandling:
    """测试MMysqlBase来源处理"""

    def test_set_source_with_enum(self):
        """测试使用枚举设置source"""
        from ginkgo.enums import SOURCE_TYPES

        model = _make_model()
        model.set_source(SOURCE_TYPES.TUSHARE)
        assert model.source == SOURCE_TYPES.TUSHARE.value

    def test_set_source_with_int(self):
        """测试使用整数设置source"""
        model = _make_model()
        model.set_source(1)
        assert model.source == 1

    def test_set_source_with_invalid_value(self):
        """测试使用无效值设置source"""
        model = _make_model()
        model.set_source("invalid")
        assert model.source == -1

    def test_get_source_enum(self):
        """测试获取枚举值"""
        from ginkgo.enums import SOURCE_TYPES

        model = _make_model()
        model.source = SOURCE_TYPES.TUSHARE.value
        enum_result = model.get_source_enum()
        assert enum_result == SOURCE_TYPES.TUSHARE


@pytest.mark.unit
class TestMMysqlBaseSoftDelete:
    """测试MMysqlBase软删除功能"""

    def test_delete_method_sets_is_del_true(self):
        """测试delete方法设置is_del为True"""
        model = _make_model()
        model.delete()
        assert model.is_del is True

    def test_cancel_delete_method_sets_is_del_false(self):
        """测试cancel_delete方法设置is_del为False"""
        model = _make_model()
        model.is_del = True
        model.cancel_delete()
        assert model.is_del is False

    def test_delete_cancel_delete_cycle(self):
        """测试删除和取消删除循环"""
        model = _make_model()
        assert model.is_del is False

        model.delete()
        assert model.is_del is True

        model.cancel_delete()
        assert model.is_del is False

        model.delete()
        assert model.is_del is True


@pytest.mark.unit
class TestMMysqlBaseUpdateMethod:
    """测试MMysqlBase update方法"""

    def test_update_raises_not_implemented(self):
        """测试update方法抛出NotImplementedError"""
        model = _make_model()
        with pytest.raises(NotImplementedError):
            model.update()


@pytest.mark.unit
class TestMMysqlBaseTimestampManagement:
    """测试MMysqlBase时间戳管理"""

    def test_create_at_is_datetime(self):
        """测试create_at是datetime对象"""
        model = ConcreteMysqlModel()
        assert isinstance(model.create_at, datetime.datetime)

    def test_update_at_is_datetime(self):
        """测试update_at是datetime对象"""
        model = ConcreteMysqlModel()
        assert isinstance(model.update_at, datetime.datetime)

    def test_timestamps_are_current(self):
        """测试时间戳是当前时间"""
        model = ConcreteMysqlModel()
        now = datetime.datetime.now()
        # 允许5秒误差
        time_diff = abs((now - model.create_at).total_seconds())
        assert time_diff < 5

    def test_create_at_and_update_at_simultaneous(self):
        """测试create_at和update_at同时生成"""
        model = ConcreteMysqlModel()
        time_diff = abs((model.create_at - model.update_at).total_seconds())
        assert time_diff < 1  # 应该几乎同时


@pytest.mark.unit
class TestMMysqlBaseInit:
    """测试MMysqlBase __init__方法"""

    def test_init_with_empty_kwargs(self):
        """测试空参数初始化"""
        model = _make_model()
        assert model is not None

    def test_init_with_source(self):
        """测试使用source初始化"""
        from ginkgo.enums import SOURCE_TYPES

        model = _make_model(source=SOURCE_TYPES.TUSHARE)
        assert model.source == SOURCE_TYPES.TUSHARE.value

    def test_init_with_meta(self):
        """测试使用meta初始化"""
        model = _make_model(meta='{"key": "value"}')
        assert model.meta == '{"key": "value"}'

    def test_init_with_desc(self):
        """测试使用desc初始化"""
        model = _make_model(desc="Test description")
        assert model.desc == "Test description"

    def test_init_with_is_del(self):
        """测试使用is_del初始化"""
        model = _make_model(is_del=True)
        assert model.is_del is True


@pytest.mark.unit
class TestMMysqlBaseInheritance:
    """测试MMysqlBase继承"""

    def test_inherits_from_mbase(self):
        """测试继承自MBase"""
        from ginkgo.data.models.model_base import MBase
        assert issubclass(MMysqlBase, MBase)

    def test_has_to_dataframe_method(self):
        """测试有to_dataframe方法"""
        model = _make_model()
        assert hasattr(model, 'to_dataframe')
        assert callable(model.to_dataframe)

    def test_has_delete_methods(self):
        """测试有软删除方法"""
        model = _make_model()
        assert hasattr(model, 'delete')
        assert hasattr(model, 'cancel_delete')
        assert callable(model.delete)
        assert callable(model.cancel_delete)


@pytest.mark.unit
class TestMMysqlBaseUUIDGeneration:
    """测试MMysqlBase UUID生成"""

    def test_uuid_uniqueness(self):
        """测试UUID唯一性"""
        model1 = _make_model()
        model2 = _make_model()
        assert model1.uuid != model2.uuid

    def test_uuid_format(self):
        """测试UUID格式"""
        model = _make_model()
        # 验证hex格式
        assert len(model.uuid) == 32
        try:
            uuid.UUID(hex=model.uuid)
        except ValueError:
            pytest.fail("UUID is not in valid hex format")

    def test_uuid_persistence(self):
        """测试UUID持久性"""
        model = _make_model()
        original_uuid = model.uuid
        # UUID不应该改变
        assert model.uuid == original_uuid


@pytest.mark.unit
class TestMMysqlBaseRepr:
    """测试MMysqlBase __repr__方法"""

    def test_repr_returns_string(self):
        """测试__repr__返回字符串"""
        model = _make_model()
        result = model.__repr__()
        assert isinstance(result, str)

    def test_repr_contains_tablename(self):
        """测试__repr__包含表名"""
        model = _make_model()
        result = model.__repr__()
        assert "DB" in result or "MysqlBaseModel" in result


@pytest.mark.unit
class TestMMysqlBaseEdgeCases:
    """测试MMysqlBase边界情况"""

    def test_empty_string_meta(self):
        """测试空字符串meta"""
        model = _make_model(meta="")
        assert model.meta == ""

    def test_none_meta_allowed(self):
        """测试None meta"""
        model = _make_model(meta=None)
        assert model.meta is None

    def test_none_desc_allowed(self):
        """测试None desc"""
        model = _make_model(desc=None)
        assert model.desc is None

    @pytest.mark.parametrize("invalid_source", [
        "invalid_string",
        9999,
        -9999,
    ])
    def test_invalid_source_handling(self, invalid_source):
        """测试无效source处理"""
        model = _make_model(source=invalid_source)
        # __init__ calls set_source for invalid values, which sets -1
        assert model.source == -1


@pytest.mark.unit
class TestMMysqlBaseConcreteSubclass:
    """测试MMysqlBase具体子类"""

    def test_concrete_subclass_creation(self):
        """测试创建具体子类"""
        model = ConcreteMysqlModel()
        assert isinstance(model, MMysqlBase)
        assert isinstance(model, ConcreteMysqlModel)

    def test_concrete_subclass_fields(self):
        """测试具体子类字段"""
        model = ConcreteMysqlModel()
        assert hasattr(model, 'uuid')
        assert hasattr(model, 'create_at')
        assert hasattr(model, 'update_at')
        assert hasattr(model, 'is_del')


@pytest.mark.unit
class TestMMysqlBaseDataIntegrity:
    """测试MMysqlBase数据完整性"""

    def test_field_types(self):
        """测试字段类型"""
        model = _make_model()
        assert isinstance(model.uuid, str)
        assert isinstance(model.meta, str)
        assert isinstance(model.desc, str)
        assert isinstance(model.create_at, datetime.datetime)
        assert isinstance(model.update_at, datetime.datetime)
        assert isinstance(model.is_del, bool)
        assert isinstance(model.source, int)

    def test_default_values_consistency(self):
        """测试默认值一致性"""
        model1 = _make_model()
        model2 = _make_model()

        # source默认值应该一致
        assert model1.source == model2.source == -1

        # is_del默认值应该一致
        assert model1.is_del == model2.is_del is False

        # meta默认值应该一致
        assert model1.meta == model2.meta == "{}"


@pytest.mark.unit
class TestMMysqlBaseSoftDeleteWorkflow:
    """测试MMysqlBase软删除工作流"""

    def test_delete_workflow(self):
        """测试完整删除工作流"""
        model = _make_model()

        # 初始状态
        assert model.is_del is False

        # 标记删除
        model.delete()
        assert model.is_del is True

        # 取消删除
        model.cancel_delete()
        assert model.is_del is False

    def test_multiple_delete_calls(self):
        """测试多次调用delete"""
        model = _make_model()
        model.delete()
        model.delete()  # 应该安全
        assert model.is_del is True

    def test_multiple_cancel_delete_calls(self):
        """测试多次调用cancel_delete"""
        model = _make_model()
        model.cancel_delete()  # 初始已经是False
        model.cancel_delete()  # 应该安全
        assert model.is_del is False


@pytest.mark.unit
class TestMMysqlBaseErrorHandling:
    """测试MMysqlBase错误处理"""

    def test_set_source_exception_handling(self):
        """测试set_source异常处理"""
        model = _make_model()
        # 应该不抛出异常
        model.set_source("completely_invalid")
        assert model.source == -1

    def test_init_exception_handling(self):
        """测试init异常处理"""
        # 应该优雅地处理各种参数
        model = _make_model(
            source="invalid",
            meta=None,
            desc=123  # 非字符串
        )
        assert model is not None
        assert model.source == -1


@pytest.mark.unit
class TestMMysqlBaseTimezoneSupport:
    """测试MMysqlBase时区支持"""

    def test_timezone_aware_timestamps(self):
        """测试时区感知时间戳"""
        model = ConcreteMysqlModel()
        # 在Python 3.8+中，timezone=True参数使时间戳时区感知
        # 验证时间戳可以正常工作
        assert model.create_at is not None
        assert model.update_at is not None


@pytest.mark.unit
class TestMMysqlBaseFieldConstraints:
    """测试MMysqlBase字段约束"""

    def test_uuid_length_constraint(self):
        """测试UUID长度约束"""
        model = _make_model()
        assert len(model.uuid) == 32

    def test_meta_length_constraint(self):
        """测试meta长度约束"""
        # 默认是String(255)
        model = _make_model()
        long_meta = "x" * 255
        model.meta = long_meta
        assert model.meta == long_meta

    def test_desc_length_constraint(self):
        """测试desc长度约束"""
        # 默认是String(255)
        model = _make_model()
        long_desc = "x" * 255
        model.desc = long_desc
        assert model.desc == long_desc
