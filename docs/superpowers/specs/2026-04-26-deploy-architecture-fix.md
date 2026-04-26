# Deploy 架构修正：Clone 强化 + 冻结机制

## 背景

设计文档（`docs/superpowers/specs/2026-03-30-one-click-deployment-design.md`）定义了 deploy 为深拷贝（deep clone）操作，但代码中存在绕过 clone 直接修改 mode 的路径，且已部署的组合没有冻结保护。本次修正堵住这些路径，补齐 deploy API，实现冻结机制。

## 设计决策

### 1. 废弃直接 mode 修改

**文件：** `src/ginkgo/data/crud/portfolio_crud.py`, `src/ginkgo/data/services/portfolio_service.py`

`PortfolioCRUD.update_mode()` 标记废弃，调用时抛出 `DeprecationWarning` + 拒绝执行。

`PortfolioService.update()` 过滤 `mode` 参数，不传递到 CRUD 层，日志提示 mode 不可直接修改。

**原则：** mode 只能通过 `DeploymentService.deploy()`（clone 创建新组合）或 `PortfolioService.add()`（直接创建空组合）设置，不可事后修改。

### 2. 冻结机制（计算值，非存储字段）

冻结状态通过查询 `MDeployment` 判定：

```python
def is_portfolio_frozen(portfolio_id: str) -> bool:
    """组合是否已部署（冻结）：MDeployment 中存在 source_portfolio_id 且 target 未删除"""
    deployments = deployment_crud.find(filters={"source_portfolio_id": portfolio_id})
    for d in deployments:
        target = portfolio_crud.find(filters={"uuid": d.target_portfolio_id, "is_del": False})
        if target and not target.is_empty():
            return True
    return False
```

**冻结范围：** 所有编辑——名称、描述、组件、参数、删除，全部拒绝。

**解冻条件：** 所有通过此组合部署的 target 组合都已软删除（`is_del=True`）或不存在。

**API 层 `config_locked` 字段：** `PortfolioSummary.config_locked` 改为调用 `is_portfolio_frozen()` 计算返回，不再硬编码 False。

### 3. 冻结检查的切入点

| 入口 | 检查方式 | 拒绝行为 |
|------|---------|---------|
| `PortfolioService.update()` | 调用 `is_portfolio_frozen()` | 返回 `ServiceResult.error("组合已部署，不可修改")` |
| `PortfolioSagaFactory.update_portfolio_saga()` | Saga 执行前检查 | 抛出 `BusinessError` |
| `PortfolioSagaFactory.delete_portfolio_saga()` | Saga 执行前检查 | 抛出 `BusinessError` |
| API `PUT /api/v1/portfolios/{uuid}` | Saga 层已拦截 | 返回 400 |
| API `DELETE /api/v1/portfolios/{uuid}` | Saga 层已拦截 | 返回 400 |

### 4. Deploy API 端点

**路由：** `POST /api/v1/deploy`

参考已有草案 `.claude/worktrees/deploy/api/routers/deployment.py`，补充到主分支。

```python
class DeployRequest(BaseModel):
    backtest_task_id: str = Field(..., description="已完成的回测任务 UUID")
    mode: str = Field(..., description="部署模式: paper / live")
    account_id: Optional[str] = Field(None, description="实盘账号 ID（live 模式必填）")
    name: Optional[str] = Field(None, description="新组合名称")

@router.post("/deploy")
async def deploy(req: DeployRequest):
    # 调用 DeploymentService.deploy()
    # 返回 { portfolio_id, deployment_id }

@router.get("/deploy/{portfolio_id}")
async def get_deployment_info(portfolio_id: str):
    # 查询部署信息

@router.get("/deploy")
async def list_deployments(task_id: Optional[str] = None):
    # 列出部署记录
```

Deploy 操作应走 `SagaTransaction`，步骤如下：
1. 创建新组合（compensate: 删除新组合）
2. 深拷贝文件/映射/参数（compensate: 删除拷贝）
3. 拷贝 MongoDB Graph（compensate: 删除拷贝）
4. 创建 MDeployment 记录（compensate: 删除记录）
5. LIVE 模式创建 MBrokerInstance（compensate: 删除实例）

### 5. create_paper_account 保留

`api/api/trading.py` 的 `create_paper_account` 允许直接创建空 PAPER 组合，走 `PortfolioService.add()`，不走 Saga。后续手动绑定组件走 `update_portfolio_saga`。

### 6. PaperTradingWorker 检查

`PaperTradingWorker._handle_deploy()` 收到 Kafka deploy 命令时，增加 mode 校验：
- 查询 portfolio 的 mode 字段
- 只接受 `PAPER` 或 `LIVE` 模式的组合
- 拒绝 `BACKTEST` 模式组合

### 7. MDeployment 状态流转

补充 `MDeployment.status` 的生命周期管理：

```
PENDING(0) → DEPLOYED(1) → STOPPED(3)
                  ↘ FAILED(2)
```

- deploy 成功后设为 DEPLOYED
- target 组合被删除时，deployment 状态更新为 STOPPED
- deploy 过程失败设为 FAILED

target 组合删除时更新 deployment 状态为 STOPPED，这是解冻 source 组合的关键——`is_portfolio_frozen()` 只检查 status=DEPLOYED 且 target 未删除的记录。

## 影响范围

```
src/ginkgo/data/crud/portfolio_crud.py           [改] 废弃 update_mode
src/ginkgo/data/services/portfolio_service.py     [改] 过滤 mode + 冻结检查
src/ginkgo/trading/services/deployment_service.py [改] 走 Saga + 状态管理
api/api/portfolio.py                              [改] config_locked 计算值
api/api/trading.py                                [改] 无（保留 create_paper_account）
api/routers/deployment.py                         [新] Deploy API 端点
api/main.py                                       [改] 注册 deploy router
api/services/saga_transaction.py                  [改] PortfolioSagaFactory 增加冻结检查 + deploy saga
src/ginkgo/workers/paper_trading_worker.py        [改] deploy 命令增加 mode 校验

图例: [新]=新增  [改]=修改
```

## 验证

1. 直接调用 `update_mode()` → 被拒绝，日志提示废弃
2. `PortfolioService.update(portfolio_id, mode=PAPER)` → mode 被忽略
3. 部署回测组合到模拟盘 → source 组合冻结，update/delete 被拒绝
4. 删除 target 模拟组合 → source 组合自动解冻
5. `POST /api/v1/deploy` → 创建新组合 + MDeployment 记录
6. `create_paper_account` → 正常创建空 PAPER 组合
7. PaperTradingWorker 收到 BACKTEST 组合的 deploy 命令 → 拒绝
