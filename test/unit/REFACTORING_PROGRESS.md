# 测试重构进度跟踪

本文档跟踪 test/unit/ 目录下测试文件的重构进度。

## 重构完成标准

- [ ] 使用 pytest 替代 unittest
- [ ] 使用 fixtures 替代 setUp/tearDown
- [ ] 使用参数化测试减少重复
- [ ] 使用 pytest.mark 标记
- [ ] 使用 pytest 原生断言
- [ ] 补全边界测试
- [ ] 测试通过且覆盖率良好

## 总体进度

- **总文件数**: 47
- **已完成**: 4
- **进行中**: 0
- **待开始**: 43
- **完成率**: 8.5%

## 详细进度

### ✅ 已完成

| 文件 | 原始路径 | 重构路径 | 状态 | 备注 |
|------|----------|----------|------|------|
| conftest.py | - | /test/unit/conftest.py | ✅ | 全局共享 fixtures |
| conftest.py | - | /test/unit/trading/conftest.py | ✅ | Trading 模块 fixtures |
| conftest.py | - | /test/unit/trading/risk/conftest.py | ✅ | Risk 模块 fixtures |
| conftest.py | - | /test/unit/backtest/conftest.py | ✅ | Backtest 模块 fixtures |
| test_loss_limit_risk.py | /test/unit/trading/risk/ | /test/unit/trading/risk/test_loss_limit_risk_refactored.py | ✅ | 完整重构 |
| test_order.py | /test/unit/backtest/ | /test/unit/backtest/test_order_refactored.py | ✅ | 完整重构 |
| test_position.py | /test/unit/backtest/ | /test/unit/backtest/test_position_refactored.py | ✅ | 完整重构 |
| test_bar.py | /test/unit/backtest/ | /test/unit/backtest/test_bar_refactored.py | ✅ | 完整重构 |

### 🔄 进行中

暂无

### 📋 待重构

#### backtest 目录 (13 个文件)

| 文件 | 优先级 | 预计工时 |
|------|--------|----------|
| test_tick.py | 高 | 2h |
| test_base_analyzer.py | 中 | 2h |
| test_events.py | 中 | 1.5h |
| containers/test_backtest_container.py | 低 | 1h |
| indicators/test_* (5个文件) | 中 | 3h |
| risk_managements/test_* (2个文件) | 高 | 2h |
| services/test_* (3个文件) | 中 | 2h |

#### trading 目录 (19 个文件)

| 文件 | 优先级 | 预计工时 |
|------|--------|----------|
| risk/test_profit_target_risk.py | 高 | 2h |
| entities/test_time_related_validation.py | 中 | 1.5h |
| feeders/test_* | 低 | 1h |
| bases/test_base_router.py | 中 | 2h |
| selector/test_fixed_selector.py | 中 | 1.5h |
| engines/test_* (2个文件) | 高 | 3h |
| brokers/test_sim_broker.py | 中 | 2h |
| integration/test_router_broker_integration.py | 低 | 1h |
| test_* (其他测试) | 中 | 4h |

#### data 目录 (7 个文件)

需要创建 data/conftest.py 后开始重构。

#### 其他目录 (8 个文件)

- containers/
- libs/
- livecore/
- lab/
- notifiers/
- service_hub/

## 重构统计

### 按模块分类

- **conftest.py**: 4/4 (100%) ✅
- **backtest**: 4/17 (23.5%)
- **trading**: 1/19 (5.3%)
- **data**: 0/7 (0%)
- **其他**: 0/8 (0%)

### 按重构类型分类

- **fixtures 创建**: 4/4 (100%) ✅
- **实体测试重构**: 4/10 (40%)
- **风控测试重构**: 1/3 (33%)
- **策略测试重构**: 0/5 (0%)
- **引擎测试重构**: 0/2 (0%)
- **CRUD 测试重构**: 0/7 (0%)

## 重构日志

### 2025-02-15

- ✅ 创建全局 conftest.py
- ✅ 创建 trading/conftest.py
- ✅ 创建 trading/risk/conftest.py
- ✅ 创建 backtest/conftest.py
- ✅ 重构 test_loss_limit_risk.py
- ✅ 重构 test_order.py
- ✅ 重构 test_position.py
- ✅ 重构 test_bar.py
- ✅ 创建 REFACTORING_GUIDE.md

## 下一步计划

### 第 1 周: backtest 核心实体
- [ ] 重构 test_tick.py
- [ ] 重构 test_events.py
- [ ] 重构 test_base_analyzer.py

### 第 2 周: trading 风控和策略
- [ ] 重构 test_profit_target_risk.py
- [ ] 重构 engines/ 目录
- [ ] 重构 brokers/ 目录

### 第 3 周: backtest 指标和分析器
- [ ] 重构 indicators/ 目录
- [ ] 重构 risk_managements/ 目录

### 第 4 周: data 和其他模块
- [ ] 创建 data/conftest.py
- [ ] 重构 data/ 目录测试
- [ ] 重构其他模块测试

## 重构模板

为快速重构，使用以下模板：

```python
"""
[模块名] 测试

使用 pytest 最佳实践测试 [功能]。
"""

import pytest
from datetime import datetime
from decimal import Decimal

from ginkgo.[模块路径] import [类名]
from ginkgo.enums import [...]


@pytest.mark.unit
@pytest.mark.[模块标记]
class Test[类名]Construction:
    """[类名] 构造和初始化测试"""

    def test_default_construction(self):
        """测试默认构造"""
        entity = [类名]()
        assert entity is not None


@pytest.mark.unit
@pytest.mark.[模块标记]
class Test[类名]Properties:
    """[类名] 属性测试"""

    @pytest.fixture
    def entity(self):
        return [类名](参数1="值1", 参数2="值2")

    def test_property1(self, entity):
        """测试属性1"""
        assert entity.property1 == "期望值"


@pytest.mark.unit
@pytest.mark.[模块标记]
class Test[类名]Operations:
    """[类名] 操作测试"""

    @pytest.mark.parametrize("input,expected", [
        (1, 2),
        (2, 4),
        (3, 6),
    ])
    def test_operation(self, entity, input, expected):
        """测试操作"""
        result = entity.operation(input)
        assert result == expected
```

## 质量检查清单

重构完成后，检查以下项目：

- [ ] 所有测试使用 pytest 格式
- [ ] 使用了适当的 fixtures
- [ ] 参数化测试覆盖了多种情况
- [ ] 使用了正确的标记
- [ ] 测试命名清晰描述性
- [ ] 测试独立运行不依赖其他测试
- [ ] 测试覆盖了正常和异常情况
- [ ] 测试通过且运行稳定
- [ ] 代码符合项目风格指南
- [ ] 文档字符串完整
