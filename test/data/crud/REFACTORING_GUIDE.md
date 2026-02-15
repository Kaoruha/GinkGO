# CRUD 测试重构指南

## Pytest 最佳实践要点

### 1. 使用 fixtures 共享设置

**❌ 不好的做法 (unittest 风格):**
```python
class TestTradeDayCRUDInsert:
    def setUp(self):
        self.crud = TradeDayCRUD()
```

**✅ 好的做法 (pytest 风格):**
```python
@pytest.mark.database
@pytest.mark.tdd
class TestTradeDayCRUDInsert:
    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = TradeDayCRUD()
```

### 2. 使用参数化减少重复代码

**❌ 不好的做法:**
```python
def test_add_china_market(self):
    test_day = MTradeDay(market=MARKET_TYPES.CHINA, ...)
    self.crud.add(test_day)
    result = self.crud.find(filters={"market": MARKET_TYPES.CHINA})
    assert len(result) >= 1

def test_add_nasdaq_market(self):
    test_day = MTradeDay(market=MARKET_TYPES.NASDAQ, ...)
    self.crud.add(test_day)
    result = self.crud.find(filters={"market": MARKET_TYPES.NASDAQ})
    assert len(result) >= 1
```

**✅ 好的做法:**
```python
@pytest.mark.parametrize("market,is_open,expected_status", [
    (MARKET_TYPES.CHINA, True, "交易日"),
    (MARKET_TYPES.CHINA, False, "休市日"),
    (MARKET_TYPES.NASDAQ, True, "交易日"),
    (MARKET_TYPES.NYSE, False, "休市日"),
])
def test_add_single_with_various_statuses(self, market, is_open, expected_status):
    """参数化测试不同状态的交易日插入"""
    test_day = MTradeDay(
        market=market,
        is_open=is_open,
        timestamp=datetime(2024, 1, 15),
        source=SOURCE_TYPES.TEST
    )
    self.crud.add(test_day)
    result = self.crud.find(filters={
        "market": market,
        "timestamp": datetime(2024, 1, 15)
    })
    assert len(result) >= 1, f"应查询到{expected_status}记录"
    assert result[0].is_open == is_open
```

### 3. 使用 pytest.mark 标记测试

**推荐的标记:**
- `@pytest.mark.database`: 需要数据库连接的测试
- `@pytest.mark.tdd`: TDD 测试用例
- `@pytest.mark.db_cleanup`: 需要清理测试数据的测试
- `@pytest.mark.enum`: 枚举类型测试
- `@pytest.mark.financial`: 金融计算测试
- `@pytest.mark.slow`: 运行缓慢的测试
- `@pytest.mark.integration`: 集成测试
- `@pytest.mark.unit`: 单元测试

**使用示例:**
```python
@pytest.mark.database
@pytest.mark.tdd
@pytest.mark.slow
class TestTradeDayCRUDBusinessLogic:
    """TradeDay CRUD层业务逻辑测试"""
    # 测试方法...
```

### 4. 使用 pytest.skip 而不是手动返回

**❌ 不好的做法:**
```python
def test_analysis(self):
    all_trade_days = self.crud.find()
    if len(all_trade_days) < 10:
        print("数据不足，跳过")
        return
    # 测试代码...
```

**✅ 好的做法:**
```python
def test_analysis(self):
    all_trade_days = self.crud.find()
    if len(all_trade_days) < 10:
        pytest.skip("交易日历数据不足，跳过分析测试")
    # 测试代码...
```

### 5. 使用 assert 而不是 self.assertX

**❌ 不好的做法 (unittest 风格):**
```python
self.assertEqual(len(result), 1)
self.assertTrue(result[0].is_open)
```

**✅ 好的做法 (pytest 风格):**
```python
assert len(result) == 1, "应查询到插入的记录"
assert result[0].is_open == True
```

### 6. 使用描述性的断言消息

**✅ 好的做法:**
```python
assert len(result) >= 1, f"应查询到{expected_status}记录"
assert inserted_count == len(test_trade_days), \
    f"应插入{len(test_trade_days)}条，实际{inserted_count}条"
```

### 7. 按功能分组测试类

**推荐的类结构:**
- `TestXxxCRUDInsert`: 插入操作测试
- `TestXxxCRUDQuery`: 查询操作测试
- `TestXxxCRUDUpdate`: 更新操作测试
- `TestXxxCRUDDelete`: 删除操作测试
- `TestXxxCRUDBusinessLogic`: 业务逻辑测试
- `TestXxxCRUDCreate`: Create 方法测试

## 共用 conftest.py 文件

`test/data/crud/conftest.py` 提供的 fixtures:

1. **db_cleanup**: 数据库清理 fixture
2. **ginkgo_config**: Ginkgo 配置 fixture
3. **sample_xxx_data**: 各类测试数据 fixtures
4. **verify_insert_count**: 验证插入数量的 fixture
5. **print_test_header**: 标准化测试输出
6. **assert_data_integrity**: 数据完整性断言
7. **measure_performance**: 性能测量

## 重构步骤

1. **识别 unittest 风格代码**
   - `setUp`/`tearDown` 方法
   - `self.assertX` 断言
   - 手动返回跳过测试

2. **转换为 pytest 风格**
   - 使用 `@pytest.fixture` 替代 `setUp`
   - 使用 `assert` 替代 `self.assertX`
   - 使用 `pytest.skip()` 替代手动返回
   - 添加 `@pytest.mark` 标记

3. **应用参数化**
   - 识别重复的测试模式
   - 提取变化的部分作为参数
   - 使用 `@pytest.mark.parametrize`

4. **按功能重组**
   - 将测试方法按功能分组
   - 创建独立的测试类
   - 使用描述性的类名和方法名

5. **添加文档**
   - 类级文档字符串
   - 方法级文档字符串
   - 参数说明
   - 业务价值说明

## 测试模板

```python
"""
XxxCRUD数据库操作TDD测试 - 功能描述

本文件测试XxxCRUD类的完整功能...

测试范围：
1. 插入操作
2. 查询操作
3. 更新操作
4. 删除操作
5. 业务逻辑测试
"""
import pytest
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.xxx_crud import XxxCRUD
from ginkgo.data.models.model_xxx import MXxx
from ginkgo.enums import SOURCE_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestXxxCRUDInsert:
    """Xxx CRUD层插入操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = XxxCRUD()

    def test_add_batch_basic(self):
        """测试批量插入Xxx数据"""
        # 测试代码...
        assert result == expected, "描述性断言消息"

    @pytest.mark.parametrize("param1,param2,expected", [
        (value1, value2, result1),
        (value3, value4, result2),
    ])
    def test_parametrized_case(self, param1, param2, expected):
        """参数化测试描述"""
        # 测试代码...
        assert actual == expected


if __name__ == "__main__":
    print("TDD验证：Xxx CRUD测试")
    print("运行: pytest test/data/crud/test_xxx_crud.py -v")
```

## 重构文件列表

需要重构的文件：
- ✅ test_trade_day_crud.py (已完成)
- test_transfer_record_crud.py
- test_engine_portfolio_mapping_crud.py
- test_handler_crud.py
- test_tick_crud.py
- test_bar_crud_contract.py
- test_file_crud.py
- test_portfolio_file_mapping_crud.py
- test_analyzer_record_crud.py
- test_stock_info_crud.py
- test_signal_tracker_crud.py
- test_engine_crud.py
- test_signal_crud.py
- test_transfer_crud.py
- test_param_crud.py
- test_position_crud.py
- test_factor_crud.py
- test_capital_adjustment_crud.py
- test_position_record_crud.py
- test_order_crud.py
- test_tick_summary_crud.py
- test_engine_handler_mapping_crud.py
- test_order_record_crud.py
- test_adjustfactor_crud.py

## 注意事项

1. **保持向后兼容**: 重构后的测试应覆盖原有测试的所有场景
2. **数据库清理**: 使用 `@pytest.mark.db_cleanup` 标记需要清理的测试
3. **性能考虑**: 使用 `@pytest.mark.slow` 标记耗时测试
4. **调试模式**: 数据库操作前必须 `GCONF.set_debug(True)`
5. **测试隔离**: 每个测试应该能独立运行
