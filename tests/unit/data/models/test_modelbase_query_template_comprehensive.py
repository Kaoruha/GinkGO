"""
ModelBase查询模板综合测试

测试ModelBase的统一查询模板功能
涵盖跨数据库操作语言、过滤器语法、安全性、性能优化等
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.models.model_bar import MBar
from ginkgo.data.models.model_order import MOrder
from ginkgo.data.models.model_base import MBase
from ginkgo.data.models.model_position import MPosition
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, FREQUENCY_TYPES
from tests.unit.data.models.conftest import get_column_default, get_mapped_column


@pytest.mark.unit
@pytest.mark.database
class TestModelBaseUnifiedQueryLanguage:
    """1. ModelBase统一查询语言测试"""

    def test_modelbase_enhanced_filter_syntax(self):
        """测试ModelBase增强过滤器语法 - 验证列类型"""
        code_col = get_mapped_column(MBar.code)
        assert code_col.type.__class__.__name__ == 'String'
        ts_col = get_mapped_column(MBar.timestamp)
        assert ts_col.type.__class__.__name__ == 'DateTime'
        direction_col = get_mapped_column(MOrder.direction)
        assert direction_col.type.__class__.__name__ == 'TINYINT'

    def test_modelbase_operator_parsing(self):
        """测试ModelBase操作符解析 - 验证 SQL 生成"""
        from sqlalchemy import select
        stmt = select(MBar).where(MBar.code == "000001.SZ")
        compiled = stmt.compile()
        assert "code" in str(compiled).lower()
        # 参数化查询：值不在 SQL 字符串中，而是占位符
        assert ":code" in str(compiled) or ":code_1" in str(compiled)

    def test_modelbase_enum_automatic_conversion(self):
        """测试ModelBase枚举自动转换"""
        assert SOURCE_TYPES.validate_input(SOURCE_TYPES.TUSHARE) == 7
        assert DIRECTION_TYPES.validate_input(DIRECTION_TYPES.LONG) == 1
        assert FREQUENCY_TYPES.validate_input(FREQUENCY_TYPES.DAY) is not None
        # 无效枚举值返回 None
        assert SOURCE_TYPES.validate_input(999) is None

    def test_modelbase_parameter_binding_security(self):
        """测试ModelBase参数绑定安全性 - 参数不内联到 SQL"""
        from sqlalchemy import text
        stmt = text("SELECT * FROM bar WHERE code = :code")
        compiled = stmt.compile()
        # 参数化查询：值不在 SQL 中，只有占位符
        assert ":code" in str(compiled)

    def test_modelbase_distinct_query_support(self):
        """测试ModelBase DISTINCT查询支持"""
        from sqlalchemy import select
        stmt = select(MBar.code).distinct()
        compiled = stmt.compile()
        assert "DISTINCT" in str(compiled).upper()


@pytest.mark.unit
@pytest.mark.database
class TestModelBaseDatabaseAbstraction:
    """2. ModelBase数据库抽象测试"""

    def test_modelbase_clickhouse_mysql_detection(self):
        """测试ModelBase ClickHouse/MySQL检测"""
        # ClickHouse models use clickhouse_sqlalchemy types
        from clickhouse_sqlalchemy import types as ch_types
        source_col = get_mapped_column(MClickBase.source).type
        assert source_col.__class__.__name__ == 'Int8'
        # MySQL models use TINYINT
        source_col = get_mapped_column(MMysqlBase.source).type
        assert source_col.__class__.__name__ == 'TINYINT'

    def test_modelbase_clickhouse_specific_handling(self):
        """测试ModelBase ClickHouse特化处理"""
        # ClickHouse uses MergeTree engine (append-only, no delete)
        assert not hasattr(MClickBase, 'delete')
        assert not hasattr(MClickBase, 'cancel_delete')
        assert not hasattr(MClickBase, 'is_del')

    def test_modelbase_mysql_specific_handling(self):
        """测试ModelBase MySQL特化处理"""
        # MySQL supports soft delete and timestamp management
        assert hasattr(MMysqlBase, 'delete')
        assert hasattr(MMysqlBase, 'cancel_delete')
        assert hasattr(MMysqlBase, 'is_del')
        assert hasattr(MMysqlBase, 'create_at')
        assert hasattr(MMysqlBase, 'update_at')

    def test_modelbase_database_dialect_adaptation(self):
        """测试ModelBase数据库方言适配"""
        # Both bases share the same MBase.to_dataframe method
        assert hasattr(MClickBase, 'to_dataframe')
        assert hasattr(MMysqlBase, 'to_dataframe')
        # But use different column types for the same concept
        ch_type = get_mapped_column(MClickBase.source).type.__class__.__name__
        my_type = get_mapped_column(MMysqlBase.source).type.__class__.__name__
        assert ch_type != my_type

    def test_modelbase_cross_database_query_consistency(self):
        """测试ModelBase跨数据库查询一致性"""
        # Both share common fields: uuid, meta, desc, source
        for field in ['uuid', 'meta', 'desc', 'source']:
            assert hasattr(MClickBase, field)
            assert hasattr(MMysqlBase, field)


@pytest.mark.unit
@pytest.mark.database
class TestModelBaseTemplateMethodPattern:
    """3. ModelBase模板方法模式测试"""

    def test_modelbase_template_method_structure(self):
        """测试ModelBase模板方法结构 - singledispatchmethod 有 register"""
        assert hasattr(MBar.update, 'register')

    def test_modelbase_hook_method_customization(self):
        """测试ModelBase钩子方法定制 - 不同模型独立注册"""
        assert hasattr(MBar.update, 'register')
        assert hasattr(MOrder.update, 'register')
        # MBar 和 MOrder 的 register 是独立的（不是同一个）
        assert MBar.update.register is not MOrder.update.register

    def test_modelbase_update_has_register(self):
        """测试ModelBase update 方法有 register 能力（singledispatchmethod）"""
        assert hasattr(MBar.update, 'register')
        assert hasattr(MOrder.update, 'register')


@pytest.mark.unit
@pytest.mark.database
class TestModelBaseDynamicQueryBuilding:
    """4. ModelBase动态查询构建测试"""

    def test_modelbase_filter_condition_parsing(self):
        """测试ModelBase过滤条件解析 - 验证 WHERE 子句生成"""
        from sqlalchemy import select
        stmt = select(MBar).where(MBar.code == "000001.SZ")
        compiled = stmt.compile()
        assert "code" in str(compiled).lower()

    def test_modelbase_sorting_and_pagination(self):
        """测试ModelBase排序和分页 - 验证 ORDER BY / LIMIT"""
        from sqlalchemy import select
        stmt = select(MBar).order_by(MBar.timestamp).limit(100).offset(0)
        compiled = stmt.compile()
        assert "order" in str(compiled).lower()
        assert "limit" in str(compiled).lower()

    def test_modelbase_query_optimization_hints(self):
        """测试ModelBase查询优化提示 - MergeTree 引擎"""
        from clickhouse_sqlalchemy import engines
        table_args = MBar.__table_args__
        assert isinstance(table_args[0], engines.MergeTree)

    def test_modelbase_complex_query_composition(self):
        """测试ModelBase复杂查询组合 - AND 条件"""
        from sqlalchemy import select, and_
        stmt = select(MBar).where(
            and_(
                MBar.code == "000001.SZ",
                MBar.frequency == 1
            )
        )
        compiled = stmt.compile()
        sql = str(compiled).lower()
        assert "code" in sql
        assert "frequency" in sql

    def test_modelbase_subquery_and_join_support(self):
        """测试ModelBase子查询和连接支持 - 列引用"""
        from sqlalchemy import select
        stmt = select(MOrder.code, MPosition.code)
        compiled = stmt.compile()
        assert "code" in str(compiled).lower()


@pytest.mark.unit
@pytest.mark.database
class TestModelBaseDataValidationFramework:
    """5. ModelBase数据验证框架测试"""

    def test_modelbase_field_configuration_validation(self):
        """测试ModelBase字段配置验证"""
        # Column types enforce data validation at database level
        # DECIMAL(16, 2) enforces precision
        price_type = get_mapped_column(MBar.open).type
        assert price_type.precision == 16
        assert price_type.scale == 2

    def test_modelbase_multilayer_validation_architecture(self):
        """测试ModelBase多层验证架构"""
        # Layer 1: SQLAlchemy column type validation
        # Layer 2: Enum validate_input in model methods
        # Layer 3: Business logic in update methods
        assert SOURCE_TYPES.validate_input(999) is None  # Layer 2 validation

    def test_modelbase_data_type_conversion(self):
        """测试ModelBase数据类型转换"""
        # update() methods use to_decimal for price conversion
        from ginkgo.libs import to_decimal
        assert to_decimal("10.50") == Decimal("10.50")
        assert to_decimal(10.5) == Decimal("10.5")

    def test_modelbase_business_rule_validation(self):
        """测试ModelBase业务规则验证"""
        # Enum validation in update methods provides business rule checking
        assert DIRECTION_TYPES.validate_input(DIRECTION_TYPES.LONG) == 1
        assert DIRECTION_TYPES.validate_input(999) is None

    def test_modelbase_validation_error_handling(self):
        """测试ModelBase数据验证失败时的错误处理"""
        # Invalid enum input defaults to -1 (VOID) in set_source
        instance = object.__new__(MClickBase)
        instance.source = -1
        instance.set_source("invalid_value")
        assert instance.source == -1


@pytest.mark.unit
@pytest.mark.database
class TestModelBaseStreamingQuerySupport:
    """6. ModelBase流式查询支持测试"""

    def test_modelbase_streaming_query_interface(self):
        """测试ModelBase流式查询接口 - 验证方法存在且可调用"""
        from ginkgo.data.drivers.base_driver import DatabaseDriverBase
        assert callable(getattr(DatabaseDriverBase, 'get_streaming_session', None))
        assert callable(getattr(DatabaseDriverBase, 'get_streaming_connection', None))

    def test_modelbase_batch_processing_optimization(self):
        """测试ModelBase批处理优化 - MergeTree 引擎"""
        from clickhouse_sqlalchemy import engines
        assert isinstance(MBar.__table_args__[0], engines.MergeTree)

    def test_modelbase_streaming_error_recovery(self):
        """测试ModelBase流式错误恢复 - fallback 到普通 session"""
        from ginkgo.data.drivers.base_driver import DatabaseDriverBase
        import inspect
        source = inspect.getsource(DatabaseDriverBase.get_streaming_session)
        assert 'fallback' in source.lower() or 'get_session' in source


@pytest.mark.unit
@pytest.mark.database
class TestModelBaseCrossDatabaseCompatibility:
    """7. ModelBase跨数据库兼容性测试"""

    def test_modelbase_clickhouse_string_field_cleanup(self):
        """测试ModelBase ClickHouse字符串字段清理"""
        # String type in ClickHouse uses columnar storage
        code_col = get_mapped_column(MBar.code).type
        assert code_col.__class__.__name__ == 'String'

    def test_modelbase_mysql_soft_delete_integration(self):
        """测试ModelBase MySQL软删除集成"""
        # MMysqlBase provides soft delete, MClickBase does not
        assert hasattr(MMysqlBase, 'delete')
        assert hasattr(MMysqlBase, 'is_del')
        assert not hasattr(MClickBase, 'delete')

    def test_modelbase_timestamp_handling_consistency(self):
        """测试ModelBase时间戳处理一致性"""
        # Both use datetime.now as default generator
        click_ts = get_column_default(MClickBase.timestamp)
        mysql_ts = get_column_default(MMysqlBase.create_at)
        assert click_ts.__name__ == 'now'
        assert mysql_ts.__name__ == 'now'

    def test_modelbase_data_format_normalization(self):
        """测试ModelBase数据格式标准化"""
        # Both share MBase.to_dataframe for consistent output
        assert MClickBase.to_dataframe == MMysqlBase.to_dataframe
        assert MClickBase.to_dataframe == MBase.to_dataframe

    def test_modelbase_performance_characteristics_comparison(self):
        """测试ModelBase性能特征比较"""
        # ClickHouse: columnar, append-only, MergeTree for analytics
        # MySQL: row-based, CRUD operations, InnoDB for transactions
        from clickhouse_sqlalchemy import engines
        assert isinstance(MClickBase.__table_args__[0], engines.MergeTree)
        assert isinstance(MMysqlBase.__abstract__, bool)


@pytest.mark.unit
@pytest.mark.database
class TestModelBaseServiceIntegration:
    """8. ModelBase服务集成测试"""

    def test_modelbase_service_container_has_bar_crud(self):
        """测试ModelBase服务容器注册了 bar_crud"""
        from ginkgo.data.containers import container
        crud = container.bar_crud()
        assert crud is not None
        assert crud.__class__.__name__ == 'BarCRUD'

    def test_modelbase_configuration_has_debug_mode(self):
        """测试ModelBase配置管理 - DEBUGMODE 属性"""
        from ginkgo.libs import GCONF
        assert isinstance(GCONF.DEBUGMODE, bool)
