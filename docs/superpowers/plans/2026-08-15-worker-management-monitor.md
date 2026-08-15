# Worker 管理页纯监控化改造 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 删除 Worker 管理页不可用的 start/stop 假按钮，改造为纯监控页：心跳相对化 + stale 预警、回测 worker 活跃任务下钻（新端点）、统计卡与筛选联动。

**Architecture:** 后端沿 Redis 心跳（`BacktestWorkerHeartbeat.task_uuids`，#6846 已有）→ `SystemService` → 新 API 端点的链路透传任务明细，MySQL `backtest_task` 提供名称/状态/进度；前端单页面改造，复用现成 `formatRelativeTime`。

**Tech Stack:** FastAPI + SQLAlchemy（后端）、Vue 3 `<script setup>` + Pinia + vitest（前端）。

**Spec:** `docs/superpowers/specs/2026-08-15-worker-management-monitor-design.md`

## Global Constraints

- 分层：API 禁止直接调 CRUD，必须经 Service（CLAUDE.md）。
- 禁止修改 Base 类（BaseCRUD/BaseService）。
- 后端测试放 `tests/`，命令用 `/home/kaoru/.ginkgo/.venv/bin/python -m pytest`。
- 前端拦截器已拆信封：`request.get()` 直接返回 payload，分页取 `.items`，禁止二次 `.data` 解包。
- 心跳节奏：backtest worker `heartbeat_interval=10s`、`ttl=30s`（`src/ginkgo/workers/backtest_worker/node.py:69-70`）→ stale 阈值 30s 橙 / 60s 红。
- commit message 带 `(#6910)`，epic 分支直接 commit，不开子 PR。
- 后端响应统一走 `core.response.ok` 信封；Service 内异常兜底返回空列表（既有模式）。

---

### Task 1: redis_service 透传 task_uuids

**Files:**
- Modify: `src/ginkgo/data/services/redis_service.py`（`get_backtest_worker_status`，约 :800-840）
- Test: `tests/unit/data/services/test_redis_service.py`（文件末尾追加）

**Interfaces:**
- Produces: `get_backtest_worker_status()` 返回的每个 worker dict 新增键 `"task_uuids": List[str]`（缺省 `[]`）。Task 2/3 依赖此键。

- [ ] **Step 1: 写失败测试**

在 `tests/unit/data/services/test_redis_service.py` 文件末尾追加（该文件已 `from unittest.mock import` 与 `RedisService` 导入，若缺则补）：

```python
class TestBacktestWorkerStatusTaskUuids:
    """get_backtest_worker_status 透传心跳 task_uuids（#6846 字段，Worker 下钻数据源）。"""

    def test_task_uuids_passthrough(self):
        """心跳含 task_uuids → worker 状态原样透传。"""
        from unittest.mock import MagicMock

        service = RedisService()
        heartbeat = {
            "worker_id": "bw_test_1",
            "status": "running",
            "running_tasks": 1,
            "max_tasks": 5,
            "last_heartbeat": "2026-08-15T10:00:00",
            "task_uuids": ["uuid-a", "uuid-b"],
        }
        service._crud_repo = MagicMock()
        service._crud_repo.keys.return_value = ["ginkgo:backtest_worker:bw_test_1"]
        service._crud_repo.get.return_value = heartbeat

        result = service.get_backtest_worker_status()

        assert result.success
        assert len(result.data) == 1
        assert result.data[0]["task_uuids"] == ["uuid-a", "uuid-b"]

    def test_task_uuids_missing_defaults_empty(self):
        """旧格式心跳无 task_uuids → 默认 []（向后兼容）。"""
        from unittest.mock import MagicMock

        service = RedisService()
        heartbeat = {
            "worker_id": "bw_test_2",
            "status": "running",
            "running_tasks": 0,
            "max_tasks": 5,
            "last_heartbeat": "2026-08-15T10:00:00",
        }
        service._crud_repo = MagicMock()
        service._crud_repo.keys.return_value = ["ginkgo:backtest_worker:bw_test_2"]
        service._crud_repo.get.return_value = heartbeat

        result = service.get_backtest_worker_status()

        assert result.success
        assert result.data[0]["task_uuids"] == []
```

- [ ] **Step 2: 跑测试确认失败**

Run: `/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/data/services/test_redis_service.py::TestBacktestWorkerStatusTaskUuids -x -q`
Expected: FAIL（`KeyError: 'task_uuids'` 或断言不等）

- [ ] **Step 3: 最小实现**

`src/ginkgo/data/services/redis_service.py` `get_backtest_worker_status` 中 `workers.append({...})`（约 :826）追加一行：

```python
                        workers.append({
                            "worker_id": heartbeat_data.get("worker_id"),
                            "status": heartbeat_data.get("status", "unknown"),
                            "active_tasks": heartbeat_data.get("running_tasks", 0),
                            "max_tasks": heartbeat_data.get("max_tasks", 0),
                            "last_heartbeat": heartbeat_data.get("last_heartbeat", ""),
                            "task_uuids": heartbeat_data.get("task_uuids", []),
                        })
```

- [ ] **Step 4: 跑测试确认通过**

Run: `/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/data/services/test_redis_service.py::TestBacktestWorkerStatusTaskUuids -x -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/data/services/redis_service.py tests/unit/data/services/test_redis_service.py
git commit -m "feat(worker-monitor): redis 心跳状态透传 task_uuids 供下钻 (#6910)"
```

---

### Task 2: system_service 透传 task_uuids + get_worker_tasks

**Files:**
- Modify: `src/ginkgo/core/services/system_service.py`（`_format_workers` backtest 分支约 :139-146；文件末尾附近新增方法）
- Test: `tests/unit/core/services/test_system_service.py`（追加）

**Interfaces:**
- Consumes: Task 1 的 `get_backtest_worker_status()` worker dict 含 `task_uuids`。
- Consumes: `ginkgo.data.containers.container.backtest_task_service()` → `BacktestTaskService.get_by_task_id(task_id: str) -> ServiceResult`（`.success` / `.data` 为 MBacktestTask 实例，含 `task_id/name/status/progress/portfolio_id`）。
- Produces:
  - `get_workers_status()` 返回的 backtest_worker dict 新增 `"task_uuids": List[str]`。
  - `SystemService.get_worker_tasks(worker_id: str) -> Dict[str, Any]`，形状 `{"worker_id": str, "found": bool, "tasks": [{"task_id": str, "name": str, "status": str, "progress": int, "portfolio_id": str}]}`。Task 3 的端点原样 `ok(data=...)` 此返回值。

- [ ] **Step 1: 写失败测试**

`tests/unit/core/services/test_system_service.py` 追加（该文件已 `from unittest.mock import MagicMock, patch`）：

```python
class TestWorkerTasks:
    """get_worker_tasks + _format_workers 透传 task_uuids（Worker 管理页下钻）。"""

    def _heartbeat_components(self):
        return {
            "backtest_workers": [{
                "worker_id": "bw1", "status": "running", "running_tasks": 1,
                "max_tasks": 5, "last_heartbeat": "2026-08-15T10:00:00",
                "task_uuids": ["t-1", "t-2"],
            }],
        }

    def test_format_workers_passes_task_uuids(self):
        """_format_workers 不丢 task_uuids（此前被丢弃，下钻无数据源）。"""
        from ginkgo.core.services.system_service import SystemService
        svc = SystemService()
        workers = svc._format_workers(self._heartbeat_components())
        assert workers[0]["type"] == "backtest_worker"
        assert workers[0]["task_uuids"] == ["t-1", "t-2"]

    def test_get_worker_tasks_returns_task_details(self):
        """心跳 task_uuids → MySQL 任务明细（name/status/progress）。"""
        from ginkgo.core.services.system_service import SystemService

        task = MagicMock()
        task.task_id = "t-1"
        task.name = "bt-name"
        task.status = "running"
        task.progress = 42
        task.portfolio_id = "p-1"

        redis_svc = MagicMock()
        redis_svc.get_all_components_status.return_value = MagicMock(
            success=True, data=self._heartbeat_components())
        bw_status = MagicMock(success=True, data=[{
            "worker_id": "bw1", "status": "running", "active_tasks": 1,
            "max_tasks": 5, "last_heartbeat": "x", "task_uuids": ["t-1"],
        }])
        redis_svc.get_backtest_worker_status.return_value = bw_status

        task_svc = MagicMock()
        task_svc.get_by_task_id.return_value = MagicMock(success=True, data=task)

        svc = SystemService()
        with patch("ginkgo.service_hub") as hub, \
             patch("ginkgo.data.containers.container") as cont:
            hub.data.redis_service.return_value = redis_svc
            cont.backtest_task_service.return_value = task_svc
            result = svc.get_worker_tasks("bw1")

        assert result["found"] is True
        assert result["tasks"] == [{
            "task_id": "t-1", "name": "bt-name", "status": "running",
            "progress": 42, "portfolio_id": "p-1",
        }]

    def test_get_worker_tasks_unknown_worker(self):
        """未知 worker_id → found=False + 空 tasks（非异常）。"""
        from ginkgo.core.services.system_service import SystemService

        redis_svc = MagicMock()
        redis_svc.get_backtest_worker_status.return_value = MagicMock(
            success=True, data=[])

        svc = SystemService()
        with patch("ginkgo.service_hub") as hub:
            hub.data.redis_service.return_value = redis_svc
            result = svc.get_worker_tasks("nope")

        assert result == {"worker_id": "nope", "found": False, "tasks": []}

    def test_get_worker_tasks_orphan_uuid_still_listed(self):
        """心跳持有但 MySQL 无记录（任务刚结束）→ 仍列出，字段兜底。"""
        from ginkgo.core.services.system_service import SystemService

        redis_svc = MagicMock()
        redis_svc.get_backtest_worker_status.return_value = MagicMock(
            success=True, data=[{
                "worker_id": "bw1", "task_uuids": ["t-gone"],
                "status": "running", "active_tasks": 1,
                "max_tasks": 5, "last_heartbeat": "x",
            }])
        task_svc = MagicMock()
        task_svc.get_by_task_id.return_value = MagicMock(success=False, data=None)

        svc = SystemService()
        with patch("ginkgo.service_hub") as hub, \
             patch("ginkgo.data.containers.container") as cont:
            hub.data.redis_service.return_value = redis_svc
            cont.backtest_task_service.return_value = task_svc
            result = svc.get_worker_tasks("bw1")

        assert result["found"] is True
        assert result["tasks"] == [{
            "task_id": "t-gone", "name": "", "status": "unknown",
            "progress": 0, "portfolio_id": "",
        }]
```

注：`patch("ginkgo.service_hub")` 需与被测代码的 import 方式一致——`system_service.py` 内是函数级 `from ginkgo import service_hub`，patch 目标用 `"ginkgo.service_hub"`（模块属性）。若实跑发现 patch 不生效，改为 `patch("ginkgo.core.services.system_service.service_hub")` 并同步调整实现里的 import 位置。

- [ ] **Step 2: 跑测试确认失败**

Run: `/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/core/services/test_system_service.py::TestWorkerTasks -x -q`
Expected: FAIL（`KeyError: 'task_uuids'` / `AttributeError: ... get_worker_tasks`）

- [ ] **Step 3: 最小实现**

`_format_workers` backtest_worker 分支（约 :139-146）追加 `"task_uuids": w.get("task_uuids", []),`：

```python
        # BacktestWorker
        for w in components.get("backtest_workers", []):
            workers.append({
                "id": w.get("worker_id", "unknown"),
                "type": "backtest_worker",
                "status": _normalize_status(w.get("status", "unknown")),
                "task_count": w.get("active_tasks", 0),
                "max_tasks": w.get("max_tasks", 0),
                "last_heartbeat": w.get("last_heartbeat", ""),
                "task_uuids": w.get("task_uuids", []),
            })
```

同文件 `SystemService` 类内（`get_workers_status` 方法之后）新增：

```python
    def get_worker_tasks(self, worker_id: str) -> Dict[str, Any]:
        """
        获取回测 Worker 当前活跃任务详情（Worker 管理页行内下钻）。

        数据链路：心跳 BacktestWorkerHeartbeat.task_uuids (#6846) → MySQL
        backtest_task（task_id = task_uuid）。心跳持有但 MySQL 无记录的任务
        仍列出（字段兜底），避免"任务刚结束就消失"的闪断。
        """
        try:
            from ginkgo import service_hub
            from ginkgo.data.containers import container

            redis_service = service_hub.data.redis_service()
            if not redis_service:
                return {"worker_id": worker_id, "found": False, "tasks": []}

            bw_result = redis_service.get_backtest_worker_status()
            workers = (bw_result.data or []) if bw_result.success else []
            worker = next(
                (w for w in workers if w.get("worker_id") == worker_id), None)
            if worker is None:
                return {"worker_id": worker_id, "found": False, "tasks": []}

            task_service = container.backtest_task_service()
            tasks = []
            for task_uuid in worker.get("task_uuids") or []:
                r = task_service.get_by_task_id(task_uuid)
                if r.success and r.data is not None:
                    t = r.data
                    tasks.append({
                        "task_id": getattr(t, "task_id", task_uuid),
                        "name": getattr(t, "name", "") or "",
                        "status": getattr(t, "status", "unknown"),
                        "progress": getattr(t, "progress", 0),
                        "portfolio_id": getattr(t, "portfolio_id", ""),
                    })
                else:
                    tasks.append({
                        "task_id": task_uuid, "name": "", "status": "unknown",
                        "progress": 0, "portfolio_id": "",
                    })
            return {"worker_id": worker_id, "found": True, "tasks": tasks}
        except Exception as e:
            GLOG.ERROR(f"Failed to get worker tasks for {worker_id}: {e}")
            return {"worker_id": worker_id, "found": False, "tasks": []}
```

- [ ] **Step 4: 跑测试确认通过（含既有回归）**

Run: `/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/core/services/test_system_service.py -q`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/core/services/system_service.py tests/unit/core/services/test_system_service.py
git commit -m "feat(worker-monitor): SystemService 透传 task_uuids + get_worker_tasks (#6910)"
```

---

### Task 3: API 端点 GET /workers/{worker_id}/tasks

**Files:**
- Modify: `api/api/system.py`（`get_workers_by_type` 之后追加）
- Test: Create `tests/api/test_system_worker_tasks.py`

**Interfaces:**
- Consumes: Task 2 的 `SystemService.get_worker_tasks(worker_id) -> Dict`。
- Produces: `GET /api/v1/system/workers/{worker_id}/tasks` → `ok(data={"worker_id", "found", "tasks"})`。Task 4 前端消费此形状。

- [ ] **Step 1: 写失败测试**

创建 `tests/api/test_system_worker_tasks.py`（仿 `tests/api/test_system_workers_by_type.py` 模式）：

```python
# Worker 管理页下钻端点 — GET /workers/{worker_id}/tasks
# Upstream: api.system.get_worker_tasks
# Downstream: WebUI Worker 管理页行内展开（回测 worker 活跃任务）
# Role: 心跳 task_uuids → MySQL backtest_task 明细，供前端懒加载下钻。
import asyncio

from unittest.mock import patch, MagicMock


def run_async(coro):
    return asyncio.run(coro)


class TestWorkerTasksEndpoint:
    def test_returns_service_result(self):
        from api.system import get_worker_tasks
        payload = {"worker_id": "bw1", "found": True, "tasks": [{
            "task_id": "t-1", "name": "n", "status": "running",
            "progress": 42, "portfolio_id": "p-1"}]}

        with patch("api.system._get_system_service") as mock_svc:
            mock_svc.return_value.get_worker_tasks.return_value = payload
            resp = run_async(get_worker_tasks("bw1"))

        assert resp["data"] == payload

    def test_exception_returns_empty_not_500(self):
        """Service 抛错 → 空载荷（沿用本模块 ok 兜底模式），不 500。"""
        from api.system import get_worker_tasks

        with patch("api.system._get_system_service") as mock_svc:
            mock_svc.return_value.get_worker_tasks.side_effect = RuntimeError("boom")
            resp = run_async(get_worker_tasks("bw1"))

        assert resp["data"] == {"worker_id": "bw1", "found": False, "tasks": []}
```

- [ ] **Step 2: 跑测试确认失败**

Run: `/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/api/test_system_worker_tasks.py -x -q`
Expected: FAIL（`ImportError: cannot import name 'get_worker_tasks'`）

- [ ] **Step 3: 最小实现**

`api/api/system.py` 在 `get_workers_by_type` 之后追加（两段路径与单段 `{worker_type}` 路由无冲突）：

```python
@router.get("/workers/{worker_id}/tasks")
async def get_worker_tasks(worker_id: str):
    """Worker 管理页行内下钻：回测 Worker 活跃任务明细（心跳 task_uuids → MySQL）。"""
    try:
        svc = _get_system_service()
        return ok(data=svc.get_worker_tasks(worker_id))
    except Exception as e:
        logger.error(f"Failed to get worker tasks for {worker_id}: {e}")
        return ok(data={"worker_id": worker_id, "found": False, "tasks": []})
```

- [ ] **Step 4: 跑测试确认通过**

Run: `/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/api/test_system_worker_tasks.py tests/api/test_system_workers_by_type.py -q`
Expected: 全部 PASS（新 2 条 + 既有回归不破）

- [ ] **Step 5: Commit**

```bash
git add api/api/system.py tests/api/test_system_worker_tasks.py
git commit -m "feat(worker-monitor): 新增 GET /workers/{worker_id}/tasks 下钻端点 (#6910)"
```

---

### Task 4: 前端 api 模块 + store 清理（删假按钮的数据层）

**Files:**
- Modify: `frontend/src/renderer/api/modules/system.ts`
- Modify: `frontend/src/renderer/stores/system.ts`
- Test: Create `frontend/src/renderer/stores/__tests__/system.spec.ts`

**Interfaces:**
- Consumes: Task 3 端点形状 `{"worker_id", "found", "tasks": [...]}`。
- Produces:
  - `WorkerInfo.task_uuids?: string[]`
  - `interface WorkerTaskInfo { task_id: string; name: string; status: string; progress: number; portfolio_id: string }`
  - `systemApi.getWorkerTasks(workerId: string): Promise<{worker_id: string; found: boolean; tasks: WorkerTaskInfo[]}>`
  - store 不再导出 `startWorker` / `stopWorker`（Task 5 依赖其已删除）。

- [ ] **Step 1: 写失败测试**

创建 `frontend/src/renderer/stores/__tests__/system.spec.ts`：

```ts
/**
 * system store 导出面回归：start/stop worker 假能力已删（后端无端点，点击必 404）。
 * 此测试防止未来误加回。页面定位收口为纯监控（spec 2026-08-15）。
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useSystemStore } from '../system'

describe('useSystemStore 导出面（纯监控化）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('不再暴露 startWorker/stopWorker（后端端点不存在）', () => {
    const store = useSystemStore()
    expect((store as any).startWorker).toBeUndefined()
    expect((store as any).stopWorker).toBeUndefined()
  })

  it('监控核心能力保留：fetchWorkers/fetchStatus/enableAutoRefresh', () => {
    const store = useSystemStore()
    expect(typeof store.fetchWorkers).toBe('function')
    expect(typeof store.fetchStatus).toBe('function')
    expect(typeof store.enableAutoRefresh).toBe('function')
  })
})
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd /home/kaoru/Ginkgo/frontend && npx vitest run src/renderer/stores/__tests__/system.spec.ts`
Expected: FAIL（`startWorker` 不是 undefined）

- [ ] **Step 3: 最小实现**

`api/modules/system.ts`：

1. `WorkerInfo` 加字段（`pending_tasks` 行后）：

```ts
  task_uuids?: string[]
```

2. `WorkersResponse` 之后加类型：

```ts
export interface WorkerTaskInfo {
  task_id: string
  name: string
  status: string
  progress: number
  portfolio_id: string
}

export interface WorkerTasksResponse {
  worker_id: string
  found: boolean
  tasks: WorkerTaskInfo[]
}
```

3. 删除 `startWorker` / `stopWorker` 两方法及其注释（:109-120），替换为：

```ts
  /**
   * 回测 Worker 活跃任务下钻（行内展开懒加载）
   */
  getWorkerTasks(workerId: string): Promise<WorkerTasksResponse> {
    return request.get(`/api/v1/system/workers/${workerId}/tasks`)
  },
```

`stores/system.ts`：删除 `startWorker`、`stopWorker` 两个函数（:161-192）及 return 块中的 `startWorker,` / `stopWorker,` 两行。

- [ ] **Step 4: 跑测试确认通过**

Run: `cd /home/kaoru/Ginkgo/frontend && npx vitest run src/renderer/stores/__tests__/system.spec.ts src/renderer/stores/__tests__/auth.spec.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/renderer/api/modules/system.ts frontend/src/renderer/stores/system.ts frontend/src/renderer/stores/__tests__/system.spec.ts
git commit -m "refactor(client): 删 start/stop worker 假 API(后端无端点) + 新增 getWorkerTasks (#6910)"
```

---

### Task 5: heartbeatStaleLevel 工具函数

**Files:**
- Modify: `frontend/src/renderer/utils/format.ts`（`formatRelativeTime` 之后）
- Test: `frontend/src/renderer/utils/format.test.ts`（追加）

**Interfaces:**
- Produces: `heartbeatStaleLevel(dateStr?: string | null, now?: Date): 0 | 1 | 2` — 0=新鲜、1=超 TTL(30s)、2=两倍 TTL(60s)。Task 6 消费。

- [ ] **Step 1: 写失败测试**

`format.test.ts` 顶部 import 处补 `heartbeatStaleLevel`，并追加：

```ts
describe('heartbeatStaleLevel', () => {
  const now = new Date('2026-08-15T10:00:00')

  it('30s 内 → 0（新鲜）', () => {
    expect(heartbeatStaleLevel('2026-08-15T09:59:45', now)).toBe(0)
  })

  it('超 30s（TTL）→ 1（橙）', () => {
    expect(heartbeatStaleLevel('2026-08-15T09:59:20', now)).toBe(1)
  })

  it('超 60s（两倍 TTL）→ 2（红）', () => {
    expect(heartbeatStaleLevel('2026-08-15T09:58:50', now)).toBe(2)
  })

  it('空/非法输入 → 0（不告警）', () => {
    expect(heartbeatStaleLevel(null, now)).toBe(0)
    expect(heartbeatStaleLevel('garbage', now)).toBe(0)
  })
})
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd /home/kaoru/Ginkgo/frontend && npx vitest run src/renderer/utils/format.test.ts`
Expected: FAIL（import 报 `heartbeatStaleLevel` 不存在）

- [ ] **Step 3: 最小实现**

`format.ts` `formatRelativeTime` 函数之后追加：

```ts
/**
 * 心跳 stale 分级（对齐 backtest worker 心跳节奏：interval=10s、ttl=30s）
 * 0=新鲜 | 1=超 TTL 30s（橙） | 2=超两倍 TTL 60s（红）
 */
export function heartbeatStaleLevel(dateStr?: string | null, now: Date = new Date()): 0 | 1 | 2 {
  if (!dateStr) return 0

  try {
    const ms = new Date(dateStr).getTime()
    if (isNaN(ms)) return 0
    const diff = (now.getTime() - ms) / 1000
    if (diff >= 60) return 2
    if (diff >= 30) return 1
    return 0
  } catch {
    return 0
  }
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd /home/kaoru/Ginkgo/frontend && npx vitest run src/renderer/utils/format.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/renderer/utils/format.ts frontend/src/renderer/utils/format.test.ts
git commit -m "feat(client): heartbeatStaleLevel 心跳 stale 分级工具 (#6910)"
```

---

### Task 6: WorkerManagement.vue 纯监控化改造

**Files:**
- Modify: `frontend/src/renderer/views/admin/WorkerManagement.vue`

**Interfaces:**
- Consumes: Task 4 的 `systemApi.getWorkerTasks` / `WorkerTaskInfo` / `WorkerInfo.task_uuids`；Task 5 的 `heartbeatStaleLevel`；既有 `formatRelativeTime`（`utils/format.ts`）。
- Consumes: `systemStore.lastUpdate`（string | null，每次 fetchStatus 刷新）作为相对时间重渲染 tick。

- [ ] **Step 1: 模板改造**

1. 删"操作"列：`<th>操作</th>`（:68）与整个操作 `<td>`（:102-126）。
2. 表头加展开提示不需要新列——展开箭头放在 Worker ID 单元格内。
3. Worker ID 单元格改为（回测 worker 才有箭头）：

```html
<td class="monospace cell-id">
  <button
    v-if="record.type === 'backtest_worker'"
    class="expand-btn"
    :class="{ expanded: expandedIds.has(record.id) }"
    @click="toggleExpand(record)"
    title="活跃任务"
  >
    <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="9 18 15 12 9 6"></polyline>
    </svg>
  </button>
  <span>{{ record.id }}</span>
</td>
```

4. 心跳单元格（`:101`）改为：

```html
<td class="monospace" :class="staleCellClass(record.last_heartbeat)">
  {{ formatRelativeTime(record.last_heartbeat) }}
</td>
```

5. `</tr>` 之后、`</tbody>` 之前，为回测 worker 插入展开行：

```html
<tr v-if="record.type === 'backtest_worker' && expandedIds.has(record.id)" class="expand-row">
  <td colspan="5">
    <div v-if="expandLoading.has(record.id)" class="expand-hint">加载中…</div>
    <div v-else-if="expandError.has(record.id)" class="expand-hint expand-error">加载失败，点击箭头重试</div>
    <div v-else-if="(expandedTasks[record.id] || []).length === 0" class="expand-hint">无活跃任务</div>
    <table v-else class="mini-table">
      <thead>
        <tr><th>任务</th><th>状态</th><th>进度</th><th>Portfolio</th></tr>
      </thead>
      <tbody>
        <tr v-for="t in expandedTasks[record.id]" :key="t.task_id">
          <td class="monospace">{{ t.name || t.task_id }}</td>
          <td>
            <span class="tag" :class="`tag-${getStatusColorClass(t.status)}`">{{ getStatusText(t.status) }}</span>
          </td>
          <td>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: `${t.progress}%` }"></div>
            </div>
            <span class="progress-num">{{ t.progress }}%</span>
          </td>
          <td class="monospace">{{ t.portfolio_id || '-' }}</td>
        </tr>
      </tbody>
    </table>
  </td>
</tr>
```

6. 删 `ConfirmDialog` 块（:133-140）。

- [ ] **Step 2: 脚本改造**

`<script setup>` 调整：

1. import 处：删 `ConfirmDialog`；加：

```ts
import { formatRelativeTime, heartbeatStaleLevel } from '@/utils/format'
import { systemApi } from '@/api'
import type { WorkerTaskInfo } from '@/api'
```

（`toast` 若仅剩 start/stop 使用则一并删；`WorkerInfo` type 保留。）

2. 删 `handleStart`、`handleStop`、`confirmOpen`、`confirmDesc`、`confirmAction`、`onConfirm`（:201-233）。

3. 统计卡联动——四个 computed 基数换为 `filteredWorkers`：

```ts
const runningCount = computed(() => filteredWorkers.value.filter(w => w.status === 'running' || w.status === 'active').length)
const stoppedCount = computed(() => filteredWorkers.value.filter(w => w.status === 'stopped' || w.status === 'idle').length)
const errorCount = computed(() => filteredWorkers.value.filter(w => w.status === 'error' || w.status === 'stale').length)
```

模板 :27 的 `workers.length` 同步改为 `filteredWorkers.length`。

4. 心跳 tick + stale 分级：

```ts
/** 相对时间重渲染 tick：随 store 每次刷新变化（自动刷新 5s 一跳） */
const heartbeatTick = computed(() => systemStore.lastUpdate)

const staleCellClass = (hb: string) => {
  heartbeatTick.value // 渲染期读取，建立响应依赖
  const level = heartbeatStaleLevel(hb)
  if (level === 2) return 'stale-2'
  if (level === 1) return 'stale-1'
  return ''
}
```

5. 下钻状态 + 懒加载：

```ts
const expandedIds = ref(new Set<string>())
const expandedTasks = ref<Record<string, WorkerTaskInfo[]>>({})
const expandLoading = ref(new Set<string>())
const expandError = ref(new Set<string>())

const toggleExpand = async (worker: WorkerInfo) => {
  const id = worker.id
  const next = new Set(expandedIds.value)
  if (next.has(id)) {
    // 收起：丢弃缓存，重展开时重新拉最新
    next.delete(id)
    expandedIds.value = next
    const { [id]: _drop, ...rest } = expandedTasks.value
    expandedTasks.value = rest
    return
  }
  next.add(id)
  expandedIds.value = next
  if (expandLoading.value.has(id)) return
  const loading = new Set(expandLoading.value)
  loading.add(id)
  expandLoading.value = loading
  const errs = new Set(expandError.value)
  errs.delete(id)
  expandError.value = errs
  try {
    const resp = await systemApi.getWorkerTasks(id)
    expandedTasks.value = { ...expandedTasks.value, [id]: resp.tasks || [] }
  } catch {
    const e = new Set(expandError.value)
    e.add(id)
    expandError.value = e
  } finally {
    const l = new Set(expandLoading.value)
    l.delete(id)
    expandLoading.value = l
  }
}
```

注意：自动刷新只重拉列表，不刷新已展开任务（避免行内容跳动）；收起再展开即重新拉取。

- [ ] **Step 3: 样式**

`<style scoped>` 删 `.action-buttons`/`.btn-icon`/`.btn-start`/`.btn-stop`（:372-405），追加：

```css
/* 心跳 stale 预警 */
.stale-1 { color: hsl(var(--warning)); }
.stale-2 { color: hsl(var(--error)); font-weight: 600; }

/* 下钻展开 */
.cell-id { display: flex; align-items: center; gap: 6px; }

.expand-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition: transform 0.2s, color 0.2s;
}

.expand-btn:hover { color: hsl(var(--foreground)); }
.expand-btn.expanded { transform: rotate(90deg); }

.expand-row > td { padding: 8px 12px 16px 40px; background: hsl(var(--secondary) / 0.3); }

.expand-hint { font-size: 12px; color: hsl(var(--muted-foreground)); padding: 4px 0; }
.expand-error { color: hsl(var(--error)); }

.mini-table { width: 100%; border-collapse: collapse; }
.mini-table th,
.mini-table td { padding: 6px 10px; text-align: left; border-bottom: 1px solid hsl(var(--border)); font-size: 12px; }
.mini-table th { color: hsl(var(--muted-foreground)); font-weight: 500; white-space: nowrap; }

.progress-bar {
  display: inline-block;
  width: 100px;
  height: 6px;
  border-radius: 3px;
  background: hsl(var(--secondary));
  overflow: hidden;
  vertical-align: middle;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  background: hsl(var(--primary));
  transition: width 0.3s;
}

.progress-num { margin-left: 8px; font-size: 11px; color: hsl(var(--muted-foreground)); }
```

（若 `--warning` token 不存在，用 `grep -rn "warning" frontend/src/renderer/assets/` 确认；没有则 `--primary` 替代橙档。）

- [ ] **Step 4: 类型检查 + 全前端测试**

Run: `cd /home/kaoru/Ginkgo/frontend && npm run build`
Expected: vue-tsc 0 error，vite build 成功

Run: `cd /home/kaoru/Ginkgo/frontend && npm run test`
Expected: 全部 PASS（含 Task 4/5 新增）

- [ ] **Step 5: 手工冒烟（可选但推荐）**

后端 `ginkgo serve api` + 前端 `npm run dev`，打开 Worker 管理页：
1. 无"操作"列，无 start/stop 按钮
2. 选类型筛选 → 四个统计卡数字联动
3. 心跳列显示"x 秒前"，停掉一个 worker 心跳后 30s+ 变橙、60s+ 变红
4. 回测 worker 行箭头展开 → 活跃任务/进度条或"无活跃任务"

- [ ] **Step 6: Commit**

```bash
git add frontend/src/renderer/views/admin/WorkerManagement.vue
git commit -m "feat(worker-monitor): Worker 管理页纯监控化——删控制列+心跳stale预警+任务下钻+统计卡联动 (#6910)"
```

---

## 收尾

- 全部任务完成后跑一次聚合回归（分批，勿单进程全量 `tests/`——OOM 铁律）：

```bash
/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/core/services/test_system_service.py tests/unit/data/services/test_redis_service.py::TestBacktestWorkerStatusTaskUuids tests/api/test_system_worker_tasks.py tests/api/test_system_workers_by_type.py -q
cd /home/kaoru/Ginkgo/frontend && npm run test
```
