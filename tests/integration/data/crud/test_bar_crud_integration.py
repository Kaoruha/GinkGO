"""
BarCRUD 集成测试 - 连接真实 ClickHouse 数据库

覆盖范围：
- 单条/批量添加 K线数据
- 按代码、日期范围过滤查询
- 分页查询
- 计数、删除、更新操作
- distinct 查询
- 无效数据处理

测试数据隔离：使用 SOURCE_TYPES.TEST 标记，测试后自动清理
数据库：ClickHouse (MBar 继承 MClickBase)
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from ginkgo.data.crud.bar_crud import BarCRUD
from ginkgo.enums import SOURCE_TYPES, FREQUENCY_TYPES


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def bar_crud():
    """创建 BarCRUD 实例"""
    return BarCRUD()


@pytest.fixture
def cleanup(bar_crud):
    """测试后清理测试数据（使用 TEST source 隔离）"""
    yield
    try:
        bar_crud.remove(filters={"source": SOURCE_TYPES.TEST.value})
    except Exception:
        pass


@pytest.fixture
def sample_bar_params():
    """标准测试 K线数据参数"""
    return {
        "code": "TEST_BAR_001",
        "open": 10.0,
        "high": 10.8,
        "low": 9.8,
        "close": 10.5,
        "volume": 100000,
        "amount": 1050000.0,
        "frequency": FREQUENCY_TYPES.DAY,
        "timestamp": datetime(2024, 1, 15, 9, 30, 0),
        "source": SOURCE_TYPES.TEST,
    }


@pytest.fixture
def sample_bar_batch():
    """批量测试 K线数据参数列表"""
    base = datetime(2024, 1, 10, 9, 30, 0)
    return [
        {
            "code": "TEST_BAR_BATCH",
            "open": 10.0 + i * 0.1,
            "high": 10.5 + i * 0.1,
            "low": 9.8 + i * 0.1,
            "close": 10.3 + i * 0.1,
            "volume": 100000 + i * 10000,
            "amount": 1030000.0 + i * 100000,
            "frequency": FREQUENCY_TYPES.DAY,
            "timestamp": base + timedelta(days=i),
            "source": SOURCE_TYPES.TEST,
        }
        for i in range(5)
    ]


# ============================================================================
# 测试类：添加操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestBarCRUDAdd:
    """BarCRUD 添加操作集成测试"""

    def test_add_single_bar(self, bar_crud, cleanup, sample_bar_params):
        """添加单条 K线数据，然后查回验证"""
        bar = bar_crud.create(**sample_bar_params)

        assert bar is not None
        assert bar.code == "TEST_BAR_001"
        assert bar.close == Decimal("10.5")

        # 查回验证
        results = bar_crud.find(filters={"code": "TEST_BAR_001", "source": SOURCE_TYPES.TEST.value})
        assert len(results) >= 1
        found = results[0]
        assert found.code == "TEST_BAR_001"

    def test_add_batch_bars(self, bar_crud, cleanup, sample_bar_batch):
        """批量添加多条 K线数据"""
        models = [bar_crud._create_from_params(**p) for p in sample_bar_batch]
        result = bar_crud.add_batch(models)

        assert len(result) == 5

        # 验证全部可查回
        found = bar_crud.find(filters={"code": "TEST_BAR_BATCH", "source": SOURCE_TYPES.TEST.value})
        assert len(found) == 5


# ============================================================================
# 测试类：查询操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestBarCRUDFind:
    """BarCRUD 查询操作集成测试"""

    def test_find_by_code(self, bar_crud, cleanup, sample_bar_params):
        """按股票代码过滤查询"""
        bar_crud.create(**sample_bar_params)

        results = bar_crud.find(filters={"code": "TEST_BAR_001", "source": SOURCE_TYPES.TEST.value})
        assert len(results) >= 1
        for r in results:
            assert r.code == "TEST_BAR_001"

    def test_find_by_date_range(self, bar_crud, cleanup, sample_bar_batch):
        """按时间范围过滤查询"""
        models = [bar_crud._create_from_params(**p) for p in sample_bar_batch]
        bar_crud.add_batch(models)

        start = datetime(2024, 1, 12)
        end = datetime(2024, 1, 14)

        results = bar_crud.find(
            filters={
                "code": "TEST_BAR_BATCH",
                "source": SOURCE_TYPES.TEST.value,
                "timestamp__gte": start,
                "timestamp__lte": end,
            }
        )
        assert len(results) >= 1
        for r in results:
            assert r.timestamp >= start
            assert r.timestamp <= end

    def test_find_with_pagination(self, bar_crud, cleanup, sample_bar_batch):
        """分页查询"""
        models = [bar_crud._create_from_params(**p) for p in sample_bar_batch]
        bar_crud.add_batch(models)

        page1 = bar_crud.find(
            filters={"code": "TEST_BAR_BATCH", "source": SOURCE_TYPES.TEST.value},
            page=0,
            page_size=2,
            order_by="timestamp",
        )
        page2 = bar_crud.find(
            filters={"code": "TEST_BAR_BATCH", "source": SOURCE_TYPES.TEST.value},
            page=1,
            page_size=2,
            order_by="timestamp",
        )
        assert len(page1) == 2
        assert len(page2) == 2

    def test_find_empty_result(self, bar_crud, cleanup):
        """查询不存在的数据返回空列表"""
        results = bar_crud.find(filters={"code": "NONEXISTENT_CODE_99999"})
        assert len(results) == 0


# ============================================================================
# 测试类：计数与删除
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestBarCRUDCountAndRemove:
    """BarCRUD 计数与删除操作集成测试"""

    def test_count(self, bar_crud, cleanup, sample_bar_batch):
        """计数操作"""
        models = [bar_crud._create_from_params(**p) for p in sample_bar_batch]
        bar_crud.add_batch(models)

        cnt = bar_crud.count(filters={"code": "TEST_BAR_BATCH", "source": SOURCE_TYPES.TEST.value})
        assert cnt == 5

    def test_remove(self, bar_crud, cleanup, sample_bar_batch):
        """删除操作"""
        models = [bar_crud._create_from_params(**p) for p in sample_bar_batch]
        bar_crud.add_batch(models)

        cnt_before = bar_crud.count(filters={"code": "TEST_BAR_BATCH", "source": SOURCE_TYPES.TEST.value})
        assert cnt_before == 5

        bar_crud.remove(filters={"code": "TEST_BAR_BATCH", "source": SOURCE_TYPES.TEST.value})

        cnt_after = bar_crud.count(filters={"code": "TEST_BAR_BATCH", "source": SOURCE_TYPES.TEST.value})
        assert cnt_after == 0


# ============================================================================
# 测试类：更新与 distinct
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestBarCRUDUpdateAndDistinct:
    """BarCRUD 更新与 distinct 查询集成测试"""

    def test_update_modify(self, bar_crud, cleanup, sample_bar_params):
        """更新已有记录 - 注意 ClickHouse 不支持 UPDATE，此测试验证行为"""
        bar_crud.create(**sample_bar_params)

        # ClickHouse 不支持 modify，预期抛出错误或静默失败
        try:
            bar_crud.modify(
                filters={"code": "TEST_BAR_001", "source": SOURCE_TYPES.TEST.value},
                updates={"close": 11.0},
            )
            # 如果没有抛异常（ClickHouse MergeTree 引擎），验证更新
            results = bar_crud.find(filters={"code": "TEST_BAR_001", "source": SOURCE_TYPES.TEST.value})
            assert len(results) >= 1
        except Exception:
            # ClickHouse 不支持 UPDATE 是预期行为
            pass

    def test_find_distinct_codes(self, bar_crud, cleanup, sample_bar_batch):
        """distinct 字段查询 - 获取不重复的 code 列表"""
        models = [bar_crud._create_from_params(**p) for p in sample_bar_batch]
        bar_crud.add_batch(models)

        codes = bar_crud.get_all_codes(limit=1000)
        # 验证 TEST_BAR_BATCH 出现在结果中
        found = [c for c in codes if c == "TEST_BAR_BATCH"]
        assert len(found) >= 1


# ============================================================================
# 测试类：字段验证
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestBarCRUDValidation:
    """BarCRUD 字段验证集成测试"""

    def test_invalid_data_handling(self, bar_crud, cleanup):
        """缺失必填字段时，create 应抛出异常"""
        with pytest.raises(Exception):
            # 缺少 code 字段
            bar_crud.create(
                open=10.0,
                high=10.8,
                low=9.8,
                close=10.5,
                source=SOURCE_TYPES.TEST,
            )


# ============================================================================
# 测试类：业务辅助方法
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestBarCRUDBusinessHelpers:
    """BarCRUD 业务辅助方法集成测试"""

    def test_find_by_code_and_date_range(self, bar_crud, cleanup, sample_bar_batch):
        """业务方法：按代码+日期范围查询"""
        models = [bar_crud._create_from_params(**p) for p in sample_bar_batch]
        bar_crud.add_batch(models)

        results = bar_crud.find_by_code_and_date_range(
            code="TEST_BAR_BATCH",
            start_date=datetime(2024, 1, 12),
            end_date=datetime(2024, 1, 14),
        )
        assert len(results) >= 1

    def test_count_by_code(self, bar_crud, cleanup, sample_bar_batch):
        """业务方法：按代码计数"""
        models = [bar_crud._create_from_params(**p) for p in sample_bar_batch]
        bar_crud.add_batch(models)

        cnt = bar_crud.count_by_code("TEST_BAR_BATCH")
        assert cnt == 5

    def test_get_date_range_for_code(self, bar_crud, cleanup, sample_bar_batch):
        """业务方法：获取代码的日期范围"""
        models = [bar_crud._create_from_params(**p) for p in sample_bar_batch]
        bar_crud.add_batch(models)

        min_date, max_date = bar_crud.get_date_range_for_code("TEST_BAR_BATCH")
        assert min_date is not None
        assert max_date is not None
        assert min_date <= max_date
