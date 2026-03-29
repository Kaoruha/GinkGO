"""
数据模型基础测试

测试MClickBase和MMysqlBase基础模型的核心功能
涵盖ID管理、元数据、时间戳、数据转换等
"""
import pytest
import sys
import datetime
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.models.model_base import MBase
from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.enums import SOURCE_TYPES
from tests.unit.data.models.conftest import get_column_default, get_mapped_column, is_column_nullable


@pytest.mark.unit
@pytest.mark.database
class TestModelBaseConstruction:
    """1. 模型基础构造测试"""

    def test_mbase_abstract_class_design(self):
        """测试MBase抽象类设计"""
        # MBase是一个普通类（不是ABC），可以直接实例化用于测试to_dataframe
        m = MBase()
        assert hasattr(m, 'to_dataframe')

    def test_mbase_interface_definition(self):
        """测试MBase接口定义"""
        m = MBase()
        # to_dataframe是其核心接口方法
        assert callable(m.to_dataframe)

    def test_mbase_common_functionality(self):
        """测试MBase通用功能"""
        m = MBase()
        # 设置一些公开属性
        m.name = "test"
        m.value = 42
        m._private = "should_be_excluded"
        df = m.to_dataframe()
        assert 'name' in df.columns
        assert 'value' in df.columns
        assert '_private' not in df.columns


@pytest.mark.unit
@pytest.mark.database
class TestClickBaseModelConstruction:
    """2. ClickBase模型构造测试"""

    def test_mclickbase_table_configuration(self):
        """测试MClickBase表配置"""
        assert MClickBase.__abstract__ is True
        assert MClickBase.__tablename__ == "ClickBaseModel"

    def test_mclickbase_id_system_initialization(self):
        """测试MClickBase ID系统初始化"""
        # MClickBase is abstract, cannot instantiate directly via SQLAlchemy
        # Test that uuid column is defined on the class
        assert hasattr(MClickBase, 'uuid')

    def test_mclickbase_metadata_fields(self):
        """测试MClickBase元数据字段"""
        # Check that metadata fields exist as class-level mapped columns
        assert hasattr(MClickBase, 'meta')
        assert hasattr(MClickBase, 'desc')
        assert hasattr(MClickBase, 'timestamp')
        assert hasattr(MClickBase, 'source')

    def test_mclickbase_default_values(self):
        """测试MClickBase默认值设置"""
        # Check column default values
        assert get_column_default(MClickBase.source) == -1
        assert get_column_default(MClickBase.meta) == "{}"
        assert get_column_default(MClickBase.desc) == "This man is lazy, there is no description."

    def test_mclickbase_abstract_table_inheritance(self):
        """测试MClickBase抽象表继承"""
        assert MClickBase.__abstract__ is True
        # MClickBase inherits from both DeclarativeBase and MBase
        assert hasattr(MClickBase, 'to_dataframe')
        assert hasattr(MClickBase, 'set_source')
        assert hasattr(MClickBase, 'get_source_enum')
        assert hasattr(MClickBase, 'update')


@pytest.mark.unit
@pytest.mark.database
class TestMySQLBaseModelConstruction:
    """3. MySQLBase模型构造测试"""

    def test_mmysqlbase_table_configuration(self):
        """测试MMysqlBase表配置"""
        assert MMysqlBase.__abstract__ is True
        assert MMysqlBase.__tablename__ == "MysqlBaseModel"

    def test_mmysqlbase_id_system_initialization(self):
        """测试MMysqlBase ID系统初始化"""
        assert hasattr(MMysqlBase, 'uuid')

    def test_mmysqlbase_timestamp_management(self):
        """测试MMysqlBase时间戳管理"""
        assert hasattr(MMysqlBase, 'create_at')
        assert hasattr(MMysqlBase, 'update_at')

    def test_mmysqlbase_soft_delete_support(self):
        """测试MMysqlBase软删除支持"""
        assert hasattr(MMysqlBase, 'is_del')
        assert hasattr(MMysqlBase, 'delete')
        assert hasattr(MMysqlBase, 'cancel_delete')

    def test_mmysqlbase_data_type_mapping(self):
        """测试MMysqlBase数据类型映射"""
        # source uses TINYINT type
        assert get_column_default(MMysqlBase.source) == -1
        assert get_column_default(MMysqlBase.is_del) is False


@pytest.mark.unit
@pytest.mark.database
class TestModelUUIDManagement:
    """4. 模型UUID管理测试"""

    def test_uuid_generation_uniqueness(self):
        """测试UUID生成唯一性"""
        # Test the default UUID generator produces unique values
        uuids = set()
        gen = get_column_default(MMysqlBase.uuid)
        for _ in range(100):
            uuids.add(gen(None))  # CallableColumnDefault lambda requires context arg
        assert len(uuids) == 100

    def test_uuid_format_validation(self):
        """测试UUID格式验证"""
        gen = get_column_default(MMysqlBase.uuid)
        result = gen(None)  # CallableColumnDefault lambda requires context arg
        # uuid4().hex produces a 32-character hex string
        assert isinstance(result, str)
        assert len(result) == 32
        # All characters should be hex
        int(result, 16)  # Will raise if not valid hex

    def test_uuid_primary_key_behavior(self):
        """测试UUID主键行为"""
        col = get_mapped_column(MMysqlBase.uuid)
        assert col.primary_key is True

    def test_uuid_indexing_performance(self):
        """测试UUID索引性能"""
        # UUID作为主键自动拥有索引
        col = get_mapped_column(MMysqlBase.uuid)
        assert col.primary_key is True


@pytest.mark.unit
@pytest.mark.database
class TestModelEngineRunIDSystem:
    """5. 模型引擎运行ID系统测试"""

    def test_engine_id_assignment(self):
        """测试引擎ID分配"""
        from ginkgo.data.models.model_backtest_record_base import MBacktestRecordBase
        assert hasattr(MBacktestRecordBase, 'engine_id')
        assert get_column_default(MBacktestRecordBase.engine_id) == ""

    def test_run_id_session_tracking(self):
        """测试运行ID会话跟踪"""
        from ginkgo.data.models.model_backtest_record_base import MBacktestRecordBase
        assert hasattr(MBacktestRecordBase, 'run_id')
        assert get_column_default(MBacktestRecordBase.run_id) == ""

    def test_hierarchical_id_relationship(self):
        """测试层次ID关系"""
        from ginkgo.data.models.model_backtest_record_base import MBacktestRecordBase
        # Both MClickBase and MMysqlBase have uuid
        assert hasattr(MClickBase, 'uuid')
        assert hasattr(MMysqlBase, 'uuid')
        # MBacktestRecordBase adds engine_id and run_id
        assert hasattr(MBacktestRecordBase, 'engine_id')
        assert hasattr(MBacktestRecordBase, 'run_id')

    def test_id_system_querying_optimization(self):
        """测试ID系统查询优化"""
        from ginkgo.data.models.model_backtest_record_base import MBacktestRecordBase
        # engine_id and run_id are String(32) for efficient indexing
        assert get_mapped_column(MBacktestRecordBase.engine_id).type.length == 32
        assert get_mapped_column(MBacktestRecordBase.run_id).type.length == 32


@pytest.mark.unit
@pytest.mark.database
class TestModelSourceEnumHandling:
    """6. 模型来源枚举处理测试"""

    def test_source_enum_conversion(self):
        """测试来源枚举转换"""
        # validate_input accepts enum instances and returns integer
        result = SOURCE_TYPES.validate_input(SOURCE_TYPES.TUSHARE)
        assert result == SOURCE_TYPES.TUSHARE.value

    def test_source_validation_logic(self):
        """测试来源验证逻辑"""
        # Valid integer returns itself
        assert SOURCE_TYPES.validate_input(7) == 7
        # Invalid integer returns None
        assert SOURCE_TYPES.validate_input(999) is None
        # None returns None
        assert SOURCE_TYPES.validate_input(None) is None
        # Invalid type returns None
        assert SOURCE_TYPES.validate_input("invalid") is None

    def test_source_enum_business_logic(self):
        """测试来源枚举业务逻辑"""
        # from_int converts integer back to enum
        result = SOURCE_TYPES.from_int(7)
        assert result == SOURCE_TYPES.TUSHARE
        assert result.value == 7

    def test_source_enum_database_storage(self):
        """测试来源枚举数据库存储"""
        # MClickBase stores source as Int8
        assert get_mapped_column(MClickBase.source).type.__class__.__name__ == 'Int8'
        # MMysqlBase stores source as TINYINT
        assert get_mapped_column(MMysqlBase.source).type.__class__.__name__ == 'TINYINT'


@pytest.mark.unit
@pytest.mark.database
class TestModelMetadataManagement:
    """7. 模型元数据管理测试"""

    def test_meta_field_json_handling(self):
        """测试元数据字段JSON处理"""
        # Default meta is "{}"
        assert get_column_default(MClickBase.meta) == "{}"
        assert get_column_default(MMysqlBase.meta) == "{}"
        # MClickBase uses String (no length limit)
        # MMysqlBase uses String(255)
        assert get_mapped_column(MMysqlBase.meta).type.length == 255

    def test_description_field_management(self):
        """测试描述字段管理"""
        default_desc = "This man is lazy, there is no description."
        assert get_column_default(MClickBase.desc) == default_desc
        assert get_column_default(MMysqlBase.desc) == default_desc

    def test_metadata_validation_rules(self):
        """测试元数据验证规则"""
        # meta and desc are Optional in both bases
        assert is_column_nullable(MMysqlBase, 'meta') is True
        assert is_column_nullable(MMysqlBase, 'desc') is True

    def test_metadata_querying_support(self):
        """测试元数据查询支持"""
        # Both models have meta and desc as mapped columns, enabling querying
        assert hasattr(MClickBase, 'meta')
        assert hasattr(MClickBase, 'desc')
        assert hasattr(MMysqlBase, 'meta')
        assert hasattr(MMysqlBase, 'desc')


@pytest.mark.unit
@pytest.mark.database
class TestModelTimestampHandling:
    """8. 模型时间戳处理测试"""

    def test_timestamp_automatic_generation(self):
        """测试时间戳自动生成"""
        # MClickBase has timestamp, MMysqlBase has create_at/update_at
        assert hasattr(MClickBase, 'timestamp')
        assert hasattr(MMysqlBase, 'create_at')
        assert hasattr(MMysqlBase, 'update_at')
        # All use datetime.datetime.now as default generator
        assert get_column_default(MClickBase.timestamp).__name__ == 'now'
        assert get_column_default(MMysqlBase.create_at).__name__ == 'now'
        assert get_column_default(MMysqlBase.update_at).__name__ == 'now'

    def test_timezone_aware_timestamps(self):
        """测试时区感知时间戳"""
        # MMysqlBase uses timezone=True for DateTime columns
        assert get_mapped_column(MMysqlBase.create_at).type.timezone is True
        assert get_mapped_column(MMysqlBase.update_at).type.timezone is True

    def test_timestamp_update_behavior(self):
        """测试时间戳更新行为"""
        # MMysqlBase has separate create_at and update_at
        # update_at is meant to be updated on modification
        assert hasattr(MMysqlBase, 'create_at')
        assert hasattr(MMysqlBase, 'update_at')
        # MClickBase only has timestamp (append-only, no update)
        assert not hasattr(MClickBase, 'create_at')
        assert not hasattr(MClickBase, 'update_at')

    def test_timestamp_querying_optimization(self):
        """测试时间戳查询优化"""
        # MClickBase __table_args__ uses order_by=("timestamp",)
        table_args = MClickBase.__table_args__
        assert len(table_args) == 2
        engine_spec = table_args[0]
        assert "timestamp" in str(engine_spec.order_by)


@pytest.mark.unit
@pytest.mark.database
class TestModelAbstractMethodImplementation:
    """9. 模型抽象方法实现测试"""

    def test_update_method_abstraction(self):
        """测试update方法抽象"""
        # MClickBase.update raises NotImplementedError
        instance = object.__new__(MClickBase)
        with pytest.raises(NotImplementedError):
            instance.update()
        # MMysqlBase.update also raises NotImplementedError
        instance = object.__new__(MMysqlBase)
        with pytest.raises(NotImplementedError):
            instance.update()

    def test_set_source_method_implementation(self):
        """测试set_source方法实现"""
        # Test with enum instance
        instance = object.__new__(MClickBase)
        instance.source = -1
        instance.set_source(SOURCE_TYPES.TUSHARE)
        assert instance.source == SOURCE_TYPES.TUSHARE.value

    def test_soft_delete_methods_implementation(self):
        """测试软删除方法实现"""
        # MMysqlBase has delete/cancel_delete, MClickBase does not
        assert hasattr(MMysqlBase, 'delete')
        assert hasattr(MMysqlBase, 'cancel_delete')
        assert not hasattr(MClickBase, 'delete')
        assert not hasattr(MClickBase, 'cancel_delete')

    def test_repr_method_customization(self):
        """测试__repr__方法定制"""
        # Both classes define __repr__ using base_repr
        import inspect
        clickbase_repr = inspect.getsource(MClickBase.__repr__)
        assert 'base_repr' in clickbase_repr
        mysqlbase_repr = inspect.getsource(MMysqlBase.__repr__)
        assert 'base_repr' in mysqlbase_repr

    def test_model_inheritance_behavior(self):
        """测试模型继承行为"""
        # MClickBase inherits from both DeclarativeBase and MBase
        assert issubclass(MClickBase, MBase)
        # MMysqlBase inherits from both DeclarativeBase and MBase
        assert issubclass(MMysqlBase, MBase)
        # Both have to_dataframe from MBase
        assert hasattr(MClickBase, 'to_dataframe')
        assert hasattr(MMysqlBase, 'to_dataframe')
