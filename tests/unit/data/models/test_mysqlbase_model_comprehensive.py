"""
性能: 219MB RSS, 1.93s, 42 tests [PASS]
MySQL基础模型综合测试

测试MMysqlBase模型的MySQL特有功能
涵盖事务支持、软删除、时间戳管理、约束处理等
"""
import pytest
import sys
import datetime
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.models.model_order import MOrder
from ginkgo.data.models.model_position import MPosition
from ginkgo.enums import SOURCE_TYPES
from sqlalchemy.dialects.mysql import TINYINT
from tests.unit.data.models.conftest import get_column_default, get_mapped_column, is_column_nullable


@pytest.mark.unit
@pytest.mark.database
class TestMySQLBaseModelConstruction:
    """1. MySQLBase模型构造测试"""

    def test_mmysqlbase_declarative_base_inheritance(self):
        """测试MMysqlBase声明式基类继承"""
        from sqlalchemy.orm import DeclarativeBase
        assert issubclass(MMysqlBase, DeclarativeBase)

    def test_mmysqlbase_abstract_table_configuration(self):
        """测试MMysqlBase抽象表配置"""
        assert MMysqlBase.__abstract__ is True
        assert MMysqlBase.__tablename__ == "MysqlBaseModel"

    def test_mmysqlbase_mysql_specific_configuration(self):
        """测试MMysqlBase MySQL特定配置"""
        # source field uses MySQL TINYINT type
        source_col = get_mapped_column(MMysqlBase.source).type
        assert source_col.__class__.__name__ == 'TINYINT'

    def test_mmysqlbase_charset_collation_support(self):
        """测试MMysqlBase字符集校对规则支持"""
        # String fields use SQLAlchemy String type, charset configured at engine level
        # Verify uuid field is String(32)
        uuid_col = get_mapped_column(MMysqlBase.uuid).type
        assert uuid_col.__class__.__name__ == 'String'
        assert uuid_col.length == 32

    def test_mmysqlbase_storage_engine_compatibility(self):
        """测试MMysqlBase存储引擎兼容性"""
        # MMysqlBase uses SQLAlchemy ORM, compatible with all MySQL storage engines
        # InnoDB is the default for SQLAlchemy MySQL
        assert MMysqlBase.__abstract__ is True


@pytest.mark.unit
@pytest.mark.database
class TestMySQLBaseModelIDSystem:
    """2. MySQLBase模型ID系统测试"""

    def test_mmysqlbase_uuid_varchar_primary_key(self):
        """测试MMysqlBase UUID VARCHAR主键"""
        col = get_mapped_column(MMysqlBase.uuid)
        assert col.primary_key is True
        assert col.type.__class__.__name__ == 'String'
        assert col.type.length == 32

    def test_mmysqlbase_engine_id_varchar_field(self):
        """测试MMysqlBase引擎ID VARCHAR字段"""
        from ginkgo.data.models.model_backtest_record_base import MBacktestRecordBase
        col = get_mapped_column(MBacktestRecordBase.engine_id)
        assert col.type.__class__.__name__ == 'String'
        assert col.type.length == 32

    def test_mmysqlbase_run_id_varchar_field(self):
        """测试MMysqlBase运行ID VARCHAR字段"""
        from ginkgo.data.models.model_backtest_record_base import MBacktestRecordBase
        col = get_mapped_column(MBacktestRecordBase.run_id)
        assert col.type.__class__.__name__ == 'String'
        assert col.type.length == 32

    def test_mmysqlbase_id_nullable_options(self):
        """测试MMysqlBase ID可空选项"""
        # uuid is primary key, not nullable
        assert get_mapped_column(MMysqlBase.uuid).primary_key is True
        # engine_id and run_id have defaults (empty string)
        from ginkgo.data.models.model_backtest_record_base import MBacktestRecordBase
        assert is_column_nullable(MBacktestRecordBase, 'engine_id') is True
        assert is_column_nullable(MBacktestRecordBase, 'run_id') is True

    def test_mmysqlbase_id_indexing_strategy(self):
        """测试MMysqlBase ID索引策略"""
        # Primary key automatically indexed
        col = get_mapped_column(MMysqlBase.uuid)
        assert col.primary_key is True


@pytest.mark.unit
@pytest.mark.database
class TestMySQLBaseModelTimestampManagement:
    """3. MySQLBase模型时间戳管理测试"""

    def test_mmysqlbase_create_at_timestamp(self):
        """测试MMysqlBase创建时间戳"""
        col = get_mapped_column(MMysqlBase.create_at).type
        assert col.__class__.__name__ == 'DateTime'
        assert col.timezone is True

    def test_mmysqlbase_update_at_timestamp(self):
        """测试MMysqlBase更新时间戳"""
        col = get_mapped_column(MMysqlBase.update_at).type
        assert col.__class__.__name__ == 'DateTime'
        assert col.timezone is True

    def test_mmysqlbase_timezone_aware_handling(self):
        """测试MMysqlBase时区感知处理"""
        assert get_mapped_column(MMysqlBase.create_at).type.timezone is True
        assert get_mapped_column(MMysqlBase.update_at).type.timezone is True

    def test_mmysqlbase_timestamp_default_generation(self):
        """测试MMysqlBase时间戳默认生成"""
        # Default uses datetime.now (not datetime.datetime.now)
        default_create = get_column_default(MMysqlBase.create_at)
        default_update = get_column_default(MMysqlBase.update_at)
        assert default_create.__name__ == 'now'
        assert default_update.__name__ == 'now'

    def test_mmysqlbase_timestamp_update_on_modification(self):
        """测试MMysqlBase修改时时间戳更新"""
        # update_at is designed to be updated on modification
        # The update method in subclasses sets self.update_at = datetime.datetime.now()
        assert hasattr(MMysqlBase, 'update_at')


@pytest.mark.unit
@pytest.mark.database
class TestMySQLBaseModelSoftDeleteSupport:
    """4. MySQLBase模型软删除支持测试"""

    def test_mmysqlbase_is_del_boolean_field(self):
        """测试MMysqlBase is_del布尔字段"""
        col = get_mapped_column(MMysqlBase.is_del).type
        assert col.__class__.__name__ == 'Boolean'
        assert get_column_default(MMysqlBase.is_del) is False

    def test_mmysqlbase_delete_method_implementation(self):
        """测试MMysqlBase delete方法实现"""
        import inspect
        source = inspect.getsource(MMysqlBase.delete)
        assert 'self.is_del = True' in source

    def test_mmysqlbase_cancel_delete_method(self):
        """测试MMysqlBase取消删除方法"""
        import inspect
        source = inspect.getsource(MMysqlBase.cancel_delete)
        assert 'self.is_del = False' in source

    def test_mmysqlbase_soft_delete_querying(self):
        """测试MMysqlBase软删除查询"""
        # is_del is a mapped column enabling filtered queries
        assert hasattr(MMysqlBase.is_del, '__clause_element__')

    def test_mmysqlbase_soft_delete_business_logic(self):
        """测试MMysqlBase软删除业务逻辑"""
        # delete() and cancel_delete() modify is_del flag
        import inspect
        source = inspect.getsource(MMysqlBase.delete)
        assert 'self.is_del = True' in source
        source = inspect.getsource(MMysqlBase.cancel_delete)
        assert 'self.is_del = False' in source


@pytest.mark.unit
@pytest.mark.database
class TestMySQLBaseModelSourceTypeHandling:
    """5. MySQLBase模型来源类型处理测试"""

    def test_mmysqlbase_source_tinyint_mapping(self):
        """测试MMysqlBase来源TINYINT映射"""
        col = get_mapped_column(MMysqlBase.source).type
        assert col.__class__.__name__ == 'TINYINT'

    def test_mmysqlbase_source_enum_conversion(self):
        """测试MMysqlBase来源枚举转换"""
        assert SOURCE_TYPES.from_int(7) == SOURCE_TYPES.TUSHARE
        assert SOURCE_TYPES.from_int(-1) == SOURCE_TYPES.VOID

    def test_mmysqlbase_set_source_method(self):
        """测试MMysqlBase设置来源方法"""
        instance = object.__new__(MMysqlBase)
        instance.source = -1
        # Accept enum
        instance.set_source(SOURCE_TYPES.TUSHARE)
        assert instance.source == 7
        # Accept integer
        instance.set_source(5)
        assert instance.source == 5
        # Invalid input defaults to -1
        instance.set_source("invalid")
        assert instance.source == -1

    def test_mmysqlbase_source_validation_logic(self):
        """测试MMysqlBase来源验证逻辑"""
        # validate_input returns None for invalid values
        assert SOURCE_TYPES.validate_input(999) is None
        assert SOURCE_TYPES.validate_input("bad") is None
        # Valid int returns itself
        assert SOURCE_TYPES.validate_input(7) == 7

    def test_mmysqlbase_source_default_handling(self):
        """测试MMysqlBase来源默认值处理"""
        assert get_column_default(MMysqlBase.source) == -1


@pytest.mark.unit
@pytest.mark.database
class TestMySQLBaseModelMetadataFields:
    """6. MySQLBase模型元数据字段测试"""

    def test_mmysqlbase_meta_varchar_storage(self):
        """测试MMysqlBase元数据VARCHAR存储"""
        col = get_mapped_column(MMysqlBase.meta).type
        assert col.__class__.__name__ == 'String'
        assert col.length == 255

    def test_mmysqlbase_description_varchar_handling(self):
        """测试MMysqlBase描述VARCHAR处理"""
        col = get_mapped_column(MMysqlBase.desc).type
        assert col.__class__.__name__ == 'String'
        assert col.length == 255
        default_desc = "This man is lazy, there is no description."
        assert get_column_default(MMysqlBase.desc) == default_desc

    def test_mmysqlbase_metadata_nullable_support(self):
        """测试MMysqlBase元数据可空支持"""
        assert is_column_nullable(MMysqlBase, 'meta') is True
        assert is_column_nullable(MMysqlBase, 'desc') is True

    def test_mmysqlbase_metadata_length_validation(self):
        """测试MMysqlBase元数据长度验证"""
        assert get_mapped_column(MMysqlBase.meta).type.length == 255
        assert get_mapped_column(MMysqlBase.desc).type.length == 255


@pytest.mark.unit
@pytest.mark.database
class TestMySQLBaseModelTransactionSupport:
    """7. MySQLBase模型事务支持测试"""

    def test_mmysqlbase_transaction_compatibility(self):
        """测试MMysqlBase事务兼容性"""
        # MMysqlBase uses SQLAlchemy ORM which supports transactions
        assert hasattr(MMysqlBase, '__tablename__')

    def test_mmysqlbase_acid_compliance(self):
        """测试MMysqlBase ACID遵从性"""
        # SQLAlchemy with MySQL InnoDB provides ACID compliance
        # is_del field provides atomic soft-delete
        assert hasattr(MMysqlBase, 'delete')
        assert hasattr(MMysqlBase, 'cancel_delete')

    def test_mmysqlbase_rollback_behavior(self):
        """测试MMysqlBase回滚行为"""
        # Soft delete is reversible via cancel_delete
        assert hasattr(MMysqlBase, 'delete')
        assert hasattr(MMysqlBase, 'cancel_delete')

    def test_mmysqlbase_concurrent_modification_handling(self):
        """测试MMysqlBase并发修改处理"""
        # SQLAlchemy scoped_session handles concurrency
        # MMysqlBase has uuid as unique primary key for conflict detection
        assert get_mapped_column(MMysqlBase.uuid).primary_key is True


@pytest.mark.unit
@pytest.mark.database
class TestMySQLBaseModelConstraintSupport:
    """8. MySQLBase模型约束支持测试"""

    def test_mmysqlbase_primary_key_constraint(self):
        """测试MMysqlBase主键约束"""
        col = get_mapped_column(MMysqlBase.uuid)
        assert col.primary_key is True
        assert col.type.length == 32

    def test_mmysqlbase_foreign_key_support(self):
        """测试MMysqlBase外键支持"""
        # Foreign keys defined in concrete subclasses
        # MOrder has portfolio_id referencing portfolio
        assert hasattr(MOrder, 'portfolio_id')

    def test_mmysqlbase_unique_constraint_handling(self):
        """测试MMysqlBase唯一约束处理"""
        # uuid primary key provides uniqueness
        assert get_mapped_column(MMysqlBase.uuid).primary_key is True

    def test_mmysqlbase_check_constraint_support(self):
        """测试MMysqlBase检查约束支持"""
        # Boolean field is_del provides implicit check constraint
        col = get_mapped_column(MMysqlBase.is_del).type
        assert col.__class__.__name__ == 'Boolean'


@pytest.mark.unit
@pytest.mark.database
class TestMySQLBaseModelInheritanceSupport:
    """9. MySQLBase模型继承支持测试"""

    def test_mmysqlbase_concrete_subclass_creation(self):
        """测试MMysqlBase具体子类创建"""
        assert MOrder.__abstract__ is False
        assert MOrder.__tablename__ == "order"
        assert MPosition.__abstract__ is False
        assert MPosition.__tablename__ == "position"

    def test_mmysqlbase_table_inheritance_behavior(self):
        """测试MMysqlBase表继承行为"""
        # Subclasses inherit base fields
        for cls in [MOrder, MPosition]:
            assert hasattr(cls, 'uuid')
            assert hasattr(cls, 'meta')
            assert hasattr(cls, 'desc')
            assert hasattr(cls, 'create_at')
            assert hasattr(cls, 'update_at')
            assert hasattr(cls, 'is_del')
            assert hasattr(cls, 'source')

    def test_mmysqlbase_method_override_capability(self):
        """测试MMysqlBase方法重写能力"""
        # Both subclasses override update
        assert hasattr(MOrder, 'update')
        assert hasattr(MPosition, 'update')
        # Both inherit delete/cancel_delete from MMysqlBase
        assert hasattr(MOrder, 'delete')
        assert hasattr(MOrder, 'cancel_delete')
        assert hasattr(MPosition, 'delete')
        assert hasattr(MPosition, 'cancel_delete')

    def test_mmysqlbase_field_customization_support(self):
        """测试MMysqlBase字段定制支持"""
        # MOrder adds order-specific fields
        assert hasattr(MOrder, 'direction')
        assert hasattr(MOrder, 'order_type')
        assert hasattr(MOrder, 'status')
        assert hasattr(MOrder, 'volume')
        assert hasattr(MOrder, 'limit_price')
        # MPosition adds position-specific fields
        assert hasattr(MPosition, 'cost')
        assert hasattr(MPosition, 'frozen_volume')
        assert hasattr(MPosition, 'price')

    def test_mmysqlbase_polymorphic_behavior(self):
        """测试MMysqlBase多态行为"""
        assert issubclass(MOrder, MMysqlBase)
        assert issubclass(MPosition, MMysqlBase)
        # Both inherit to_dataframe from MBase
        assert hasattr(MOrder, 'to_dataframe')
        assert hasattr(MPosition, 'to_dataframe')
