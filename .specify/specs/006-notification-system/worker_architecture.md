# Notification Worker 架构设计

## 架构原则

参考 GTM 模块的设计，NotificationWorker 采用**进程级隔离架构**，支持容器化部署。

## 架构组件

### 1. Worker 运行模式

#### 前台模式（开发/测试）
```bash
ginkgo worker start --notification
```
- 在前台运行 Worker
- 输出日志到控制台
- 支持 Ctrl+C 优雅停止
- **已实现** ✅

#### 后台模式（生产环境）
```bash
ginkgo worker start --notification --daemon
ginkgo worker start --notification --daemon --count 3
```
- 使用 nohup 在后台运行
- 输出日志到文件
- 支持多实例部署
- **待实现** ⏸️

### 2. WorkerManager（进程管理器）

参考 GTM 的 `GinkgoThreadManager`，创建 `NotificationWorkerManager`：

```python
class NotificationWorkerManager:
    """Notification Worker 进程管理器"""

    def start_worker(count: int = 1)
    def stop_worker(pid: str)
    def stop_all_workers()
    def get_worker_status() -> Dict
    def scale_workers(count: int)
```

**功能**：
- 启动/停止 worker 进程
- 监控 worker 状态（通过 Redis）
- 支持水平扩缩容
- 自动重启失败的 worker

### 3. 消息格式标准化

**Worker 期望的格式**（已修复 ✅）：
```json
{
  "message_type": "simple",
  "user_uuid": "...",
  "content": "...",
  "title": "...",
  "channels": ["webhook"],
  "priority": 1
}
```

### 4. 容器化支持

#### 环境变量配置
```bash
KAFKA_HOST=localhost
KAFKA_PORT=9092
WORKER_MODE=daemon  # foreground | daemon
WORKER_COUNT=3
```

#### 健康检查端点
```bash
GET /health/workers
```
返回：
```json
{
  "healthy": true,
  "workers": [
    {"pid": 1234, "status": "running", "uptime": 3600},
    {"pid": 1235, "status": "running", "uptime": 3600}
  ]
}
```

#### 优雅停止
```python
def signal_handler(signum, frame):
    if signum in (signal.SIGTERM, signal.SIGINT):
        worker.stop(timeout=30)
        sys.exit(0)
```

## 实现计划

### Phase 1: 后台模式支持
- [ ] 添加 `--daemon` 标志到 `ginkgo worker start`
- [ ] 创建临时 worker 脚本
- [ ] 使用 nohup/subprocess 启动后台进程
- [ ] 日志重定向到文件

### Phase 2: WorkerManager
- [ ] 创建 `NotificationWorkerManager` 类
- [ ] 实现 PID 管理（Redis 存储）
- [ ] 实现状态监控
- [ ] 实现扩缩容功能

### Phase 3: 容器化优化
- [ ] 环境变量配置支持
- [ ] 健康检查端点
- [ ] Dockerfile 示例
- [ ] Kubernetes 部署示例

## Kafka Topic 设计

| Topic | 用途 | Partitions | Consumer Group |
|-------|------|------------|----------------|
| `notifications` | 通知消息 | 24 | `notification_worker_group` |

**分区策略**：
- 使用 `user_uuid` 作为 partition key
- 同一用户的消息总是发送到同一分区
- 保证消息顺序性

**消费策略**：
- `auto_offset_reset: earliest`
- `enable_auto_commit: false`
- 手动提交 offset（处理成功后）

## 监控指标

```python
{
  "messages_consumed": 1234,      # 总消费消息数
  "messages_sent": 1200,           # 成功发送数
  "messages_failed": 34,           # 失败数
  "messages_retried": 10,          # 重试数
  "avg_processing_time_ms": 50,    # 平均处理时间
  "uptime_seconds": 3600           # 运行时间
}
```

## 与 GTM 的对比

| 特性 | GTM (DataWorker) | NotificationWorker |
|------|------------------|-------------------|
| 进程隔离 | ✅ | ✅ |
| 后台模式 | ✅ | ⏸️ |
| 多实例 | ✅ | ⏸️ |
| WorkerManager | ✅ | ⏸️ |
| 容器化 | ⏸️ | ✅ (计划) |
| 消息格式 | `{type, code, ...}` | `{message_type, ...}` |
