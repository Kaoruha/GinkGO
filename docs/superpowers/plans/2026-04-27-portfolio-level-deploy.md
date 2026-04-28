# Portfolio 级部署 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将部署入口从回测任务级别改为 Portfolio 级别，以 `portfolio_id` 为主键。

**Architecture:** 后端 `DeploymentService.deploy()` 改为接收 `portfolio_id` 而非 `backtest_task_id`，跳过 task 验证，直接克隆源组合。前端提取部署模态框为独立组件 `DeployModal.vue`，在 `PortfolioDetail` header 和 `PortfolioList` 下拉菜单两处触发。移除 `BacktestTab` 中所有部署相关代码。

**Tech Stack:** Python 3.12 + FastAPI + SQLAlchemy (后端), TypeScript + Vue 3 (前端)

---

### Task 1: MDeployment model — source_task_id nullable

**Files:**
- Modify: `src/ginkgo/data/models/model_deployment.py:27`

- [ ] **Step 1: 修改 source_task_id 为 nullable**

将 `source_task_id` 的 `default=""` 改为 `nullable=True, default=None`，并更新 `update` 方法的 singledispatch 签名：

```python
source_task_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, default=None, comment="回测任务ID（兼容旧数据）")
```

`update` 方法的 `str` 注册保持不变（兼容旧调用），不影响。

- [ ] **Step 2: Commit**

```bash
git add src/ginkgo/data/models/model_deployment.py
git commit -m "refactor(deploy): make MDeployment.source_task_id nullable"
```

---

### Task 2: DeploymentCRUD — 新增 get_by_source_portfolio

**Files:**
- Modify: `src/ginkgo/data/crud/deployment_crud.py`

- [ ] **Step 1: 添加 get_by_source_portfolio 方法**

在 `get_by_source_task` 后面新增：

```python
def get_by_source_portfolio(self, portfolio_id: str):
    """根据源Portfolio ID查询部署记录"""
    return self.find(filters={"source_portfolio_id": portfolio_id})
```

- [ ] **Step 2: Commit**

```bash
git add src/ginkgo/data/crud/deployment_crud.py
git commit -m "feat(deploy): add DeploymentCRUD.get_by_source_portfolio"
```

---

### Task 3: DeploymentService — 改为 portfolio_id 主键

**Files:**
- Modify: `src/ginkgo/trading/services/deployment_service.py`

- [ ] **Step 1: 重写 deploy() 方法签名和验证**

将 `deploy()` 从 `backtest_task_id` 改为 `portfolio_id`。跳过 task 验证，改为验证 portfolio 存在且未冻结。从 portfolio 本身获取名称。

新签名：

```python
def deploy(
    self,
    portfolio_id: str,
    mode: PORTFOLIO_MODE_TYPES,
    account_id: Optional[str] = None,
    name: Optional[str] = None,
) -> ServiceResult:
```

验证逻辑改为：

```python
# 1. 验证源 Portfolio 存在
portfolio_result = self._portfolio_service.get(portfolio_id=portfolio_id)
if not portfolio_result.success or not portfolio_result.data:
    return ServiceResult(success=False, error=f"组合不存在: {portfolio_id}")

portfolio_data = portfolio_result.data

# 2. 检查是否已冻结
if self._portfolio_service.is_portfolio_frozen(portfolio_id):
    return ServiceResult(success=False, error="组合已部署，不可再次部署")

# 3. 实盘模式验证账号
if mode == PORTFOLIO_MODE_TYPES.LIVE and not account_id:
    return ServiceResult(success=False, error="实盘部署需要提供 account_id")
```

- [ ] **Step 2: 更新 _deploy_core() 调用**

`deploy()` 中创建 MDeployment 记录时，`source_task_id` 设为 `None`，`source_portfolio_id` 直接用传入的 `portfolio_id`：

```python
deployment = MDeployment(
    source_task_id=None,
    target_portfolio_id="",
    source_portfolio_id=portfolio_id,
    mode=mode.value,
    account_id=account_id,
    status=DEPLOYMENT_STATUS.PENDING,
)
```

调用 `_deploy_core` 时去掉 `backtest_task_id` 和 `task_data` 参数，改为传 `portfolio_name`：

```python
return self._deploy_core(
    source_portfolio_id=portfolio_id,
    mode=mode,
    account_id=account_id,
    name=name,
    portfolio_name=portfolio_data.get("name", portfolio_id),
    deployment_id=deployment_id,
)
```

- [ ] **Step 3: 更新 _deploy_core() 签名和名称生成**

`_deploy_core` 去掉 `backtest_task_id`、`task_data` 参数，改为接收 `portfolio_name: str`。名称生成改为：

```python
if not name:
    mode_label = "PAPER" if mode == PORTFOLIO_MODE_TYPES.PAPER else "LIVE"
    name = f"{portfolio_name}_{mode_label}"
```

创建新 portfolio 的描述改为：

```python
description=f"部署自组合 {source_portfolio_id}"
```

日志也相应更新：

```python
GLOG.INFO(f"部署完成: {new_portfolio_id} <- {source_portfolio_id}")
```

- [ ] **Step 4: 更新 list_deployments() 筛选参数**

`list_deployments` 改为接收 `portfolio_id`（按源组合筛选）：

```python
def list_deployments(self, portfolio_id: str = None) -> ServiceResult:
    """列出部署记录"""
    if portfolio_id:
        records = self._deployment_crud.get_by_source_portfolio(portfolio_id)
    else:
        records = self._deployment_crud.find()
    # ... 后续不变
```

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/trading/services/deployment_service.py
git commit -m "refactor(deploy): DeploymentService uses portfolio_id as primary key"
```

---

### Task 4: Saga — deploy_saga 改为 portfolio_id

**Files:**
- Modify: `api/services/saga_transaction.py:691-731`

- [ ] **Step 1: 更新 deploy_saga 参数**

将 `deploy_saga` 的 `backtest_task_id` 参数改为 `portfolio_id`：

```python
@staticmethod
def deploy_saga(
    portfolio_id: str,
    mode: int,
    account_id: str = None,
    name: str = None,
) -> SagaTransaction:
    """创建部署 Saga（深拷贝 + MDeployment 记录）"""
    from ginkgo.data.containers import container
    from ginkgo.enums import PORTFOLIO_MODE_TYPES

    deployment_service = container.deployment_service()

    saga = SagaTransaction(f"portfolio:deploy:{portfolio_id}")
    context = {}

    def execute_deploy():
        result = deployment_service.deploy(
            portfolio_id=portfolio_id,
            mode=PORTFOLIO_MODE_TYPES(mode),
            account_id=account_id,
            name=name,
        )
        if not result.success:
            raise Exception(f"Deploy failed: {result.error}")
        context['result'] = result.data
        return result.data

    def compensate_deploy(data):
        portfolio_id_created = context.get('result', {}).get('portfolio_id')
        if portfolio_id_created:
            try:
                from ginkgo.data.containers import container as c
                portfolio_service = c.portfolio_service()
                portfolio_service.delete(portfolio_id=portfolio_id_created)
                logger.info(f"Compensated: deleted deployed portfolio {portfolio_id_created}")
            except Exception as e:
                logger.error(f"Deploy compensation failed: {e}")

    saga.add_step("deploy", execute_deploy, compensate_deploy)
    return saga
```

- [ ] **Step 2: Commit**

```bash
git add api/services/saga_transaction.py
git commit -m "refactor(deploy): deploy_saga uses portfolio_id"
```

---

### Task 5: API 层 — deployment.py 改为 portfolio_id

**Files:**
- Modify: `api/api/deployment.py`

- [ ] **Step 1: 更新 DeployRequest 模型**

```python
class DeployRequest(BaseModel):
    portfolio_id: str = Field(..., description="源组合 UUID")
    mode: str = Field(..., description="部署模式: paper / live")
    account_id: Optional[str] = Field(None, description="实盘账号 ID（live 模式必填）")
    name: Optional[str] = Field(None, description="新组合名称")
```

- [ ] **Step 2: 更新 deploy 端点**

```python
@router.post("/")
async def deploy(req: DeployRequest):
    """一键部署（走 Saga 事务）"""
    from ginkgo.enums import PORTFOLIO_MODE_TYPES
    from services.saga_transaction import PortfolioSagaFactory

    mode_map = {
        "paper": PORTFOLIO_MODE_TYPES.PAPER.value,
        "live": PORTFOLIO_MODE_TYPES.LIVE.value,
    }
    mode = mode_map.get(req.mode.lower())
    if mode is None:
        raise BusinessError(f"无效部署模式: {req.mode}，支持: paper / live")

    if mode == PORTFOLIO_MODE_TYPES.LIVE.value and not req.account_id:
        raise BusinessError("实盘部署需要提供 account_id")

    saga = PortfolioSagaFactory.deploy_saga(
        portfolio_id=req.portfolio_id,
        mode=mode,
        account_id=req.account_id,
        name=req.name,
    )

    success = await saga.execute()
    if not success:
        raise BusinessError(f"部署失败: {saga.error}. 事务已回滚。")

    return ok(data=saga.steps[0].result, message="部署成功")
```

- [ ] **Step 3: 更新 list_deployments 端点**

将 `task_id` query 参数改为 `portfolio_id`：

```python
@router.get("/")
async def list_deployments(portfolio_id: Optional[str] = Query(None, description="按源组合 ID 筛选")):
    """列出部署记录"""
    service = _get_deployment_service()
    result = service.list_deployments(portfolio_id=portfolio_id)

    if not result.success:
        raise BusinessError(result.error)

    return ok(data=result.data or [], message="查询成功")
```

- [ ] **Step 4: Commit**

```bash
git add api/api/deployment.py
git commit -m "refactor(deploy): API uses portfolio_id instead of backtest_task_id"
```

---

### Task 6: 前端 API 类型 — deployment.ts

**Files:**
- Modify: `web-ui/src/api/modules/deployment.ts`

- [ ] **Step 1: 更新类型和方法**

```typescript
import request from '../request'

// ========== 类型定义 ==========

export interface DeployRequest {
  portfolio_id: string
  mode: 'paper' | 'live'
  account_id?: string
  name?: string
}

export interface DeployResponse {
  portfolio_id: string
  deployment_id: string
  source_portfolio_id: string
}

export interface DeploymentInfo {
  deployment_id: string
  source_task_id: string | null
  target_portfolio_id: string
  source_portfolio_id: string
  mode: string
  account_id: string | null
  status: string
  create_at: string | null
}

// ========== API 方法 ==========

export const deploymentApi = {
  /**
   * 部署组合到模拟盘/实盘
   */
  deploy(params: DeployRequest) {
    return request.post('/api/v1/deploy/', params)
  },

  /**
   * 查询组合的部署信息
   */
  getStatus(portfolioId: string) {
    return request.get(`/api/v1/deploy/${portfolioId}`)
  },

  /**
   * 列出部署记录
   */
  list(portfolioId?: string) {
    const params: Record<string, string> = {}
    if (portfolioId) params.portfolio_id = portfolioId
    return request.get('/api/v1/deploy/', { params })
  },
}
```

- [ ] **Step 2: Commit**

```bash
git add web-ui/src/api/modules/deployment.ts
git commit -m "refactor(deploy): frontend API types use portfolio_id"
```

---

### Task 7: 前端 — 提取 DeployModal 组件

**Files:**
- Create: `web-ui/src/components/business/DeployModal.vue`

- [ ] **Step 1: 创建 DeployModal.vue**

从 BacktestTab 提取模态框逻辑为独立组件，接收 `portfolioId` prop，emit `success` 事件：

```vue
<template>
  <div v-if="visible" class="modal-overlay" @click.self="close">
    <div class="modal-box">
      <div class="modal-header">
        <h3>部署到模拟盘/实盘</h3>
        <button class="btn-close" @click="close">×</button>
      </div>
      <div class="modal-body">
        <div class="form-item">
          <label>目标模式</label>
          <div class="radio-group">
            <button class="radio-button" :class="{ active: mode === 'paper' }" @click="mode = 'paper'">模拟盘</button>
            <button class="radio-button" :class="{ active: mode === 'live' }" @click="mode = 'live'">实盘</button>
          </div>
        </div>
        <div v-if="mode === 'live'" class="form-item">
          <label>实盘账号</label>
          <select v-model="accountId" class="form-select">
            <option value="">选择实盘账号</option>
            <option v-for="acc in liveAccounts" :key="acc.uuid" :value="acc.uuid">
              {{ acc.name }} ({{ acc.exchange }} - {{ acc.environment }})
            </option>
          </select>
          <p v-if="liveAccounts.length === 0" class="form-hint">暂无可用实盘账号，请先在实盘账号管理中添加</p>
        </div>
        <div class="form-item">
          <label>组合名称（可选）</label>
          <input v-model="name" type="text" placeholder="留空自动生成" class="form-input" />
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" @click="close">取消</button>
        <button class="btn-primary" :disabled="deploying || (mode === 'live' && !accountId)" @click="handleDeploy">
          {{ deploying ? '部署中...' : '确认部署' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { deploymentApi, liveAccountApi } from '@/api'
import type { LiveAccount } from '@/api'
import { message } from '@/utils/toast'

const props = defineProps<{
  visible: boolean
  portfolioId: string
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'success', portfolioId: string): void
}>()

const mode = ref<'paper' | 'live'>('paper')
const accountId = ref('')
const name = ref('')
const deploying = ref(false)
const liveAccounts = ref<LiveAccount[]>([])

const close = () => emit('update:visible', false)

watch(() => props.visible, (val) => {
  if (val) {
    mode.value = 'paper'
    accountId.value = ''
    name.value = ''
    loadLiveAccounts()
  }
})

const loadLiveAccounts = async () => {
  try {
    const res: any = await liveAccountApi.getAccounts({ page: 1, page_size: 100, status: 'enabled' })
    liveAccounts.value = res?.data?.accounts || []
  } catch { liveAccounts.value = [] }
}

const handleDeploy = async () => {
  if (deploying.value) return
  if (mode.value === 'live' && !accountId.value) {
    message.warning('请选择实盘账号')
    return
  }
  deploying.value = true
  try {
    const res: any = await deploymentApi.deploy({
      portfolio_id: props.portfolioId,
      mode: mode.value,
      account_id: mode.value === 'live' ? accountId.value : undefined,
      name: name.value || undefined,
    })
    const newPortfolioId = res?.data?.portfolio_id
    close()
    message.success('部署成功')
    emit('success', newPortfolioId || '')
  } catch (e: any) {
    message.error('部署失败: ' + (e?.message || e))
  } finally {
    deploying.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-box {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  width: 480px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
}
.modal-header h3 { margin: 0; color: #fff; font-size: 16px; }
.btn-close { background: none; border: none; color: #8a8a9a; font-size: 18px; cursor: pointer; }
.btn-close:hover { color: #fff; }
.modal-body { padding: 20px; }
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 20px;
  border-top: 1px solid #2a2a3e;
}
.form-item { margin-bottom: 14px; }
.form-item label { display: block; font-size: 12px; color: #8a8a9a; margin-bottom: 4px; }
.form-input, .form-select {
  width: 100%;
  padding: 7px 10px;
  background: #0f0f1a;
  border: 1px solid #2a2a3e;
  border-radius: 4px;
  color: #fff;
  font-size: 13px;
}
.form-input:focus, .form-select:focus { border-color: #1890ff; outline: none; }
.form-hint { margin: 6px 0 0; font-size: 12px; color: #8a8a9a; }
.radio-group {
  display: inline-flex;
  background: #2a2a3e;
  border-radius: 4px;
  padding: 2px;
}
.radio-button {
  padding: 5px 12px;
  background: transparent;
  border: none;
  border-radius: 2px;
  color: #8a8a9a;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.radio-button:hover { color: #fff; }
.radio-button.active { background: #1890ff; color: #fff; }
.btn-primary {
  padding: 6px 14px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}
.btn-primary:hover { background: #40a9ff; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary {
  padding: 6px 14px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}
.btn-secondary:hover { background: #3a3a4e; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add web-ui/src/components/business/DeployModal.vue
git commit -m "feat(deploy): extract DeployModal as standalone component"
```

---

### Task 8: 前端 — PortfolioDetail 加入部署按钮

**Files:**
- Modify: `web-ui/src/views/portfolio/PortfolioDetail.vue`

- [ ] **Step 1: 导入 DeployModal**

在 `<script setup>` 的 import 区域添加：

```typescript
import DeployModal from '@/components/business/DeployModal.vue'
```

- [ ] **Step 2: 添加部署状态和方法**

在 `watch` 之前添加：

```typescript
const showDeployModal = ref(false)

const openDeploy = () => { showDeployModal.value = true }

const onDeploySuccess = (newPortfolioId: string) => {
  if (newPortfolioId) {
    router.push(`/portfolios/${newPortfolioId}`)
  }
  loadPortfolio()
}
```

- [ ] **Step 3: 在 header-actions 添加部署按钮**

在 `header-actions` div 中，在「编辑」按钮之后、「新建回测」按钮之前添加部署按钮：

```html
<button v-if="portfolioStatus === 'idle'" class="btn-deploy" @click="openDeploy">部署</button>
```

- [ ] **Step 4: 在 template 末尾添加 DeployModal**

在 `</div>` (`.portfolio-detail` 的闭合标签) 之前添加：

```html
<DeployModal
  v-model:visible="showDeployModal"
  :portfolio-id="portfolioId"
  @success="onDeploySuccess"
/>
```

- [ ] **Step 5: 添加 .btn-deploy 样式**

在 `<style scoped>` 中添加：

```css
.btn-deploy {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid #52c41a;
  border-radius: 6px;
  color: #52c41a;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-deploy:hover { background: #52c41a; color: #fff; }
```

- [ ] **Step 6: Commit**

```bash
git add web-ui/src/views/portfolio/PortfolioDetail.vue
git commit -m "feat(deploy): add deploy button to PortfolioDetail header"
```

---

### Task 9: 前端 — PortfolioList 加入部署操作

**Files:**
- Modify: `web-ui/src/views/portfolio/PortfolioList.vue`

- [ ] **Step 1: 导入 DeployModal**

在 import 区域添加：

```typescript
import DeployModal from '@/components/business/DeployModal.vue'
```

- [ ] **Step 2: 添加部署状态和方法**

在 `activeMenu` ref 后添加：

```typescript
const showDeployModal = ref(false)
const deployingPortfolio = ref<any>(null)

const openDeploy = (portfolio: any) => {
  deployingPortfolio.value = portfolio
  showDeployModal.value = true
  activeMenu.value = null
}

const onDeploySuccess = (newPortfolioId: string) => {
  fetchPortfolios({ page: 0, append: false })
  fetchStats()
  if (newPortfolioId) {
    router.push(`/portfolios/${newPortfolioId}`)
  }
}
```

- [ ] **Step 3: 在下拉菜单中添加部署项**

在 `dropdown-menu` 中，在「详情」按钮之后、「divider」之前，添加「部署」按钮，仅对 BACKTEST 模式显示（mode 为 0 或 'BACKTEST'）：

```html
<button v-if="portfolio.mode === 0 || portfolio.mode === 'BACKTEST'" class="dropdown-item" @click="openDeploy(portfolio)">
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M5 12h14"></path>
    <path d="M12 5l7 7-7 7"></path>
  </svg>
  部署
</button>
```

- [ ] **Step 4: 在 template 末尾添加 DeployModal**

在最后一个 `</template>` 之前（删除确认模态框之后）添加：

```html
<!-- 部署模态框 -->
<DeployModal
  v-if="deployingPortfolio"
  v-model:visible="showDeployModal"
  :portfolio-id="deployingPortfolio.uuid"
  @success="onDeploySuccess"
/>
```

- [ ] **Step 5: Commit**

```bash
git add web-ui/src/views/portfolio/PortfolioList.vue
git commit -m "feat(deploy): add deploy action to PortfolioList dropdown"
```

---

### Task 10: 前端 — 移除 BacktestTab 部署代码

**Files:**
- Modify: `web-ui/src/views/portfolio/tabs/BacktestTab.vue`

- [ ] **Step 1: 移除 import 中的 deploymentApi 和 liveAccountApi**

将第 497 行：

```typescript
import { backtestApi, deploymentApi, liveAccountApi } from '@/api'
```

改为：

```typescript
import { backtestApi } from '@/api'
```

移除 LiveAccount 类型导入（第 499 行）：

```typescript
import type { LiveAccount } from '@/api'
```

- [ ] **Step 2: 移除列表视图中的部署按钮**

删除第 72 行：

```html
<button v-if="task.status === 'completed'" class="link-btn link-deploy" @click="openDeployModal(task.uuid)">部署</button>
```

- [ ] **Step 3: 移除详情视图中的部署按钮**

删除第 233 行：

```html
<button v-if="currentTask.status === 'completed'" class="btn-deploy" @click="openDeployModal(currentTask.uuid)">部署</button>
```

- [ ] **Step 4: 移除部署模态框 HTML**

删除第 177-214 行的整个部署模态框 `<div v-if="showDeployModal"...>...</div>`。

- [ ] **Step 5: 移除部署相关的 script 状态和方法**

删除整个「部署状态」区块（第 544-597 行），包括：
- `showDeployModal`, `deployTaskId`, `deployMode`, `deployAccountId`, `deployName`, `deploying`, `liveAccounts` refs
- `openDeployModal()` 方法
- `loadLiveAccounts()` 方法
- `handleDeploy()` 方法

- [ ] **Step 6: 移除部署相关的 CSS**

删除以下 CSS 规则：
- `.link-btn.link-deploy` 和 `:hover`
- `.btn-deploy` 和 `:hover`

- [ ] **Step 7: Commit**

```bash
git add web-ui/src/views/portfolio/tabs/BacktestTab.vue
git commit -m "refactor(deploy): remove deploy code from BacktestTab"
```

---

### Task 11: 验证

- [ ] **Step 1: TypeScript 编译检查**

```bash
cd web-ui && npx vue-tsc --noEmit 2>&1 | head -30
```

Expected: 0 errors

- [ ] **Step 2: 检查所有变更文件**

```bash
git diff --stat master
```

确认变更文件列表与 spec 一致。

- [ ] **Step 3: Push**

```bash
git push
```
