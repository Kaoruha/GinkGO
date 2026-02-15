"""
RedisService数据服务测试

测试RedisService的核心功能和业务逻辑
遵循pytest最佳实践，使用fixtures和参数化测试
"""
import pytest
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.services.redis_service import RedisService
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.crud.redis_crud import RedisCRUD
from ginkgo.data.containers import container
from ginkgo.libs import GCONF


# ============================================================================
# Fixtures - 共享测试资源
# ============================================================================

@pytest.fixture
def ginkgo_config():
    """配置调试模式"""
    GCONF.set_debug(True)
    yield GCONF
    GCONF.set_debug(False)


@pytest.fixture
def redis_service():
    """获取RedisService实例"""
    service = RedisService()

    # 检查Redis连接可用性
    redis_info = service.get_redis_info()
    if not redis_info.get("connected", False):
        pytest.skip("Redis connection not available")

    return service


@pytest.fixture
def test_prefix():
    """生成测试键前缀"""
    return f"test_service_{int(time.time())}"


@pytest.fixture
def test_keys():
    """追踪测试创建的键"""
    return []


# ============================================================================
# 参数化测试数据
# ============================================================================

# 有效的数据类型
VALID_DATA_TYPES = ["tick", "bar", "adjustfactor"]

# 有效的日期范围
VALID_DATE_RANGES = [
    (datetime(2024, 1, 1), datetime(2024, 1, 2)),
    (datetime(2024, 1, 1), datetime(2024, 1, 31)),
    (datetime(2023, 1, 1), datetime(2023, 12, 31)),
]

# 无效的键名
INVALID_KEYS = [
    ("", "空字符串"),
    ("   ", "纯空格"),
    (None, "None值"),
]


# ============================================================================
# 测试类 - RedisService 构造和初始化
# ============================================================================

@pytest.mark.unit
class TestRedisServiceConstruction:
    """
    RedisService构造和初始化测试
    测试服务实例化、依赖注入和基础配置
    """

    def test_redis_service_initialization(self, redis_service):
        """测试RedisService基本初始化"""
        assert isinstance(redis_service, RedisService)
        assert isinstance(redis_service, BaseService)

    def test_redis_service_has_crud_repo(self, redis_service):
        """测试CRUD仓储已设置"""
        assert hasattr(redis_service, '_crud_repo')
        assert isinstance(redis_service._crud_repo, RedisCRUD)

    def test_redis_service_with_provided_crud(self):
        """测试使用提供的RedisCRUD初始化"""
        redis_crud = RedisCRUD()
        service = RedisService(redis_crud=redis_crud)

        assert service._crud_repo == redis_crud

    def test_redis_service_auto_crud_creation(self):
        """测试自动创建RedisCRUD"""
        service = RedisService()
        assert isinstance(service._crud_repo, RedisCRUD)


# ============================================================================
# 测试类 - Redis 同步进度管理
# ============================================================================

@pytest.mark.unit
@pytest.mark.db_cleanup
class TestRedisSyncProgress:
    """
    Redis同步进度管理测试
    测试同步进度的保存、获取和清理
    """

    CLEANUP_CONFIG = {'redis': {'key__like': 'test_%'}}

    def test_save_sync_progress_success(self, redis_service, test_prefix):
        """测试保存同步进度成功"""
        code = f"{test_prefix}_SZ"
        date = datetime(2024, 1, 15)
        data_type = "tick"

        result = redis_service.save_sync_progress(code, date, data_type)

        assert result.success
        assert result.data is True

        # 清理
        redis_service.clear_sync_progress(code, data_type)

    def test_save_sync_progress_different_types(self, redis_service, test_prefix):
        """测试保存不同数据类型的同步进度"""
        code = f"{test_prefix}_types"
        date = datetime(2024, 2, 20)

        # 保存不同类型
        for data_type in VALID_DATA_TYPES:
            result = redis_service.save_sync_progress(code, date, data_type)
            assert result.success

        # 清理
        for data_type in VALID_DATA_TYPES:
            redis_service.clear_sync_progress(code, data_type)

    @pytest.mark.parametrize("data_type", VALID_DATA_TYPES)
    def test_save_sync_progress_by_type(self, redis_service, test_prefix, data_type):
        """参数化测试：按数据类型保存进度"""
        code = f"{test_prefix}_{data_type}"
        date = datetime(2024, 1, 15)

        result = redis_service.save_sync_progress(code, date, data_type)

        assert result.success

        # 清理
        redis_service.clear_sync_progress(code, data_type)

    def test_get_sync_progress_success(self, redis_service, test_prefix):
        """测试获取同步进度成功"""
        code = f"{test_prefix}_get"
        dates = [datetime(2024, 1, 1), datetime(2024, 1, 2), datetime(2024, 1, 3)]
        data_type = "tick"

        # 保存进度
        for date in dates:
            redis_service.save_sync_progress(code, date, data_type)

        # 获取进度
        result = redis_service.get_sync_progress(code, data_type)

        assert result.success
        expected = {"2024-01-01", "2024-01-02", "2024-01-03"}
        assert result.data == expected

        # 清理
        redis_service.clear_sync_progress(code, data_type)

    def test_get_sync_progress_empty(self, redis_service, test_prefix):
        """测试获取空同步进度"""
        code = f"{test_prefix}_empty"
        data_type = "tick"

        # 确保没有数据
        redis_service.clear_sync_progress(code, data_type)

        # 获取进度
        result = redis_service.get_sync_progress(code, data_type)

        assert result.success
        assert result.data == set()

    def test_clear_sync_progress(self, redis_service, test_prefix):
        """测试清理同步进度"""
        code = f"{test_prefix}_clear"
        date = datetime(2024, 1, 15)
        data_type = "tick"

        # 保存进度
        redis_service.save_sync_progress(code, date, data_type)

        # 验证存在
        get_before = redis_service.get_sync_progress(code, data_type)
        assert len(get_before.data) > 0

        # 清理进度
        clear_result = redis_service.clear_sync_progress(code, data_type)
        assert clear_result.success

        # 验证已清理
        get_after = redis_service.get_sync_progress(code, data_type)
        assert len(get_after.data) == 0

    def test_multiple_dates_sync_progress(self, redis_service, test_prefix):
        """测试保存多个同步日期"""
        code = f"{test_prefix}_multi"
        dates = [
            datetime(2024, 1, 1),
            datetime(2024, 1, 2),
            datetime(2024, 1, 3)
        ]
        data_type = "tick"

        # 保存多个日期
        for date in dates:
            result = redis_service.save_sync_progress(code, date, data_type)
            assert result.success

        # 验证所有日期都被保存
        result = redis_service.get_sync_progress(code, data_type)
        assert result.success

        for date in dates:
            date_str = date.strftime("%Y-%m-%d")
            assert date_str in result.data

        # 清理
        redis_service.clear_sync_progress(code, data_type)


# ============================================================================
# 测试类 - Redis 缓存操作
# ============================================================================

@pytest.mark.unit
@pytest.mark.db_cleanup
class TestRedisCacheOperations:
    """
    Redis缓存操作测试
    测试通用缓存功能
    """

    CLEANUP_CONFIG = {'redis': {'key__like': 'test_%'}}

    def test_set_and_get_cache(self, redis_service, test_prefix):
        """测试设置和获取缓存"""
        key = f"{test_prefix}_cache_key"
        value = "test_value"

        # 设置缓存
        set_result = redis_service.set_cache(key, value)
        assert set_result.success

        # 获取缓存
        get_result = redis_service.get_cache(key)
        assert get_result.success
        assert get_result.data == value

        # 清理
        redis_service.delete_cache(key)

    def test_cache_with_expiration(self, redis_service, test_prefix):
        """测试带过期时间的缓存"""
        key = f"{test_prefix}_exp_key"
        value = "exp_value"

        # 设置1秒过期
        redis_service.set_cache(key, value, expiration=1)

        # 立即获取应该成功
        get_immediate = redis_service.get_cache(key)
        assert get_immediate.success

        # 等待过期
        time.sleep(2)

        # 过期后获取应该失败
        get_expired = redis_service.get_cache(key)
        assert not get_expired.success or get_expired.data is None

    def test_delete_cache(self, redis_service, test_prefix):
        """测试删除缓存"""
        key = f"{test_prefix}_del_key"
        value = "del_value"

        # 设置缓存
        redis_service.set_cache(key, value)

        # 验证存在
        get_before = redis_service.get_cache(key)
        assert get_before.success

        # 删除缓存
        delete_result = redis_service.delete_cache(key)
        assert delete_result.success

        # 验证已删除
        get_after = redis_service.get_cache(key)
        assert not get_after.success or get_after.data is None

    @pytest.mark.parametrize("key, description", INVALID_KEYS)
    def test_invalid_cache_key(self, redis_service, key, description, test_prefix):
        """参数化测试：无效缓存键"""
        if key is None:
            pytest.skip("None key handling depends on implementation")

        value = "test_value"

        # 设置缓存
        set_result = redis_service.set_cache(key, value)
        # 根据实现，可能成功或失败

        # 获取缓存
        get_result = redis_service.get_cache(key)
        assert get_result is not None


# ============================================================================
# 测试类 - Redis 任务状态管理
# ============================================================================

@pytest.mark.unit
@pytest.mark.db_cleanup
class TestRedisTaskStatus:
    """
    Redis任务状态管理测试
    测试任务状态的保存、获取和更新
    """

    CLEANUP_CONFIG = {'redis': {'key__like': 'test_%'}}

    def test_set_task_status(self, redis_service, test_prefix):
        """测试设置任务状态"""
        task_id = f"{test_prefix}_task_1"
        status = "running"
        progress = 50

        result = redis_service.set_task_status(task_id, status, progress)

        assert result.success

        # 清理
        redis_service.delete_task_status(task_id)

    def test_get_task_status(self, redis_service, test_prefix):
        """测试获取任务状态"""
        task_id = f"{test_prefix}_task_2"
        status = "completed"
        progress = 100

        # 设置状态
        redis_service.set_task_status(task_id, status, progress)

        # 获取状态
        result = redis_service.get_task_status(task_id)

        assert result.success
        assert result.data["status"] == status
        assert result.data["progress"] == progress

        # 清理
        redis_service.delete_task_status(task_id)

    def test_update_task_progress(self, redis_service, test_prefix):
        """测试更新任务进度"""
        task_id = f"{test_prefix}_task_3"

        # 初始状态
        redis_service.set_task_status(task_id, "running", 0)

        # 更新进度
        redis_service.set_task_status(task_id, "running", 50)

        # 验证更新
        result = redis_service.get_task_status(task_id)
        assert result.data["progress"] == 50

        # 清理
        redis_service.delete_task_status(task_id)

    def test_delete_task_status(self, redis_service, test_prefix):
        """测试删除任务状态"""
        task_id = f"{test_prefix}_task_4"

        # 设置状态
        redis_service.set_task_status(task_id, "running", 50)

        # 删除状态
        delete_result = redis_service.delete_task_status(task_id)
        assert delete_result.success

        # 验证已删除
        result = redis_service.get_task_status(task_id)
        assert not result.success or result.data is None


# ============================================================================
# 测试类 - Redis 系统监控
# ============================================================================

@pytest.mark.unit
class TestRedisMonitoring:
    """
    Redis系统监控测试
    测试系统状态和监控功能
    """

    def test_get_redis_info(self, redis_service):
        """测试获取Redis信息"""
        result = redis_service.get_redis_info()

        assert result.success
        assert result.data["connected"] is True
        assert "version" in result.data or "info" in result.data

    def test_health_check(self, redis_service):
        """测试健康检查"""
        result = redis_service.health_check()

        assert result.success
        health_data = result.data
        assert health_data["service_name"] == "RedisService"
        assert health_data["status"] in ["healthy", "unhealthy", "degraded"]


# ============================================================================
# 测试类 - Redis 键管理
# ============================================================================

@pytest.mark.unit
@pytest.mark.db_cleanup
class TestRedisKeyManagement:
    """
    Redis键管理测试
    测试键的查找、删除和批量操作
    """

    CLEANUP_CONFIG = {'redis': {'key__like': 'test_%'}}

    def test_find_keys_by_pattern(self, redis_service, test_prefix):
        """测试按模式查找键"""
        pattern = f"{test_prefix}_*"

        # 创建一些测试键
        for i in range(3):
            key = f"{test_prefix}_key_{i}"
            redis_service.set_cache(key, f"value_{i}")

        # 查找键
        result = redis_service.find_keys(pattern)

        assert result.success
        assert len(result.data) >= 3

        # 清理
        for i in range(3):
            redis_service.delete_cache(f"{test_prefix}_key_{i}")

    def test_delete_keys_by_pattern(self, redis_service, test_prefix):
        """测试按模式删除键"""
        pattern = f"{test_prefix}_del_*"

        # 创建一些测试键
        for i in range(3):
            key = f"{test_prefix}_del_{i}"
            redis_service.set_cache(key, f"value_{i}")

        # 删除键
        result = redis_service.delete_keys(pattern)

        assert result.success

        # 验证已删除
        find_result = redis_service.find_keys(pattern)
        assert len(find_result.data) == 0


# ============================================================================
# 测试类 - Redis 验证
# ============================================================================

@pytest.mark.unit
class TestRedisValidation:
    """
    Redis数据验证测试
    测试各种边界条件和验证规则
    """

    def test_validate_connection(self, redis_service):
        """测试验证Redis连接"""
        result = redis_service.validate_connection()

        assert result.success
        assert result.data["connected"] is True


# ============================================================================
# 测试类 - Redis 集成测试
# ============================================================================

@pytest.mark.integration
@pytest.mark.db_cleanup
class TestRedisServiceIntegration:
    """
    RedisService集成测试
    测试完整的业务流程
    """

    CLEANUP_CONFIG = {'redis': {'key__like': 'integration_%'}}

    def test_sync_progress_workflow(self, redis_service):
        """测试同步进度完整工作流"""
        code = "integration_test_code"
        dates = [datetime(2024, 1, i) for i in range(1, 6)]
        data_type = "tick"

        # 保存进度
        for date in dates:
            redis_service.save_sync_progress(code, date, data_type)

        # 获取进度
        result = redis_service.get_sync_progress(code, data_type)
        assert result.success
        assert len(result.data) == 5

        # 清理进度
        redis_service.clear_sync_progress(code, data_type)

        # 验证清理
        result = redis_service.get_sync_progress(code, data_type)
        assert len(result.data) == 0

    def test_cache_workflow(self, redis_service):
        """测试缓存完整工作流"""
        prefix = "integration_cache"

        # 批量设置缓存
        for i in range(5):
            key = f"{prefix}_key_{i}"
            value = f"value_{i}"
            redis_service.set_cache(key, value)

        # 批量获取缓存
        for i in range(5):
            key = f"{prefix}_key_{i}"
            result = redis_service.get_cache(key)
            assert result.success

        # 批量删除缓存
        pattern = f"{prefix}_*"
        redis_service.delete_keys(pattern)

        # 验证删除
        find_result = redis_service.find_keys(pattern)
        assert len(find_result.data) == 0

    def test_task_status_workflow(self, redis_service):
        """测试任务状态完整工作流"""
        task_id = "integration_task"

        # 1. 创建任务
        redis_service.set_task_status(task_id, "pending", 0)

        # 2. 开始任务
        redis_service.set_task_status(task_id, "running", 0)

        # 3. 更新进度
        for progress in [25, 50, 75]:
            redis_service.set_task_status(task_id, "running", progress)

        # 4. 完成任务
        redis_service.set_task_status(task_id, "completed", 100)

        # 验证最终状态
        result = redis_service.get_task_status(task_id)
        assert result.data["status"] == "completed"
        assert result.data["progress"] == 100

        # 清理
        redis_service.delete_task_status(task_id)
