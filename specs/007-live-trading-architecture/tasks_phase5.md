# Phase 5: User Story 3 - Portfolio动态调度 (P3)

**状态**: ⚪ 未开始
**依赖**: Phase 3-4完成
**任务总数**: 16
**User Story**: 作为系统管理员，我希望能够动态添加、删除、迁移Portfolio到不同的ExecutionNode

---

## 📋 验收标准

- [ ] Scheduler可以定期执行调度算法（每30秒）
- [ ] ExecutionNode心跳正常（每10秒上报，TTL=30秒）
- [ ] Portfolio配置更新时触发优雅重启（< 30秒）
- [ ] ExecutionNode故障时Portfolio自动迁移到健康Node（< 60秒）
- [ ] 手动迁移Portfolio功能正常

---

## 📥 待办任务池 (16个)

### 5.1 Scheduler调度器 (4个任务)

### T041 [P] 创建Scheduler主类
**文件**: `src/ginkgo/livecore/scheduler.py`
**并行**: 是
**描述**: 创建Scheduler主类，LiveCore容器线程，包含schedule_loop方法

### T042 实现Scheduler.assign_portfolios()方法
**文件**: `src/ginkgo/livecore/scheduler.py`
**依赖**: T041
**描述**: 实现负载均衡算法

### T043 实现Scheduler.publish_schedule_update()方法
**文件**: `src/ginkgo/livecore/scheduler.py`
**依赖**: T041
**描述**: 发布调度计划到Kafka schedule.updates topic

### T044 实现Scheduler.check_heartbeat()方法
**文件**: `src/ginkgo/livecore/scheduler.py`
**依赖**: T041
**描述**: 检查ExecutionNode心跳并检测离线

---

### 5.2 心跳机制 (3个任务)

### T045 [P] 实现ExecutionNode.send_heartbeat()方法
**文件**: `src/ginkgo/workers/execution_node/node.py`
**并行**: 是
**描述**: 每10秒向Redis SET heartbeat:node:{id} EX 30

### T046 实现ExecutionNode.subscribe_schedule_updates()方法
**文件**: `src/ginkgo/workers/execution_node/node.py`
**依赖**: T045
**描述**: 订阅Kafka schedule.updates topic

### T047 [P] 编写心跳机制集成测试
**文件**: `tests/integration/live/test_heartbeat.py`
**依赖**: T045, T046
**描述**: 验证心跳上报和超时检测

---

### 5.3 优雅重启机制 (4个任务)

### T048 实现ExecutionNode.handle_portfolio_reload()方法
**文件**: `src/ginkgo/workers/execution_node/node.py`
**依赖**: T046
**描述**: 处理portfolio.reload命令

### T049 实现Portfolio.graceful_reload()方法
**文件**: `src/ginkgo/core/portfolios/portfolio.py`
**依赖**: T048
**描述**: 实现完整的优雅重启流程（包含以下子步骤）

**详细子步骤**:
1. **状态转换**: RUNNING → STOPPING → STOPPED → RELOADING → RUNNING
   - 每个状态变更同步到Redis `portfolio:{id}:status`

2. **消息缓存**: STOPPING期间缓存消息到event_buffer
   - EventEngine检测到STOPPING状态，不再向Queue发送新消息
   - 将消息缓存到ExecutionNode的`event_buffer[portfolio_id]`
   - 限制buffer大小（MAX_BUFFER_SIZE=1000），防止内存溢出

3. **等待Queue清空**: 等待Portfolio Queue消费完所有消息
   - 检查Queue.size() == 0
   - 超时30秒强制进入下一步

4. **优雅关闭**: 调用portfolio.on_stop()清理资源

5. **加载新配置**: 从数据库加载新配置（version验证）

6. **重新初始化**: 创建新Portfolio实例（新配置）

7. **重放缓存消息**: 按顺序重放event_buffer中缓存的消息到Queue

8. **标记为RUNNING**: 更新Redis状态

**验收**: 配置更新时消息不丢失，切换时间 < 30秒

### T050 实现ExecutionNode.migrate_portfolio()方法
**文件**: `src/ginkgo/workers/execution_node/node.py`
**依赖**: T048
**描述**: 迁移Portfolio到其他Node

### T051 [P] 编写优雅重启集成测试
**文件**: `tests/integration/live/test_graceful_reload.py`
**依赖**: T048, T049, T050
**描述**: 验证配置更新时消息不丢失

---

### 5.4 控制命令集成 (5个任务)

### T052 [P] 创建引擎API路由
**文件**: `api/routers/engine.py`
**并行**: 是
**描述**: POST /api/engine/live/start, POST /api/engine/live/stop, GET /api/engine/live/status

### T053 实现API Gateway通过Redis查询LiveEngine状态
**文件**: `api/routers/engine.py`
**依赖**: T052
**描述**: GET /api/engine/live/status返回engine_status, running_portfolios等

### T054 [P] 创建调度API路由
**文件**: `api/routers/schedule.py`
**并行**: 是
**描述**: GET /api/scheduler/status, GET /api/schedule/plan

### T055 实现API Gateway通过Redis查询Scheduler状态
**文件**: `api/routers/schedule.py`
**依赖**: T054
**描述**: GET /api/scheduler/status返回scheduler_status, node_count等

### T056 实现API Gateway发布控制命令到Kafka
**文件**: `api/routers/engine.py, api/routers/schedule.py`
**依赖**: T052, T054
**描述**: engine.start/stop, portfolio.reload

---

## 📝 备注

- T041, T045, T052, T054可以并行（4个任务）
- T047, T051可以并行编写测试

**文档版本**: 1.0.0 | **最后更新**: 2026-01-04
