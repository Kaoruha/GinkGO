# Kafka Topic 重构设计

**Date**: 2025-01-26
**Status**: 提案中

## 问题陈述

当前 DataWorker 订阅 `ginkgo.live.control.commands`，导致收到不相关的命令（如 `update_selector`），需要在代码中忽略。这是架构设计问题，应该通过合理的 Topic 分离来解决。

## 当前问题

```
TaskTimer → ginkgo.live.control.commands → {
    DataManager (data_manager_control_group)
    DataWorker (data_worker_group) ← ❌ 收到不相关消息
}
```

## 重构方案

### 1. 数据采集专用 Topic

创建专门的数据采集 Topic，**替代 DataWorker 订阅 `ginkgo.live.control.commands`**：

```python
# 新增 Topic
DATA_COMMANDS = "ginkgo.data.commands"  # 数据采集命令专用

# 或者使用已存在但未使用的 Topic
# DATA_UPDATE = "ginkgo.data.update"
```

### 2. Topic 职责分离

| Topic | 用途 | 生产者 | 消费者 | 命令类型 |
|-------|------|--------|--------|----------|
| **`ginkgo.live.control.commands`** | 实盘交易控制命令 | TaskTimer, Scheduler | DataManager, ExecutionNode | `update_selector`, `update_data`, `heartbeat_test` |
| **`ginkgo.data.commands`** | 数据采集命令 | TaskTimer | DataWorker | `bar_snapshot`, `stockinfo`, `adjustfactor`, `tick` |

### 3. TaskTimer 发送逻辑修改

TaskTimer 需要根据命令类型发送到不同的 Topic：

```python
# TaskTimer 修改前
producer.send(KafkaTopics.CONTROL_COMMANDS, command_dto.model_dump_json())

# TaskTimer 修改后
if command in ("bar_snapshot", "stockinfo", "adjustfactor", "tick"):
    producer.send(KafkaTopics.DATA_COMMANDS, command_dto.model_dump_json())
else:
    producer.send(KafkaTopics.CONTROL_COMMANDS, command_dto.model_dump_json())
```

### 4. DataWorker 订阅修改

```python
# DataWorker 修改前
CONTROL_COMMANDS_TOPIC: str = "ginkgo.live.control.commands"

# DataWorker 修改后
CONTROL_COMMANDS_TOPIC: str = "ginkgo.data.commands"
```

### 5. KafkaTopics 类更新

```python
class KafkaTopics:
    # ... existing topics ...

    # ============================================
    # 数据采集 Topics (Data Collection)
    # ============================================

    # 数据采集命令（TaskTimer → DataWorker）
    # 命令类型: bar_snapshot, stockinfo, adjustfactor, tick
    DATA_COMMANDS = "ginkgo.data.commands"
```

## 迁移步骤

### Phase 1: 添加新 Topic
1. ✅ 在 `KafkaTopics` 添加 `DATA_COMMANDS` 常量
2. ✅ 修改 DataWorker 订阅新 Topic
3. ✅ 修改 TaskTimer 发送逻辑

### Phase 2: 测试验证
1. ✅ 启动 DataWorker，验证订阅新 Topic
2. ✅ TaskTimer 发送测试命令，验证路由正确
3. ✅ 验证 DataWorker 不再收到 `update_selector` 等命令

### Phase 3: 清理旧逻辑
1. ✅ 移除 DataWorker 中的命令过滤逻辑
2. ✅ 更新文档和注释

## 兼容性

- ✅ 不影响现有组件（DataManager, ExecutionNode）
- ✅ 仅修改 DataWorker 和 TaskTimer
- ✅ 向后兼容，新旧 Topic 可以共存

## 好处

1. **职责清晰** - 每个 Topic 有明确的用途
2. **性能提升** - 减少不必要的消息传递
3. **代码简化** - 不需要在 DataWorker 中过滤命令
4. **易于扩展** - 新增数据采集命令不影响其他组件
