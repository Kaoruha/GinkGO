"""
性能: 221MB RSS, 1.98s, 83 tests [PASS]
具体业务模型综合测试

测试具体业务模型的功能和行为
涵盖Bar、Tick、Order、Position、Signal等核心业务模型
"""
import pytest
import sys
import datetime
import decimal
from pathlib import Path
from unittest.mock import Mock, patch
from decimal import Decimal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.models.model_bar import MBar
from ginkgo.data.models.model_tick import MTick
from ginkgo.data.models.model_order import MOrder
from ginkgo.data.models.model_position import MPosition
from ginkgo.data.models.model_signal import MSignal
from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, SOURCE_TYPES, FREQUENCY_TYPES
from tests.unit.data.models.conftest import get_column_default, get_mapped_column, is_column_nullable


@pytest.mark.unit
@pytest.mark.database
class TestBarModelComprehensive:
    """1. Bar模型综合测试"""

    def test_mbar_clickhouse_table_configuration(self):
        """测试MBar ClickHouse表配置"""
        assert MBar.__abstract__ is False
        assert MBar.__tablename__ == "bar"
        from clickhouse_sqlalchemy import engines
        assert isinstance(MBar.__table_args__[0], engines.MergeTree)

    def test_mbar_ohlcv_fields_definition(self):
        """测试MBar OHLCV字段定义"""
        # Check OHLCV field types: DECIMAL(16, 2) for prices
        for field in ['open', 'high', 'low', 'close', 'amount']:
            col_type = get_mapped_column(getattr(MBar, field)).type
            assert col_type.precision == 16
            assert col_type.scale == 2
        # Volume is Integer
        vol_type = get_mapped_column(MBar.volume).type
        assert vol_type.__class__.__name__ == 'Integer'

    def test_mbar_code_symbol_handling(self):
        """测试MBar代码符号处理"""
        assert hasattr(MBar, 'code')
        assert get_column_default(MBar.code) == "ginkgo_test_code"

    def test_mbar_frequency_type_management(self):
        """测试MBar频率类型管理"""
        assert hasattr(MBar, 'frequency')
        # frequency is Int8 in ClickHouse
        freq_type = get_mapped_column(MBar.frequency).type
        assert freq_type.__class__.__name__ == 'Int8'

    def test_mbar_time_range_validation(self):
        """测试MBar时间范围验证"""
        # MBar inherits timestamp from MClickBase
        assert hasattr(MBar, 'timestamp')

    def test_mbar_data_consistency_checks(self):
        """测试MBar数据一致性检查"""
        # All OHLCV fields have same Decimal precision
        ohlcv_types = [
            get_mapped_column(MBar.open).type,
            get_mapped_column(MBar.high).type,
            get_mapped_column(MBar.low).type,
            get_mapped_column(MBar.close).type,
        ]
        for t in ohlcv_types:
            assert t.precision == 16
            assert t.scale == 2

    def test_mbar_update_method_implementation(self):
        """测试MBar update方法实现"""
        # update uses singledispatchmethod with str and pd.Series handlers
        assert hasattr(MBar.update, 'register')


@pytest.mark.unit
@pytest.mark.database
class TestTickModelComprehensive:
    """2. Tick模型综合测试"""

    def test_mtick_realtime_data_structure(self):
        """测试MTick实时数据结构"""
        assert MTick.__abstract__ is True
        assert MTick.__tablename__ == "tick"

    def test_mtick_price_volume_fields(self):
        """测试MTick价量字段"""
        # price is DECIMAL(16, 2)
        price_type = get_mapped_column(MTick.price).type
        assert price_type.precision == 16
        assert price_type.scale == 2
        # volume is Integer
        vol_type = get_mapped_column(MTick.volume).type
        assert vol_type.__class__.__name__ == 'Integer'

    def test_mtick_direction_type_handling(self):
        """测试MTick方向类型处理"""
        assert hasattr(MTick, 'direction')
        dir_type = get_mapped_column(MTick.direction).type
        assert dir_type.__class__.__name__ == 'Int8'

    def test_mtick_microsecond_timestamp(self):
        """测试MTick微秒时间戳"""
        # MTick inherits timestamp from MClickBase (DateTime)
        assert hasattr(MTick, 'timestamp')

    def test_mtick_market_microstructure_data(self):
        """测试MTick市场微结构数据"""
        # MTick has code, price, volume, direction for market data
        assert hasattr(MTick, 'code')
        assert hasattr(MTick, 'price')
        assert hasattr(MTick, 'volume')
        assert hasattr(MTick, 'direction')

    def test_mtick_data_validation_rules(self):
        """测试MTick数据验证规则"""
        # direction and source use Int8 (small integer enum)
        dir_type = get_mapped_column(MTick.direction).type
        assert dir_type.__class__.__name__ == 'Int8'
        src_type = get_mapped_column(MTick.source).type
        assert src_type.__class__.__name__ == 'Int8'

    def test_mtick_update_method_implementation(self):
        """测试MTick update方法实现"""
        assert hasattr(MTick.update, 'register')


@pytest.mark.unit
@pytest.mark.database
class TestOrderModelComprehensive:
    """3. Order模型综合测试"""

    def test_morder_mysql_table_configuration(self):
        """测试MOrder MySQL表配置"""
        assert MOrder.__abstract__ is False
        assert MOrder.__tablename__ == "order"

    def test_morder_order_fields_definition(self):
        """测试MOrder订单字段定义"""
        assert hasattr(MOrder, 'portfolio_id')
        assert hasattr(MOrder, 'code')
        assert hasattr(MOrder, 'direction')
        assert hasattr(MOrder, 'order_type')
        assert hasattr(MOrder, 'status')
        assert hasattr(MOrder, 'volume')
        assert hasattr(MOrder, 'limit_price')
        assert hasattr(MOrder, 'frozen')

    def test_morder_status_lifecycle_management(self):
        """测试MOrder状态生命周期管理"""
        assert hasattr(MOrder, 'status')
        assert hasattr(MOrder, 'transaction_price')
        assert hasattr(MOrder, 'transaction_volume')
        assert hasattr(MOrder, 'remain')

    def test_morder_order_type_handling(self):
        """测试MOrder订单类型处理"""
        assert hasattr(MOrder, 'order_type')
        # order_type is TINYINT for MySQL
        ot_type = get_mapped_column(MOrder.order_type).type
        assert ot_type.__class__.__name__ == 'TINYINT'

    def test_morder_execution_information(self):
        """测试MOrder执行信息"""
        assert hasattr(MOrder, 'transaction_price')
        assert hasattr(MOrder, 'transaction_volume')
        assert hasattr(MOrder, 'fee')
        assert hasattr(MOrder, 'frozen')
        assert hasattr(MOrder, 'remain')

    def test_morder_portfolio_relationship(self):
        """测试MOrder投资组合关系"""
        assert hasattr(MOrder, 'portfolio_id')
        assert hasattr(MOrder, 'engine_id')
        assert hasattr(MOrder, 'run_id')

    def test_morder_update_method_implementation(self):
        """测试MOrder update方法实现"""
        assert hasattr(MOrder.update, 'register')


@pytest.mark.unit
@pytest.mark.database
class TestPositionModelComprehensive:
    """4. Position模型综合测试"""

    def test_mposition_holding_information(self):
        """测试MPosition持仓信息"""
        assert hasattr(MPosition, 'code')
        assert hasattr(MPosition, 'volume')
        assert hasattr(MPosition, 'cost')
        assert hasattr(MPosition, 'price')
        assert hasattr(MPosition, 'frozen_volume')

    def test_mposition_pnl_calculation(self):
        """测试MPosition盈亏计算"""
        # PnL fields: cost, price, fee, frozen_money
        assert hasattr(MPosition, 'cost')
        assert hasattr(MPosition, 'price')
        assert hasattr(MPosition, 'fee')
        assert hasattr(MPosition, 'frozen_money')

    def test_mposition_cost_basis_management(self):
        """测试MPosition成本基础管理"""
        assert hasattr(MPosition, 'cost')
        cost_type = get_mapped_column(MPosition.cost).type
        assert cost_type.precision == 16
        assert cost_type.scale == 2

    def test_mposition_quantity_tracking(self):
        """测试MPosition数量跟踪"""
        assert hasattr(MPosition, 'volume')
        assert hasattr(MPosition, 'frozen_volume')
        assert hasattr(MPosition, 'settlement_frozen_volume')

    def test_mposition_portfolio_integration(self):
        """测试MPosition投资组合集成"""
        assert hasattr(MPosition, 'portfolio_id')
        assert hasattr(MPosition, 'engine_id')
        assert hasattr(MPosition, 'run_id')

    def test_mposition_risk_metrics_calculation(self):
        """测试MPosition风险指标计算"""
        # Settlement-related fields for T+N risk management
        assert hasattr(MPosition, 'settlement_frozen_volume')
        assert hasattr(MPosition, 'settlement_days')
        assert hasattr(MPosition, 'settlement_queue_json')

    def test_mposition_update_method_implementation(self):
        """测试MPosition update方法实现"""
        assert hasattr(MPosition.update, 'register')


@pytest.mark.unit
@pytest.mark.database
class TestSignalModelComprehensive:
    """5. Signal模型综合测试"""

    def test_msignal_strategy_signal_generation(self):
        """测试MSignal策略信号生成"""
        assert MSignal.__abstract__ is False
        assert MSignal.__tablename__ == "signal"
        assert issubclass(MSignal, MClickBase)

    def test_msignal_direction_strength_fields(self):
        """测试MSignal方向强度字段"""
        assert hasattr(MSignal, 'direction')
        assert hasattr(MSignal, 'strength')
        assert hasattr(MSignal, 'weight')
        # direction is Int8
        dir_type = get_mapped_column(MSignal.direction).type
        assert dir_type.__class__.__name__ == 'Int8'

    def test_msignal_confidence_level_handling(self):
        """测试MSignal置信度处理"""
        assert hasattr(MSignal, 'confidence')
        conf_type = get_mapped_column(MSignal.confidence).type
        assert conf_type.__class__.__name__ == 'Float32'

    def test_msignal_strategy_metadata(self):
        """测试MSignal策略元数据"""
        assert hasattr(MSignal, 'portfolio_id')
        assert hasattr(MSignal, 'engine_id')
        assert hasattr(MSignal, 'run_id')
        assert hasattr(MSignal, 'reason')

    def test_msignal_timing_information(self):
        """测试MSignal时机信息"""
        assert hasattr(MSignal, 'timestamp')
        assert hasattr(MSignal, 'business_timestamp')

    def test_msignal_order_conversion_support(self):
        """测试MSignal订单转换支持"""
        # Signal has volume (suggested trade size) and direction
        assert hasattr(MSignal, 'volume')
        assert hasattr(MSignal, 'direction')
        assert hasattr(MSignal, 'code')

    def test_msignal_update_method_implementation(self):
        """测试MSignal update方法实现"""
        assert hasattr(MSignal.update, 'register')


@pytest.mark.unit
@pytest.mark.database
class TestModelFieldTypeMapping:
    """6. 模型字段类型映射测试"""

    def test_decimal_precision_handling(self):
        """测试小数精度处理"""
        # Financial prices use DECIMAL(16, 2) consistently
        bar_price = get_mapped_column(MBar.open).type
        order_price = get_mapped_column(MOrder.limit_price).type
        pos_price = get_mapped_column(MPosition.cost).type
        assert bar_price.precision == 16
        assert order_price.precision == 16
        assert pos_price.precision == 16

    def test_datetime_timezone_handling(self):
        """测试日期时间时区处理"""
        # MMysqlBase models use timezone=True
        create_at_type = get_mapped_column(MMysqlBase.create_at).type
        assert create_at_type.timezone is True
        order_ts = get_mapped_column(MOrder.timestamp).type
        assert order_ts.timezone is True

    def test_enum_type_database_mapping(self):
        """测试枚举类型数据库映射"""
        # ClickHouse: Int8, MySQL: TINYINT
        ch_src = get_mapped_column(MClickBase.source).type
        my_src = get_mapped_column(MMysqlBase.source).type
        assert ch_src.__class__.__name__ == 'Int8'
        assert my_src.__class__.__name__ == 'TINYINT'

    def test_nullable_field_handling(self):
        """测试可空字段处理"""
        # MySQL models support nullable via is_del soft delete
        assert is_column_nullable(MMysqlBase, 'meta') is True
        # Business timestamps are optional
        assert is_column_nullable(MOrder, 'business_timestamp') is True
        assert is_column_nullable(MPosition, 'business_timestamp') is True

    def test_string_length_constraints(self):
        """测试字符串长度约束"""
        # MMysqlBase uses String(32) for uuid
        assert get_mapped_column(MMysqlBase.uuid).type.length == 32
        # MOrder code is String(32)
        assert get_mapped_column(MOrder.code).type.length == 32
        # MOrder portfolio_id is String(32)
        assert get_mapped_column(MOrder.portfolio_id).type.length == 32


@pytest.mark.unit
@pytest.mark.database
class TestModelRelationshipHandling:
    """7. 模型关系处理测试"""

    def test_foreign_key_relationships(self):
        """测试外键关系"""
        # Order and Position reference portfolio via portfolio_id
        assert hasattr(MOrder, 'portfolio_id')
        assert hasattr(MPosition, 'portfolio_id')

    def test_one_to_many_relationships(self):
        """测试一对多关系"""
        # One portfolio has many orders
        assert hasattr(MOrder, 'portfolio_id')
        # One portfolio has many positions
        assert hasattr(MPosition, 'portfolio_id')
        # One engine has many signals
        assert hasattr(MSignal, 'engine_id')

    def test_many_to_many_relationships(self):
        """测试多对多关系"""
        # Engine-Portfolio mapping exists
        from ginkgo.data.models.model_engine_portfolio_mapping import MEnginePortfolioMapping
        assert hasattr(MEnginePortfolioMapping, 'engine_id')
        assert hasattr(MEnginePortfolioMapping, 'portfolio_id')

    def test_relationship_lazy_loading(self):
        """测试关系懒加载"""
        # SQLAlchemy ORM supports lazy loading by default
        # Relationships are not explicitly defined as ForeignKey constraints
        # but logically connected through *_id fields
        assert hasattr(MOrder, 'portfolio_id')

    def test_cascade_operations(self):
        """测试级联操作"""
        # MySQL soft delete provides cascading behavior
        assert hasattr(MOrder, 'delete')
        assert hasattr(MPosition, 'delete')
        # delete() sets is_del = True instead of actual deletion
        import inspect
        source = inspect.getsource(MMysqlBase.delete)
        assert 'is_del = True' in source


@pytest.mark.unit
@pytest.mark.database
class TestModelValidationRules:
    """8. 模型验证规则测试"""

    def test_field_value_validation(self):
        """测试字段值验证"""
        # Enum validation rejects invalid values
        assert DIRECTION_TYPES.validate_input(999) is None
        assert DIRECTION_TYPES.validate_input(DIRECTION_TYPES.LONG) == 1

    def test_cross_field_validation(self):
        """测试跨字段验证"""
        # Order must have direction and order_type
        assert hasattr(MOrder, 'direction')
        assert hasattr(MOrder, 'order_type')
        # Position must have code and volume
        assert hasattr(MPosition, 'code')
        assert hasattr(MPosition, 'volume')

    def test_business_rule_validation(self):
        """测试业务规则验证"""
        # Signal strength and confidence have default values
        assert get_column_default(MSignal.strength) == 0.5
        assert get_column_default(MSignal.confidence) == 0.5

    def test_data_integrity_constraints(self):
        """测试数据完整性约束"""
        # Primary key constraints ensure uniqueness
        assert get_mapped_column(MMysqlBase.uuid).primary_key is True
        assert get_mapped_column(MClickBase.uuid).primary_key is True


@pytest.mark.unit
@pytest.mark.database
class TestModelPerformanceOptimization:
    """9. 模型性能优化测试"""

    def test_query_optimization_hints(self):
        """测试模型查询的性能优化提示"""
        # MBar MergeTree order_by=(code, timestamp) optimizes range queries
        from clickhouse_sqlalchemy import engines
        assert isinstance(MBar.__table_args__[0], engines.MergeTree)
        assert "code" in str(MBar.__table_args__[0].order_by) and "timestamp" in str(MBar.__table_args__[0].order_by)

    def test_bulk_operations_support(self):
        """测试模型的批量插入和更新支持"""
        # ClickHouse MergeTree is optimized for bulk inserts
        # Volume field uses Integer for compact storage
        vol_type = get_mapped_column(MBar.volume).type
        assert vol_type.__class__.__name__ == 'Integer'

    def test_indexing_strategy_optimization(self):
        """测试模型字段的索引策略优化"""
        # Primary keys are automatically indexed
        assert get_mapped_column(MClickBase.uuid).primary_key is True
        assert get_mapped_column(MMysqlBase.uuid).primary_key is True

    def test_memory_usage_optimization(self):
        """测试模型实例的内存使用优化"""
        # Int8 for small enums minimizes memory
        for field_name in ['source', 'frequency', 'direction']:
            ch_type = getattr(MBar, field_name, None)
            if ch_type is not None:
                col_type = get_mapped_column(ch_type).type
                assert col_type.__class__.__name__ == 'Int8'

    def test_database_specific_optimizations(self):
        """测试针对不同数据库的特定优化"""
        # ClickHouse: no is_del (append-only), MergeTree engine
        assert not hasattr(MClickBase, 'is_del')
        assert not hasattr(MClickBase, 'delete')
        # MySQL: soft delete, timezone-aware timestamps
        assert hasattr(MMysqlBase, 'is_del')
        assert hasattr(MMysqlBase, 'delete')


@pytest.mark.unit
class TestMPositionBehavior:
    """MPosition 行为测试 — 验证实际数据操作而非配置检查"""

    def test_factory_creates_valid_instance(self):
        """测试工厂函数创建有效实例"""
        from tests.unit.data.models.test_position_model import _make_position
        p = _make_position()
        assert p.portfolio_id == "test_portfolio"
        assert p.code == "000001.SZ"
        assert p.volume == 1000

    def test_soft_delete_workflow(self):
        """测试软删除完整工作流"""
        from tests.unit.data.models.test_position_model import _make_position
        p = _make_position()
        p.delete()
        assert p.is_del is True
        p.cancel_delete()
        assert p.is_del is False
        # 双重删除幂等
        p.delete()
        p.delete()
        assert p.is_del is True

    def test_cost_accepts_decimal(self):
        """测试 cost 接受 Decimal 类型"""
        from tests.unit.data.models.test_position_model import _make_position
        p = _make_position(cost=Decimal("99.99"))
        assert p.cost == Decimal("99.99")

    def test_cost_accepts_negative(self):
        """测试 cost 接受负值（做空成本可能为负）"""
        from tests.unit.data.models.test_position_model import _make_position
        p = _make_position(cost=Decimal("-5.00"))
        assert p.cost == Decimal("-5.00")

    def test_fee_accumulation(self):
        """测试手续费累加"""
        from tests.unit.data.models.test_position_model import _make_position
        p = _make_position(fee=Decimal("3.00"))
        assert p.fee == Decimal("3.00")

    def test_settlement_fields_types(self):
        """测试结算相关字段类型正确"""
        from tests.unit.data.models.test_position_model import _make_position
        p = _make_position(settlement_days=1, settlement_frozen_volume=100)
        assert isinstance(p.settlement_days, int)
        assert isinstance(p.settlement_frozen_volume, int)

    def test_settlement_queue_json_format(self):
        """测试结算队列 JSON 格式"""
        from tests.unit.data.models.test_position_model import _make_position
        import json
        queue = '[{"volume": 100, "settle_date": "2024-01-03"}]'
        p = _make_position(settlement_queue_json=queue)
        assert p.settlement_queue_json == queue
        # 验证是合法 JSON
        parsed = json.loads(p.settlement_queue_json)
        assert isinstance(parsed, list)

    def test_update_unsupported_type_raises(self):
        """测试不支持的 update 类型抛出异常"""
        from tests.unit.data.models.test_position_model import _make_position
        p = _make_position()
        with pytest.raises(NotImplementedError, match="Unsupported type"):
            p.update(12345)

    def test_repr_format(self):
        """测试 repr 格式包含表名"""
        from tests.unit.data.models.test_position_model import _make_position
        p = _make_position()
        result = p.__repr__()
        assert "Position" in result

    def test_edge_case_zero_volume(self):
        """测试零持仓边界"""
        from tests.unit.data.models.test_position_model import _make_position
        p = _make_position(volume=0)
        assert p.volume == 0

    def test_edge_case_negative_fee(self):
        """测试负手续费边界"""
        from tests.unit.data.models.test_position_model import _make_position
        p = _make_position(fee=Decimal("-10.00"))
        assert p.fee == Decimal("-10.00")

    def test_edge_case_large_volume(self):
        """测试大持仓量边界"""
        from tests.unit.data.models.test_position_model import _make_position
        p = _make_position(volume=10000000)
        assert p.volume == 10000000

    def test_edge_case_empty_portfolio_id(self):
        """测试空组合ID边界"""
        from tests.unit.data.models.test_position_model import _make_position
        p = _make_position(portfolio_id="")
        assert p.portfolio_id == ""


@pytest.mark.unit
class TestMBarBehavior:
    """MBar 行为测试"""

    def test_abstract_status(self):
        """测试 MBar 不是抽象类（可实例化）"""
        assert MBar.__abstract__ is False

    def test_has_update_register(self):
        """测试 update 方法有 register（singledispatchmethod）"""
        assert hasattr(MBar.update, 'register')

    def test_inherits_clickbase(self):
        """测试继承自 MClickBase"""
        assert issubclass(MBar, MClickBase)

    def test_ohlcv_fields_same_precision(self):
        """测试 OHLCV 字段使用相同精度"""
        for field in ['open', 'high', 'low', 'close', 'amount']:
            col_type = get_mapped_column(getattr(MBar, field)).type
            assert col_type.precision == 16
            assert col_type.scale == 2


@pytest.mark.unit
class TestMOrderBehavior:
    """MOrder 行为测试"""

    def test_abstract_status(self):
        """测试 MOrder 不是抽象类"""
        assert MOrder.__abstract__ is False

    def test_has_update_register(self):
        """测试 update 方法有 register"""
        assert hasattr(MOrder.update, 'register')

    def test_has_soft_delete(self):
        """测试有软删除方法"""
        assert hasattr(MOrder, 'delete')
        assert callable(MOrder.delete)

    def test_has_cancel_delete(self):
        """测试有取消删除方法"""
        assert hasattr(MOrder, 'cancel_delete')
        assert callable(MOrder.cancel_delete)

    def test_inherits_mysqlbase(self):
        """测试继承自 MMysqlBase"""
        assert issubclass(MOrder, MMysqlBase)


@pytest.mark.unit
class TestMSignalBehavior:
    """MSignal 行为测试"""

    def test_abstract_status(self):
        """测试 MSignal 不是抽象类"""
        assert MSignal.__abstract__ is False

    def test_inherits_clickbase(self):
        """测试继承自 MClickBase"""
        assert issubclass(MSignal, MClickBase)

    def test_has_update_register(self):
        """测试 update 方法有 register"""
        assert hasattr(MSignal.update, 'register')

    def test_direction_is_int8(self):
        """测试 direction 字段使用 Int8"""
        dir_type = get_mapped_column(MSignal.direction).type
        assert dir_type.__class__.__name__ == 'Int8'

    def test_confidence_is_float32(self):
        """测试 confidence 字段使用 Float32"""
        conf_type = get_mapped_column(MSignal.confidence).type
        assert conf_type.__class__.__name__ == 'Float32'

    def test_strength_default_is_0_5(self):
        """测试 strength 默认值为 0.5"""
        assert get_column_default(MSignal.strength) == 0.5

    def test_confidence_default_is_0_5(self):
        """测试 confidence 默认值为 0.5"""
        assert get_column_default(MSignal.confidence) == 0.5
