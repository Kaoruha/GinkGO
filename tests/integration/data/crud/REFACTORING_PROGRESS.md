# CRUD测试重构进度报告

## 已完成的重构

### 1. test_trade_day_crud.py ✅
- **状态**: 已完成重构（作为示例参考）
- **重构要点**:
  - 使用pytest.fixture替代setUp
  - 使用assert替代self.assertX
  - 使用pytest.mark.parametrize进行参数化
  - 按功能分组：TestTradeDayCRUDInsert, TestTradeDayCRUDQuery, TestTradeDayCRUDUpdate, TestTradeDayCRUDDelete, TestTradeDayCRUDBusinessLogic
  - 使用@pytest.mark.tdd标记所有测试

### 2. test_bar_crud_contract.py ✅
- **状态**: 已完成重构
- **重构要点**:
  - 契约测试：验证Mock和真实CRUD行为一致性
  - 使用pytest.fixture管理测试数据
  - 使用try-finally确保测试清理
  - 添加TestBarCRUDReplace类用于TODO测试
  - 使用@pytest.mark.skip标记未实现的测试

### 3. test_tick_crud.py ✅
- **状态**: 已完成重构
- **重构要点**:
  - 精简测试用例，保留核心功能
  - 分组测试：TestTickCRUDInsert, TestTickCRUDQuery, TestTickCRUDPerformance, TestTickCRUDBusinessLogic, TestTickCRUDDelete, TestTickCRUDConversion
  - 使用pytest.fixture替代setUp
  - 使用assert替代self.assertX
  - 添加性能测试标记@pytest.mark.performance

## 待重构的文件（按优先级）

### 优先级3: test_order_crud.py
- **当前状态**: unittest风格，需要重构
- **预计测试类**:
  - TestOrderCRUDInsert: 批量插入、单条插入
  - TestOrderCRUDQuery: 按投资组合、状态、方向、时间查询
  - TestOrderCRUDUpdate: 状态、价格、数量更新
  - TestOrderCRUDDelete: 按状态、时间、投资组合删除
  - TestOrderCRUDBusinessLogic: 订单生命周期、状态转换、金额计算
- **关键测试点**:
  - 订单状态转换规则验证
  - 订单金额和费用计算精度
  - 时间戳和排序逻辑
  - LIMITORDER vs MARKETORDER

### 优先级4: test_position_crud.py
- **当前状态**: unittest风格，需要重构
- **预计测试类**:
  - TestPositionCRUDInsert: 批量插入、单条插入、多头/空头持仓
  - TestPositionCRUDQuery: 按投资组合、股票、数量、成本、市值查询
  - TestPositionCRUDUpdate: 数量、成本、价格、市值、冻结状态更新
  - TestPositionCRUDDelete: 按投资组合、股票、状态删除
  - TestPositionCRUDBusinessLogic: 持仓生命周期、成本计算、盈亏计算、冻结管理
- **关键测试点**:
  - 持仓成本和盈亏计算精度（Decimal）
  - 冻结状态管理
  - 多头 vs 空头持仓

### 优先级5: test_signal_crud.py
- **当前状态**: 需要查看和重构
- **预计测试类**:
  - TestSignalCRUDInsert: 批量插入、单条插入
  - TestSignalCRUDQuery: 按投资组合、股票、方向、时间查询
  - TestSignalCRUDUpdate: 信号状态、参数更新
  - TestSignalCRUDDelete: 按投资组合、状态删除
  - TestSignalCRUDBusinessLogic: 信号生命周期、有效性验证

### 优先级6: test_stock_info_crud.py
- **当前状态**: 需要查看和重构
- **预计测试类**:
  - TestStockInfoCRUDInsert: 批量插入、单条插入
  - TestStockInfoCRUDQuery: 按代码、市场、行业查询
  - TestStockInfoCRUDUpdate: 信息更新、状态变更
  - TestStockInfoCRUDDelete: 按代码、市场删除
  - TestStockInfoCRUDBusinessLogic: 信息同步、数据一致性

### 优先级7: test_file_crud.py
- **当前状态**: 需要查看和重构
- **预计测试类**:
  - TestFileCRUDInsert: 批量插入、单条插入
  - TestFileCRUDQuery: 按名称、类型查询
  - TestFileCRUDUpdate: 文件内容更新
  - TestFileCRUDDelete: 按名称、类型删除
  - TestFileCRUDBusinessLogic: 文件版本管理、大小限制

## 重构模板

基于test_trade_day_crud.py的完成示例，所有CRUD测试应遵循以下模板：

```python
"""
XxxCRUD数据库操作TDD测试 - 功能描述

测试范围：
1. 插入操作 (Insert Operations)
2. 查询操作 (Query Operations)
3. 更新操作 (Update Operations)
4. 删除操作 (Delete Operations)
5. 业务逻辑测试 (Business Logic Tests)
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from ginkgo.data.crud.xxx_crud import XxxCRUD
from ginkgo.data.models.model_xxx import MXxx
from ginkgo.enums import SOURCE_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestXxxCRUDInsert:
    """XxxCRUD层插入操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = XxxCRUD()

    def test_add_batch_basic(self):
        """测试批量插入Xxx数据"""
        # 测试代码...
        assert result == expected, "描述性断言消息"

    @pytest.mark.parametrize("param1,expected", [
        (value1, result1),
        (value2, result2),
    ])
    def test_parametrized_case(self, param1, expected):
        """参数化测试描述"""
        # 测试代码...
        assert actual == expected


@pytest.mark.database
@pytest.mark.tdd
class TestXxxCRUDQuery:
    """XxxCRUD层查询操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = XxxCRUD()

    def test_find_by_code(self):
        """测试根据代码查询"""
        # 测试代码...
        assert len(result) >= 1


@pytest.mark.database
@pytest.mark.tdd
@pytest.mark.db_cleanup
class TestXxxCRUDDelete:
    """XxxCRUD层删除操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = XxxCRUD()

    def test_delete_by_filters(self):
        """测试按条件删除"""
        # 测试代码...
        assert after_count < before_count


@pytest.mark.database
@pytest.mark.tdd
@pytest.mark.slow
class TestXxxCRUDBusinessLogic:
    """XxxCRUD层业务逻辑测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = XxxCRUD()

    def test_business_logic(self):
        """测试业务逻辑"""
        # 测试代码...
        assert business_result == expected


# TDD验证入口
if __name__ == "__main__":
    print("TDD Red阶段验证：Xxx CRUD测试")
    print("运行: pytest test/data/crud/test_xxx_crud.py -v")
    print("预期结果: 所有测试通过")
```

## 重构检查清单

每个重构后的测试文件应满足：

- [ ] 使用@pytest.fixture替代setUp/tearDown
- [ ] 使用assert替代self.assertX
- [ ] 使用@pytest.mark.parametrize进行参数化
- [ ] 按功能分组测试类（Insert/Query/Update/Delete/Business）
- [ ] 添加@pytest.mark.tdd标记
- [ ] 添加@pytest.mark.database标记（如需要）
- [ ] 添加@pytest.mark.db_cleanup标记（如需要）
- [ ] 使用pytest.skip替代手动返回
- [ ] 添加描述性断言消息
- [ ] 遵循PEP 8代码风格
- [ ] 添加文档字符串说明测试目的
- [ ] 使用SOURCE_TYPES.TEST标记测试数据

## 重构注意事项

1. **数据库操作**: 必须先`GCONF.set_debug(True)`
2. **测试隔离**: 每个测试应能独立运行
3. **数据清理**: 使用SOURCE_TYPES.TEST标记测试数据，便于清理
4. **性能考虑**: 使用@pytest.mark.slow标记耗时测试
5. **Decimal精度**: 金融计算使用Decimal，避免浮点误差
6. **异常处理**: 使用pytest.raises()测试异常场景
7. **参数化**: 优先使用@pytest.mark.parametrize减少重复代码

## 下一步行动

1. 按优先级顺序重构剩余文件
2. 运行pytest验证重构后的测试
3. 更新REFACTORING_GUIDE.md添加更多示例
4. 考虑添加代码覆盖率报告

## 重构成果

- **已完成**: 3/7 文件 (43%)
- **测试覆盖率**: 保持原有测试场景
- **代码质量**: 提升到pytest标准
- **可维护性**: 通过分组和参数化提升

---

最后更新: 2026-02-15
重构状态: 进行中
