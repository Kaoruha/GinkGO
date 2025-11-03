"""
Mock DataService工厂 - 支持多数据库环境

只Mock CRUD层，使用真实的Service层逻辑。
提供ClickHouse、MySQL、Redis等多种数据库的Mock环境。
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional, Union
import uuid

from test.fixtures.mock_crud_repo import MockBarCRUD


class MockDataSource:
    """Mock数据源 - 不执行任何实际操作"""

    def connect(self):
        """Mock连接"""
        return True

    def disconnect(self):
        """Mock断开连接"""
        pass

    def is_connected(self) -> bool:
        """Mock连接状态"""
        return True


class MockStockinfoService:
    """Mock股票信息服务"""

    def is_code_in_stocklist(self, code: str) -> bool:
        """默认所有代码都有效"""
        return True

    def get_stockinfos(self, *args, **kwargs):
        """返回空股票信息列表"""
        return []

    def sync_all(self, *args, **kwargs):
        """Mock同步操作"""
        return True


class MockAdjustfactorService:
    """Mock复权因子服务 - 暂不支持复权"""

    def get_adjustfactors(self, *args, **kwargs):
        """返回空列表，表示无复权数据"""
        return []


class MockTickCRUD:
    """Mock Tick数据CRUD"""

    def __init__(self):
        self._data = []

    def find(self, *args, **kwargs):
        return self._data

    def add(self, item, **kwargs):
        self._data.append(item)
        return item

    def add_batch(self, models, **kwargs):
        self._data.extend(models)

    def count(self, *args, **kwargs):
        return len(self._data)


class MockOrderCRUD:
    """Mock订单CRUD"""

    def __init__(self):
        self._orders = []

    def find(self, *args, **kwargs):
        return self._orders

    def add(self, order, **kwargs):
        self._orders.append(order)
        return order

    def add_batch(self, orders, **kwargs):
        self._orders.extend(orders)

    def count(self, *args, **kwargs):
        return len(self._orders)


class MockPositionCRUD:
    """Mock持仓CRUD"""

    def __init__(self):
        self._positions = []

    def find(self, *args, **kwargs):
        return self._positions

    def add(self, position, **kwargs):
        self._positions.append(position)
        return position

    def update(self, uuid, data, **kwargs):
        for pos in self._positions:
            if hasattr(pos, 'uuid') and pos.uuid == uuid:
                for key, value in data.items():
                    setattr(pos, key, value)
                break

    def count(self, *args, **kwargs):
        return len(self._positions)


class MockRedisClient:
    """Mock Redis客户端"""

    def __init__(self):
        self._data = {}
        self._sets = {}
        self._hashes = {}

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value, ex=None):
        self._data[key] = value
        return True

    def delete(self, *keys):
        for key in keys:
            self._data.pop(key, None)
            self._sets.pop(key, None)
            self._hashes.pop(key, None)
        return len(keys)

    def exists(self, key):
        return key in self._data or key in self._sets or key in self._hashes

    def sadd(self, key, *values):
        if key not in self._sets:
            self._sets[key] = set()
        self._sets[key].update(values)
        return len(values)

    def srem(self, key, *values):
        if key in self._sets:
            for value in values:
                self._sets[key].discard(value)
        return len(values)

    def smembers(self, key):
        return list(self._sets.get(key, set()))

    def hset(self, key, field, value):
        if key not in self._hashes:
            self._hashes[key] = {}
        self._hashes[key][field] = value
        return 1

    def hget(self, key, field):
        return self._hashes.get(key, {}).get(field)

    def hgetall(self, key):
        return self._hashes.get(key, {}).copy()


class MockClickHouseClient:
    """Mock ClickHouse客户端"""

    def __init__(self):
        self._tables = {}

    def execute(self, query, *args, **kwargs):
        """Mock执行查询"""
        # 简单的SELECT查询模拟
        if 'SELECT' in query.upper():
            return []
        # INSERT查询模拟
        elif 'INSERT' in query.upper():
            return []
        return []

    def execute_iter(self, query, *args, **kwargs):
        """Mock执行迭代查询"""
        return iter([])

    def ping(self):
        """Mock连接检查"""
        return True


# ===== 数据库Mock工厂函数 =====

def create_mock_bar_service():
    """
    创建带MockCRUD的真实BarService

    架构：MockBarCRUD → 真实BarService

    Returns:
        BarService: 使用MockBarCRUD的BarService实例
    """
    from ginkgo.data.services.bar_service import BarService

    # 只Mock CRUD层
    mock_crud = MockBarCRUD()

    # Mock其他必需依赖
    mock_source = MockDataSource()
    mock_stockinfo = MockStockinfoService()
    mock_adjustfactor = MockAdjustfactorService()

    # 依赖注入：使用真实BarService + Mock依赖
    bar_service = BarService(
        crud_repo=mock_crud,
        data_source=mock_source,
        stockinfo_service=mock_stockinfo,
        adjustfactor_service=mock_adjustfactor
    )

    return bar_service


def create_mock_tick_service():
    """
    创建Mock Tick数据服务

    Returns:
        使用Mock TickCRUD的服务实例
    """
    # 由于当前没有独立的TickService，返回MockCRUD
    return MockTickCRUD()


def create_mock_order_service():
    """
    创建Mock订单服务

    Returns:
        使用Mock OrderCRUD的服务实例
    """
    # 由于当前没有独立的OrderService，返回MockCRUD
    return MockOrderCRUD()


def create_mock_position_service():
    """
    创建Mock持仓服务

    Returns:
        使用Mock PositionCRUD的服务实例
    """
    # 由于当前没有独立的PositionService，返回MockCRUD
    return MockPositionCRUD()


# ===== 多数据库Mock环境工厂 =====

def create_mock_clickhouse_environment():
    """
    创建Mock ClickHouse环境

    Returns:
        Dict: 包含Mock ClickHouse客户端和相关配置
    """
    return {
        'client': MockClickHouseClient(),
        'database': 'test_db',
        'host': 'localhost',
        'port': 8123,
        'connected': True
    }


def create_mock_mysql_environment():
    """
    创建Mock MySQL环境

    Returns:
        Dict: 包含Mock MySQL连接和相关配置
    """
    return {
        'connection': MockDataSource(),
        'database': 'test_mysql_db',
        'host': 'localhost',
        'port': 3306,
        'connected': True
    }


def create_mock_redis_environment():
    """
    创建Mock Redis环境

    Returns:
        Dict: 包含Mock Redis客户端和相关配置
    """
    return {
        'client': MockRedisClient(),
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'connected': True
    }


def create_multi_database_mock_environment():
    """
    创建完整的多数据库Mock环境

    Returns:
        Dict: 包含所有数据库Mock环境的字典
    """
    return {
        'clickhouse': create_mock_clickhouse_environment(),
        'mysql': create_mock_mysql_environment(),
        'redis': create_mock_redis_environment(),
        'services': {
            'bar': create_mock_bar_service(),
            'tick': create_mock_tick_service(),
            'order': create_mock_order_service(),
            'position': create_mock_position_service()
        }
    }


# ===== 便利函数 =====

def setup_complete_mock_environment():
    """
    设置完整的Mock测试环境

    这个函数会设置所有必要的Mock对象，适合集成测试使用。

    Returns:
        Dict: 包含所有Mock服务配置的字典
    """
    env = create_multi_database_mock_environment()

    # 添加一些测试数据
    mock_bar_crud = MockBarCRUD()

    return {
        'environment': env,
        'test_data': {
            'bar_crud': mock_bar_crud,
            'sample_codes': ['000001.SZ', '000002.SZ', '600000.SH'],
            'sample_dates': [
                datetime(2023, 1, 3),
                datetime(2023, 1, 4),
                datetime(2023, 1, 5)
            ]
        },
        'config': {
            'debug_mode': True,
            'mock_all_databases': True,
            'use_real_services': True
        }
    }


def reset_all_mocks():
    """
    重置所有Mock对象状态

    这个函数可以在每个测试开始前调用，确保测试隔离。
    """
    # 由于Mock对象都是新创建的，暂时不需要特殊重置逻辑
    pass


# ===== 增强框架Mock支持 =====

class MockEventEnhancedService:
    """Mock事件增强服务"""

    def __init__(self):
        self.event_contexts = {}
        self.event_history = []
        self.performance_metrics = []

    def create_event_context(self, **kwargs):
        """创建事件上下文"""
        context_id = str(uuid.uuid4())
        context = {
            'context_id': context_id,
            'correlation_id': kwargs.get('correlation_id', str(uuid.uuid4())),
            'causation_id': kwargs.get('causation_id'),
            'session_id': kwargs.get('session_id'),
            'trace_depth': kwargs.get('trace_depth', 0),
            'start_time': datetime.now()
        }
        self.event_contexts[context_id] = context
        return context

    def enhance_event(self, event, context=None):
        """增强事件"""
        if context:
            event.correlation_id = context.get('correlation_id')
            event.causation_id = context.get('causation_id')
            event.session_id = context.get('session_id')

        # 添加引擎信息
        event.engine_id = getattr(event, 'engine_id', 'test_engine')
        event.run_id = getattr(event, 'run_id', 'test_run')
        event.sequence_number = len(self.event_history) + 1

        self.event_history.append({
            'event': event,
            'timestamp': datetime.now(),
            'context': context
        })

        return event

    def record_event_metrics(self, event, duration_ms, success=True):
        """记录事件指标"""
        metric = {
            'event_type': getattr(event, 'event_type', 'unknown'),
            'duration_ms': duration_ms,
            'success': success,
            'timestamp': datetime.now()
        }
        self.performance_metrics.append(metric)

    def get_event_statistics(self):
        """获取事件统计"""
        return {
            'total_events': len(self.event_history),
            'performance_metrics': self.performance_metrics[-10:],  # 最近10条
            'active_contexts': len(self.event_contexts)
        }


class MockTimeProviderService:
    """Mock时间提供者服务"""

    def __init__(self):
        self.current_time = datetime(2024, 1, 1, 9, 30, 0)
        self.time_records = []

    def now(self):
        """获取当前时间"""
        return self.current_time

    def advance_time(self, delta):
        """推进时间"""
        self.current_time += delta
        self.time_records.append({
            'old_time': self.current_time - delta,
            'new_time': self.current_time,
            'delta': delta,
            'timestamp': datetime.now()
        })

    def set_time(self, new_time):
        """设置时间"""
        old_time = self.current_time
        self.current_time = new_time
        self.time_records.append({
            'old_time': old_time,
            'new_time': new_time,
            'delta': new_time - old_time,
            'timestamp': datetime.now()
        })

    def is_future_data(self, timestamp):
        """检查是否为未来数据"""
        return timestamp > self.current_time


class MockConfigurationService:
    """Mock配置服务"""

    def __init__(self):
        self.config_data = {
            'engine': {
                'name': 'TestEngine',
                'mode': 'backtest',
                'max_event_queue_size': 1000,
                'event_timeout_seconds': 30.0,
                'enable_performance_monitoring': True,
                'enable_event_storage': False
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
            'performance': {
                'max_memory_usage_mb': 512,
                'enable_profiling': False
            }
        }
        self.watchers = []

    def get_config(self, key=None):
        """获取配置"""
        if key:
            return self.config_data.get(key, {})
        return self.config_data

    def set_config(self, key, value):
        """设置配置"""
        self.config_data[key] = value
        self._notify_watchers(key, value)

    def register_watcher(self, callback):
        """注册配置变更观察者"""
        self.watchers.append(callback)

    def _notify_watchers(self, key, value):
        """通知观察者"""
        for callback in self.watchers:
            try:
                callback({key: value})
            except Exception:
                pass


# ===== 增强框架Mock工厂函数 =====

def create_mock_event_enhanced_service():
    """
    创建Mock事件增强服务

    Returns:
        MockEventEnhancedService: 事件增强服务Mock实例
    """
    return MockEventEnhancedService()


def create_mock_time_provider_service():
    """
    创建Mock时间提供者服务

    Returns:
        MockTimeProviderService: 时间提供者服务Mock实例
    """
    return MockTimeProviderService()


def create_mock_configuration_service():
    """
    创建Mock配置服务

    Returns:
        MockConfigurationService: 配置服务Mock实例
    """
    return MockConfigurationService()


def create_enhanced_framework_mock_environment():
    """
    创建增强框架的完整Mock环境

    Returns:
        Dict: 包含所有增强框架Mock服务的环境
    """
    # 基础多数据库环境
    base_env = create_multi_database_mock_environment()

    # 增强框架服务
    enhanced_services = {
        'event_enhanced': create_mock_event_enhanced_service(),
        'time_provider': create_mock_time_provider_service(),
        'configuration': create_mock_configuration_service()
    }

    return {
        **base_env,
        'enhanced_services': enhanced_services,
        'framework_config': {
            'protocol_interfaces_enabled': True,
            'mixin_features_enabled': True,
            'event_enhancement_enabled': True,
            'time_provider_enabled': True
        }
    }


# ===== 增强框架专用装饰器 =====

def with_enhanced_mock_framework(test_func):
    """
    增强框架Mock装饰器

    为测试函数自动注入完整的增强框架Mock环境。

    Usage:
        @with_enhanced_mock_framework
        def test_enhanced_feature():
            # 可以访问所有增强框架的Mock服务
            pass
    """
    def wrapper(*args, **kwargs):
        # 创建增强框架Mock环境
        enhanced_env = create_enhanced_framework_mock_environment()
        kwargs['enhanced_environment'] = enhanced_env

        try:
            return test_func(*args, **kwargs)
        finally:
            # 清理Mock环境
            pass

    return wrapper


def with_time_travel(start_time=None, time_steps=None):
    """
    时间旅行Mock装饰器

    为测试函数提供时间操控能力。

    Args:
        start_time: 起始时间
        time_steps: 时间步长列表

    Usage:
        @with_time_travel(
            start_time=datetime(2024, 1, 1),
            time_steps=[timedelta(days=1), timedelta(days=2)]
        )
        def test_strategy_over_time():
            # 测试跨越时间的策略行为
            pass
    """
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            # 创建时间提供者Mock
            time_provider = create_mock_time_provider_service()

            if start_time:
                time_provider.set_time(start_time)

            kwargs['time_provider'] = time_provider
            kwargs['time_steps'] = time_steps or []

            try:
                return test_func(*args, **kwargs)
            finally:
                # 记录时间操作历史
                pass

        return wrapper
    return decorator


# ===== 数据库兼容性装饰器 =====

def with_mock_databases(databases: List[str] = None):
    """
    数据库Mock装饰器

    为测试函数自动注入所需数据库的Mock环境。

    Args:
        databases: 需要Mock的数据库列表，如 ['clickhouse', 'mysql', 'redis']

    Usage:
        @with_mock_databases(['clickhouse', 'redis'])
        def test_something_with_databases():
            # 测试代码可以访问mock_ch_client和mock_redis_client
            pass
    """
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            if databases is None:
                databases = ['clickhouse', 'mysql', 'redis']

            # 创建所需数据库的Mock环境
            mock_envs = {}
            for db in databases:
                if db == 'clickhouse':
                    mock_envs['mock_clickhouse'] = create_mock_clickhouse_environment()
                elif db == 'mysql':
                    mock_envs['mock_mysql'] = create_mock_mysql_environment()
                elif db == 'redis':
                    mock_envs['mock_redis'] = create_mock_redis_environment()

            # 将Mock环境注入到测试函数的kwargs中
            kwargs.update(mock_envs)

            try:
                return test_func(*args, **kwargs)
            finally:
                # 清理Mock环境（如果需要）
                pass

        return wrapper
    return decorator
