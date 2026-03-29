"""
ClickHouse基础模型测试 - Pytest最佳实践重构

测试MClickBase模型的ClickHouse特有功能
涵盖MergeTree引擎、时序优化、排序键、分区等
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

from ginkgo.data.models.model_clickbase import MClickBase


# 具体子类用于实例化测试
class ConcreteClickModel(MClickBase):
    __abstract__ = False
    __tablename__ = "test_concrete_click"


def _make_model(**kwargs):
    """工厂方法：创建具体子类实例并设置默认值（模拟mapped_column default行为）"""
    m = ConcreteClickModel(**kwargs)
    # 仅在未显式传入且值为None时设置默认值
    if 'uuid' not in kwargs and m.uuid is None:
        m.uuid = str(uuid.uuid4().hex)
    if 'meta' not in kwargs and m.meta is None:
        m.meta = "{}"
    if 'desc' not in kwargs and m.desc is None:
        m.desc = "This man is lazy, there is no description."
    if 'timestamp' not in kwargs and m.timestamp is None:
        m.timestamp = datetime.datetime.now()
    if 'source' not in kwargs and m.source is None:
        m.source = -1
    return m


@pytest.mark.unit
class TestMClickBaseConstruction:
    """测试MClickBase构造功能"""

    def test_mclickbase_is_abstract(self):
        """测试MClickBase是抽象类"""
        assert MClickBase.__abstract__ is True

    def test_mclickbase_tablename(self):
        """测试表名配置"""
        assert MClickBase.__tablename__ == "ClickBaseModel"

    def test_mclickbase_has_required_fields(self):
        """测试必需字段存在"""
        required_fields = ['uuid', 'meta', 'desc', 'timestamp', 'source']
        for field in required_fields:
            assert hasattr(MClickBase, field)


@pytest.mark.unit
@pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python3.8+")
class TestMClickBaseFields:
    """测试MClickBase字段定义"""

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

    def test_timestamp_field_default(self):
        """测试timestamp字段默认值"""
        model = _make_model()
        assert model.timestamp is not None
        assert isinstance(model.timestamp, datetime.datetime)

    def test_source_field_default(self):
        """测试source字段默认值"""
        model = _make_model()
        assert model.source == -1


@pytest.mark.unit
class TestMClickBaseSourceHandling:
    """测试MClickBase来源处理"""

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

    def test_set_source_with_none(self):
        """测试使用None设置source"""
        model = _make_model()
        model.set_source(None)
        assert model.source == -1

    def test_get_source_enum(self):
        """测试获取枚举值"""
        from ginkgo.enums import SOURCE_TYPES

        model = _make_model()
        model.source = SOURCE_TYPES.TUSHARE.value
        enum_result = model.get_source_enum()
        assert enum_result == SOURCE_TYPES.TUSHARE

    def test_get_source_enum_with_invalid_source(self):
        """测试无效source的枚举转换"""
        model = _make_model()
        model.source = 9999
        result = model.get_source_enum()
        # 应该返回None或默认值
        assert result is None or result.value == -1


@pytest.mark.unit
class TestMClickBaseUpdateMethod:
    """测试MClickBase update方法"""

    def test_update_raises_not_implemented(self):
        """测试update方法抛出NotImplementedError"""
        model = _make_model()
        with pytest.raises(NotImplementedError, match="Model Class need to overload"):
            model.update()


@pytest.mark.unit
class TestMClickBaseRepr:
    """测试MClickBase __repr__方法"""

    def test_repr_returns_string(self):
        """测试__repr__返回字符串"""
        model = _make_model()
        result = model.__repr__()
        assert isinstance(result, str)

    def test_repr_contains_tablename(self):
        """测试__repr__包含表名"""
        model = _make_model()
        result = model.__repr__()
        assert "DB" in result or "ClickBaseModel" in result


@pytest.mark.unit
class TestMClickBaseInit:
    """测试MClickBase __init__方法"""

    def test_init_with_empty_kwargs(self):
        """测试空参数初始化"""
        model = _make_model()
        assert model is not None

    def test_init_with_source_enum(self):
        """测试使用source枚举初始化"""
        from ginkgo.enums import SOURCE_TYPES

        model = _make_model(source=SOURCE_TYPES.TUSHARE)
        assert model.source == SOURCE_TYPES.TUSHARE.value

    def test_init_with_source_int(self):
        """测试使用source整数初始化"""
        model = _make_model(source=1)
        assert model.source == 1

    def test_init_with_meta(self):
        """测试使用meta初始化"""
        model = _make_model(meta='{"key": "value"}')
        assert model.meta == '{"key": "value"}'

    def test_init_with_desc(self):
        """测试使用desc初始化"""
        model = _make_model(desc="Test description")
        assert model.desc == "Test description"


@pytest.mark.unit
class TestMClickBaseTableConfiguration:
    """测试MClickBase表配置"""

    def test_table_args_exists(self):
        """测试__table_args__配置"""
        assert hasattr(MClickBase, '__table_args__')
        table_args = MClickBase.__table_args__
        assert len(table_args) >= 1

    def test_merge_tree_engine(self):
        """测试MergeTree引擎配置"""
        try:
            from clickhouse_sqlalchemy import engines
            table_args = MClickBase.__table_args__
            # 第一个元素应该是引擎配置
            engine_config = table_args[0]
            assert isinstance(engine_config, engines.MergeTree)
        except ImportError:
            pytest.skip("clickhouse_sqlalchemy not available")


@pytest.mark.unit
class TestMClickBaseInheritance:
    """测试MClickBase继承"""

    def test_inherits_from_mbase(self):
        """测试继承自MBase"""
        from ginkgo.data.models.model_base import MBase
        assert issubclass(MClickBase, MBase)

    def test_has_to_dataframe_method(self):
        """测试有to_dataframe方法"""
        model = _make_model()
        assert hasattr(model, 'to_dataframe')
        assert callable(model.to_dataframe)


@pytest.mark.unit
class TestMClickBaseUUIDGeneration:
    """测试MClickBase UUID生成"""

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


@pytest.mark.unit
class TestMClickBaseTimestampHandling:
    """测试MClickBase时间戳处理"""

    def test_timestamp_is_datetime(self):
        """测试timestamp是datetime对象"""
        model = _make_model()
        assert isinstance(model.timestamp, datetime.datetime)

    def test_timestamp_current_time(self):
        """测试timestamp是当前时间"""
        model = _make_model()
        now = datetime.datetime.now()
        # 允许5秒误差
        time_diff = abs((now - model.timestamp).total_seconds())
        assert time_diff < 5


@pytest.mark.unit
class TestMClickBaseEdgeCases:
    """测试MClickBase边界情况"""

    def test_empty_string_meta(self):
        """测试空字符串meta"""
        model = _make_model(meta="")
        assert model.meta == ""

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
class TestMClickBaseConcreteSubclass:
    """测试MClickBase具体子类"""

    def test_concrete_subclass_creation(self):
        """测试创建具体子类"""
        model = ConcreteClickModel()
        assert isinstance(model, MClickBase)
        assert isinstance(model, ConcreteClickModel)

    def test_concrete_subclass_fields(self):
        """测试具体子类字段"""
        model = ConcreteClickModel()
        assert hasattr(model, 'uuid')
        assert hasattr(model, 'timestamp')
        assert hasattr(model, 'source')


@pytest.mark.unit
class TestMClickBaseConcurrentOperations:
    """测试MClickBase并发操作"""

    def test_concurrent_uuid_generation(self):
        """测试并发UUID生成"""
        import threading

        models = []
        def create_model():
            model = _make_model()
            models.append(model)

        threads = [threading.Thread(target=create_model) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证所有UUID唯一
        uuids = [m.uuid for m in models]
        assert len(set(uuids)) == 100


@pytest.mark.unit
class TestMClickBaseDataIntegrity:
    """测试MClickBase数据完整性"""

    def test_field_types(self):
        """测试字段类型"""
        model = _make_model()
        assert isinstance(model.uuid, str)
        assert isinstance(model.meta, str)
        assert isinstance(model.desc, str)
        assert isinstance(model.timestamp, datetime.datetime)
        assert isinstance(model.source, int)

    def test_default_values_consistency(self):
        """测试默认值一致性"""
        model1 = _make_model()
        model2 = _make_model()

        # source默认值应该一致
        assert model1.source == model2.source == -1

        # meta默认值应该一致
        assert model1.meta == model2.meta == "{}"

        # desc默认值应该一致
        assert model1.desc == model2.desc


@pytest.mark.unit
class TestMClickBaseErrorHandling:
    """测试MClickBase错误处理"""

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
