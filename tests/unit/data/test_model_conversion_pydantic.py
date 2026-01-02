# Upstream: MMongoBase Model, ModelConversion
# Downstream: None (单元测试)
# Role: Pydantic模型转换兼容性测试验证to_dataframe/to_entity与现有架构兼容


import pytest
import pandas as pd
from pydantic import BaseModel
from ginkgo.data.models.model_mongobase import MMongoBase
from ginkgo.data.crud.model_conversion import ModelConversion


class TestPydanticModelConversion:
    """Pydantic 模型转换兼容性测试"""

    def test_pydantic_model_dict(self):
        """测试 Pydantic 模型 __dict__ 兼容性"""
        class SimpleModel(BaseModel):
            name: str
            value: int

        model = SimpleModel(name="test", value=42)
        data_dict = model.model_dump()

        assert data_dict == {"name": "test", "value": 42}
        assert isinstance(data_dict, dict)

    def test_pydantic_model_to_dataframe(self):
        """测试 Pydantic 模型 to DataFrame 转换"""
        class SimpleModel(BaseModel):
            name: str
            value: int

        model = SimpleModel(name="test", value=42)
        df = pd.DataFrame([model.model_dump()])

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert df['name'].iloc[0] == "test"
        assert df['value'].iloc[0] == 42

    def test_mmongobase_to_dataframe(self):
        """测试 MMongoBase to_dataframe 方法"""
        class TestDoc(MMongoBase):
            __collection__ = "test_docs"
            name: str = "default"
            value: int = 0

        doc = TestDoc(name="test", value=123)
        df = doc.to_dataframe()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert 'name' in df.columns
        assert 'value' in df.columns
        assert df['name'].iloc[0] == "test"
        assert df['value'].iloc[0] == 123

    def test_mmongobase_model_dump(self):
        """测试 MMongoBase model_dump 方法"""
        class TestDoc(MMongoBase):
            __collection__ = "test_docs"
            name: str = "default"
            value: int = 0

        doc = TestDoc(name="test", value=123)
        data = doc.model_dump()

        assert isinstance(data, dict)
        assert data['name'] == "test"
        assert data['value'] == 123
        assert 'uuid' in data
        assert 'create_at' in data

    def test_mmongobase_from_mongo_roundtrip(self):
        """测试 MMongoBase from_mongo 往返转换"""
        class TestDoc(MMongoBase):
            __collection__ = "test_docs"
            name: str = "default"
            value: int = 0

        # 创建原始文档
        original = TestDoc(name="test", value=123)

        # 转换为 MongoDB 格式
        mongo_data = original.model_dump_for_mongo()

        # 从 MongoDB 数据重建
        restored = TestDoc.from_mongo(mongo_data)

        # 验证关键字段
        assert restored.uuid == original.uuid
        assert restored.name == original.name
        assert restored.value == original.value

    def test_pydantic_list_to_dataframe(self):
        """测试 Pydantic 模型列表转 DataFrame"""
        class SimpleModel(BaseModel):
            name: str
            value: int

        models = [
            SimpleModel(name="test1", value=1),
            SimpleModel(name="test2", value=2),
            SimpleModel(name="test3", value=3),
        ]

        df = pd.DataFrame([m.model_dump() for m in models])

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert df['name'].tolist() == ["test1", "test2", "test3"]
        assert df['value'].tolist() == [1, 2, 3]

    def test_model_conversion_mixin_with_pydantic(self):
        """测试 ModelConversion mixin 与 Pydantic 模型"""
        class TestDoc(MMongoBase, ModelConversion):
            __collection__ = "test_docs"
            name: str = "default"
            value: int = 0

        doc = TestDoc(name="test", value=123)
        df = doc.to_dataframe()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert 'name' in df.columns
        assert 'value' in df.columns


class TestPydanticVsSQLAlchemyCompatibility:
    """Pydantic 与 SQLAlchemy 模型兼容性对比测试"""

    def test_both_models_to_dataframe(self):
        """测试两种模型类型都可以转换为 DataFrame"""
        # Pydantic 模型
        class PydanticModel(BaseModel):
            name: str
            value: int

        pydantic_model = PydanticModel(name="test", value=42)
        df_pydantic = pd.DataFrame([pydantic_model.model_dump()])

        # SQLAlchemy 风格的 __dict__ (模拟)
        class SQLAlchemyLike:
            def __init__(self):
                self.name = "test"
                self.value = 42
                self._sa_instance_state = None  # SQLAlchemy 内部属性

        sa_model = SQLAlchemyLike()
        df_sa = pd.DataFrame([sa_model.__dict__])
        # 移除 SQLAlchemy 内部属性
        if '_sa_instance_state' in df_sa.columns:
            df_sa = df_sa.drop('_sa_instance_state', axis=1)

        # 验证两者的 DataFrame 结构相同
        assert df_pydantic.shape == df_sa.shape
        assert set(df_pydantic.columns) == set(df_sa.columns)
        assert df_pydantic['name'].iloc[0] == df_sa['name'].iloc[0]
        assert df_pydantic['value'].iloc[0] == df_sa['value'].iloc[0]


class TestMMongoBaseDataFrameCompatibility:
    """MMongoBase DataFrame 兼容性测试"""

    def test_dataframe_columns_match_model_fields(self):
        """测试 DataFrame 列与模型字段匹配"""
        class TestDoc(MMongoBase):
            __collection__ = "test_docs"
            name: str = "default"
            value: int = 0

        doc = TestDoc(name="test", value=123)
        df = doc.to_dataframe()

        # 验证基础字段存在
        base_fields = ['uuid', 'meta', 'desc', 'create_at', 'update_at', 'is_del', 'source']
        for field in base_fields:
            assert field in df.columns, f"Missing field: {field}"

        # 验证自定义字段存在
        assert 'name' in df.columns
        assert 'value' in df.columns

    def test_multiple_models_to_dataframe(self):
        """测试多个 MMongoBase 模型转 DataFrame"""
        class TestDoc(MMongoBase):
            __collection__ = "test_docs"
            name: str = "default"
            value: int = 0

        docs = [
            TestDoc(name="test1", value=1),
            TestDoc(name="test2", value=2),
            TestDoc(name="test3", value=3),
        ]

        df = pd.DataFrame([doc.model_dump() for doc in docs])

        assert len(df) == 3
        assert df['name'].tolist() == ["test1", "test2", "test3"]
        assert df['value'].tolist() == [1, 2, 3]
