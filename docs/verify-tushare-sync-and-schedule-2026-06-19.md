# 验证：tushare 数据更新 + schedule 定期更新（2026-06-19）

> 目标：在不被远端封禁前提下，验证「数据更新功能是否正常」+「结合 schedule 定期更新是否 work」。

## 结论速览
| 部分 | 结论 |
|---|---|
| A. 手动数据更新（4 类全覆盖） | ✅ **day/adjustfactor/tick/stockinfo 均正常**（tick 走 TDX 非 tushare；stockinfo 需绕过 CLI 桩） |
| B. schedule 定期更新 `TaskTimer→Kafka→DataWorker` | ❌ **不 work**（两个独立 bug，**已于 PR #6185 修复**，merge `2488120e`） |

## 跟踪 issue（2026-06-19 拆分 → **已由 PR #6185 修复合并**，merge `2488120e`，2026-06-19T15:03Z；3 issue 已闭）
- ✅ #6184 接线 stockinfo CLI → service（P2, mod:cli+mod:data）
- ✅ #6182 修复定时作业取不到股票列表（P1, mod:live+mod:data）— Bug 1
- ✅ #6183 修复 DataWorker 消费者 None 无重建（P1, mod:data+mod:live）— Bug 2

> 修复含完整单测（`test_data_cli`/`test_task_timer`/`test_data_worker`）；`_rebuild_consumer` 对运行时 poll 断连仍有已知局限，待定时/实盘验证。

## Part A — 手动同步（4 类全覆盖）✅
| 数据类型 | 数据源 | 实测结果 | 落库核验 |
|---|---|---|---|
| day/bar | tushare `pro.daily` | 缺口检测→1 次 API 取 8 条（20260609~0619）→ rm+ins 8 | ✅ latest=2026-06-19 |
| adjustfactor | tushare `pro.adj_factor` | 1 次 API 取 243 条（2025-06-19~2026-06-19）→ ✅ completed | ✅ upsert 成功 |
| **tick** | **TDX（通达信）非 tushare** | 单股单日取 **4909** 条 → 清旧→ClickHouse 批量写 | ✅ count=4909 |
| **stockinfo** | tushare `pro.stock_basic` | **1 次 API 取 5529 条，0 失败**（`stockinfo_service.sync()`）| ✅ 600036=银行/list_date=2002-04-09 |

### 各类要点
- **day**（`ginkgo data sync day --code`）：smart 增量，单股 ≤3yr=1 次 API。token/fetch/增量/DB 写全通。
- **adjustfactor**（`ginkgo data sync adjustfactor --code`）：增量 243 条，upsert 成功。
- **tick**（`ginkgo data sync tick --code --date`）：⚠ 数据源是 **TDX 不是 tushare**——不受 tushare 限流，天然安全；单日 4909 条秒级完成。
- **stockinfo**：⚠ **CLI `data sync stockinfo` 是桩**（"not yet implemented"），但 **service 层 `stockinfo_service.sync()` 完整可用**（5529 条 0 失败），DataWorker 也实现了 `_handle_stockinfo`。手动验证需直接调 service 或走调度路径。

### 限流安全分析（核心）
- **单股 ≤3yr = 1 次 API 调用**（`_calculate_daybar_window_size`：≤3yr 单请求）。tushare daily ~500 次/分，1 次调用零风险。
- ⚠ **架构张力**：`retry` 装饰器（`libs/utils/common.py:236`）`base_sleep=30s × backoff^i`，但 **`GCONF.DEBUGMODE` 为真时跳过等待立即重试**（line 272-274）。CLAUDE.md 要求 DB 操作 debug ON，但 debug ON 会让 tushare 失败时**立即重试 5-11 次**——正是会被封禁的行为。
- 风险边界：单次成功调用不触发 retry，安全；**批量同步遇瞬时 tushare 限流时**才暴露（debug ON 立即重试加剧封禁）。建议批量同步前关 debug，或加显式 token-bucket 限流。

## Part B — schedule 定期更新 ❌
链路：`TaskTimer(cron) → Kafka(ginkgo.data.commands) → DataWorker → tushare → DB`。
基础设施**全在跑**（docker：kafka1/2/3 三 broker + redis + mysql + clickhouse + 7 个 worker，up 25h）。但链路两处断裂：

### Bug 1 — 数据作业取不到股票列表（bar_snapshot/adjustfactor 变空操作）
- 现象：每日 21:00 `bar_snapshot` 触发 → `WARNING No stocks found, skipping`（48h 内仅 `update_selector` 发出 47 次，因它不需要股票列表）。
- 根因（`livecore/task_timer.py:841` `_get_all_stock_codes`）：
  1. **line 841 漏 `()`**：`service_hub.data.stockinfo_service` 取到的是 `dependency_injector.providers.Singleton` provider 对象，非实例（对比同文件 line 223/264 正确写法 `task_timer_execution_service()` 带括号）。
  2. **返值类型变了**：`get_stockinfos()` 现返 `ServiceResult`（有 `.data/.is_success`），非旧版 list。task_timer 仍按 list 用。
- 容器报 "MySQL object has no attribute"（旧码）、host 复现报 "Singleton..."（新码）——两者都失败，属 #6177/#6179 service 层重构后的遗留断裂。
- 修复方向：`svc = service_hub.data.stockinfo_service(); res = svc.get_stockinfos(); stocks = res.data if res.is_success else []`。

### Bug 2 — DataWorker 消费者 None 永久卡死
- 现象：`AttributeError: 'NoneType' object has no attribute 'consumer'`，错误计数 **18250+ 且每 5s +1** 持续上涨。启动期（00:51:02）consumer 曾成功连上 `ginkgo.data.commands`，05:12 后某瞬时错误致永久卡死。
- 根因（双重）：
  1. `GinkgoConsumer.__init__`（`data/drivers/ginkgo_kafka.py:200-242`）：任何异常都 `self.consumer = None`（line 237/242）。kafka-python 3.0.0 后瞬时断连异常类型多变，易落入 `except Exception` → consumer 被置 None。
  2. `DataWorker.run()`（`data/worker/worker.py:246-302`）：捕获到 None.poll() 异常后只 `time.sleep(5)` 重试**同一 None.poll()**，**无 `_init_consumer()` 重建逻辑** → 永久空转。
- 修复方向：run() 循环检测 `self._consumer.consumer is None` 时调 `_init_consumer()` 重建；或 GinkgoConsumer 加 reconnect。

## 副产物（正常项）
- **TaskTimer cron 机制本身正常**：`update_selector`（`0 * * * *` 每小时）48h 内准时发出 47 次，`bar_snapshot`/`heartbeat_test` 等 job 也正确注册（`Added job: bar_snapshot (0 21 * * *)`）。
- `data status` CLI 是未实现桩（"not yet implemented"）。
- `ginkgo status` 宿主显示 Workers:0 是可见性盲区（看不到 docker 容器内 worker）。

## 复现命令
```bash
# Part A 手动同步（单股，安全）
ginkgo data sync day --code 600036.SH
# Part B 诊断
docker logs ginkgo-tasktimer --since 48h 2>&1 | grep -iE "bar_snapshot|No stocks"
docker logs ginkgo-data-worker-1 2>&1 | grep -iE "NoneType|consumer" | tail
```
