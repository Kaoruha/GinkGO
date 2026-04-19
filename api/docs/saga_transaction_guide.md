# Saga 事务管理器使用指南

## 概述

Saga 事务管理器实现了补偿事务模式，确保分布式操作的一致性。当任何步骤失败时，自动执行已完成步骤的补偿操作，实现回滚效果。

## 核心概念

### 1. Saga 事务

Saga 是一种长事务模式，通过将事务分解为多个步骤，并为每个步骤定义补偿操作来实现一致性。

**特点：**
- 每个步骤都有对应的补偿操作
- 步骤按顺序执行
- 失败时逆序补偿已完成步骤
- 补偿失败不影响其他补偿

### 2. 补偿事务

补偿事务是"撤销"已执行操作的逻辑。

**示例：**
- 执行操作：`create_portfolio()`
- 补偿操作：`delete_portfolio(portfolio_uuid)`

## 快速开始

### 基本使用

```python
from services.saga_transaction import SagaTransaction

# 创建 Saga
saga = SagaTransaction("my_transaction")

# 添加步骤
saga.add_step(
    name="step1",
    execute=lambda: perform_action(),
    compensate=lambda result: undo_action(result)
)

# 执行事务
success = await saga.execute()

if success:
    print("事务成功")
else:
    print("事务失败，已自动回滚")
```

### Portfolio 创建

```python
from services.saga_transaction import PortfolioSagaFactory

# 创建 Saga
saga = PortfolioSagaFactory.create_portfolio_saga(
    name="My Portfolio",
    is_live=False,
    selectors=[
        {"component_uuid": "selector-uuid-1", "config": {"param1": "value1"}}
    ],
    sizer={"component_uuid": "sizer-uuid", "config": {}},
    strategies=[
        {"component_uuid": "strategy-uuid", "config": {}}
    ],
    risk_managers=[
        {"component_uuid": "risk-uuid", "config": {}}
    ],
    analyzers=[]
)

# 执行事务
success = await saga.execute()

if success:
    portfolio_uuid = saga.steps[0].result.uuid
    print(f"Portfolio {portfolio_uuid} 创建成功")
```

### Portfolio 更新

```python
# 创建更新 Saga
saga = PortfolioSagaFactory.update_portfolio_saga(
    portfolio_uuid="portfolio-uuid",
    name="New Name",
    selectors=[{"component_uuid": "new-selector", "config": {}}],
    strategies=[]
)

# 执行事务
success = await saga.execute()
```

### Portfolio 删除

```python
# 创建删除 Saga
saga = PortfolioSagaFactory.delete_portfolio_saga("portfolio-uuid")

# 执行事务
success = await saga.execute()
```

## 高级用法

### 异步步骤

Saga 支持同步和异步函数：

```python
async def async_operation():
    return await some_async_call()

saga.add_step(
    name="async_step",
    execute=async_operation,
    compensate=lambda result: cleanup()
)
```

### 上下文共享

使用闭包在步骤间共享数据：

```python
context = {}

def step1():
    context['portfolio'] = create_portfolio()
    return context['portfolio']

def step2():
    # 使用 context['portfolio']
    add_component(context['portfolio'].uuid)

saga.add_step("step1", step1, lambda r: context.clear())
saga.add_step("step2", step2, lambda r: None)
```

### 事务记录

将 Saga 执行结果转换为记录：

```python
from services.transaction_monitor import transaction_monitor

# 执行 Saga
success = await saga.execute()

# 记录事务
record = transaction_monitor.record_transaction(saga)

print(f"事务状态: {record.status}")
print(f"步骤数: {len(record.steps)}")
```

### 自定义监控

```python
from services.transaction_monitor import TransactionMonitor

def my_storage(record):
    # 存储到数据库
    db.transactions.insert(record.dict())

monitor = TransactionMonitor(storage_backend=my_storage)

@monitor.monitor("portfolio")
async def create_portfolio(data):
    # ... 创建逻辑
    pass
```

## 错误处理

### 补偿失败

补偿操作失败不会中断其他补偿：

```python
def step1_compensate(result):
    # 这个补偿失败不会影响 step2 的补偿
    raise Exception("Compensation failed")

def step2_compensate(result):
    # 仍会执行
    cleanup()

saga.add_step("step1", step1, step1_compensate)
saga.add_step("step2", step2, step2_compensate)
```

### 获取错误信息

```python
success = await saga.execute()

if not success:
    print(f"失败原因: {saga.error}")
    print(f"失败步骤: {[s.name for s in saga.steps if s.error]}")
```

## 最佳实践

### 1. 补偿操作幂等性

补偿操作应该可以安全地多次执行：

```python
def compensate_delete_portfolio(portfolio_uuid):
    # 检查是否存在再删除
    if portfolio_exists(portfolio_uuid):
        delete_portfolio(portfolio_uuid)
```

### 2. 精确定义补偿范围

只补偿必要的操作：

```python
# 好的做法：只撤销已执行的操作
def compensate(result):
    if result.get('created'):
        delete_result(result['id'])

# 避免：补偿不应该做额外操作
def compensate(result):
    delete_result(result['id'])
    send_notification()  # 不应该在补偿中做
```

### 3. 步骤命名规范

使用清晰的步骤名称便于日志追踪：

```python
# 好的命名
saga.add_step("create_portfolio_entity", ...)

# 避免模糊命名
saga.add_step("step1", ...)
```

### 4. 事务粒度

合理划分事务粒度：

```python
# 好的做法：一个完整的事务
saga = PortfolioSagaFactory.create_portfolio_saga(...)

# 避免：将独立操作放在一个事务中
saga.add_step("create_portfolio", ...)
saga.add_step("create_backtest", ...)  # 不相关操作
```

## 架构设计

### 类图

```
┌─────────────────────┐
│   SagaTransaction   │
├─────────────────────┤
│ - name: str         │
│ - steps: List       │
│ - completed_steps   │
│ - failed: bool      │
├─────────────────────┤
│ + add_step()        │
│ + execute()         │
│ + _compensate()     │
│ + to_record()       │
└─────────────────────┘
         │
         │ 使用
         │
┌─────────────────────────┐
│ PortfolioSagaFactory    │
├─────────────────────────┤
│ + create_portfolio_saga()│
│ + update_portfolio_saga()│
│ + delete_portfolio_saga()│
└─────────────────────────┘
```

### 执行流程

```
开始
  │
  ├─> 步骤1执行 ──成功──> 步骤2执行 ──成功──> ... ──成功──> 完成
  │                     │
  │                    失败
  │                     │
  └─────────────────────┴─> 补偿步骤2 ──> 补偿步骤1 ──> 回滚完成
```

## 监控和调试

### 日志输出

Saga 执行时会输出详细日志：

```
INFO: Saga 'portfolio:create:test' started with 6 steps
INFO: Executing step: create_portfolio
INFO: Step 'create_portfolio' completed successfully
INFO: Executing step: add_selector_sel-1
INFO: Step 'add_selector_sel-1' completed successfully
ERROR: Step 'add_strategy_str-1' failed: ...
WARNING: Compensating 2 completed steps...
INFO: Compensating step: add_selector_sel-1
INFO: Compensating step: create_portfolio
```

### 事务状态查询

```python
record = saga.to_record()

for step in record.steps:
    print(f"{step.name}: {step.status}")
    if step.error:
        print(f"  错误: {step.error}")
```

## 性能考虑

### 1. 步骤数量

避免过多步骤（建议 < 20 个），每个步骤都有性能开销。

### 2. 补偿复杂度

补偿操作应该快速高效，避免长时间占用资源。

### 3. 并发限制

Saga 顺序执行步骤，不适合需要高并发的场景。

## 故障恢复

### 部分完成状态

如果系统在 Saga 执行过程中崩溃，可能留下部分完成状态：

1. 检查事务状态
2. 手动执行补偿操作
3. 或重新执行 Saga（幂等设计）

### 恢复策略

```python
# 检查 Portfolio 是否有完整组件
def is_portfolio_complete(portfolio_uuid):
    mappings = get_mappings(portfolio_uuid)
    return has_required_components(mappings)

# 如果不完整，执行补偿
if not is_portfolio_complete(portfolio_uuid):
    delete_portfolio(portfolio_uuid)
```

## 参考资料

- [Saga Pattern (Microservices Patterns)](https://microservices.io/patterns/data/saga.html)
- [补偿事务模式](https://docs.microsoft.com/zh-cn/azure/architecture/patterns/compensating-transaction)
