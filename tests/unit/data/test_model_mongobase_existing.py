# Upstream: MMongoBase Model
# Downstream: None (单元测试)
# Role: MMongoBase单元测试验证模型初始化/枚举处理/序列化功能


import pytest
import datetime
import pandas as pd
from ginkgo.data.models.model_mongobase import MMongoBase
from ginkgo.enums import SOURCE_TYPES


# 测试模型定义
class TestDocument(MMongoBase):
    """测试文档模型"""
    __collection__ = "test_documents"

    name: str = "default_name"
    value: int = 0


class TestMMongoBaseBasics:
    """MMongoBase 基础功能测试"""

    def test_default_constructor(self):
        """测试默认构造函数"""
        doc = TestDocument()
        assert doc.uuid is not None
        assert len(doc.uuid) == 32
        assert doc.meta == "{}"
        assert doc.desc == "This man is lazy, there is no description."
        assert doc.is_del is False
        assert doc.source == -1
        assert doc.name == "default_name"
        assert doc.value == 0

    def test_uuid_generation(self):
        """测试 UUID 自动生成"""
        doc1 = TestDocument()
        doc2 = TestDocument()
        assert doc1.uuid != doc2.uuid
        assert len(doc1.uuid) == 32

    def test_datetime_fields(self):
        """测试日期时间字段"""
        doc = TestDocument()
        assert isinstance(doc.create_at, datetime.datetime)
        assert isinstance(doc.update_at, datetime.datetime)
        # 验证时间是最近的（1秒内）
        now = datetime.datetime.now()
        delta = (now - doc.create_at).total_seconds()
        assert -1 < delta < 1


class TestMMongoBaseFields:
    """MMongoBase 字段操作测试"""

    def test_meta_field(self):
        """测试 meta 字段"""
        doc = TestDocument(meta='{"key": "value"}')
        assert doc.meta == '{"key": "value"}'

    def test_desc_field(self):
        """测试 desc 字段"""
        doc = TestDocument(desc="Test description")
        assert doc.desc == "Test description"

    def test_is_del_field(self):
        """测试 is_del 字段"""
        doc = TestDocument(is_del=True)
        assert doc.is_del is True

    def test_custom_fields(self):
        """测试自定义字段"""
        doc = TestDocument(name="custom_name", value=42)
        assert doc.name == "custom_name"
        assert doc.value == 42


class TestMMongoBaseEnumHandling:
    """MMongoBase 枚举处理测试"""

    def test_get_source_enum_default(self):
        """测试获取默认 source 枚举"""
        doc = TestDocument()
        enum_val = doc.get_source_enum()
        assert enum_val == SOURCE_TYPES.VOID

    def test_set_source_with_enum(self):
        """测试使用枚举设置 source"""
        doc = TestDocument()
        doc.set_source(SOURCE_TYPES.TUSHARE)
        assert doc.source == SOURCE_TYPES.TUSHARE.value

    def test_set_source_with_int(self):
        """测试使用整数设置 source"""
        doc = TestDocument()
        doc.set_source(0)  # TUSHARE
        assert doc.source == 0

    def test_set_source_with_string(self):
        """测试使用字符串设置 source"""
        doc = TestDocument()
        doc.set_source("tushare")
        assert doc.source == SOURCE_TYPES.TUSHARE.value

    def test_set_source_invalid(self):
        """测试无效 source 值处理"""
        doc = TestDocument()
        doc.set_source("invalid_source")
        assert doc.source == -1

    def test_source_validator(self):
        """测试 source 字段验证器"""
        doc = TestDocument(source=SOURCE_TYPES.AKSHARE.value)
        assert doc.source == SOURCE_TYPES.AKSHARE.value


class TestMMongoBaseStateManagement:
    """MMongoBase 状态管理测试"""

    def test_delete(self):
        """测试软删除功能"""
        doc = TestDocument()
        assert doc.is_del is False

        doc.delete()
        assert doc.is_del is True
        # 验证 update_at 被更新
        now = datetime.datetime.now()
        delta = (now - doc.update_at).total_seconds()
        assert -1 < delta < 1

    def test_cancel_delete(self):
        """测试取消软删除功能"""
        doc = TestDocument(is_del=True)
        assert doc.is_del is True

        doc.cancel_delete()
        assert doc.is_del is False

    def test_delete_toggle(self):
        """测试软删除切换"""
        doc = TestDocument()
        assert doc.is_del is False

        doc.delete()
        assert doc.is_del is True

        doc.cancel_delete()
        assert doc.is_del is False


class TestMMongoBasePydanticFeatures:
    """MMongoBase Pydantic 特性测试"""

    def test_model_dump(self):
        """测试 model_dump 方法"""
        doc = TestDocument(name="test", value=123)
        data = doc.model_dump()

        assert isinstance(data, dict)
        assert 'uuid' in data
        assert 'name' in data
        assert 'value' in data
        assert data['name'] == "test"
        assert data['value'] == 123
        assert data['is_del'] is False

    def test_model_dump_exclude_none(self):
        """测试 model_dump 排除 None 值"""
        # 使用 Pydantic 模型可以处理 None
        # 但 value 字段是 int 类型，Pydantic 会拒绝 None
        # 所以我们测试创建后设置 None
        from pydantic import ValidationError

        # Pydantic 2.x 会拒绝 None 对于 int 类型字段
        # 这是预期行为
        with pytest.raises(ValidationError):
            TestDocument(name="test", value=None)

        # 测试排除其他可选的 None 字段
        doc = TestDocument(name="test", value=0)
        data = doc.model_dump(exclude_none=True)

        # 所有字段都在字典中（因为没有 None 值）
        assert 'uuid' in data
        assert 'name' in data
        assert 'value' in data

    def test_model_dump_for_mongo(self):
        """测试 model_dump_for_mongo 方法"""
        doc = TestDocument(name="test")
        data = doc.model_dump_for_mongo()

        assert isinstance(data, dict)
        # 验证 datetime 被转换为字符串
        assert isinstance(data['create_at'], str)
        assert isinstance(data['update_at'], str)

    def test_from_mongo(self):
        """测试 from_mongo 类方法"""
        mongo_data = {
            "uuid": "abc123def456",
            "name": "from_mongo",
            "value": 999,
            "meta": "{}",
            "desc": "test",
            "create_at": datetime.datetime.now().isoformat(),
            "update_at": datetime.datetime.now().isoformat(),
            "is_del": False,
            "source": 0
        }

        doc = TestDocument.from_mongo(mongo_data)
        assert doc.uuid == "abc123def456"
        assert doc.name == "from_mongo"
        assert doc.value == 999
        assert isinstance(doc.create_at, datetime.datetime)


class TestMMongoBaseCollectionName:
    """MMongoBase 集合名称测试"""

    def test_get_collection_name(self):
        """测试获取集合名称"""
        assert TestDocument.get_collection_name() == "test_documents"

    def test_base_collection_name(self):
        """测试基类默认集合名称"""
        assert MMongoBase.get_collection_name() == "mongobase_default"

    def test_collection_name_attribute(self):
        """测试 __collection__ 属性"""
        assert TestDocument.__collection__ == "test_documents"


class TestMMongoBaseRepr:
    """MMongoBase 字符串表示测试"""

    def test_repr(self):
        """测试 __repr__ 方法"""
        doc = TestDocument(name="test")
        repr_str = repr(doc)

        assert "MMongoBase" in repr_str
        assert "test_documents" in repr_str
        assert "is_del=False" in repr_str


class TestMMongoBaseToDataFrame:
    """MMongoBase to_dataframe 功能测试（继承自 MBase）"""

    def test_to_dataframe(self):
        """测试 to_dataframe 方法"""
        doc = TestDocument(name="test", value=42)
        df = doc.to_dataframe()

        assert isinstance(df, pd.DataFrame)
        # 验证包含模型字段
        assert 'uuid' in df.columns
        assert 'name' in df.columns
        assert 'value' in df.columns
        assert df['name'].iloc[0] == "test"
        assert df['value'].iloc[0] == 42

    def test_to_dataframe_with_enum(self):
        """测试 to_dataframe 枚举处理"""
        doc = TestDocument(source=SOURCE_TYPES.TUSHARE.value)
        df = doc.to_dataframe()

        # source 应该是整数值
        assert df['source'].iloc[0] == SOURCE_TYPES.TUSHARE.value


class TestMMongoBaseUpdate:
    """MMongoBase update 方法测试"""

    def test_update_not_implemented(self):
        """测试基类 update 方法抛出异常"""
        doc = TestDocument()

        with pytest.raises(NotImplementedError):
            doc.update("some_data")

    def test_update_with_series(self, monkeypatch):
        """测试使用 pd.Series 更新（子类实现）"""
        # 这个测试需要子类实现 update 方法
        # 这里只验证基类行为
        doc = TestDocument()

        # 基类应该抛出 NotImplementedError
        series_data = pd.Series({'name': 'updated_name'})
        with pytest.raises(NotImplementedError):
            doc.update(series_data)


@pytest.mark.parametrize("source_input,expected_value", [
    (SOURCE_TYPES.TUSHARE, SOURCE_TYPES.TUSHARE.value),
    (SOURCE_TYPES.TUSHARE.value, SOURCE_TYPES.TUSHARE.value),
    ("tushare", SOURCE_TYPES.TUSHARE.value),
    (0, 0),
    (-1, -1),
    ("invalid", -1),
    (None, -1),
])
def test_set_source_various_inputs(source_input, expected_value):
    """参数化测试：各种 source 输入"""
    doc = TestDocument()
    doc.set_source(source_input)
    assert doc.source == expected_value
