# Portfolio 级部署重设计

## 背景

当前部署入口在 BacktestTab 的回测任务卡片上，以 `backtest_task_id` 为主键。部署本质上是"克隆一个组合 + 设定新模式"，所以入口和 API 应以 `portfolio_id` 为中心。

## 设计决策

### 1. API 参数改为 portfolio_id

**文件：** `api/api/deployment.py`

`DeployRequest.backtest_task_id` 改为 `portfolio_id`（必填）。

```python
class DeployRequest(BaseModel):
    portfolio_id: str = Field(..., description="源组合 UUID")
    mode: str = Field(..., description="部署模式: paper / live")
    account_id: Optional[str] = Field(None, description="实盘账号 ID（live 模式必填）")
    name: Optional[str] = Field(None, description="新组合名称")
```

### 2. DeploymentService.deploy() 简化

**文件：** `src/ginkgo/trading/services/deployment_service.py`

- `deploy()` 直接接收 `portfolio_id`，跳过 task 验证步骤
- 从 portfolio 本身获取名称（不再从 task_data 取）
- `MDeployment.source_task_id` 设为 None（字段保留，nullable）

```
deploy(portfolio_id, mode, account_id, name) 流程:
1. 验证源 portfolio 存在且未冻结
2. 创建 PENDING deployment 记录
3. 读取源 portfolio 组件映射
4. 创建新 portfolio（目标模式）
5. 深拷贝组件（MFile clone + Mapping + Params）
6. 拷贝 MongoDB Graph
7. Live 模式创建 MBrokerInstance
8. 更新 deployment 为 DEPLOYED
```

### 3. Saga 层同步调整

**文件：** `api/services/saga_transaction.py`

`PortfolioSagaFactory.deploy_saga()` 参数改为 `portfolio_id`，内部调用更新后的 `deployment_service.deploy()`。

### 4. 前端：部署模态框提取为独立组件

**新文件：** `web-ui/src/components/portfolio/DeployModal.vue`

从 BacktestTab.vue 提取部署模态框（目标模式选择、实盘账号选择、名称输入），以 `portfolioId` 为 prop。

### 5. 前端：PortfolioDetail 加入部署按钮

**文件：** `web-ui/src/views/portfolio/PortfolioDetail.vue`

header-actions 区域新增「部署」按钮，条件：
- 仅 `portfolioStatus === 'idle'`（BACKTEST 模式）时显示
- PAPER/LIVE 模式不显示

### 6. 前端：PortfolioList 加入部署操作

**文件：** `web-ui/src/views/portfolio/PortfolioList.vue`

下拉菜单新增「部署」项，条件：
- 仅 BACKTEST 模式组合显示

### 7. 前端：移除 BacktestTab 的部署逻辑

**文件：** `web-ui/src/views/portfolio/tabs/BacktestTab.vue`

- 移除部署按钮（列表卡片和详情页两处）
- 移除部署模态框及相关状态/方法
- 移除 deploymentApi 导入

### 8. 前端 API 类型更新

**文件：** `web-ui/src/api/modules/deployment.ts`

`DeployRequest.backtest_task_id` → `portfolio_id`。

### 9. MDeployment.source_task_id 改为 nullable

**文件：** `src/ginkgo/data/models/model_deployment.py`

`source_task_id` 字段已有 nullable 语义，确认或显式标记。

### 10. DeploymentService.list_deployments 调整

**文件：** `src/ginkgo/trading/services/deployment_service.py`

`list_deployments` 的筛选参数从 `source_task_id` 改为 `portfolio_id`（按源组合筛选）。

API 端点 `GET /api/v1/deploy/` 的 query 参数同步调整。

## 不变的部分

- 克隆核心逻辑（映射、文件、参数、图、Broker）不变
- 冻结保护机制不变
- MDeployment 表结构不变（source_task_id 保留为 nullable）
- Saga 事务框架不变

## 影响文件

```
api/api/deployment.py                                    [改] API 参数
api/services/saga_transaction.py                         [改] deploy_saga 参数
src/ginkgo/trading/services/deployment_service.py        [改] deploy() 以 portfolio_id 为主键
src/ginkgo/data/models/model_deployment.py               [改] source_task_id nullable 确认
src/ginkgo/data/crud/deployment_crud.py                  [改] 新增 get_by_source_portfolio
web-ui/src/api/modules/deployment.ts                     [改] 类型定义
web-ui/src/components/portfolio/DeployModal.vue          [新] 独立部署模态框组件
web-ui/src/views/portfolio/PortfolioDetail.vue           [改] 新增部署按钮
web-ui/src/views/portfolio/PortfolioList.vue             [改] 菜单新增部署项
web-ui/src/views/portfolio/tabs/BacktestTab.vue          [改] 移除部署相关代码
```

## 验证

1. PortfolioDetail 页「部署」按钮仅对 BACKTEST 组合显示
2. PortfolioList 下拉菜单「部署」仅对 BACKTEST 组合显示
3. 部署成功后创建新组合 + MDeployment 记录，源组合冻结
4. BacktestTab 不再有部署按钮
5. `POST /api/v1/deploy/` 接收 portfolio_id，不再需要 task_id
6. `GET /api/v1/deploy/?portfolio_id=xxx` 按源组合筛选
