"""
pytest配置文件 - TDD优化版本 + 安全检查

提供TDD开发所需的核心fixtures和配置：
1. 减少Mock依赖，使用真实对象
2. 标准化测试数据创建
3. 性能监控和TDD度量
4. DEBUG模式安全检查，防止在生产环境运行测试
5. 数据库连接验证和生产环境保护
"""

import os

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Any
import tempfile
import sqlite3
from unittest.mock import Mock
import warnings

# 使用pip install -e安装的ginkgo包，无需额外路径配置

# Ginkgo核心组件 - 使用已安装的包
try:
    from ginkgo.entities.order import Order
    from ginkgo.entities.position import Position
    from ginkgo.entities.signal import Signal
    from ginkgo.trading.events.price_update import EventPriceUpdate
    from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
    from ginkgo.libs import datetime_normalize
    GINKGO_AVAILABLE = True
except ImportError:
    GINKGO_AVAILABLE = False
    warnings.warn("Ginkgo modules not available, using mock objects")


# ===== TDD配置 =====

def pytest_configure(config):
    """pytest配置 - 添加TDD标记和DEBUG模式检查"""
    # CLI 单元测试通过环境变量豁免 DEBUG 检查
    if os.environ.get("GINKGO_SKIP_DEBUG_CHECK") == "1":
        return
    # 强制检查DEBUG模式
    if not check_debug_mode():
        pytest.exit(
            "❌ DEBUG模式未启用！测试无法继续。\n"
            "请运行以下命令启用DEBUG模式：\n"
            "   ginkgo system config set --debug on\n"
            "然后重新运行测试。\n\n"
            "这是为了保护生产环境数据库安全。"
        )

    # 添加TDD标记
    config.addinivalue_line("markers", "tdd: TDD开发的测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "slow: 慢速测试")
    config.addinivalue_line("markers", "requires_db: 需要数据库的测试")
    config.addinivalue_line("markers", "financial: 金融精度测试")
    config.addinivalue_line("markers", "protocol: Protocol接口测试")
    config.addinivalue_line("markers", "mixin: Mixin功能测试")
    config.addinivalue_line("markers", "enhancement: 框架增强功能测试")
    config.addinivalue_line("markers", "event_system: 事件系统测试")
    config.addinivalue_line("markers", "time_provider: 时间提供者测试")


def check_debug_mode() -> bool:
    """
    检查DEBUG模式是否启用

    Returns:
        bool: True表示DEBUG模式已启用，False表示未启用
    """
    try:
        # 重新导入GCONF确保可用
        from ginkgo.libs import GCONF

        if not GINKGO_AVAILABLE:
            print("⚠️  Ginkgo模块不可用，跳过DEBUG模式检查")
            return True

        debug_mode = GCONF.DEBUGMODE
        print(f"🔍 检查DEBUG模式: {'✅ 已启用' if debug_mode else '❌ 未启用'}")

        if not debug_mode:
            print("\n" + "="*60)
            print("🚨 安全检查失败：DEBUG模式未启用")
            print("="*60)
            print("为了保护生产环境数据库安全，必须启用DEBUG模式才能运行测试。")
            print("")
            print("解决方案：")
            print("  1. 运行命令启用DEBUG模式：")
            print("     ginkgo system config set --debug on")
            print("  2. 重新运行pytest")
            print("")
            print("原因说明：")
            print("  - DEBUG模式会启用额外的安全检查")
            print("  - 防止测试意外操作生产数据库")
            print("  - 确保测试在安全环境中进行")
            print("="*60)
            return False

        return True

    except Exception as e:
        print(f"❌ 检查DEBUG模式时出错: {e}")
        print("请确保Ginkgo已正确安装和配置")
        return False


# ===== 核心业务对象Fixtures =====

@pytest.fixture
def test_timestamp():
    """标准测试时间戳"""
    return datetime(2024, 1, 15, 9, 30, 0)


@pytest.fixture
def sample_stock_code():
    """标准测试股票代码"""
    return "000001.SZ"


@pytest.fixture
def test_order(test_timestamp, sample_stock_code):
    """创建标准测试订单"""
    if not GINKGO_AVAILABLE:
        pytest.skip("Ginkgo not available")

    # 使用正确的Order构造函数，提供所有必需参数
    order = Order(
        portfolio_id="test_portfolio",
        engine_id="test_engine",
        run_id="test_run",
        code=sample_stock_code,
        direction=DIRECTION_TYPES.LONG,
        order_type=ORDER_TYPES.LIMITORDER,
        status=ORDERSTATUS_TYPES.NEW,
        volume=1000,
        limit_price=10.50,
        frozen_money=10500.0,  # 买单冻结资金：1000 * 10.50
        timestamp=test_timestamp
    )
    return order


@pytest.fixture
def test_position(sample_stock_code):
    """创建标准测试持仓"""
    if not GINKGO_AVAILABLE:
        pytest.skip("Ginkgo not available")

    position = Position()
    position.code = sample_stock_code
    position.volume = 1000
    position.average_cost = Decimal('10.0')
    position.current_price = Decimal('10.5')
    return position


@pytest.fixture
def test_signal(test_timestamp, sample_stock_code):
    """创建标准测试信号"""
    if not GINKGO_AVAILABLE:
        pytest.skip("Ginkgo not available")

    signal = Signal()
    signal.code = sample_stock_code
    signal.direction = DIRECTION_TYPES.LONG
    signal.timestamp = test_timestamp
    signal.strength = 0.8
    signal.reason = "TDD测试信号"
    return signal


@pytest.fixture
def price_update_event(test_timestamp, sample_stock_code):
    """创建价格更新事件"""
    if not GINKGO_AVAILABLE:
        pytest.skip("Ginkgo not available")

    event = EventPriceUpdate()
    event.code = sample_stock_code
    event.open = Decimal('10.0')
    event.high = Decimal('10.8')
    event.low = Decimal('9.8')
    event.close = Decimal('10.5')
    event.volume = 100000
    event.timestamp = test_timestamp
    return event


# ===== 投资组合测试数据 =====

@pytest.fixture
def test_portfolio_info():
    """标准测试投资组合信息"""
    return {
        "uuid": "test_portfolio",
        "cash": Decimal('100000.0'),
        "total_value": Decimal('150000.0'),
        "positions": {
            "000001.SZ": {
                "code": "000001.SZ",
                "volume": 1000,
                "cost": Decimal('10.0'),
                "current_price": Decimal('12.0'),
                "market_value": Decimal('12000.0'),
                "profit_loss": Decimal('2000.0'),
                "profit_loss_ratio": 0.2
            }
        }
    }


@pytest.fixture
def losing_portfolio_info():
    """亏损投资组合信息"""
    return {
        "uuid": "losing_portfolio",
        "cash": Decimal('100000.0'),
        "total_value": Decimal('140000.0'),
        "positions": {
            "000001.SZ": {
                "code": "000001.SZ",
                "volume": 1000,
                "cost": Decimal('10.0'),
                "current_price": Decimal('8.5'),  # 亏损15%
                "market_value": Decimal('8500.0'),
                "profit_loss": Decimal('-1500.0'),
                "profit_loss_ratio": -0.15
            }
        }
    }


# ===== 测试数据库 =====

@pytest.fixture
def test_database():
    """创建内存SQLite测试数据库"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 创建测试表
    cursor.execute('''
        CREATE TABLE test_orders (
            id INTEGER PRIMARY KEY,
            code TEXT,
            direction TEXT,
            volume INTEGER,
            price DECIMAL(10,2),
            timestamp DATETIME
        )
    ''')

    cursor.execute('''
        CREATE TABLE test_positions (
            id INTEGER PRIMARY KEY,
            code TEXT,
            volume INTEGER,
            cost DECIMAL(10,2),
            current_price DECIMAL(10,2)
        )
    ''')

    conn.commit()
    yield conn

    conn.close()
    os.unlink(db_path)


# ===== TDD度量 =====

@pytest.fixture
def tdd_metrics():
    """TDD度量收集器"""
    return {
        "tests_written_first": 0,
        "tests_passing": 0,
        "refactor_cycles": 0,
        "mock_usage_count": 0
    }


def pytest_runtest_setup(item):
    """测试运行前检查"""
    # 检查TDD标记
    if "tdd" in item.keywords:
        # TDD测试的特殊处理
        pass


def pytest_runtest_teardown(item):
    """测试运行后清理"""
    # 清理Mock对象
    pass


# ===== 辅助函数 =====

def create_market_scenario(scenario_type: str) -> Dict[str, Any]:
    """创建市场场景数据

    Args:
        scenario_type: 场景类型 ('bull_market', 'bear_market', 'volatile_market')

    Returns:
        包含市场数据的字典
    """
    scenarios = {
        'bull_market': {
            'trend': 'up',
            'price_changes': [0.02, 0.015, 0.03, 0.01, 0.025],
            'volume_multiplier': 1.2
        },
        'bear_market': {
            'trend': 'down',
            'price_changes': [-0.02, -0.03, -0.015, -0.025, -0.01],
            'volume_multiplier': 0.8
        },
        'volatile_market': {
            'trend': 'sideways',
            'price_changes': [0.03, -0.02, 0.025, -0.035, 0.01],
            'volume_multiplier': 1.5
        }
    }

    return scenarios.get(scenario_type, scenarios['bull_market'])


def assert_financial_precision(actual: Decimal, expected: Decimal, places: int = 4):
    """断言金融数据精度

    Args:
        actual: 实际值
        expected: 期望值
        places: 小数位精度
    """
    assert abs(actual - expected) < Decimal(10) ** (-places), \
        f"财务精度不匹配: {actual} != {expected} (精度: {places}位小数)"


# ===== 数据库自动清理 =====

@pytest.fixture(scope="function", autouse=True)
def configured_crud_cleanup(request):
    """
    基于类配置的精确CRUD清理 - 带验证的异步等待版本

    每个测试类只需要添加一行配置即可自动清理：
        CRUD_TEST_CONFIG = {'crud_class': YourCRUDClass}

    这个fixture会：
    1. 读取类的CRUD_TEST_CONFIG配置
    2. 删除前查询数据条数，记录清理前的数据量
    3. 自动创建带清理接口的CRUD实例
    4. 执行清理操作
    5. 删除后查询数据条数，确认清理有效
    6. 使用异步等待确保清理完成
    7. 输出详细的清理验证日志
    """
    from ginkgo.enums import SOURCE_TYPES

    # 检查测试类是否有CRUD配置
    crud_config = getattr(request.cls, 'CRUD_TEST_CONFIG', None)
    if not crud_config:
        yield
        return

    # 获取CRUD类和默认filters
    crud_class = crud_config.get('crud_class')
    default_filters = crud_config.get('filters', {})

    # 自动添加source字段（如果不存在）
    if 'source' not in default_filters:
        default_filters['source'] = SOURCE_TYPES.TEST.value
    if not crud_class:
        yield
        return

    # 导入依赖
    from ginkgo.enums import SOURCE_TYPES

    # 延迟导入异步清理工具
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root / "test" / "libs" / "utils"))

    try:
        from async_cleanup import AsyncCleanupMixin, async_cleanup_with_wait
    except ImportError:
        # 如果异步清理工具不可用，使用简单清理
        yield
        return

    # 创建带清理接口的CRUD类
    class CleanupCRUD(crud_class, AsyncCleanupMixin):
        pass

    crud_obj = CleanupCRUD()
    filters = default_filters

    # Setup：测试前清理残留数据并验证
    # 对 TickCRUD 使用更安全的表检查
    if crud_class.__name__ == 'TickCRUD':
        try:
            before_count = len(crud_obj.find(filters=filters))
        except Exception as e:
            # 表不存在时跳过清理
            if "Unknown table" in str(e):
                before_count = 0
            else:
                raise
    else:
        before_count = len(crud_obj.find(filters=filters))

    if before_count > 0:
        print(f"\n🧹 Pre-test cleanup for {crud_class.__name__}: {before_count} records found")

        async_cleanup_with_wait(
            crud_obj,
            filters,
            f"{crud_class.__name__} test data (pre-test)"
        )

        # 对 TickCRUD 使用更安全的表检查
        if crud_class.__name__ == 'TickCRUD':
            try:
                after_count = len(crud_obj.find(filters=filters))
            except Exception as e:
                if "Unknown table" in str(e):
                    after_count = 0
                else:
                    raise
        else:
            after_count = len(crud_obj.find(filters=filters))

        if after_count == 0:
            print(f"✓ Pre-test cleanup successful: {before_count} → 0 records (deleted {before_count} records)")
        else:
            print(f"⚠️ Pre-test cleanup partial: {before_count} → {after_count} records (deleted {before_count - after_count} records)")
    else:
        print(f"✓ No {crud_class.__name__} test data to clean (pre-test)")

    yield  # 执行测试

    # Teardown：测试后清理本次测试数据并验证
    # 对 TickCRUD 使用更安全的表检查
    if crud_class.__name__ == 'TickCRUD':
        try:
            before_count = len(crud_obj.find(filters=filters))
        except Exception as e:
            if "Unknown table" in str(e):
                before_count = 0
            else:
                raise
    else:
        before_count = len(crud_obj.find(filters=filters))

    if before_count > 0:
        print(f"\n🧹 Post-test cleanup for {crud_class.__name__}: {before_count} records found")

        async_cleanup_with_wait(
            crud_obj,
            filters,
            f"{crud_class.__name__} test data (post-test)"
        )

        # 对 TickCRUD 使用更安全的表检查
        if crud_class.__name__ == 'TickCRUD':
            try:
                after_count = len(crud_obj.find(filters=filters))
            except Exception as e:
                if "Unknown table" in str(e):
                    after_count = 0
                else:
                    raise
        else:
            after_count = len(crud_obj.find(filters=filters))

        if after_count == 0:
            print(f"✓ Post-test cleanup successful: {before_count} → 0 records (deleted {before_count} records)")
        else:
            print(f"⚠️ Post-test cleanup partial: {before_count} → {after_count} records (deleted {before_count - after_count} records)")
    else:
        print(f"✓ No {crud_class.__name__} test data to clean (post-test)")

    # 特殊处理：TickCRUD 使用模块级清理，这里跳过
    if crud_class.__name__ == 'TickCRUD':
        print(f"⏭️ Skipping TickCRUD cleanup (handled by module-level fixture)")
        return


@pytest.fixture(scope="module", autouse=True)
def tick_crud_module_cleanup(request):
    """
    模块级别的TickCRUD清理fixture

    只在整个测试模块开始前和结束后各清理一次，提高性能。
    适用于TickCRUD这种需要动态创建表的测试场景。
    """
    # 检查模块是否包含TickCRUD测试
    if not hasattr(request.module, '__dict__'):
        yield
        return

    # 检查模块中是否有TickCRUD的引用
    module_content = str(request.module.__dict__.values())
    if 'TickCRUD' not in module_content:
        yield
        return

    # 导入TickCRUD
    try:
        from ginkgo.data.crud.tick_crud import TickCRUD
    except ImportError:
        yield
        return

    print(f"\n🧹 Module-level TickCRUD cleanup for {request.module.__name__}")

    # 模块开始前清理
    try:
        tick_crud = TickCRUD()
        deleted_tables = tick_crud.drop_all_test_tables()
        if deleted_tables > 0:
            print(f"✓ Pre-module cleanup: removed {deleted_tables} test tables")
    except Exception as e:
        print(f"⚠️ Pre-module cleanup failed: {e}")

    yield

    # 模块结束后清理
    try:
        tick_crud = TickCRUD()
        deleted_tables = tick_crud.drop_all_test_tables()
        if deleted_tables > 0:
            print(f"✓ Post-module cleanup: removed {deleted_tables} test tables")
    except Exception as e:
        print(f"⚠️ Post-module cleanup failed: {e}")


@pytest.fixture(scope="function", autouse=True)
def auto_clean_test_data(request):
    """
    通用智能清理fixture：根据@pytest.mark.db_cleanup标记自动清理数据库

    使用方式：
    1. 在测试类上添加 @pytest.mark.db_cleanup 标记
    2. 定义 CLEANUP_CONFIG 类变量指定清理规则

    配置示例：
        @pytest.mark.db_cleanup
        class TestSomething:
            # 单个CRUD清理
            CLEANUP_CONFIG = {
                'bar': {'code__like': 'TEST_HIST_%'}
            }

            # 多个CRUD + 不同字段
            CLEANUP_CONFIG = {
                'bar': {'code__like': 'TEST_%'},
                'order': {'portfolio_id__like': 'TEST_PORT_%'},
                'position': {'symbol__like': 'TEST_%', 'status': 1}
            }

    清理策略：
    - Setup阶段：清理可能残留的测试数据
    - Teardown阶段：清理本次测试产生的数据
    """
    # 检查是否需要清理
    needs_cleanup = request.node.get_closest_marker("db_cleanup") is not None
    if not needs_cleanup:
        yield
        return

    # 获取清理配置
    cleanup_config = getattr(request.cls, 'CLEANUP_CONFIG', None)
    if not cleanup_config:
        warnings.warn(
            f"{request.cls.__name__} 使用了 @pytest.mark.db_cleanup "
            f"但未定义 CLEANUP_CONFIG，跳过数据库清理。"
            f"请添加 CLEANUP_CONFIG 类变量指定清理规则。"
        )
        yield
        return

    # 延迟导入CRUD类（避免循环导入）
    from ginkgo.data.crud.bar_crud import BarCRUD
    try:
        from ginkgo.data.crud.tick_crud import TickCRUD
    except ImportError:
        TickCRUD = None
    try:
        from ginkgo.data.crud.order_crud import OrderCRUD
    except ImportError:
        OrderCRUD = None
    try:
        from ginkgo.data.crud.position_crud import PositionCRUD
    except ImportError:
        PositionCRUD = None
    try:
        from ginkgo.data.crud.signal_tracker_crud import SignalTrackerCRUD
    except ImportError:
        SignalTrackerCRUD = None
    try:
        from ginkgo.data.crud.param_crud import ParamCRUD
    except ImportError:
        ParamCRUD = None
    try:
        from ginkgo.data.crud.file_crud import FileCRUD
    except ImportError:
        FileCRUD = None
    try:
        from ginkgo.data.crud.portfolio_crud import PortfolioCRUD
    except ImportError:
        PortfolioCRUD = None

    crud_map = {
        'bar': BarCRUD,
        'tick': TickCRUD,
        'order': OrderCRUD,
        'position': PositionCRUD,
        'signal_tracker': SignalTrackerCRUD,
        'param': ParamCRUD,
        'file': FileCRUD,
        'portfolio': PortfolioCRUD,
    }

    # 清理函数
    def do_cleanup():
        for crud_type, filters in cleanup_config.items():
            crud_class = crud_map.get(crud_type)
            if crud_class is None:
                warnings.warn(f"CRUD类型 '{crud_type}' 不可用，跳过清理")
                continue
            try:
                crud_class().remove(filters=filters)
            except Exception as e:
                warnings.warn(f"清理 {crud_type} 数据失败: {e}")

    # Setup：测试前清理残留数据
    do_cleanup()

    yield

    # Teardown：测试后清理本次测试数据
    do_cleanup()


# ===== 金融精度测试装饰器 =====

def financial_precision_test(decimal_places: int = 4):
    """
    金融精度测试装饰器

    自动为测试函数添加金融数据精度验证，确保数值计算符合金融业务要求。

    Args:
        decimal_places: 小数位数精度，默认4位

    Usage:
        @financial_precision_test(decimal_places=4)
        def test_portfolio_valuation():
            # 金融精度测试逻辑
            pass
    """
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            try:
                result = test_func(*args, **kwargs)
                # 验证结果中的Decimal类型数据精度
                _validate_financial_precision(result, decimal_places)
                return result
            except Exception as e:
                # 记录精度测试失败信息
                print(f"金融精度测试失败: {e}")
                raise
        return wrapper
    return decorator


def _validate_financial_precision(data, decimal_places: int):
    """验证数据中的金融精度"""
    from decimal import Decimal

    def check_value(value):
        if isinstance(value, Decimal):
            # 检查小数位数
            tuple_parts = value.as_tuple()
            if tuple_parts.exponent < -decimal_places:
                raise ValueError(
                    f"数值精度超出限制: {value} (小数位数: {-tuple_parts.exponent}, "
                    f"允许最大位数: {decimal_places})"
                )
        elif isinstance(value, (dict, list)):
            for item in value:
                check_value(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                check_value(item)

    check_value(data)


# ===== Protocol接口测试装饰器 =====

def protocol_test(protocol_class):
    """
    Protocol接口测试装饰器

    自动验证测试对象是否符合指定Protocol接口的要求。

    Args:
        protocol_class: Protocol接口类

    Usage:
        @protocol_test(IStrategy)
        def test_strategy_interface():
            strategy = MyStrategy()
            return strategy
    """
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            result = test_func(*args, **kwargs)

            # 验证接口实现
            if hasattr(protocol_class, '__instancecheck__'):
                if not isinstance(result, protocol_class):
                    raise TypeError(
                        f"测试对象不符合 {protocol_class.__name__} 接口要求"
                    )
            else:
                # 对于不支持isinstance的Protocol，手动检查方法
                _validate_protocol_methods(result, protocol_class)

            return result
        return wrapper
    return decorator


def protocol_compatibility_test(*protocol_classes):
    """
    多Protocol接口兼容性测试装饰器

    验证测试对象是否同时符合多个Protocol接口的要求。

    Args:
        *protocol_classes: 多个Protocol接口类

    Usage:
        @protocol_compatibility_test(IStrategy, IRiskManagement)
        def test_multi_interface_component():
            component = MultiFunctionComponent()
            return component
    """
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            result = test_func(*args, **kwargs)

            for protocol_class in protocol_classes:
                if hasattr(protocol_class, '__instancecheck__'):
                    if not isinstance(result, protocol_class):
                        raise TypeError(
                            f"测试对象不符合 {protocol_class.__name__} 接口要求"
                        )
                else:
                    _validate_protocol_methods(result, protocol_class)

            return result
        return wrapper
    return decorator


def _validate_protocol_methods(obj, protocol_class):
    """手动验证Protocol方法实现"""
    import inspect

    for name, method in inspect.getmembers(protocol_class, predicate=inspect.isfunction):
        if not name.startswith('_'):
            if not hasattr(obj, name):
                raise AttributeError(
                    f"对象缺少必需的方法: {name} (来自 {protocol_class.__name__})"
                )


# ===== Mixin功能测试装饰器 =====

def mixin_test(mixin_class, base_class=None):
    """
    Mixin功能测试装饰器

    验证Mixin类是否能正确增强基础类功能。

    Args:
        mixin_class: Mixin类
        base_class: 基础类，如果为None则使用测试返回的对象

    Usage:
        @mixin_test(StrategyMixin, BaseStrategy)
        def test_strategy_mixin():
            class TestStrategy(BaseStrategy, StrategyMixin):
                pass
            return TestStrategy()
    """
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            result = test_func(*args, **kwargs)

            # 验证Mixin功能
            if base_class:
                # 检查是否正确继承了基类和Mixin
                if not isinstance(result, base_class):
                    raise TypeError(f"对象未正确继承基类: {base_class.__name__}")

            if not isinstance(result, mixin_class):
                raise TypeError(f"对象未正确继承Mixin: {mixin_class.__name__}")

            # 验证Mixin方法存在
            _validate_mixin_methods(result, mixin_class)

            return result
        return wrapper
    return decorator


def _validate_mixin_methods(obj, mixin_class):
    """验证Mixin方法实现"""
    import inspect

    mixin_methods = {
        name: method for name, method in inspect.getmembers(mixin_class, predicate=inspect.isfunction)
        if not name.startswith('_') and hasattr(method, '__doc__') and method.__doc__
    }

    for method_name in mixin_methods:
        if not hasattr(obj, method_name):
            raise AttributeError(
                f"Mixin方法未正确添加: {method_name} (来自 {mixin_class.__name__})"
            )


# ===== TDD阶段验证装饰器 =====

def tdd_phase(phase: str):
    """
    TDD阶段验证装饰器

    标记测试处于TDD的哪个阶段（Red/Green/Refactor）。

    Args:
        phase: TDD阶段 ('red', 'green', 'refactor')

    Usage:
        @tdd_phase('red')
        def test_new_feature():
            assert False, "TDD Red阶段：测试用例尚未实现"
    """
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            print(f"[TDD {phase.upper()}] 运行测试: {test_func.__name__}")
            return test_func(*args, **kwargs)
        wrapper.tdd_phase = phase
        return wrapper
    return decorator


# ===== 市场场景测试装饰器 =====

def market_scenario(scenario_type: str, **scenario_params):
    """
    市场场景测试装饰器

    为测试函数提供模拟的市场场景数据。

    Args:
        scenario_type: 场景类型 ('bull_market', 'bear_market', 'volatile_market')
        **scenario_params: 额外的场景参数

    Usage:
        @market_scenario('bull_market', volatility=0.02)
        def test_strategy_in_bull_market(market_data):
            # market_data包含市场场景数据
            pass
    """
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            market_data = create_market_scenario(scenario_type)
            market_data.update(scenario_params)
            kwargs['market_data'] = market_data
            return test_func(*args, **kwargs)
        return wrapper
    return decorator


# ===== 增强框架Fixtures =====

@pytest.fixture
def mock_strategy():
    """创建模拟策略对象"""
    class MockStrategy:
        def __init__(self):
            self.name = "TestStrategy"
            self.signals_generated = []

        def cal(self, portfolio_info, event):
            # 简单的信号生成逻辑
            return self.signals_generated

        def get_strategy_info(self):
            return {"name": self.name, "version": "1.0"}

        def validate_parameters(self, params):
            return True

        def initialize(self, context):
            pass

        def finalize(self):
            return {"signals_count": len(self.signals_generated)}

    return MockStrategy()


@pytest.fixture
def mock_risk_manager():
    """创建模拟风控管理器"""
    class MockRiskManager:
        def __init__(self):
            self.name = "TestRiskManager"
            self.adjusted_orders = []

        def validate_order(self, portfolio_info, order):
            # 简单的订单验证逻辑
            self.adjusted_orders.append(order)
            return order

        def generate_risk_signals(self, portfolio_info, event):
            return []  # 默认不生成风控信号

        def check_risk_limits(self, portfolio_info):
            return []

        def update_risk_parameters(self, parameters):
            pass

        def get_risk_metrics(self, portfolio_info):
            return {"var": 0.02, "max_drawdown": 0.05}

    return MockRiskManager()


@pytest.fixture
def mock_portfolio():
    """创建模拟投资组合"""
    class MockPortfolio:
        def __init__(self):
            self.name = "TestPortfolio"
            self.portfolio_id = "test_portfolio_id"
            self.cash = Decimal('100000.0')
            self.frozen = Decimal('0.0')
            self.positions = {}
            self.strategies = []
            self.risk_managers = []

        @property
        def worth(self):
            return self.cash + sum(p.get('market_value', 0) for p in self.positions.values())

        def add_strategy(self, strategy):
            self.strategies.append(strategy)

        def add_risk_manager(self, risk_manager):
            self.risk_managers.append(risk_manager)

        def get_portfolio_info(self):
            return {
                "portfolio_id": self.portfolio_id,
                "cash": self.cash,
                "total_value": self.worth,
                "positions": self.positions
            }

    return MockPortfolio()


@pytest.fixture
def enhanced_event_context():
    """创建增强事件上下文"""
    return {
        "correlation_id": "test_correlation_001",
        "causation_id": "test_causation_001",
        "session_id": "test_session_001",
        "user_id": "test_user",
        "trace_depth": 1,
        "start_time": datetime.now()
    }


@pytest.fixture
def event_sequence_test_data():
    """创建事件序列测试数据"""
    return [
        {
            "type": "price_update",
            "symbol": "000001.SZ",
            "price": 10.0,
            "timestamp": datetime(2024, 1, 1, 9, 30, 0)
        },
        {
            "type": "price_update",
            "symbol": "000001.SZ",
            "price": 10.5,
            "timestamp": datetime(2024, 1, 1, 9, 31, 0)
        },
        {
            "type": "price_update",
            "symbol": "000001.SZ",
            "price": 11.0,
            "timestamp": datetime(2024, 1, 1, 9, 32, 0)
        }
    ]


# ===== 增强框架装饰器 =====

def enhanced_framework_test(test_func):
    """
    增强框架测试装饰器

    为框架增强功能提供统一的测试环境和验证。
    """
    def wrapper(*args, **kwargs):
        # 设置增强框架测试环境
        kwargs['enhancement_context'] = {
            'test_mode': True,
            'framework_version': 'enhanced',
            'features_enabled': ['protocol_interfaces', 'mixins', 'event_enhancement']
        }

        result = test_func(*args, **kwargs)

        # 验证增强功能
        return result
    return wrapper


def time_travel_test(time_delta: timedelta):
    """
    时间旅行测试装饰器

    用于测试时间相关功能，模拟时间推进场景。

    Args:
        time_delta: 时间推进量

    Usage:
        @time_travel_test(timedelta(days=1))
        def test_strategy_with_time_advance():
            # 测试时间推进后的策略行为
            pass
    """
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            # 设置时间旅行上下文
            kwargs['time_delta'] = time_delta
            kwargs['original_time'] = datetime.now()
            kwargs['travel_time'] = datetime.now() + time_delta

            result = test_func(*args, **kwargs)

            # 验证时间相关行为
            return result
        return wrapper
    return decorator


def event_trace_test(test_func):
    """
    事件追踪测试装饰器

    验证事件的完整生命周期和追踪信息。
    """
    def wrapper(*args, **kwargs):
        # 设置事件追踪环境
        kwargs['trace_context'] = {
            'correlation_id': 'test_trace_001',
            'event_chain': [],
            'trace_enabled': True
        }

        result = test_func(*args, **kwargs)

        # 验证事件追踪完整性
        return result
    return wrapper


# ===== Mock数据源fixtures =====

@pytest.fixture(scope="session", autouse=True)
def mock_tushare_data_source():
    """
    全局Mock Tushare数据源fixture

    使用patch自动替换GinkgoTushare类实例化，让所有调用GinkgoTushare()的地方
    都返回MockGinkgoTushare实例，无需手动设置data_source属性。
    """
    try:
        # 导入Mock数据源和patch工具
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

        from unittest.mock import patch
        from test.mock_data.mock_ginkgo_tushare import MockGinkgoTushare

        # 使用patch自动替换GinkgoTushare类 - 修复导入路径
        with patch('ginkgo.data.sources.GinkgoTushare', MockGinkgoTushare):
            print("✅ 全局Mock数据源已启用 - 自动patch GinkgoTushare类")
            yield

    except ImportError as e:
        print(f"⚠️ Mock数据源导入失败，使用真实数据源: {e}")
        yield
    except Exception as e:
        print(f"⚠️ Mock数据源patch失败，使用真实数据源: {e}")
        yield
