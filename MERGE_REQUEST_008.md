# Merge Request: 008-live-data-module

## Overview

**Branch**: `008-live-data-module` → `main`
**Status**: Ready for Review
**Created**: 2026-01-08
**Completed**: 2026-01-20

This MR implements the **Live Data Module** for Ginkgo quantitative trading system, enabling real-time market data processing, scheduled task management, and multi-source data integration.

---

## Summary

完善实盘的数据模块，支持两种触发模式：
- **Tick 数据触发**：实时接收市场行情数据并触发策略计算
- **定时触发**：通过 TaskTimer 按计划发送控制命令

---

## Key Features

### 1. DataManager - 实时数据管理器
- 多数据源统一接入（东方财富、复星、Alpaca）
- 实时 Tick 数据接收与处理
- 数据格式标准化（EventPriceUpdate DTO）
- Kafka 消息发布到 `ginkgo.live.market.data`
- 异常数据过滤与质量监控

### 2. TaskTimer - 定时任务调度器
- 基于 APScheduler 的 cron 调度
- 支持多种控制命令（bar_snapshot, update_selector, update_data）
- Kafka 命令发布到 `ginkgo.live.control.commands`
- Redis 心跳上报（组件存活监控）
- 配置热重载支持
- Docker 容器化部署

### 3. Kafka Topic 标准化
- 统一使用 `KafkaTopics` 常量类
- 命名规范：`ginkgo.live.*` (实盘) / `ginkgo.*` (全局)
- 修复 Producer 配置（移除不支持的 enable_idempotence）

### 4. DTO 数据传输对象
- `BarDTO` - K线数据
- `PriceUpdateDTO` - 价格更新
- `ControlCommandDTO` - 控制命令
- `InterestUpdateDTO` - 持仓更新

### 5. LiveDataFeeder 接口
- 统一的数据源接入接口
- 工厂模式创建不同数据源实例
- 支持动态订阅/取消订阅

---

## Changes Statistics

```
83 files changed, 17070 insertions(+), 1672 deletions(-)
```

| Category | Files | Lines | Description |
|----------|-------|-------|-------------|
| **Source Code** | 20 | ~3500 | Core implementation |
| **Tests** | 20 | ~3500 | Unit & integration tests |
| **Documentation** | 15 | ~6500 | Spec, design, research |
| **Configuration** | 5 | ~200 | Docker, configs |
| **Examples** | 10 | ~1800 | Manual test scripts |

---

## New Components

### Core Modules
```
src/ginkgo/livecore/
├── data_manager.py          # 实时数据管理器
├── task_timer.py            # 定时任务调度器
├── utils/
│   ├── decorators.py        # 任务装饰器
│   └── heartbeat.py         # 心跳监控工具
└── trade_gateway_adapter.py # 交易网关适配器

src/ginkgo/interfaces/
├── dtos/                    # 数据传输对象
│   ├── bar_dto.py
│   ├── price_update_dto.py
│   ├── control_command_dto.py
│   └── interest_update_dto.py
└── kafka_topics.py          # Kafka主题常量

src/ginkgo/trading/feeders/   # 实时数据源
├── eastmoney_feeder.py
├── fushu_feeder.py
└── alpaca_feeder.py

src/ginkgo/client/
└── tasktimer_cli.py         # TaskTimer CLI
```

### Tests
```
tests/
├── unit/
│   ├── interfaces/          # DTO 单元测试
│   └── livecore/            # DataManager & TaskTimer 测试
├── integration/
│   └── livecore/            # 集成测试
└── manual/                  # 手动测试脚本
    ├── test_cron.py
    ├── test_data_flow.py
    ├── e2e_test.py
    └── heartbeat_monitor.py
```

---

## Docker Deployment

### New Services in docker-compose.yml

```yaml
tasktimer:
  image: ginkgo/tasktimer:latest
  depends_on:
    - kafka1
    - redis-master
    - mongo-master
    - mysql-test
  environment:
    GINKGO_KAFKA_HOST: kafka1
    GINKGO_REDIS_HOST: redis-master
    GINKGO_MONGODB_HOST: mongo-master
    GINKGO_MYSQL_HOST: mysql-test
```

### TaskTimer Configuration

**File**: `~/.ginkgo/task_timer.yml`

```yaml
scheduled_tasks:
  - name: heartbeat_test
    cron: "0 0 * * *"      # 每天 00:00
    command: heartbeat_test
    enabled: true

  - name: bar_snapshot
    cron: "0 21 * * *"     # 每天 21:00
    command: bar_snapshot
    enabled: true

  - name: update_selector
    cron: "0 * * * *"      # 每小时
    command: update_selector
    enabled: true
```

---

## Testing

### Unit Tests
```bash
# DTO 测试
pytest tests/unit/interfaces/test_bar_dto.py
pytest tests/unit/interfaces/test_control_command_dto.py

# LiveCore 测试
pytest tests/unit/livecore/test_data_manager.py
pytest tests/unit/livecore/test_task_timer.py
pytest tests/unit/livecore/test_feeders.py
```

### Integration Tests
```bash
pytest tests/integration/livecore/test_data_manager_integration.py
pytest tests/integration/livecore/test_task_timer_integration.py
```

### Manual Tests
```bash
# 测试 TaskTimer
python tests/manual/start_task_timer.py
python tests/manual/test_cron.py
python tests/manual/test_reload.py

# 测试数据流
python tests/manual/test_data_flow.py
python tests/manual/e2e_test.py

# 监控心跳
python tests/manual/heartbeat_monitor.py
```

---

## Breaking Changes

### None
This is a pure addition module. Existing functionality remains unchanged.

---

## Migration Notes

### 1. Environment Variables
No new environment variables required for existing services.

### 2. Dependencies
Added to `requirements.txt`:
```
apscheduler==3.11.0
```

### 3. Kafka Topics
New topics created automatically:
- `ginkgo.live.market.data` - 实时行情数据
- `ginkgo.live.control.commands` - 控制命令
- `ginkgo.live.schedule.updates` - 调度更新

### 4. Configuration Files
New optional configuration:
- `~/.ginkgo/task_timer.yml` - TaskTimer 调度配置

---

## Acceptance Checklist

### P1 - Critical Features
- [x] DataManager 能够接收实时 Tick 数据并发布到 Kafka
- [x] TaskTimer 能够按 cron 表达式发送控制命令
- [x] ExecutionNode 能够接收并处理控制命令
- [x] Kafka topic 命名标准化完成
- [x] Docker 容器化部署完成

### P2 - Important Features
- [x] 多数据源接口定义完成
- [x] DTO 数据验证通过单元测试
- [x] Redis 心跳监控正常工作
- [x] 配置热重载功能正常

### P3 - Nice to Have
- [x] 手动测试脚本完成
- [x] 集成测试覆盖
- [x] 文档完整（spec, design, research）

---

## Known Issues

1. **Kafka Producer Warning**
   - 症状：`Kafka producer not available, falling back to sync mode`
   - 影响：NotificationService 降级到同步模式
   - 状态：非致命警告，功能正常

2. **待完成功能**
   - 数据源自动切换（多数据源容错）
   - 数据质量监控告警
   - Tick 数据去重逻辑

---

## Review Points

### For Reviewers
1. **DataManager 设计** - 多数据源接入架构是否合理？
2. **TaskTimer 调度** - cron 表达式配置是否满足需求？
3. **Kafka 消息流** - EventPriceUpdate 和 ControlCommand 的设计是否完整？
4. **DTO 验证** - 数据校验规则是否严格？
5. **测试覆盖** - 单元测试和集成测试是否充分？

---

## Related Specs

- [Feature Spec](specs/008-live-data-module/spec.md)
- [Design Document](specs/008-live-data-module/design/data-manager-multi-source.md)
- [Research Notes](specs/008-live-data-module/research.md)
- [Tasks Breakdown](specs/008-live-data-module/tasks.md)

---

## Commits

```
e335af0 feat(tasktimer): add container deployment and kafka topic standardization
f9a9c23 fix: correct test_thread_can_be_started assertion logic
b01db08 fix: correct import path for DIRECTION_TYPES and ORDER_TYPES
cc38795 fix: implement TDD Green phase tests for strategy evaluation rules
bf51bb1 test: implement TDD Green phase tests for 008-live-data-module
d49de15 test: implement TDD Green phase tests for DTOs and TaskTimer
8627aae feat: complete 008-live-data-module implementation
```

---

## Deploy Instructions

### 1. Pull Latest Code
```bash
git pull origin main
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start Services
```bash
# 使用 docker-compose 启动所有服务
docker compose -f .conf/docker-compose.yml up -d tasktimer

# 或手动启动 TaskTimer
ginkgo tasktimer start
```

### 4. Verify Status
```bash
# 查看 TaskTimer 状态
docker logs tasktimer --tail 50

# 检查 Kafka topics
ginkgo data kafka list topics
```

---

## Contact

**Author**: Claude + kaoru
**Branch**: `008-live-data-module`
**Reviewers**: TBD

---

*Last Updated: 2026-01-20*
