# Deploy 架构修正 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 堵住绕过 clone 直接修改 mode 的路径，补齐 Deploy API，实现基于 MDeployment 的冻结机制。

**Architecture:** 冻结状态通过查询 MDeployment 计算得出（非存储字段），所有编辑操作（update/delete）在 Service 层和 Saga 层增加冻结检查。Deploy 操作走 Saga 事务确保一致性。

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, dependency_injector

---

## File Structure

```
src/ginkgo/data/crud/portfolio_crud.py           [改] 废弃 update_mode
src/ginkgo/data/services/portfolio_service.py     [改] 过滤 mode + 冻结检查 + is_portfolio_frozen
src/ginkgo/trading/services/deployment_service.py [改] 走 Saga
api/api/portfolio.py                              [改] config_locked 计算值
api/api/trading.py                                [查] create_paper_account 保留不动
api/routers/deployment.py                         [新] Deploy API 端点
api/main.py                                       [改] 注册 deploy router
api/services/saga_transaction.py                  [改] 冻结检查 + deploy saga
src/ginkgo/workers/paper_trading_worker.py        [改] deploy 命令增加 mode 校验
tests/unit/data/services/test_portfolio_freeze.py [新] 冻结机制单元测试
tests/api/test_deployment_api.py                  [新] Deploy API 测试
```

---

### Task 1: 废弃 PortfolioCRUD.update_mode()

**Files:**
- Modify: `src/ginkgo/data/crud/portfolio_crud.py:225-228`

- [ ] **Step 1: 写测试**

在 `tests/unit/data/crud/test_portfolio_crud_mock.py`（如不存在则新建）添加：

```python
import pytest
import warnings

def test_update_mode_raises_deprecation():
    """update_mode 应抛出 DeprecationWarning 并拒绝执行"""
    from ginkgo.data.crud.portfolio_crud import PortfolioCRUD

    crud = PortfolioCRUD.__new__(PortfolioCRUD)
    with pytest.raises(DeprecationWarning, match="update_mode is deprecated"):
        crud.update_mode("test-uuid", 1)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/data/crud/test_portfolio_crud_mock.py::test_update_mode_raises_deprecation -v`
Expected: FAIL（当前 update_mode 不抛异常）

- [ ] **Step 3: 修改 update_mode 抛出 DeprecationWarning**

```python
def update_mode(self, uuid: str, mode) -> None:
    """Update portfolio mode.

    .. deprecated::
        mode 只能通过 DeploymentService.deploy() 或 PortfolioService.add() 设置。
        直接修改 mode 已废弃。
    """
    raise DeprecationWarning(
        "update_mode is deprecated. "
        "Use DeploymentService.deploy() to create deployed portfolios, "
        "or PortfolioService.add() for new portfolios."
    )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/data/crud/test_portfolio_crud_mock.py::test_update_mode_raises_deprecation -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/data/crud/portfolio_crud.py tests/unit/data/crud/test_portfolio_crud_mock.py
git commit -m "refactor: deprecate PortfolioCRUD.update_mode() with DeprecationWarning"
```

---

### Task 2: PortfolioService.update() 过滤 mode 参数

**Files:**
- Modify: `src/ginkgo/data/services/portfolio_service.py:114-161`

- [ ] **Step 1: 写测试**

```python
import pytest
from unittest.mock import MagicMock, patch

def test_update_ignores_mode_parameter():
    """update() 应忽略 mode 参数，不传递到 CRUD 层"""
    from ginkgo.data.services.portfolio_service import PortfolioService

    service = PortfolioService.__new__(PortfolioService)
    mock_crud = MagicMock()
    service._crud_repo = mock_crud

    result = service.update(
        portfolio_id="test-uuid",
        name="new-name",
        mode=1,  # 应被忽略
    )

    assert result.is_success()
    # 验证 modify 没有收到 mode
    call_args = mock_crud.modify.call_args
    updates = call_args[1]["updates"]
    assert "mode" not in updates
    assert "name" in updates
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/data/services/test_portfolio_freeze.py::test_update_ignores_mode_parameter -v`
Expected: FAIL（当前 mode 会传入 updates）

- [ ] **Step 3: 修改 PortfolioService.update()**

在 `src/ginkgo/data/services/portfolio_service.py` 的 `update()` 方法中，将 mode 处理块改为：

```python
if mode is not None:
    GLOG.WARN(
        f"Portfolio {portfolio_id}: mode modification ignored. "
        "Use DeploymentService.deploy() or PortfolioService.add()."
    )
    warnings.append("mode modification is not allowed, use deploy instead")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/data/services/test_portfolio_freeze.py::test_update_ignores_mode_parameter -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/data/services/portfolio_service.py tests/unit/data/services/test_portfolio_freeze.py
git commit -m "refactor: filter mode from PortfolioService.update() with warning"
```

---

### Task 3: 实现 is_portfolio_frozen() 冻结判定函数

**Files:**
- Modify: `src/ginkgo/data/services/portfolio_service.py`（添加新方法）

- [ ] **Step 1: 写测试**

在 `tests/unit/data/services/test_portfolio_freeze.py` 中追加：

```python
def test_is_portfolio_frozen_with_active_deployment():
    """有活跃部署时应返回 True"""
    from ginkgo.data.services.portfolio_service import PortfolioService

    service = PortfolioService.__new__(PortfolioService)
    mock_deployment_crud = MagicMock()
    mock_portfolio_crud = MagicMock()

    # 模拟：MDeployment 存在 source_portfolio_id 匹配
    mock_deployment = MagicMock()
    mock_deployment.target_portfolio_id = "target-uuid"
    mock_deployment.status = 1  # DEPLOYED
    mock_deployment_crud.find.return_value = [mock_deployment]

    # 模拟：target portfolio 存在且未删除
    mock_target = MagicMock()
    mock_portfolio_crud.find.return_value = [mock_target]

    service._deployment_crud = mock_deployment_crud
    service._crud_repo = mock_portfolio_crud

    assert service.is_portfolio_frozen("source-uuid") is True


def test_is_portfolio_frozen_no_deployment():
    """无部署记录时应返回 False"""
    from ginkgo.data.services.portfolio_service import PortfolioService

    service = PortfolioService.__new__(PortfolioService)
    mock_deployment_crud = MagicMock()
    mock_deployment_crud.find.return_value = []
    service._deployment_crud = mock_deployment_crud

    assert service.is_portfolio_frozen("source-uuid") is False


def test_is_portfolio_frozen_target_deleted():
    """target 已删除时应返回 False（可解冻）"""
    from ginkgo.data.services.portfolio_service import PortfolioService

    service = PortfolioService.__new__(PortfolioService)
    mock_deployment_crud = MagicMock()
    mock_portfolio_crud = MagicMock()

    mock_deployment = MagicMock()
    mock_deployment.target_portfolio_id = "target-uuid"
    mock_deployment.status = 1  # DEPLOYED
    mock_deployment_crud.find.return_value = [mock_deployment]

    # target 已删除（空列表）
    mock_portfolio_crud.find.return_value = []

    service._deployment_crud = mock_deployment_crud
    service._crud_repo = mock_portfolio_crud

    assert service.is_portfolio_frozen("source-uuid") is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/data/services/test_portfolio_freeze.py -v -k "frozen"`
Expected: FAIL（方法不存在）

- [ ] **Step 3: 添加 is_portfolio_frozen 方法**

在 `PortfolioService` 类中添加：

```python
def is_portfolio_frozen(self, portfolio_id: str) -> bool:
    """检查组合是否已部署（冻结）

    通过查询 MDeployment 判定：存在 source_portfolio_id 匹配且
    target 未删除且状态为 DEPLOYED 的记录时返回 True。
    """
    if not hasattr(self, '_deployment_crud') or self._deployment_crud is None:
        return False

    deployments = self._deployment_crud.find(
        filters={"source_portfolio_id": portfolio_id}
    )

    for d in deployments:
        if getattr(d, 'status', -1) != 1:  # DEPLOYMENT_STATUS.DEPLOYED = 1
            continue
        target_id = getattr(d, 'target_portfolio_id', None)
        if not target_id:
            continue
        targets = self._crud_repo.find(
            filters={"uuid": target_id, "is_del": False}
        )
        if targets and len(targets) > 0:
            return True

    return False
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/data/services/test_portfolio_freeze.py -v -k "frozen"`
Expected: PASS

- [ ] **Step 5: 注入 deployment_crud 到 PortfolioService**

修改 `src/ginkgo/data/services/portfolio_service.py` 构造函数，添加 `deployment_crud=None` 参数并存储为 `self._deployment_crud`。

修改 `src/ginkgo/data/containers.py`，在 `portfolio_service` provider 的构造参数中注入 `deployment_crud`。

- [ ] **Step 6: Commit**

```bash
git add src/ginkgo/data/services/portfolio_service.py src/ginkgo/data/containers.py tests/unit/data/services/test_portfolio_freeze.py
git commit -m "feat: add is_portfolio_frozen() to PortfolioService with MDeployment lookup"
```

---

### Task 4: PortfolioService.update() 增加冻结检查

**Files:**
- Modify: `src/ginkgo/data/services/portfolio_service.py`（update 方法开头加检查）

- [ ] **Step 1: 写测试**

```python
def test_update_rejected_when_frozen():
    """冻结组合的 update 应被拒绝"""
    from ginkgo.data.services.portfolio_service import PortfolioService

    service = PortfolioService.__new__(PortfolioService)
    mock_crud = MagicMock()
    service._crud_repo = mock_crud
    service.is_portfolio_frozen = MagicMock(return_value=True)

    result = service.update(portfolio_id="frozen-uuid", name="new-name")

    assert not result.is_success()
    assert "已部署" in result.error or "不可修改" in result.error
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/data/services/test_portfolio_freeze.py::test_update_rejected_when_frozen -v`
Expected: FAIL

- [ ] **Step 3: 在 update() 方法开头添加冻结检查**

在 `update()` 方法的 input validation 之后、构建 `updates` 字典之前，添加：

```python
# 冻结检查
if self.is_portfolio_frozen(portfolio_id):
    return ServiceResult.error("组合已部署，不可修改")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/data/services/test_portfolio_freeze.py::test_update_rejected_when_frozen -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/data/services/portfolio_service.py tests/unit/data/services/test_portfolio_freeze.py
git commit -m "feat: add freeze check to PortfolioService.update()"
```

---

### Task 5: PortfolioSagaFactory 增加冻结检查

**Files:**
- Modify: `api/services/saga_transaction.py:223+`（PortfolioSagaFactory 的 update/delete 方法）

- [ ] **Step 1: 写测试**

在 `tests/api/test_deployment_api.py`（如不存在则新建）添加：

```python
import pytest
from unittest.mock import MagicMock, patch

def test_update_saga_rejects_frozen_portfolio():
    """update_portfolio_saga 应拒绝冻结组合"""
    from services.saga_transaction import PortfolioSagaFactory

    with patch("services.saga_transaction.container") as mock_container:
        mock_service = MagicMock()
        mock_service.is_portfolio_frozen.return_value = True
        mock_container.portfolio_service.return_value = mock_service

        with pytest.raises(Exception, match="已部署"):
            PortfolioSagaFactory.update_portfolio_saga(
                portfolio_uuid="frozen-uuid",
                name="new-name",
            )


def test_delete_saga_rejects_frozen_portfolio():
    """delete_portfolio_saga 应拒绝冻结组合"""
    from services.saga_transaction import PortfolioSagaFactory

    with patch("services.saga_transaction.container") as mock_container:
        mock_service = MagicMock()
        mock_service.is_portfolio_frozen.return_value = True
        mock_container.portfolio_service.return_value = mock_service

        with pytest.raises(Exception, match="已部署"):
            PortfolioSagaFactory.delete_portfolio_saga(
                portfolio_uuid="frozen-uuid",
            )
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/kaoru/Ginkgo/api && python -m pytest tests/test_deployment_api.py -v`
Expected: FAIL

- [ ] **Step 3: 在 update_portfolio_saga 和 delete_portfolio_saga 开头添加冻结检查**

在 `PortfolioSagaFactory.update_portfolio_saga()` 开头（获取服务之后）添加：

```python
portfolio_service = container.portfolio_service()
if portfolio_service.is_portfolio_frozen(portfolio_uuid):
    raise BusinessError(f"组合 {portfolio_uuid} 已部署，不可修改")
```

在 `PortfolioSagaFactory.delete_portfolio_saga()` 开头添加同样的检查。

需要确保 `BusinessError` 已在文件顶部导入：

```python
from core.exceptions import BusinessError
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /home/kaoru/Ginkgo/api && python -m pytest tests/test_deployment_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api/services/saga_transaction.py tests/api/test_deployment_api.py
git commit -m "feat: add freeze checks to PortfolioSagaFactory update/delete sagas"
```

---

### Task 6: API 层 config_locked 改为计算值

**Files:**
- Modify: `api/api/portfolio.py:86,246`

- [ ] **Step 1: 修改 list_portfolios 的 config_locked**

将 `api/api/portfolio.py` 第 86 行的 `"config_locked": False` 改为调用冻结判定：

在 `list_portfolios()` 中，获取 portfolio_service 后添加辅助函数：

```python
def _check_frozen(pid):
    try:
        return portfolio_service.is_portfolio_frozen(pid)
    except Exception:
        return False
```

然后在构建 portfolio dict 时：

```python
"config_locked": _check_frozen(p.uuid),
```

- [ ] **Step 2: 修改 get_portfolio 的 config_locked**

同理，在 `get_portfolio()` 函数中，获取 portfolio_service 后，将第 246 行的 `"config_locked": False` 改为：

```python
"config_locked": portfolio_service.is_portfolio_frozen(uuid),
```

- [ ] **Step 3: Commit**

```bash
git add api/api/portfolio.py
git commit -m "fix: config_locked computed from MDeployment instead of hardcoded False"
```

---

### Task 7: Deploy API 端点

**Files:**
- Create: `api/api/deployment.py`
- Modify: `api/main.py:115,130`

- [ ] **Step 1: 创建 deployment.py 路由文件**

```python
"""部署 API 路由"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel, Field
from core.response import ok
from core.exceptions import BusinessError
from core.logging import logger

router = APIRouter()


class DeployRequest(BaseModel):
    backtest_task_id: str = Field(..., description="已完成的回测任务 UUID")
    mode: str = Field(..., description="部署模式: paper / live")
    account_id: Optional[str] = Field(None, description="实盘账号 ID（live 模式必填）")
    name: Optional[str] = Field(None, description="新组合名称")


def _get_deployment_service():
    from ginkgo.data.containers import container
    return container.deployment_service()


@router.post("/")
async def deploy(req: DeployRequest):
    """一键部署：从回测结果部署到模拟盘/实盘"""
    from ginkgo.enums import PORTFOLIO_MODE_TYPES

    mode_map = {
        "paper": PORTFOLIO_MODE_TYPES.PAPER,
        "live": PORTFOLIO_MODE_TYPES.LIVE,
    }
    mode = mode_map.get(req.mode.lower())
    if mode is None:
        raise BusinessError(f"无效部署模式: {req.mode}，支持: paper / live")

    if mode == PORTFOLIO_MODE_TYPES.LIVE and not req.account_id:
        raise BusinessError("实盘部署需要提供 account_id")

    service = _get_deployment_service()
    result = service.deploy(
        backtest_task_id=req.backtest_task_id,
        mode=mode,
        account_id=req.account_id,
        name=req.name,
    )

    if not result.success:
        raise BusinessError(result.error)

    return ok(data=result.data, message="部署成功")


@router.get("/{portfolio_id}")
async def get_deployment_info(portfolio_id: str):
    """查询指定 Portfolio 的部署信息"""
    service = _get_deployment_service()
    result = service.get_deployment_info(portfolio_id)

    if not result.success:
        raise HTTPException(status_code=404, detail=result.error)

    return ok(data=result.data, message="查询成功")


@router.get("/")
async def list_deployments(task_id: Optional[str] = Query(None, description="按回测任务 ID 筛选")):
    """列出部署记录"""
    service = _get_deployment_service()
    result = service.list_deployments(source_task_id=task_id)

    if not result.success:
        raise BusinessError(result.error)

    return ok(data=result.data or [], message="查询成功")
```

- [ ] **Step 2: 注册路由到 main.py**

在 `api/main.py` 第 115 行的 import 中添加：

```python
from api import auth, dashboard, portfolio, backtest, components, data, arena, node_graph, accounts, trading, validation, deployment
```

在第 130 行后添加：

```python
app.include_router(deployment.router, prefix=f"{API_PREFIX}/deploy", tags=["deploy"])
```

- [ ] **Step 3: Commit**

```bash
git add api/api/deployment.py api/main.py
git commit -m "feat: add Deploy API endpoints (POST/GET /api/v1/deploy)"
```

---

### Task 8: MDeployment 状态生命周期管理

**Files:**
- Modify: `src/ginkgo/trading/services/deployment_service.py`（deploy 方法设置状态）
- Modify: `src/ginkgo/data/services/portfolio_service.py`（delete 方法更新 deployment 状态）

- [ ] **Step 1: deploy 方法中设置初始状态为 PENDING，成功后更新为 DEPLOYED**

修改 `deployment_service.py` 的 `deploy()` 方法：

将步骤 4（创建 Portfolio）之前设置 deployment 为 PENDING，在所有步骤成功完成后更新为 DEPLOYED。

在步骤 4 之前添加创建 deployment 记录（status=PENDING）：

```python
# 4a. 创建 PENDING deployment 记录
deployment = MDeployment(
    source_task_id=backtest_task_id,
    target_portfolio_id="",
    source_portfolio_id=source_portfolio_id,
    mode=mode.value,
    account_id=account_id,
    status=DEPLOYMENT_STATUS.PENDING,
)
self._deployment_crud.add(deployment)
deployment_id = deployment.uuid
```

在步骤 8（原创建 deployment）改为更新状态：

```python
# 8. 更新 MDeployment 状态为 DEPLOYED
self._deployment_crud.modify(
    filters={"uuid": deployment_id},
    updates={
        "target_portfolio_id": new_portfolio_id,
        "status": DEPLOYMENT_STATUS.DEPLOYED,
    },
)
```

在异常路径中，deploy 失败时更新为 FAILED：

```python
except Exception as e:
    # 更新 deployment 状态为 FAILED
    self._deployment_crud.modify(
        filters={"uuid": deployment_id},
        updates={"status": DEPLOYMENT_STATUS.FAILED},
    )
    return ServiceResult(success=False, error=str(e))
```

- [ ] **Step 2: PortfolioService.delete() 中更新相关 deployment 为 STOPPED**

在 `PortfolioService.delete()` 方法（或 `remove` 方法）中，删除 portfolio 后更新相关 deployment：

```python
def delete(self, portfolio_id: str) -> ServiceResult:
    """删除组合"""
    # ... 现有删除逻辑 ...

    # 如果是已部署的 target，将对应 deployment 状态更新为 STOPPED
    if hasattr(self, '_deployment_crud') and self._deployment_crud:
        deployments = self._deployment_crud.find(
            filters={"target_portfolio_id": portfolio_id}
        )
        for d in deployments:
            if getattr(d, 'status', -1) == 1:  # DEPLOYED
                self._deployment_crud.modify(
                    filters={"uuid": d.uuid},
                    updates={"status": 3},  # STOPPED
                )
```

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/trading/services/deployment_service.py src/ginkgo/data/services/portfolio_service.py
git commit -m "feat: MDeployment status lifecycle (PENDING→DEPLOYED→STOPPED/FAILED)"
```

---

### Task 9: PaperTradingWorker deploy 命令增加 mode 校验

**Files:**
- Modify: `src/ginkgo/workers/paper_trading_worker.py:743-780`

- [ ] **Step 1: 在 _handle_deploy 中添加 mode 校验**

在 `_handle_deploy()` 获取 `db_portfolio` 之后（约第 777 行），添加 mode 检查：

```python
db_portfolio = db_portfolios[0]

# Mode 校验：只接受 PAPER 或 LIVE
portfolio_mode = getattr(db_portfolio, 'mode', -1)
if portfolio_mode == 0:  # BACKTEST
    GLOG.ERROR(
        f"[PAPER-WORKER] Cannot deploy BACKTEST portfolio {portfolio_id}. "
        "Deploy first via DeploymentService.deploy()."
    )
    return False
```

- [ ] **Step 2: Commit**

```bash
git add src/ginkgo/workers/paper_trading_worker.py
git commit -m "feat: PaperTradingWorker rejects BACKTEST portfolios on deploy command"
```

---

### Task 10: DeploymentService 改为走 Saga

**Files:**
- Modify: `src/ginkgo/trading/services/deployment_service.py`
- Modify: `api/services/saga_transaction.py`（添加 deploy saga）

- [ ] **Step 1: 在 PortfolioSagaFactory 中添加 deploy_saga**

```python
@staticmethod
def deploy_saga(
    backtest_task_id: str,
    mode: int,
    account_id: str = None,
    name: str = None,
) -> SagaTransaction:
    """创建部署 Saga（深拷贝 + MDeployment 记录）"""
    from ginkgo.data.containers import container
    from ginkgo.enums import PORTFOLIO_MODE_TYPES

    deployment_service = container.deployment_service()

    saga = SagaTransaction(f"portfolio:deploy:{backtest_task_id}")
    context = {}

    def execute_deploy():
        result = deployment_service.deploy(
            backtest_task_id=backtest_task_id,
            mode=PORTFOLIO_MODE_TYPES(mode),
            account_id=account_id,
            name=name,
        )
        if not result.success:
            raise Exception(f"Deploy failed: {result.error}")
        context['result'] = result.data
        return result.data

    def compensate_deploy(data):
        portfolio_id = context.get('result', {}).get('portfolio_id')
        if portfolio_id:
            try:
                portfolio_service = container.portfolio_service()
                portfolio_service.delete(portfolio_id=portfolio_id)
            except Exception as e:
                logger.error(f"Deploy compensation failed: {e}")

    saga.add_step("deploy", execute_deploy, compensate_deploy)
    return saga
```

- [ ] **Step 2: 修改 Deploy API 端点调用 saga**

修改 `api/api/deployment.py` 中的 `deploy()` 端点：

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
        backtest_task_id=req.backtest_task_id,
        mode=mode,
        account_id=req.account_id,
        name=req.name,
    )

    success = await saga.execute()
    if not success:
        raise BusinessError(f"部署失败: {saga.error}. 事务已回滚。")

    return ok(data=saga.steps[0].result, message="部署成功")
```

- [ ] **Step 3: Commit**

```bash
git add api/services/saga_transaction.py api/api/deployment.py
git commit -m "feat: deploy operation uses Saga transaction for consistency"
```

---

## 验证清单

| # | 验证项 | 方法 |
|---|--------|------|
| 1 | `PortfolioCRUD.update_mode()` 被拒绝 | 调用后抛 DeprecationWarning |
| 2 | `PortfolioService.update(mode=PAPER)` | mode 被忽略，日志提示 |
| 3 | 部署回测组合到模拟盘 | source 组合冻结，update/delete 被拒绝 |
| 4 | 删除 target 模拟组合 | source 组合自动解冻 |
| 5 | `POST /api/v1/deploy` | 创建新组合 + MDeployment 记录 |
| 6 | `create_paper_account` | 正常创建空 PAPER 组合（不走 Saga） |
| 7 | PaperTradingWorker 收到 BACKTEST 组合 | 拒绝 deploy 命令 |
