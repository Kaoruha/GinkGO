# Phase 7: User Story 5 - 系统监控 (P3)

**状态**: ⚪ 未开始
**依赖**: Phase 3-4完成
**任务总数**: 8
**User Story**: 作为运维人员，我希望能够监控所有ExecutionNode和Portfolio的运行状态，在异常时接收通知

---

## 📋 验收标准

- [ ] ExecutionNode心跳正常上报
- [ ] Portfolio状态实时更新到Redis
- [ ] Queue满时触发通知（使用现有notification系统）
- [ ] API Gateway提供监控查询接口

---

## 📥 待办任务池 (8个)

### 7.1 监控指标收集 (5个任务)

### T065 [P] 创建metrics.py（留空）
**文件**: `src/ginkgo/workers/execution_node/metrics.py`
**并行**: 是
**描述**: 创建空文件，未来接入Prometheus监控

### T066 实现ExecutionNode.collect_metrics()方法
**文件**: `src/ginkgo/workers/execution_node/metrics.py`
**依赖**: T065
**描述**: 占位方法，return NotImplementedError（留待未来实现）

### T067 实现PortfolioState缓存到Redis
**文件**: `src/ginkgo/workers/execution_node/node.py`
**依赖**: T065
**描述**: portfolio:{id}:state

### T068 实现ExecutionNode状态缓存到Redis
**文件**: `src/ginkgo/workers/execution_node/node.py`
**依赖**: T065
**描述**: execution_node:{id}:info

### T069 [P] 编写监控指标单元测试
**文件**: `tests/unit/live/test_metrics.py`
**依赖**: T065, T067, T068
**描述**: 验证指标正确收集

---

### 7.2 监控API和容错 (3个任务)

### T070 [P] 创建监控查询API路由
**文件**: `api/routers/monitoring.py`
**并行**: 是
**描述**: GET /api/metrics, GET /api/nodes

### T071 编写Redis故障恢复测试
**文件**: `tests/integration/live/test_redis_failover.py`
**依赖**: T067, T068
**描述**: 验证Redis服务重启后ConnectionPool自动重连，Scheduler从Redis恢复状态

**详细测试场景**:
1. **ConnectionPool自动重连**:
   - 模拟Redis服务停止
   - 验证ExecutionNode心跳发送失败时捕获异常并重试
   - 验证不退出进程，继续尝试重连
   - Redis恢复后验证ConnectionPool自动重新连接

2. **Scheduler状态恢复**:
   - Scheduler将调度数据存储在Redis（execution_nodes, portfolio_assignments）
   - 模拟LiveCore重启
   - 验证Scheduler从Redis恢复最新调度计划
   - 验证恢复时间 < 5秒

3. **Docker DNS配置验证**:
   - 验证使用Docker Compose service名称配置Redis地址（REDIS_HOST=redis）
   - 验证Docker DNS自动解析IP变化

**验收**: Redis重启后ExecutionNode和Scheduler能自动恢复，状态不丢失

---

### T072 编写Redis容错机制测试
**文件**: `tests/integration/live/test_redis_tolerance.py`
**依赖**: T067, T068
**并行**: 否
**描述**: 验证Redis操作失败时的容错处理（FR-036, FR-037, FR-038）

**详细测试场景**:
1. **心跳失败重试 (FR-036)**:
   - 模拟Redis连接超时
   - 验证ExecutionNode.send_heartbeat()捕获异常并重试
   - 验证不退出进程，继续运行
   - 验证重试次数限制和退避策略

2. **Scheduler操作失败继续运行 (FR-037)**:
   - 模拟Scheduler Redis操作失败（读取节点状态）
   - 验证捕获异常并返回空值继续运行
   - 验证不影响调度循环的执行
   - 验证记录错误日志

3. **ConnectionPool重连配置 (FR-038)**:
   - 验证ConnectionPool配置retry_on_timeout=True
   - 验证连接池参数（socket_timeout, socket_connect_timeout）
   - 验证连接池大小和复用

**验收**: Redis操作失败时系统稳定运行，不崩溃

---

## 📝 备注

- T065, T070可以并行（2个任务）
- T071, T072是Redis容错测试任务
- 系统通知使用现有notification系统(006-notification-system)，不单独创建alerts模块

**文档版本**: 1.1.0 | **最后更新**: 2026-01-04 (移除alerts任务，使用notification系统)
