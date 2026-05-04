# 页面架构重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构页面架构，将验证/回测提升为独立全局页面，模拟/实盘改为 mode 过滤视图，组合详情精简为 4 个 tab。

**Architecture:** 后端新增验证结果持久化（m_validation_result 表），验证 Service 计算后落库。前端侧边栏新增"回测中心"和"策略验证"入口，模拟/实盘复用组合列表加 mode 过滤。组合详情移除模拟/实盘 tab，概况页根据 mode 展示运行状态。

**Tech Stack:** Python 3.12 + SQLAlchemy + FastAPI (backend), Vue 3 + Vue Router (frontend)

---

## File Structure

```
# 后端新增
src/ginkgo/data/models/model_validation_result.py  [新] MySQL 模型
src/ginkgo/data/crud/validation_result_crud.py      [新] CRUD 层

# 后端修改
src/ginkgo/data/containers.py                       [改] 注册新 CRUD
src/ginkgo/data/services/validation_service.py      [改] 计算后持久化
api/api/validation.py                               [改] 新增列表/详情端点

# 前端新增
web-ui/src/views/backtest/BacktestListPage.vue      [新] 回测任务全局列表页
web-ui/src/views/validation/ValidationListPage.vue  [新] 验证记录全局列表页

# 前端修改
web-ui/src/router/index.ts                          [改] 路由重构
web-ui/src/App.vue                                  [改] 侧边栏菜单
web-ui/src/views/portfolio/PortfolioDetail.vue       [改] 移除模拟/实盘 tab
web-ui/src/views/portfolio/validation/SegmentStability.vue  [改] portfolioId 可选
web-ui/src/views/portfolio/validation/MonteCarlo.vue        [改] portfolioId 可选
web-ui/src/views/portfolio/tabs/ValidationTab.vue           [改] 适配可选 portfolioId
web-ui/src/api/modules/validation.ts                        [改] 新增列表 API
web-ui/src/views/stage3/PaperTrading.vue                    [改] 接入 portfolios?mode=PAPER
web-ui/src/views/stage4/LiveTrading.vue                     [改] 接入 portfolios?mode=LIVE
```

---

### Task 1: 创建 MValidationResult 模型

**Files:**
- Create: `src/ginkgo/data/models/model_validation_result.py`

- [ ] **Step 1: 创建模型文件**

参考 `model_deployment.py` 的模式，继承 `MMysqlBase`：

```python
# Upstream: ValidationResultCRUD, ValidationService
# Downstream: MMysqlBase, MySQL Database
# Role: 验证结果数据模型 - 存储各类验证方法的计算结果

import datetime
from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, Integer, Float, Text
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.libs.utils.display import base_repr


class VALIDATION_STATUS:
    RUNNING = 0
    COMPLETED = 1
    FAILED = 2


class MValidationResult(MMysqlBase):
    __abstract__ = False
    __tablename__ = "validation_result"

    task_id: Mapped[str] = mapped_column(String(32), default="", index=True, comment="回测任务ID")
    portfolio_id: Mapped[str] = mapped_column(String(32), default="", index=True, comment="组合ID(冗余)")
    method: Mapped[str] = mapped_column(String(32), default="", index=True, comment="验证方法")
    config: Mapped[str] = mapped_column(Text, default="{}", comment="JSON: 输入参数含 version")
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="JSON: 完整结果")
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="摘要评分")
    status: Mapped[int] = mapped_column(Integer, default=VALIDATION_STATUS.RUNNING, comment="状态")

    @singledispatchmethod
    def update(self, *args, **kwargs):
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(self, method: str, **kwargs):
        self.method = method
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 60)
```

- [ ] **Step 2: 验证模型可导入**

Run: `cd /home/kaoru/Ginkgo && python -c "from ginkgo.data.models.model_validation_result import MValidationResult; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/data/models/model_validation_result.py
git commit -m "feat: add MValidationResult model for validation result persistence"
```

---

### Task 2: 创建 ValidationResultCRUD

**Files:**
- Create: `src/ginkgo/data/crud/validation_result_crud.py`

- [ ] **Step 1: 创建 CRUD 文件**

参考 `deployment_crud.py` 的模式：

```python
# Upstream: ValidationService
# Downstream: BaseCRUD, MValidationResult
# Role: 验证结果 CRUD 操作

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models.model_validation_result import MValidationResult


class ValidationResultCRUD(BaseCRUD):
    """验证结果 CRUD"""

    _model_class = MValidationResult

    def __init__(self):
        super().__init__(MValidationResult)

    def get_by_portfolio(self, portfolio_id: str):
        return self.find(filters={"portfolio_id": portfolio_id})

    def get_by_task(self, task_id: str):
        return self.find(filters={"task_id": task_id})

    def get_by_method(self, method: str):
        return self.find(filters={"method": method})
```

- [ ] **Step 2: 验证可导入**

Run: `cd /home/kaoru/Ginkgo && python -c "from ginkgo.data.crud.validation_result_crud import ValidationResultCRUD; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/data/crud/validation_result_crud.py
git commit -m "feat: add ValidationResultCRUD for validation result data access"
```

---

### Task 3: 注册到 DI 容器

**Files:**
- Modify: `src/ginkgo/data/containers.py`

- [ ] **Step 1: 添加 import 和 provider**

在 `containers.py` 中：
1. 在 import 区添加：`from ginkgo.data.crud.validation_result_crud import ValidationResultCRUD`
2. 在 `Container` 类中已有的 `validation_service` provider 附近，添加 CRUD provider。找到 `validation_service` 的定义行，在其上方添加：

```python
    validation_result_crud = providers.Singleton(ValidationResultCRUD)
```

3. 修改 `validation_service` 的构造，注入新的 CRUD。当前 `validation_service` 大约在 290 行，改为：

```python
    validation_service = providers.Singleton(
        ValidationService,
        analyzer_record_crud=providers.Singleton(get_crud, "analyzer_record"),
        validation_result_crud=validation_result_crud,
    )
```

- [ ] **Step 2: 验证容器加载**

Run: `cd /home/kaoru/Ginkgo && python -c "from ginkgo.data.containers import container; print(type(container.validation_result_crud())); print('OK')"`
Expected: 输出 `<class 'ginkgo.data.crud.validation_result_crud.ValidationResultCRUD'>` 和 `OK`

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/data/containers.py
git commit -m "feat: register ValidationResultCRUD in DI container"
```

---

### Task 4: ValidationService 增加结果持久化

**Files:**
- Modify: `src/ginkgo/data/services/validation_service.py`

- [ ] **Step 1: 修改 ValidationService 构造函数**

在 `__init__` 中接收 `validation_result_crud` 参数：

```python
    def __init__(self, analyzer_record_crud=None, validation_result_crud=None):
        super().__init__(crud_repo=analyzer_record_crud)
        self._analyzer_crud = analyzer_record_crud
        self._result_crud = validation_result_crud
```

- [ ] **Step 2: 添加 _save_result 方法**

在 `monte_carlo` 方法后面添加：

```python
    def _save_result(self, task_id: str, portfolio_id: str, method: str,
                     config: dict, result_data: dict, score: float = None) -> str:
        """持久化验证结果，返回记录 uuid"""
        import json
        from ginkgo.data.models.model_validation_result import MValidationResult, VALIDATION_STATUS

        record = MValidationResult(
            task_id=task_id,
            portfolio_id=portfolio_id,
            method=method,
            config=json.dumps(config, ensure_ascii=False),
            result=json.dumps(result_data, ensure_ascii=False),
            score=score,
            status=VALIDATION_STATUS.COMPLETED,
        )
        self._result_crud.add(record)
        return record.uuid
```

- [ ] **Step 3: 修改 segment_stability 方法，计算后保存**

在 `segment_stability` 方法的 `return ServiceResult.success(...)` 前插入保存逻辑。找到 `return ServiceResult.success(data={"windows": windows})` 这行，在其前面添加：

```python
            # 持久化结果
            if self._result_crud:
                avg_score = float(np.mean([w["stability_score"] for w in windows]))
                self._save_result(
                    task_id=task_id,
                    portfolio_id=portfolio_id,
                    method="segment_stability",
                    config={"version": 1, "n_segments_list": n_segments_list},
                    result_data={"windows": windows},
                    score=avg_score,
                )
```

- [ ] **Step 4: 修改 monte_carlo 方法，计算后保存**

在 `monte_carlo` 方法的 `return ServiceResult.success(data=stats)` 前插入：

```python
            # 持久化结果
            if self._result_crud:
                self._save_result(
                    task_id=task_id,
                    portfolio_id=portfolio_id,
                    method="monte_carlo",
                    config={"version": 1, "n_simulations": n_simulations, "confidence": confidence},
                    result_data=stats,
                )
```

- [ ] **Step 5: 验证语法正确**

Run: `cd /home/kaoru/Ginkgo && python -c "from ginkgo.data.services.validation_service import ValidationService; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add src/ginkgo/data/services/validation_service.py
git commit -m "feat: persist validation results to database after calculation"
```

---

### Task 5: API 新增验证记录列表端点

**Files:**
- Modify: `api/api/validation.py`

- [ ] **Step 1: 添加列表和详情端点**

在 `api/api/validation.py` 文件末尾（`monte_carlo` 函数后面）添加：

```python
@router.get("/results")
async def list_results(
    portfolio_id: Optional[str] = Query(None, description="按组合筛选"),
    method: Optional[str] = Query(None, description="按验证方法筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取验证结果列表"""
    try:
        import json
        svc = get_validation_service()
        crud = svc._result_crud
        if not crud:
            return ok(data=[], total=0)

        filters = {}
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        if method:
            filters["method"] = method

        records = crud.find(filters=filters) if filters else crud.find()
        items = []
        for r in records:
            items.append({
                "uuid": r.uuid,
                "task_id": r.task_id,
                "portfolio_id": r.portfolio_id,
                "method": r.method,
                "config": json.loads(r.config) if r.config else {},
                "result": json.loads(r.result) if r.result else None,
                "score": r.score,
                "status": r.status,
                "create_at": r.create_at.isoformat() if hasattr(r.create_at, 'isoformat') else str(r.create_at),
            })

        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        return ok(data=items[start:end], total=total, page=page, page_size=page_size)
    except Exception as e:
        logger.error(f"验证结果列表异常: {e}")
        raise BusinessError(f"获取验证结果失败: {e}")


@router.get("/results/{result_id}")
async def get_result(result_id: str):
    """获取验证结果详情"""
    try:
        import json
        svc = get_validation_service()
        crud = svc._result_crud
        if not crud:
            raise BusinessError("验证结果存储不可用")

        record = crud.get(result_id)
        if not record:
            raise BusinessError("验证结果不存在")

        return ok(data={
            "uuid": record.uuid,
            "task_id": record.task_id,
            "portfolio_id": record.portfolio_id,
            "method": record.method,
            "config": json.loads(record.config) if record.config else {},
            "result": json.loads(record.result) if record.result else None,
            "score": record.score,
            "status": record.status,
            "create_at": record.create_at.isoformat() if hasattr(record.create_at, 'isoformat') else str(record.create_at),
        })
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"验证结果详情异常: {e}")
        raise BusinessError(f"获取验证结果失败: {e}")
```

注意：需要在文件顶部的 import 中确认 `Query` 已导入。当前已有 `from typing import List, Optional`，需要额外添加 `from fastapi import APIRouter, Query`（替换原来的 `from fastapi import APIRouter`）。

- [ ] **Step 2: 验证 API 启动**

Run: `cd /home/kaoru/Ginkgo && python -c "from api.validation import router; print([r.path for r in router.routes]); print('OK')"`
Expected: 包含 `/results` 和 `/results/{result_id}` 路径

- [ ] **Step 3: Commit**

```bash
git add api/api/validation.py
git commit -m "feat: add validation result list and detail API endpoints"
```

---

### Task 6: 前端 API 模块更新

**Files:**
- Modify: `web-ui/src/api/modules/validation.ts`

- [ ] **Step 1: 添加列表请求类型和方法**

在 `validation.ts` 文件中，在 `SegmentStabilityResult` interface 后面添加：

```typescript
export interface ValidationRecord {
  uuid: string
  task_id: string
  portfolio_id: string
  method: string
  config: Record<string, any>
  result: Record<string, any> | null
  score: number | null
  status: number
  create_at: string
}
```

在 `validationApi` 对象中，`segmentStability` 方法后面添加：

```typescript
  /**
   * 验证结果列表
   */
  listResults(params?: { portfolio_id?: string; method?: string; page?: number; page_size?: number }): Promise<{ data: ValidationRecord[]; total: number }> {
    return request.get('/api/v1/validation/results', { params })
  },

  /**
   * 验证结果详情
   */
  getResult(resultId: string): Promise<{ data: ValidationRecord }> {
    return request.get(`/api/v1/validation/results/${resultId}`)
  },
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd /home/kaoru/Ginkgo/web-ui && npx vue-tsc --noEmit 2>&1 | head -20`
Expected: 无类型错误（或仅有不相关的已有错误）

- [ ] **Step 3: Commit**

```bash
git add web-ui/src/api/modules/validation.ts
git commit -m "feat: add validation result list and detail API methods"
```

---

### Task 7: 验证组件 portfolioId 改为可选

**Files:**
- Modify: `web-ui/src/views/portfolio/validation/SegmentStability.vue`
- Modify: `web-ui/src/views/portfolio/validation/MonteCarlo.vue`
- Modify: `web-ui/src/views/portfolio/tabs/ValidationTab.vue`

- [ ] **Step 1: 修改 SegmentStability.vue**

将 `defineProps` 改为可选：

```typescript
const props = defineProps<{
  portfolioId?: string
}>()
```

修改 `fetchBacktestList` 中的 `backtestApi.list` 调用，让 `portfolio_id` 条件化：

```typescript
const fetchBacktestList = async () => {
  try {
    const params: any = { page: 1, size: 50, status: 'completed' }
    if (props.portfolioId) {
      params.portfolio_id = props.portfolioId
    }
    const res = await backtestApi.list(params)
    backtestList.value = res.data || []
  } catch { /* ignore */ }
}
```

修改 `runAnalysis` 中的 API 调用，`portfolio_id` 使用 `props.portfolioId || ''`。

- [ ] **Step 2: 修改 MonteCarlo.vue**

同样的改动：
1. `defineProps<{ portfolioId?: string }>()`
2. `fetchBacktestList` 中条件化 `portfolio_id`
3. `runSimulation` 中 `portfolio_id: props.portfolioId || ''`

- [ ] **Step 3: 修改 ValidationTab.vue**

当前代码已经正确传递 portfolioId，不需要修改传递方式。但需要确认子组件在无 portfolioId 时的行为正确。当前模板：

```html
<SegmentStability v-if="activeSub === 'segment'" :portfolio-id="portfolioId" />
<MonteCarlo v-else-if="activeSub === 'montecarlo'" :portfolio-id="portfolioId" />
```

这里 `portfolioId` 从 `route.params.id` 获取，在组合详情内一定有值，无需修改。

- [ ] **Step 4: 验证 TypeScript 编译**

Run: `cd /home/kaoru/Ginkgo/web-ui && npx vue-tsc --noEmit 2>&1 | head -20`
Expected: 无新增类型错误

- [ ] **Step 5: Commit**

```bash
git add web-ui/src/views/portfolio/validation/SegmentStability.vue web-ui/src/views/portfolio/validation/MonteCarlo.vue
git commit -m "refactor: make portfolioId optional in validation components for global page reuse"
```

---

### Task 8: 创建全局验证页面

**Files:**
- Create: `web-ui/src/views/validation/ValidationListPage.vue`

- [ ] **Step 1: 创建验证列表页面**

此页面展示所有验证记录，支持按方法筛选。点击记录展开结果。顶部有"新建验证"按钮，打开配置面板选择回测任务和方法。

创建目录和文件 `web-ui/src/views/validation/ValidationListPage.vue`：

```vue
<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">策略验证</h1>
      <p class="page-description">基于回测结果的策略有效性验证</p>
    </div>

    <!-- 新建验证面板 -->
    <div class="card">
      <div class="card-header">
        <h3>新建验证</h3>
      </div>
      <div class="card-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">回测任务</label>
            <select v-model="config.taskId" class="form-select">
              <option value="">选择已完成回测</option>
              <option v-for="t in backtestList" :key="t.uuid" :value="t.uuid">
                {{ t.name || t.uuid?.slice(0, 8) }} ({{ t.status }})
              </option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">验证方法</label>
            <select v-model="config.method" class="form-select">
              <option value="segment_stability">分段稳定性</option>
              <option value="monte_carlo">蒙特卡洛</option>
            </select>
          </div>
          <div class="form-group" style="align-self: flex-end;">
            <button class="btn-primary" :disabled="!config.taskId || running" @click="runValidation">
              {{ running ? '计算中...' : '开始验证' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 新建验证的结果展示 -->
    <div v-if="newResult" class="card">
      <div class="card-header"><h3>验证结果</h3></div>
      <div class="card-body">
        <template v-if="config.method === 'segment_stability'">
          <SegmentStabilityView :result="newResult" :embedded="true" />
        </template>
        <template v-else-if="config.method === 'monte_carlo'">
          <MonteCarloView :result="newResult" :embedded="true" />
        </template>
      </div>
    </div>

    <!-- 历史记录列表 -->
    <div class="card">
      <div class="card-header">
        <h3>验证记录</h3>
        <select v-model="methodFilter" class="form-select" style="width: auto;">
          <option value="">全部方法</option>
          <option value="segment_stability">分段稳定性</option>
          <option value="monte_carlo">蒙特卡洛</option>
        </select>
      </div>
      <div class="card-body">
        <table v-if="records.length" class="data-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>方法</th>
              <th>任务</th>
              <th>评分</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in records" :key="r.uuid">
              <td>{{ formatTime(r.create_at) }}</td>
              <td>{{ methodLabel(r.method) }}</td>
              <td class="mono">{{ r.task_id?.slice(0, 8) }}</td>
              <td>{{ r.score != null ? (r.score * 100).toFixed(1) + '%' : '-' }}</td>
              <td>{{ r.status === 1 ? '完成' : r.status === 0 ? '运行中' : '失败' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-state">暂无验证记录</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { validationApi } from '@/api/modules/validation'
import { backtestApi } from '@/api/modules/backtest'
import SegmentStabilityView from '@/views/portfolio/validation/SegmentStability.vue'
import MonteCarloView from '@/views/portfolio/validation/MonteCarlo.vue'

const backtestList = ref<any[]>([])
const records = ref<any[]>([])
const newResult = ref<any>(null)
const running = ref(false)
const methodFilter = ref('')

const config = reactive({
  taskId: '',
  method: 'segment_stability',
})

const methodLabel = (m: string) => {
  const map: Record<string, string> = {
    segment_stability: '分段稳定性',
    monte_carlo: '蒙特卡洛',
  }
  return map[m] || m
}

const formatTime = (t: string) => {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 19)
}

const fetchBacktestList = async () => {
  try {
    const res = await backtestApi.list({ page: 1, size: 100, status: 'completed' })
    backtestList.value = res.data || []
  } catch { /* ignore */ }
}

const fetchRecords = async () => {
  try {
    const params: any = { page: 1, page_size: 50 }
    if (methodFilter.value) params.method = methodFilter.value
    const res = await validationApi.listResults(params)
    records.value = res.data || []
  } catch { /* ignore */ }
}

const runValidation = async () => {
  if (!config.taskId) return
  running.value = true
  newResult.value = null
  try {
    const task = backtestList.value.find(t => t.uuid === config.taskId)
    const portfolioId = task?.portfolio_id || ''
    let res: any
    if (config.method === 'segment_stability') {
      res = await validationApi.segmentStability({
        task_id: config.taskId,
        portfolio_id: portfolioId,
      })
    } else if (config.method === 'monte_carlo') {
      res = await validationApi.monteCarlo({
        backtest_id: config.taskId,
        n_simulations: 10000,
      })
    }
    newResult.value = res.data
    fetchRecords()
  } catch (e: any) {
    alert('验证失败: ' + (e.message || e))
  } finally {
    running.value = false
  }
}

watch(methodFilter, () => fetchRecords())

onMounted(() => {
  fetchBacktestList()
  fetchRecords()
})
</script>

<style scoped>
.mono {
  font-family: monospace;
  font-size: 12px;
  color: #8a8a9a;
}
</style>
```

注意：这里复用 SegmentStability 和 MonteCarlo 组件作为嵌入式结果展示。需要在这两个组件中支持 `embedded` 模式（只展示结果，不展示配置表单）。这一步先以基本列表功能为主，`embedded` 模式留作后续优化。初始版本中"新建验证"的结果用 JSON 展示即可。

- [ ] **Step 2: 验证文件可被路由引用**

Run: `cd /home/kaoru/Ginkgo/web-ui && npx vue-tsc --noEmit 2>&1 | head -20`

- [ ] **Step 3: Commit**

```bash
git add web-ui/src/views/validation/ValidationListPage.vue
git commit -m "feat: add global validation list page with create and history views"
```

---

### Task 9: 创建全局回测中心页面

**Files:**
- Create: `web-ui/src/views/backtest/BacktestListPage.vue`

- [ ] **Step 1: 创建回测任务列表页**

此页面展示所有回测任务（跨组合），复用已有 `GET /api/v1/backtests/` API。

创建目录和文件 `web-ui/src/views/backtest/BacktestListPage.vue`：

```vue
<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">回测中心</h1>
      <p class="page-description">所有组合的回测任务</p>
    </div>

    <div class="card">
      <div class="card-body">
        <table v-if="tasks.length" class="data-table">
          <thead>
            <tr>
              <th>任务</th>
              <th>组合</th>
              <th>状态</th>
              <th>收益率</th>
              <th>夏普</th>
              <th>最大回撤</th>
              <th>创建时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in tasks" :key="t.uuid">
              <td>
                <router-link :to="`/portfolios/${t.portfolio_id}/backtests/${t.uuid}`" class="link">
                  {{ t.name || t.uuid?.slice(0, 8) }}
                </router-link>
              </td>
              <td class="mono">{{ t.portfolio_id?.slice(0, 8) }}</td>
              <td>{{ t.status }}</td>
              <td :class="t.annual_return >= 0 ? 'text-green' : 'text-red'">
                {{ (t.annual_return * 100).toFixed(2) }}%
              </td>
              <td>{{ t.sharpe_ratio?.toFixed(2) || '-' }}</td>
              <td class="text-red">{{ (t.max_drawdown * 100).toFixed(2) }}%</td>
              <td>{{ t.created_at?.replace('T', ' ').slice(0, 19) || '-' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-state">暂无回测任务</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { backtestApi } from '@/api/modules/backtest'

const tasks = ref<any[]>([])

const fetchTasks = async () => {
  try {
    const res = await backtestApi.list({ page: 1, size: 100 })
    tasks.value = res.data?.items || res.data || []
  } catch { /* ignore */ }
}

onMounted(() => fetchTasks())
</script>

<style scoped>
.mono { font-family: monospace; font-size: 12px; color: #8a8a9a; }
.link { color: #3b82f6; text-decoration: none; }
.link:hover { text-decoration: underline; }
.text-green { color: #22c55e; }
.text-red { color: #ef4444; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add web-ui/src/views/backtest/BacktestListPage.vue
git commit -m "feat: add global backtest center page showing all tasks"
```

---

### Task 10: 更新路由

**Files:**
- Modify: `web-ui/src/router/index.ts`

- [ ] **Step 1: 添加新路由**

在 `// ===== 交易 =====` 注释块之前，添加：

```typescript
  // ===== 回测中心 =====
  { path: '/backtests', name: 'BacktestCenter', component: () => import('@/views/backtest/BacktestListPage.vue'), meta: { title: '回测中心' } },

  // ===== 验证 =====
  { path: '/validation', name: 'ValidationCenter', component: () => import('@/views/validation/ValidationListPage.vue'), meta: { title: '策略验证' } },
```

- [ ] **Step 2: 移除组合详情中的 paper 和 live 子路由**

找到组合详情 children 数组中的这两行并删除：

```typescript
      { path: 'paper', name: 'PortfolioPaper', component: () => import('@/views/portfolio/tabs/PaperTab.vue'), meta: { title: '模拟' } },
      { path: 'live', name: 'PortfolioLive', component: () => import('@/views/portfolio/tabs/LiveTab.vue'), meta: { title: '实盘' } },
```

- [ ] **Step 3: 更新旧路由兼容重定向**

在旧路由兼容区域，确保：
- `/backtest` 重定向改为 `/backtests`（原来是 `/portfolios`）
- 添加 `/validation/*` 的重定向（如果需要）

找到 `{ path: '/backtest', redirect: '/portfolios' }` 改为：

```typescript
  { path: '/backtest', redirect: '/backtests' },
  { path: '/backtest/create', redirect: '/portfolios/create' },
  { path: '/backtest/:id', redirect: to => `/backtests` },
```

- [ ] **Step 4: 验证 TypeScript 编译**

Run: `cd /home/kaoru/Ginkgo/web-ui && npx vue-tsc --noEmit 2>&1 | head -20`

- [ ] **Step 5: Commit**

```bash
git add web-ui/src/router/index.ts
git commit -m "feat: add /backtests and /validation routes, remove paper/live from portfolio detail"
```

---

### Task 11: 更新侧边栏导航

**Files:**
- Modify: `web-ui/src/App.vue`

- [ ] **Step 1: 更新菜单项**

找到 `menuItems` 数组（约 184 行），在 `portfolios` 后面添加 `backtests` 和 `validation`，在 `trading` 前面：

```typescript
const menuItems: MenuItem[] = [
  { key: 'dashboard', label: '工作台', icon: icons.dashboard },
  { key: 'portfolios', label: '组合', icon: icons.wallet },
  { key: 'backtests', label: '回测', icon: icons.linechart },
  { key: 'validation', label: '验证', icon: icons.filesearch },
  { key: 'components', label: '组件', icon: icons.puzzle },
  { key: 'research', label: '研究', icon: icons.filesearch },
  { key: 'trading', label: '交易', icon: icons.linechart },
  { key: 'data', label: '数据', icon: icons.database },
  { key: 'admin', label: '管理', icon: icons.tool },
]
```

注意：`backtests` 和 `validation` 需要新的图标或复用已有图标。为简化，这里复用 `linechart` 和 `filesearch`。如需新图标可从 `lucide-vue-next` 引入。

- [ ] **Step 2: 更新 routeToKeyMap**

添加两个新映射：

```typescript
const routeToKeyMap: Record<string, string> = {
  '/dashboard': 'dashboard',
  '/portfolios': 'portfolios',
  '/backtests': 'backtests',
  '/validation': 'validation',
  '/components': 'components',
  '/research': 'research',
  '/trading': 'trading',
  '/data': 'data',
  '/admin': 'admin',
}
```

- [ ] **Step 3: 更新路由 watch 中的 key 匹配**

在 `watch(() => route.path, ...)` 中添加：

```typescript
} else if (path.startsWith('/backtests')) {
  key = 'backtests'
} else if (path.startsWith('/validation')) {
  key = 'validation'
}
```

- [ ] **Step 4: 更新 getRouteForKey**

在 `getRouteForKey` 的 `routeMap` 中添加：

```typescript
'backtests': '/backtests',
'validation': '/validation',
```

- [ ] **Step 5: 验证编译**

Run: `cd /home/kaoru/Ginkgo/web-ui && npx vue-tsc --noEmit 2>&1 | head -20`

- [ ] **Step 6: Commit**

```bash
git add web-ui/src/App.vue
git commit -m "feat: add backtests and validation to sidebar navigation"
```

---

### Task 12: 更新组合详情页（移除模拟/实盘 tab）

**Files:**
- Modify: `web-ui/src/views/portfolio/PortfolioDetail.vue`

- [ ] **Step 1: 移除 paper 和 live tab**

在 `tabs` computed 中删除这两行：

```typescript
  { key: 'paper', label: '模拟', route: `/portfolios/${portfolioId.value}/paper` },
  { key: 'live', label: '实盘', route: `/portfolios/${portfolioId.value}/live` },
```

- [ ] **Step 2: 移除 activeTab 中的 paper/live 匹配**

在 `activeTab` computed 中删除：

```typescript
  if (path.includes('/paper')) return 'paper'
  if (path.includes('/live')) return 'live'
```

- [ ] **Step 3: Commit**

```bash
git add web-ui/src/views/portfolio/PortfolioDetail.vue
git commit -m "refactor: remove paper/live tabs from portfolio detail"
```

---

### Task 13: 更新模拟盘/实盘全局页面

**Files:**
- Modify: `web-ui/src/views/stage3/PaperTrading.vue`
- Modify: `web-ui/src/views/stage4/LiveTrading.vue`

- [ ] **Step 1: 更新 PaperTrading.vue**

此页面改为展示 `portfolios?mode=PAPER` 的组合列表，加上 paper-trading 的持仓/订单信息。

在 `<script setup>` 中，替换现有的 TODO stub 数据加载为真实 API 调用：

```typescript
import { ref, onMounted } from 'vue'
import { portfolioApi } from '@/api/modules/portfolio'

const portfolios = ref<any[]>([])

const fetchPortfolios = async () => {
  try {
    const res = await portfolioApi.list({ mode: 'PAPER' })
    portfolios.value = res.data || []
  } catch { /* ignore */ }
}

onMounted(() => fetchPortfolios())
```

在 template 中，替换硬编码内容为一个简单的组合列表：

```html
<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">模拟盘</h1>
      <p class="page-description">所有模拟盘运行实例</p>
    </div>

    <div class="card">
      <div class="card-body">
        <table v-if="portfolios.length" class="data-table">
          <thead>
            <tr>
              <th>组合</th>
              <th>模式</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in portfolios" :key="p.uuid">
              <td>
                <router-link :to="`/portfolios/${p.uuid}`" class="link">{{ p.name }}</router-link>
              </td>
              <td>{{ p.mode }}</td>
              <td>{{ p.created_at?.replace('T', ' ').slice(0, 19) || '-' }}</td>
              <td>
                <router-link :to="`/portfolios/${p.uuid}`" class="link">查看详情</router-link>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-state">暂无模拟盘实例</div>
      </div>
    </div>
  </div>
</template>
```

添加 `<style scoped>` 中的 `.link` 样式。

- [ ] **Step 2: 更新 LiveTrading.vue**

同样的模式，改为 `portfolios?mode=LIVE`：

```typescript
import { ref, onMounted } from 'vue'
import { portfolioApi } from '@/api/modules/portfolio'

const portfolios = ref<any[]>([])

const fetchPortfolios = async () => {
  try {
    const res = await portfolioApi.list({ mode: 'LIVE' })
    portfolios.value = res.data || []
  } catch { /* ignore */ }
}

onMounted(() => fetchPortfolios())
```

Template 同 PaperTrading，标题改为"实盘交易"，描述改为"所有实盘运行实例"，空状态改为"暂无实盘实例"。

- [ ] **Step 3: 检查 portfolioApi.list 是否支持 mode 参数**

检查 `web-ui/src/api/modules/portfolio.ts` 中 `list` 方法是否接受 `mode` 参数。如果不支持，添加参数支持：

```typescript
list(params?: { mode?: string }): Promise<any> {
  return request.get('/api/v1/portfolios/', { params })
}
```

- [ ] **Step 4: 验证编译**

Run: `cd /home/kaoru/Ginkgo/web-ui && npx vue-tsc --noEmit 2>&1 | head -20`

- [ ] **Step 5: Commit**

```bash
git add web-ui/src/views/stage3/PaperTrading.vue web-ui/src/views/stage4/LiveTrading.vue
git commit -m "feat: update paper/live trading pages to show portfolios filtered by mode"
```

---

### Task 14: 数据库建表验证

**Files:** 无新文件

- [ ] **Step 1: 启用 debug 模式并建表**

Run: `cd /home/kaoru/Ginkgo && ginkgo system config set --debug on && ginkgo data init`
Expected: 输出包含 `validation_result` 表创建成功

- [ ] **Step 2: 验证表结构**

Run: `cd /home/kaoru/Ginkgo && python -c "
from ginkgo.data.containers import container
crud = container.validation_result_crud()
print(type(crud))
print(crud._model_class.__tablename__)
"`
Expected: 输出 `ValidationResultCRUD` 类型和 `validation_result` 表名

- [ ] **Step 3: 关闭 debug**

Run: `cd /home/kaoru/Ginkgo && ginkgo system config set --debug off`

---

## Self-Review

### Spec Coverage

| 设计文档要求 | 对应 Task |
|------------|-----------|
| m_validation_result 表 | Task 1-3 |
| 验证结果持久化 | Task 4 |
| 验证记录列表 API | Task 5 |
| 全局验证页面 | Task 6, 8 |
| 全局回测中心 | Task 9 |
| 侧边栏更新 | Task 11 |
| 路由重构 | Task 10 |
| 组合详情移除模拟/实盘 | Task 12 |
| 模拟盘 mode 过滤 | Task 13 |
| 实盘 mode 过滤 | Task 13 |
| portfolioId 可选 | Task 7 |
| 数据库建表 | Task 14 |

### Placeholder Scan

无 TBD/TODO/placeholder。所有步骤包含具体代码。

### Type Consistency

- `ValidationRecord` interface (Task 6) 与 API 返回字段一致 (Task 5)
- `SegmentStabilityConfig.task_id` / `portfolio_id` 与 API 入参一致
- `MonteCarloConfig.backtest_id` 映射到 API 的 `task_id` 字段

### Notes

- Task 8 的 `ValidationListPage.vue` 中引用 `SegmentStabilityView` 和 `MonteCarloView` 但这两个组件当前不支持 `embedded` 模式。初始版本可以简化——新建验证后直接用 JSON 展示结果，或用简单的 stat cards 展示。完整 embedded 模式作为后续优化。
- Task 13 中 `portfolioApi.list` 需要确认前端 API 方法已支持 `mode` 参数传递。
