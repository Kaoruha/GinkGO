"""
Mock数据服务工厂测试

测试Mock工厂的正确性和完整性，确保TDD测试环境的可靠性。
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any

# 导入Mock工厂
from test.fixtures.mock_data_service_factory import (
    MockDataSource, MockStockinfoService, MockBarCRUD,
    MockRedisClient, MockClickHouseClient,
    create_mock_bar_service, create_mock_tick_service,
    create_multi_database_mock_environment,
    create_enhanced_framework_mock_environment,
    MockEventEnhancedService, MockTimeProviderService,
    with_enhanced_mock_framework, with_time_travel
)


@pytest.mark.tdd
@pytest.mark.fixtures
class TestMockBasicServices:
    """基础Mock服务测试"""

    def test_mock_data_source_functionality(self):
        """测试Mock数据源功能"""
        source = MockDataSource()

        # 测试连接功能
        assert source.connect() == True, "连接应该成功"
        assert source.disconnect() is None, "断开连接不应该返回值"
        assert source.is_connected() == True, "应该显示已连接"

    def test_mock_stockinfo_service(self):
        """测试Mock股票信息服务"""
        service = MockStockinfoService()

        # 测试代码验证
        assert service.is_code_in_stocklist("000001.SZ") == True, "默认应该接受所有代码"
        assert service.is_code_in_stocklist("INVALID") == True, "应该接受任何代码"

        # 测试获取股票信息
        stocks = service.get_stockinfos()
        assert isinstance(stocks, list), "应该返回列表"
        assert len(stocks) == 0, "默认应该返回空列表"

        # 测试同步操作
        assert service.sync_all() == True, "同步应该成功"

    def test_mock_bar_crud(self):
        """测试Mock Bar数据CRUD"""
        crud = MockBarCRUD()

        # 测试数据添加
        test_bar = {"code": "000001.SZ", "close": 10.50}
        result = crud.add(test_bar)
        assert result == test_bar, "添加应该返回相同对象"

        # 测试批量添加
        bars = [
            {"code": "000001.SZ", "close": 10.50},
            {"code": "000002.SZ", "close": 15.25}
        ]
        crud.add_batch(bars)
        assert len(crud._data) == 3, "应该有3条数据"  # 包括之前添加的1条

        # 测试查询
        found = crud.find(code="000001.SZ")
        assert len(found) > 0, "应该找到数据"

        # 测试计数
        count = crud.count()
        assert count == 3, "应该返回正确计数"

    def test_mock_redis_client(self):
        """测试Mock Redis客户端"""
        redis = MockRedisClient()

        # 测试字符串操作
        assert redis.get("nonexistent") is None, "不存在的键应该返回None"
        assert redis.set("test_key", "test_value") == True, "设置应该成功"
        assert redis.get("test_key") == "test_value", "获取应该返回正确值"
        assert redis.delete("test_key") == 1, "删除应该成功"

        # 测试集合操作
        assert redis.sadd("test_set", "member1", "member2") == 2, "添加集合成员应该成功"
        members = redis.smembers("test_set")
        assert set(members) == {"member1", "member2"}, "应该返回正确成员"
        assert redis.srem("test_set", "member1") == 1, "移除成员应该成功"

        # 测试哈希操作
        assert redis.hset("test_hash", "field1", "value1") == 1, "设置哈希字段应该成功"
        assert redis.hget("test_hash", "field1") == "value1", "获取哈希字段应该成功"
        hash_all = redis.hgetall("test_hash")
        assert hash_all == {"field1": "value1"}, "获取所有哈希字段应该成功"

    def test_mock_clickhouse_client(self):
        """测试Mock ClickHouse客户端"""
        client = MockClickHouseClient()

        # 测试查询执行
        result = client.execute("SELECT * FROM test_table")
        assert isinstance(result, list), "查询应该返回列表"

        # 测试迭代查询
        result_iter = client.execute_iter("SELECT * FROM test_table")
        assert list(result_iter) == [], "迭代查询应该返回空列表"

        # 测试ping
        assert client.ping() == True, "ping应该成功"


@pytest.mark.tdd
@pytest.mark.fixtures
class TestMockServiceFactory:
    """Mock服务工厂测试"""

    def test_create_mock_bar_service(self):
        """测试创建Mock Bar服务"""
        service = create_mock_bar_service()

        assert service is not None, "应该创建成功的服务"
        assert hasattr(service, 'crud_repo'), "应该有CRUD仓库"
        assert hasattr(service, 'data_source'), "应该有数据源"
        assert hasattr(service, 'stockinfo_service'), "应该有股票信息服务"
        assert hasattr(service, 'adjustfactor_service'), "应该有复权因子服务"

    def test_create_mock_tick_service(self):
        """测试创建Mock Tick服务"""
        service = create_mock_tick_service()

        assert service is not None, "应该创建成功的服务"
        assert hasattr(service, 'find'), "应该有查询方法"
        assert hasattr(service, 'add'), "应该有添加方法"

    def test_create_multi_database_mock_environment(self):
        """测试创建多数据库Mock环境"""
        env = create_multi_database_mock_environment()

        # 验证环境结构
        assert 'clickhouse' in env, "应该包含ClickHouse环境"
        assert 'mysql' in env, "应该包含MySQL环境"
        assert 'redis' in env, "应该包含Redis环境"
        assert 'services' in env, "应该包含服务配置"

        # 验证服务配置
        services = env['services']
        assert 'bar' in services, "应该包含Bar服务"
        assert 'tick' in services, "应该包含Tick服务"
        assert 'order' in services, "应该包含Order服务"
        assert 'position' in services, "应该包含Position服务"

        # 验证数据库连接
        assert env['clickhouse']['connected'] == True, "ClickHouse应该已连接"
        assert env['mysql']['connected'] == True, "MySQL应该已连接"
        assert env['redis']['connected'] == True, "Redis应该已连接"


@pytest.mark.tdd
@pytest.mark.fixtures
class TestEnhancedFrameworkMockServices:
    """增强框架Mock服务测试"""

    def test_mock_event_enhanced_service(self):
        """测试Mock事件增强服务"""
        service = MockEventEnhancedService()

        # 测试创建事件上下文
        context = service.create_event_context(
            correlation_id="test_corr",
            session_id="test_session"
        )
        assert context is not None, "应该创建上下文"
        assert 'context_id' in context, "应该有上下文ID"
        assert context['correlation_id'] == "test_corr", "关联ID应该正确"

        # 测试事件增强
        mock_event = {"code": "000001.SZ", "price": 10.50}
        enhanced_event = service.enhance_event(mock_event, context)
        assert enhanced_event is not None, "应该增强事件"
        assert hasattr(enhanced_event, 'correlation_id'), "应该有关联ID"
        assert hasattr(enhanced_event, 'engine_id'), "应该有引擎ID"
        assert hasattr(enhanced_event, 'sequence_number'), "应该有序列号"

        # 测试事件指标记录
        service.record_event_metrics(enhanced_event, 50.5, success=True)
        assert len(service.performance_metrics) == 1, "应该记录1个指标"
        assert service.performance_metrics[0]['duration_ms'] == 50.5, "应该记录持续时间"

        # 测试统计信息
        stats = service.get_event_statistics()
        assert stats['total_events'] == 1, "应该有1个事件"
        assert stats['active_contexts'] == 1, "应该有1个活跃上下文"

    def test_mock_time_provider_service(self):
        """测试Mock时间提供者服务"""
        service = MockTimeProviderService()

        # 测试初始时间
        initial_time = service.now()
        assert isinstance(initial_time, datetime), "应该返回datetime对象"
        assert initial_time.year == 2024, "默认年份应该是2024"

        # 测试时间推进
        original_time = service.now()
        service.advance_time(timedelta(hours=1))
        new_time = service.now()
        assert new_time > original_time, "时间应该推进"
        assert new_time - original_time == timedelta(hours=1), "推进时间应该正确"

        # 测试时间设置
        test_time = datetime(2024, 12, 25, 10, 30, 0)
        service.set_time(test_time)
        assert service.now() == test_time, "设置的时间应该生效"

        # 测试未来数据检查
        past_time = test_time - timedelta(days=1)
        future_time = test_time + timedelta(days=1)
        assert service.is_future_data(past_time) == False, "过去时间不应该是未来数据"
        assert service.is_future_data(future_time) == True, "未来时间应该是未来数据"

        # 测试时间记录
        assert len(service.time_records) == 2, "应该有2条时间记录"  # advance_time + set_time

    def test_create_enhanced_framework_mock_environment(self):
        """测试创建增强框架Mock环境"""
        env = create_enhanced_framework_mock_environment()

        # 验证基础环境
        assert 'clickhouse' in env, "应该包含基础数据库环境"
        assert 'mysql' in env, "应该包含基础数据库环境"
        assert 'redis' in env, "应该包含基础数据库环境"

        # 验证增强服务
        assert 'enhanced_services' in env, "应该包含增强服务"
        enhanced_services = env['enhanced_services']
        assert 'event_enhanced' in enhanced_services, "应该包含事件增强服务"
        assert 'time_provider' in enhanced_services, "应该包含时间提供者服务"
        assert 'configuration' in enhanced_services, "应该包含配置服务"

        # 验证框架配置
        assert 'framework_config' in env, "应该包含框架配置"
        config = env['framework_config']
        assert config['protocol_interfaces_enabled'] == True, "应该启用Protocol接口"
        assert config['mixin_features_enabled'] == True, "应该启用Mixin功能"
        assert config['event_enhancement_enabled'] == True, "应该启用事件增强"
        assert config['time_provider_enabled'] == True, "应该启用时间提供者"


@pytest.mark.tdd
@pytest.mark.fixtures
class TestMockDecorators:
    """Mock装饰器测试"""

    def test_with_enhanced_mock_framework_decorator(self):
        """测试增强框架Mock装饰器"""

        @with_enhanced_mock_framework
        def test_function(arg1, arg2, enhanced_environment=None):
            assert enhanced_environment is not None, "应该注入增强环境"
            assert 'enhanced_services' in enhanced_environment, "应该包含增强服务"
            assert 'framework_config' in enhanced_environment, "应该包含框架配置"
            return f"result_{arg1}_{arg2}"

        result = test_function("test1", "test2")
        assert result == "result_test1_test2", "应该返回正确结果"

    def test_with_time_travel_decorator(self):
        """测试时间旅行装饰器"""

        @with_time_travel(
            start_time=datetime(2024, 1, 1, 9, 30, 0),
            time_steps=[timedelta(days=1), timedelta(days=2)]
        )
        def test_function(time_provider=None, time_steps=None):
            assert time_provider is not None, "应该注入时间提供者"
            assert time_steps is not None, "应该注入时间步长"
            assert len(time_steps) == 2, "应该有2个时间步长"

            initial_time = time_provider.now()
            assert initial_time == datetime(2024, 1, 1, 9, 30, 0), "初始时间应该正确"

            # 测试时间推进
            time_provider.advance_time(time_steps[0])
            advanced_time = time_provider.now()
            assert advanced_time - initial_time == time_steps[0], "时间推进应该正确"

            return time_provider

        result_time_provider = test_function()
        assert result_time_provider is not None, "应该返回时间提供者"


@pytest.mark.tdd
@pytest.mark.fixtures
class TestMockFactoryEdgeCases:
    """Mock工厂边界情况测试"""

    def test_mock_service_error_handling(self):
        """测试Mock服务错误处理"""
        redis = MockRedisClient()

        # 测试无效操作
        assert redis.get("nonexistent") is None, "获取不存在的键应该返回None"
        assert redis.delete("nonexistent") == 0, "删除不存在的键应该返回0"

        # 测试空操作
        assert redis.srem("nonexistent_set", "member") == 0, "从不存在的集合移除应该返回0"
        assert redis.hget("nonexistent_hash", "field") is None, "从不存在的哈希获取应该返回None"

    def test_mock_factory_with_invalid_inputs(self):
        """测试Mock工厂处理无效输入"""
        service = create_mock_bar_service()

        # 测试空数据
        result = service.crud_repo.find(nonexistent_field="value")
        assert isinstance(result, list), "查询应该返回列表"

        # 测试无效参数
        try:
            service.crud_repo.add(None)  # 应该能处理None
        except Exception as e:
            # 如果有异常，应该是预期的
            assert isinstance(e, (TypeError, AttributeError))

    def test_concurrent_access_to_mock_services(self):
        """测试Mock服务的并发访问"""
        import threading
        import time

        redis = MockRedisClient()
        results = []
        errors = []

        def worker(worker_id):
            try:
                for i in range(10):
                    key = f"worker_{worker_id}_key_{i}"
                    value = f"worker_{worker_id}_value_{i}"
                    redis.set(key, value)
                    retrieved = redis.get(key)
                    if retrieved == value:
                        results.append(worker_id)
                    time.sleep(0.001)  # 模拟处理时间
            except Exception as e:
                errors.append((worker_id, e))

        # 启动多个工作线程
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证结果
        assert len(errors) == 0, f"并发访问不应该产生错误: {errors}"
        assert len(results) == 50, "应该有50个成功操作"

    def test_mock_service_memory_management(self):
        """测试Mock服务的内存管理"""
        service = MockEventEnhancedService()

        # 创建大量事件上下文
        for i in range(100):
            service.create_event_context(
                correlation_id=f"corr_{i}",
                session_id=f"session_{i}"
            )

        # 验证内存使用
        assert len(service.event_contexts) == 100, "应该有100个上下文"

        # 模拟清理（如果实现了清理逻辑）
        # 这里只是验证当前状态
        stats = service.get_event_statistics()
        assert stats['active_contexts'] == 100, "统计应该反映实际状态"


# ===== TDD阶段标记 =====

def tdd_phase(phase: str):
    """TDD阶段标记装饰器"""
    def decorator(test_func):
        test_func.tdd_phase = phase
        return test_func
    return decorator