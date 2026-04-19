# Saga 事务管理器快速参考

## 核心概念

```python
# Saga 事务 = 多个步骤 + 每步的补偿操作
# 失败时逆序执行补偿 → 实现回滚效果
```

## 快速开始

### 1. 基本使用
```python
from services.saga_transaction import SagaTransaction

saga = SagaTransaction("my_operation")
saga.add_step("step1", execute_func, compensate_func)
success = await saga.execute()
```

### 2. Portfolio 操作
```python
from services.saga_transaction import PortfolioSagaFactory

# 创建
saga = PortfolioSagaFactory.create_portfolio_saga(
    name="Portfolio Name",
    is_live=False,
    selectors=[{"component_uuid": "...", "config": {}}],
    sizer={"component_uuid": "...", "config": {}},
    strategies=[{"component_uuid": "...", "config": {}}],
    risk_managers=[],
    analyzers=[]
)
await saga.execute()

# 更新
saga = PortfolioSagaFactory.update_portfolio_saga(
    portfolio_uuid="uuid",
    name="New Name",
    selectors=[...],
    strategies=[]
)
await saga.execute()

# 删除
saga = PortfolioSagaFactory.delete_portfolio_saga("uuid")
await saga.execute()
```

## 常用模式

### 异步步骤
```python
async def async_step():
    return await some_async_call()

saga.add_step("async_step", async_step, compensate)
```

### 上下文共享
```python
context = {}

def step1():
    context['id'] = create_resource()
    return context['id']

def step2():
    use_id(context['id'])

saga.add_step("step1", step1, lambda r: context.clear())
saga.add_step("step2", step2, lambda r: None)
```

### 事务记录
```python
from services.transaction_monitor import transaction_monitor

record = transaction_monitor.record_transaction(saga)
print(f"状态: {record.status}, 步骤: {len(record.steps)}")
```

## API 参考

### SagaTransaction

| 方法 | 说明 |
|------|------|
| `__init__(name)` | 创建事务 |
| `add_step(name, execute, compensate)` | 添加步骤 |
| `execute()` | 执行事务 |
| `to_record()` | 转换为记录 |

### PortfolioSagaFactory

| 方法 | 说明 |
|------|------|
| `create_portfolio_saga(...)` | 创建 Saga |
| `update_portfolio_saga(...)` | 更新 Saga |
| `delete_portfolio_saga(uuid)` | 删除 Saga |

## 错误处理

```python
success = await saga.execute()

if not success:
    print(f"失败原因: {saga.error}")
    print(f"已补偿步骤: {[s.name for s in saga.completed_steps]}")
    # 事务已自动回滚
```

## 最佳实践

1. **补偿幂等性**: 补偿可以安全重复执行
2. **精确定义**: 只撤销必要的操作
3. **清晰命名**: 使用描述性的步骤名称
4. **合理粒度**: 一个完整的事务包含相关操作

## 文件位置

- 实现: `/home/kaoru/Ginkgo/apiserver/services/saga_transaction.py`
- 工厂: `/home/kaoru/Ginkgo/apiserver/services/saga_helpers.py`
- 监控: `/home/kaoru/Ginkgo/apiserver/services/transaction_monitor.py`
- 模型: `/home/kaoru/Ginkgo/apiserver/models/transaction.py`
- 文档: `/home/kaoru/Ginkgo/apiserver/docs/saga_transaction_guide.md`
