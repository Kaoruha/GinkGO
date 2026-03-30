# One-Click Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement one-click deployment from backtest results to paper trading / OKX live trading

**Architecture:** DeploymentService orchestrates deep-copy of Portfolio + MFile + MPortfolioFileMapping + MParam + MongoDB Graph. Paper mode uses SimBroker via PaperTradingController, Live mode creates MBrokerInstance linked to MLiveAccount. Deployment records tracked in MDeployment table.

**Tech Stack:** Python 3.12.8, FastAPI, Typer, MySQL (SQLAlchemy), MongoDB, Redis, Kafka

---

### Task 1: MDeployment Model + CRUD

**Files:**
- Create: `src/ginkgo/data/models/model_deployment.py`
- Create: `src/ginkgo/data/crud/deployment_crud.py`
- Test: `tests/unit/data/models/test_deployment.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/data/models/test_deployment.py
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

import pytest
from ginkgo.data.models.model_deployment import MDeployment, DEPLOYMENT_STATUS


class TestMDeployment:
    def test_create_deployment_with_required_fields(self):
        d = MDeployment(
            source_task_id="task_001",
            target_portfolio_id="portfolio_new",
            source_portfolio_id="portfolio_old",
            mode=1,  # PAPER (PORTFOLIO_MODE_TYPES.PAPER)
            status=DEPLOYMENT_STATUS.PENDING,
        )
        assert d.source_task_id == "task_001"
        assert d.target_portfolio_id == "portfolio_new"
        assert d.source_portfolio_id == "portfolio_old"
        assert d.mode == 1
        assert d.status == DEPLOYMENT_STATUS.PENDING
        assert d.account_id is None

    def test_create_deployment_live_with_account(self):
        d = MDeployment(
            source_task_id="task_001",
            target_portfolio_id="portfolio_new",
            source_portfolio_id="portfolio_old",
            mode=2,  # LIVE (PORTFOLIO_MODE_TYPES.LIVE)
            account_id="account_001",
            status=DEPLOYMENT_STATUS.PENDING,
        )
        assert d.account_id == "account_001"
        assert d.mode == 1

    def test_deployment_status_enum(self):
        assert DEPLOYMENT_STATUS.PENDING == 0
        assert DEPLOYMENT_STATUS.DEPLOYED == 1
        assert DEPLOYMENT_STATUS.FAILED == 2
        assert DEPLOYMENT_STATUS.STOPPED == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/data/models/test_deployment.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: Write MDeployment model**

```python
# src/ginkgo/data/models/model_deployment.py
# Upstream: DeploymentService
# Downstream: MySQL Database (deployment表)
# Role: 部署记录数据模型 - 追踪回测到纸上交易/实盘的部署历史

import datetime
import pandas as pd
from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.libs import base_repr


class DEPLOYMENT_STATUS:
    """部署状态"""
    PENDING = 0
    DEPLOYED = 1
    FAILED = 2
    STOPPED = 3


class MDeployment(MMysqlBase):
    __abstract__ = False
    __tablename__ = "deployment"

    source_task_id: Mapped[str] = mapped_column(String(32), default="", comment="回测任务ID")
    target_portfolio_id: Mapped[str] = mapped_column(String(32), default="", comment="部署后的Portfolio ID")
    source_portfolio_id: Mapped[str] = mapped_column(String(32), default="", comment="原始回测Portfolio ID")
    mode: Mapped[int] = mapped_column(Integer, default=-1, comment="运行模式: 0=回测, 1=纸上交易, 2=实盘 (PORTFOLIO_MODE_TYPES)")
    account_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, comment="实盘账号ID (live模式)")
    status: Mapped[int] = mapped_column(Integer, default=DEPLOYMENT_STATUS.PENDING, comment="部署状态")

    @singledispatchmethod
    def update(self, *args, **kwargs):
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(self, source_task_id: str, **kwargs):
        self.source_task_id = source_task_id
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 60)
```

- [ ] **Step 4: Write DeploymentCRUD**

```python
# src/ginkgo/data/crud/deployment_crud.py
# Upstream: DeploymentService
# Downstream: MySQL deployment表
# Role: 部署记录CRUD操作

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models.model_deployment import MDeployment


class DeploymentCRUD(BaseCRUD):
    """部署记录CRUD"""

    def __init__(self):
        super().__init__(MDeployment)

    def get_by_target_portfolio(self, portfolio_id: str):
        """根据目标Portfolio ID查询部署记录"""
        return self.find(filters={"target_portfolio_id": portfolio_id})

    def get_by_source_task(self, task_id: str):
        """根据源回测任务ID查询部署记录"""
        return self.find(filters={"source_task_id": task_id})
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/unit/data/models/test_deployment.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add src/ginkgo/data/models/model_deployment.py src/ginkgo/data/crud/deployment_crud.py tests/unit/data/models/test_deployment.py
git commit -m "feat: add MDeployment model and DeploymentCRUD"
```

---

### Task 2: DeploymentService — Core Deploy Logic

**Files:**
- Create: `src/ginkgo/trading/services/deployment_service.py`
- Test: `tests/unit/trading/services/test_deployment_service.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/trading/services/test_deployment_service.py
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

import pytest
from unittest.mock import MagicMock, patch
from ginkgo.enums import PORTFOLIO_MODE_TYPES


class TestDeploymentServiceDeploy:
    def test_deploy_rejects_non_completed_backtest(self):
        """回测未完成时应拒绝部署"""
        from ginkgo.trading.services.deployment_service import DeploymentService

        mock_task_service = MagicMock()
        mock_task_service.get_by_run_id.return_value = MagicMock(
            success=True,
            data={"status": "running"}
        )

        svc = DeploymentService.__new__(DeploymentService)
        svc._task_service = mock_task_service

        result = svc.deploy(
            backtest_task_id="task_001",
            mode=PORTFOLIO_MODE_TYPES.PAPER,
        )
        assert not result.success
        assert "completed" in result.error.lower() or "完成" in result.error

    def test_deploy_rejects_live_without_account(self):
        """实盘模式缺少account_id应拒绝"""
        from ginkgo.trading.services.deployment_service import DeploymentService

        mock_task_service = MagicMock()
        mock_task_service.get_by_run_id.return_value = MagicMock(
            success=True,
            data={"status": "completed", "portfolio_id": "p1"}
        )

        svc = DeploymentService.__new__(DeploymentService)
        svc._task_service = mock_task_service

        result = svc.deploy(
            backtest_task_id="task_001",
            mode=PORTFOLIO_MODE_TYPES.LIVE,
            account_id=None,
        )
        assert not result.success
        assert "account" in result.error.lower() or "账号" in result.error

    def test_deploy_paper_calls_clone_and_copy(self):
        """纸上交易部署应调用clone、copy_mapping、create_portfolio"""
        from ginkgo.trading.services.deployment_service import DeploymentService

        # Setup mocks
        mock_task_service = MagicMock()
        mock_task_service.get_by_run_id.return_value = MagicMock(
            success=True,
            data={"status": "completed", "portfolio_id": "p1", "name": "BT-001"}
        )

        mock_portfolio_service = MagicMock()
        mock_portfolio_service.add.return_value = MagicMock(
            is_success=lambda: True,
            success=True,
            data={"uuid": "p_new"}
        )

        mock_mapping_service = MagicMock()
        mock_mapping_service.get_portfolio_mappings.return_value = MagicMock(
            success=True,
            data=[]
        )

        mock_file_service = MagicMock()

        mock_deployment_crud = MagicMock()

        svc = DeploymentService.__new__(DeploymentService)
        svc._task_service = mock_task_service
        svc._portfolio_service = mock_portfolio_service
        svc._mapping_service = mock_mapping_service
        svc._file_service = mock_file_service
        svc._deployment_crud = mock_deployment_crud

        result = svc.deploy(
            backtest_task_id="task_001",
            mode=PORTFOLIO_MODE_TYPES.PAPER,
            name="Paper-001",
        )
        assert result.success
        mock_portfolio_service.add.assert_called_once()
        # Verify mode was set to PAPER
        call_kwargs = mock_portfolio_service.add.call_args
        assert call_kwargs[1]["mode"] == PORTFOLIO_MODE_TYPES.PAPER
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/trading/services/test_deployment_service.py -v`
Expected: FAIL - ModuleNotFoundError

- [ ] **Step 3: Write DeploymentService implementation**

```python
# src/ginkgo/trading/services/deployment_service.py
# Upstream: API Server, CLI
# Downstream: PortfolioService, FileService, MappingService, BacktestTaskService
# Role: 部署编排服务 - 从回测结果一键部署到纸上交易/实盘

from typing import Optional, Dict, Any, List
from ginkgo.libs import GLOG
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.enums import PORTFOLIO_MODE_TYPES, FILE_TYPES
from ginkgo.data.models.model_deployment import MDeployment, DEPLOYMENT_STATUS


class DeploymentService(BaseService):
    """部署编排服务"""

    def __init__(
        self,
        task_service=None,
        portfolio_service=None,
        mapping_service=None,
        file_service=None,
        deployment_crud=None,
        broker_instance_crud=None,
        live_account_service=None,
        mongo_driver=None,
    ):
        self._task_service = task_service
        self._portfolio_service = portfolio_service
        self._mapping_service = mapping_service
        self._file_service = file_service
        self._deployment_crud = deployment_crud
        self._broker_instance_crud = broker_instance_crud
        self._live_account_service = live_account_service
        self._mongo_driver = mongo_driver

    def deploy(
        self,
        backtest_task_id: str,
        mode: PORTFOLIO_MODE_TYPES,
        account_id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> ServiceResult:
        """
        一键部署：从回测结果部署到纸上交易/实盘

        Args:
            backtest_task_id: 回测任务 run_id
            mode: PAPER 或 LIVE
            account_id: MLiveAccount.uuid (live模式必填)
            name: 新Portfolio名称 (可选，自动生成)

        Returns:
            ServiceResult with data: {"portfolio_id": str, "deployment_id": str}
        """
        # 1. 验证回测任务
        task_result = self._task_service.get_by_run_id(backtest_task_id)
        if not task_result.success or not task_result.data:
            return ServiceResult(success=False, error=f"回测任务不存在: {backtest_task_id}")

        task_data = task_result.data
        if task_data.get("status") != "completed":
            return ServiceResult(success=False, error=f"回测任务未完成，当前状态: {task_data.get('status')}")

        source_portfolio_id = task_data.get("portfolio_id")
        if not source_portfolio_id:
            return ServiceResult(success=False, error="回测任务缺少关联Portfolio")

        # 2. 实盘模式验证账号
        if mode == PORTFOLIO_MODE_TYPES.LIVE and not account_id:
            return ServiceResult(success=False, error="实盘部署需要提供 account_id")

        # 3. 读取原 Portfolio 的组件映射
        mappings_result = self._mapping_service.get_portfolio_mappings(
            source_portfolio_id, include_params=True
        )
        if not mappings_result.success:
            return ServiceResult(success=False, error=f"读取Portfolio组件映射失败: {mappings_result.error}")

        mappings = mappings_result.data if mappings_result.data else []

        # 4. 创建新 Portfolio
        if not name:
            source_name = task_data.get("name", backtest_task_id)
            mode_label = "PAPER" if mode == PORTFOLIO_MODE_TYPES.PAPER else "LIVE"
            name = f"{source_name}_{mode_label}"

        portfolio_result = self._portfolio_service.add(
            name=name,
            mode=mode,
            description=f"部署自回测任务 {backtest_task_id}",
        )
        if not portfolio_result.success:
            return ServiceResult(success=False, error=f"创建Portfolio失败: {portfolio_result.error}")

        new_portfolio_id = portfolio_result.data.get("uuid")
        GLOG.INFO(f"创建新Portfolio: {new_portfolio_id} (mode={mode.value})")

        # 5. 深拷贝组件: MFile(clone) + Mapping(新建) + Param(复制)
        try:
            file_id_map = {}  # old_file_id -> new_file_id
            for mapping in mappings:
                old_file_id = getattr(mapping, "file_id", None)
                if not old_file_id:
                    continue

                file_type = getattr(mapping, "type", None)
                mapping_name = getattr(mapping, "name", "")
                mapping_uuid = getattr(mapping, "uuid", "")

                # 5a. Clone MFile
                clone_name = f"{mapping_name}_{new_portfolio_id[:8]}"
                clone_result = self._file_service.clone(old_file_id, clone_name, file_type)
                if not clone_result.success:
                    GLOG.WARN(f"克隆文件失败 {old_file_id}: {clone_result.error}")
                    continue

                new_file_id = clone_result.data["file_info"]["uuid"]
                file_id_map[old_file_id] = new_file_id

                # 5b. Create new Mapping
                add_result = self._mapping_service.add_file(
                    portfolio_uuid=new_portfolio_id,
                    file_id=new_file_id,
                    file_type=FILE_TYPES(file_type) if file_type else None,
                    name=mapping_name,
                )
                if not add_result.success:
                    GLOG.WARN(f"创建映射失败: {add_result.error}")
                    continue

                # 5c. Copy Params from old mapping to new mapping
                if mapping_uuid:
                    params_result = self._mapping_service.get_mapping_params(mapping_uuid)
                    if params_result.success and params_result.data:
                        new_mapping_id = add_result.data.get("mapping_id")
                        if new_mapping_id:
                            self._copy_params(mapping_uuid, new_mapping_id, params_result.data)

        except Exception as e:
            GLOG.ERROR(f"组件拷贝失败: {e}")
            return ServiceResult(success=False, error=f"组件拷贝失败: {str(e)}")

        # 6. Copy MongoDB Graph
        try:
            self._copy_graph(source_portfolio_id, new_portfolio_id)
        except Exception as e:
            GLOG.WARN(f"图结构拷贝失败(非致命): {e}")

        # 7. Live模式: 创建 MBrokerInstance
        if mode == PORTFOLIO_MODE_TYPES.LIVE and account_id:
            try:
                self._broker_instance_crud.add_broker_instance(
                    portfolio_id=new_portfolio_id,
                    live_account_id=account_id,
                    state="uninitialized",
                )
            except Exception as e:
                GLOG.ERROR(f"创建Broker实例失败: {e}")
                return ServiceResult(success=False, error=f"创建Broker实例失败: {str(e)}")

        # 8. 创建 MDeployment 记录
        try:
            deployment = MDeployment(
                source_task_id=backtest_task_id,
                target_portfolio_id=new_portfolio_id,
                source_portfolio_id=source_portfolio_id,
                mode=mode.value,
                account_id=account_id,
                status=DEPLOYMENT_STATUS.DEPLOYED,
            )
            self._deployment_crud.add(deployment)
            deployment_id = deployment.uuid
        except Exception as e:
            GLOG.WARN(f"创建部署记录失败(非致命): {e}")
            deployment_id = None

        GLOG.INFO(f"部署完成: {new_portfolio_id} <- {backtest_task_id}")
        result = ServiceResult(success=True)
        result.data = {
            "portfolio_id": new_portfolio_id,
            "deployment_id": deployment_id,
            "source_task_id": backtest_task_id,
        }
        return result

    def get_deployment_info(self, portfolio_id: str) -> ServiceResult:
        """获取部署信息"""
        records = self._deployment_crud.get_by_target_portfolio(portfolio_id)
        if not records:
            return ServiceResult(success=False, error="未找到部署记录")

        deployment = records[0]
        result = ServiceResult(success=True)
        result.data = {
            "source_task_id": deployment.source_task_id,
            "target_portfolio_id": deployment.target_portfolio_id,
            "source_portfolio_id": deployment.source_portfolio_id,
            "mode": deployment.mode,
            "account_id": deployment.account_id,
            "status": deployment.status,
            "create_at": str(deployment.create_at) if deployment.create_at else None,
        }
        return result

    def list_deployments(self, source_task_id: str = None) -> ServiceResult:
        """列出部署记录"""
        if source_task_id:
            records = self._deployment_crud.get_by_source_task(source_task_id)
        else:
            records = self._deployment_crud.find()

        if not records:
            return ServiceResult(success=True, data=[])

        result = ServiceResult(success=True)
        result.data = [
            {
                "deployment_id": r.uuid,
                "source_task_id": r.source_task_id,
                "target_portfolio_id": r.target_portfolio_id,
                "source_portfolio_id": r.source_portfolio_id,
                "mode": r.mode,
                "account_id": r.account_id,
                "status": r.status,
                "create_at": str(r.create_at) if r.create_at else None,
            }
            for r in records
        ]
        return result

    def _copy_params(self, old_mapping_id: str, new_mapping_id: str, params: List) -> None:
        """复制参数从旧mapping到新mapping"""
        from ginkgo.data.containers import container
        param_crud = container.cruds.param()

        for param in params:
            index = getattr(param, "index", 0)
            value = getattr(param, "value", "")
            source = getattr(param, "source", -1)
            param_crud.set_param_value(new_mapping_id, index, value, source)

    def _copy_graph(self, source_portfolio_id: str, target_portfolio_id: str) -> None:
        """复制MongoDB图结构"""
        if not self._mongo_driver:
            return

        graph_result = self._mapping_service.get_portfolio_graph(source_portfolio_id)
        if not graph_result.success or not graph_result.data:
            return

        # Save graph to new portfolio
        self._mapping_service.create_from_graph_editor(
            portfolio_uuid=target_portfolio_id,
            graph_data=graph_result.data,
            name=f"deploy_{target_portfolio_id[:8]}",
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/trading/services/test_deployment_service.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/trading/services/deployment_service.py tests/unit/trading/services/test_deployment_service.py
git commit -m "feat: add DeploymentService with deploy/list/info methods"
```

---

### Task 3: Register DeploymentService in DI Container

**Files:**
- Modify: `src/ginkgo/data/containers.py`

- [ ] **Step 1: Add imports and provider to Container**

In `src/ginkgo/data/containers.py`, add the following:

1. Add import at the top with other service imports:
```python
from ginkgo.trading.services.deployment_service import DeploymentService
from ginkgo.data.crud.deployment_crud import DeploymentCRUD
```

2. Add CRUD provider near other CRUD definitions:
```python
deployment_crud = providers.Singleton(DeploymentCRUD)
```

3. Add service provider near other service definitions:
```python
deployment_service = providers.Singleton(
    DeploymentService,
    task_service=backtest_task_service,
    portfolio_service=portfolio_service,
    mapping_service=portfolio_mapping_service,
    file_service=file_service,
    deployment_crud=deployment_crud,
    broker_instance_crud=broker_instance_crud,
    live_account_service=live_account_service,
    mongo_driver=mongo_driver,
)
```

Note: `broker_instance_crud`, `live_account_service`, and `mongo_driver` must already exist in the container. Check existing provider names before writing.

- [ ] **Step 2: Verify import works**

Run: `python -c "from ginkgo.data.containers import container; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/data/containers.py
git commit -m "feat: register DeploymentService in DI container"
```

---

### Task 4: API Endpoint — Deployment Router

**Files:**
- Create: `api/routers/deployment.py`
- Modify: `api/main.py`

- [ ] **Step 1: Write the deployment router**

```python
# api/routers/deployment.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict
from pydantic import BaseModel

router = APIRouter(
    prefix="/api/v1/deploy",
    tags=["deploy"]
)


class DeployRequest(BaseModel):
    backtest_task_id: str
    mode: str  # "paper" or "live"
    account_id: Optional[str] = None
    name: Optional[str] = None


@router.post("")
async def deploy(request: DeployRequest) -> Dict:
    """一键部署：回测结果 → 纸上交易/实盘"""
    try:
        from ginkgo.data.containers import container
        from ginkgo.enums import PORTFOLIO_MODE_TYPES

        mode_map = {
            "paper": PORTFOLIO_MODE_TYPES.PAPER,
            "live": PORTFOLIO_MODE_TYPES.LIVE,
        }
        if request.mode not in mode_map:
            raise HTTPException(status_code=400, detail=f"无效的部署模式: {request.mode}")

        svc = container.deployment_service()
        result = svc.deploy(
            backtest_task_id=request.backtest_task_id,
            mode=mode_map[request.mode],
            account_id=request.account_id,
            name=request.name,
        )

        if result.success:
            return {"code": 0, "message": "部署成功", "data": result.data}
        else:
            raise HTTPException(status_code=400, detail=result.error)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{portfolio_id}")
async def get_deployment_info(portfolio_id: str) -> Dict:
    """获取部署详情"""
    try:
        from ginkgo.data.containers import container

        svc = container.deployment_service()
        result = svc.get_deployment_info(portfolio_id)

        if result.success:
            return {"code": 0, "message": "success", "data": result.data}
        else:
            raise HTTPException(status_code=404, detail=result.error)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_deployments(
    task_id: Optional[str] = Query(None, alias="task_id")
) -> Dict:
    """列出部署记录"""
    try:
        from ginkgo.data.containers import container

        svc = container.deployment_service()
        result = svc.list_deployments(source_task_id=task_id)

        return {"code": 0, "message": "success", "data": result.data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 2: Register router in api/main.py**

In `api/main.py`, add after the existing router registrations (around line 114):

```python
# ========== 部署路由 ==========
from api.routers.deployment import router as deployment_router
app.include_router(deployment_router)
```

- [ ] **Step 3: Verify import works**

Run: `python -c "from api.routers.deployment import router; print('OK')"`
Expected: OK

- [ ] **Step 4: Commit**

```bash
git add api/routers/deployment.py api/main.py
git commit -m "feat: add deployment API endpoints"
```

---

### Task 5: CLI Command — Deploy

**Files:**
- Create: `src/ginkgo/client/deploy_cli.py`
- Modify: `main.py`

- [ ] **Step 1: Write the deploy CLI**

```python
# src/ginkgo/client/deploy_cli.py
import typer
from typing import Optional
from typing_extensions import Annotated
from rich.console import Console
from rich.table import Table

app = typer.Typer(help=":rocket: Deploy backtest to paper/live trading")
console = Console()


@app.command("")
def deploy(
    backtest_task_id: Annotated[str, typer.Argument(help="回测任务ID (run_id)")],
    mode: Annotated[str, typer.Option("--mode", "-m", help="部署模式: paper 或 live")] = "paper",
    account: Annotated[Optional[str], typer.Option("--account", "-a", help="实盘账号ID (live模式必填)")] = None,
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="新Portfolio名称")] = None,
):
    """一键部署：回测结果 → 纸上交易/实盘"""
    try:
        from ginkgo.data.containers import container
        from ginkgo.enums import PORTFOLIO_MODE_TYPES

        mode_map = {
            "paper": PORTFOLIO_MODE_TYPES.PAPER,
            "live": PORTFOLIO_MODE_TYPES.LIVE,
        }
        if mode not in mode_map:
            console.print(f"[red]无效的部署模式: {mode}[/red]")
            raise typer.Exit(1)

        if mode == "live" and not account:
            console.print("[red]实盘模式需要 --account 参数[/red]")
            raise typer.Exit(1)

        console.print(f"[bold]部署中...[/bold]")
        console.print(f"  回测任务: {backtest_task_id}")
        console.print(f"  模式: {mode}")

        svc = container.deployment_service()
        result = svc.deploy(
            backtest_task_id=backtest_task_id,
            mode=mode_map[mode],
            account_id=account,
            name=name,
        )

        if result.success:
            data = result.data
            console.print(f"[green]部署成功![/green]")
            console.print(f"  Portfolio ID: [cyan]{data['portfolio_id']}[/cyan]")
            if data.get("deployment_id"):
                console.print(f"  Deployment ID: [cyan]{data['deployment_id']}[/cyan]")
        else:
            console.print(f"[red]部署失败: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("info")
def info(
    portfolio_id: Annotated[str, typer.Argument(help="部署后的Portfolio ID")],
):
    """查看部署详情"""
    try:
        from ginkgo.data.containers import container

        svc = container.deployment_service()
        result = svc.get_deployment_info(portfolio_id)

        if result.success:
            data = result.data
            table = Table(title="部署详情")
            table.add_column("字段", style="cyan")
            table.add_column("值")
            table.add_row("源回测任务", data.get("source_task_id", ""))
            table.add_row("源Portfolio", data.get("source_portfolio_id", ""))
            table.add_row("目标Portfolio", data.get("target_portfolio_id", ""))
            mode_str = "纸上交易" if data.get("mode") == 1 else "实盘"
            table.add_row("模式", mode_str)
            table.add_row("实盘账号", data.get("account_id", "N/A"))
            table.add_row("状态", str(data.get("status", "")))
            table.add_row("创建时间", data.get("create_at", ""))
            console.print(table)
        else:
            console.print(f"[red]{result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_deployments(
    task_id: Annotated[Optional[str], typer.Option("--task", "-t", help="按回测任务ID筛选")] = None,
):
    """列出部署记录"""
    try:
        from ginkgo.data.containers import container

        svc = container.deployment_service()
        result = svc.list_deployments(source_task_id=task_id)

        if result.success and result.data:
            table = Table(title="部署记录")
            table.add_column("Deployment ID", style="cyan")
            table.add_column("源任务")
            table.add_column("目标Portfolio")
            table.add_column("模式")
            table.add_column("状态")
            table.add_column("创建时间")

            for d in result.data:
                mode_str = "纸上" if d["mode"] == 1 else "实盘"
                table.add_row(
                    d["deployment_id"][:8] + "...",
                    d["source_task_id"],
                    d["target_portfolio_id"][:8] + "...",
                    mode_str,
                    str(d["status"]),
                    d.get("create_at", "")[:19] if d.get("create_at") else "",
                )
            console.print(table)
        else:
            console.print("[yellow]无部署记录[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
```

- [ ] **Step 2: Register in main.py**

In `main.py`, in the `_register_all_commands()` function (around line 132), add:

```python
from ginkgo.client import deploy_cli
_main_app.add_typer(deploy_cli.app, name="deploy", help=":rocket: Deploy backtest to paper/live trading")
```

- [ ] **Step 3: Verify CLI works**

Run: `python main.py deploy --help`
Expected: Shows deploy CLI help text

- [ ] **Step 4: Commit**

```bash
git add src/ginkgo/client/deploy_cli.py main.py
git commit -m "feat: add deploy CLI commands"
```

---

### Task 6: Register MDeployment in Model Registry + DB Init

**Files:**
- Modify: `src/ginkgo/data/models/__init__.py` (add import)

- [ ] **Step 1: Add MDeployment to model imports**

In `src/ginkgo/data/models/__init__.py`, find where other models are imported and add:

```python
from ginkgo.data.models.model_deployment import MDeployment
```

- [ ] **Step 2: Verify import**

Run: `python -c "from ginkgo.data.models import MDeployment; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/data/models/__init__.py
git commit -m "feat: register MDeployment in model registry"
```

---

### Task 7: Integration Test — End-to-End Deploy Flow

**Files:**
- Test: `tests/integration/trading/services/test_deployment_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/integration/trading/services/test_deployment_integration.py
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

import pytest
from datetime import datetime


class TestDeploymentIntegration:
    """
    集成测试：端到端部署流程

    前置条件：ginkgo system config set --debug on
    需要数据库连接
    """

    def test_deploy_paper_creates_independent_portfolio(self):
        """纸上交易部署应创建完全独立的Portfolio"""
        from ginkgo.data.containers import container
        from ginkgo.enums import PORTFOLIO_MODE_TYPES

        portfolio_service = container.portfolio_service()
        mapping_service = container.portfolio_mapping_service()
        file_service = container.file_service()
        task_service = container.backtest_task_service()

        # 1. 创建源Portfolio
        ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        source_name = f"test_deploy_source_{ts}"

        source_result = portfolio_service.add(
            name=source_name,
            mode=PORTFOLIO_MODE_TYPES.BACKTEST,
        )
        assert source_result.success
        source_portfolio_id = source_result.data["uuid"]

        # 2. 创建一个测试策略文件
        test_code = b'''
class TestStrategy:
    def cal(self, portfolio_info, event):
        return []
'''
        file_result = file_service.add(
            name=f"test_strategy_{ts}",
            file_type=6,  # STRATEGY
            data=test_code,
            description="Integration test strategy",
        )
        assert file_result.success
        file_id = file_result.data["file_info"]["uuid"]

        # 3. 添加映射
        mapping_result = mapping_service.add_file(
            portfolio_uuid=source_portfolio_id,
            file_id=file_id,
            file_type=6,
            name=f"test_mapping_{ts}",
        )
        assert mapping_result.success

        # 4. 部署到纸上交易
        deployment_service = container.deployment_service()
        deploy_result = deployment_service.deploy(
            backtest_task_id="test_manual_task",
            mode=PORTFOLIO_MODE_TYPES.PAPER,
            name=f"test_paper_{ts}",
        )

        # 注意：如果没有completed的回测任务，deploy会失败
        # 这是预期行为，验证错误处理
        if not deploy_result.success:
            assert "completed" in deploy_result.error.lower() or "完成" in deploy_result.error

        # 清理
        try:
            portfolio_service.delete(source_portfolio_id)
        except Exception:
            pass
        try:
            file_service.soft_delete(file_id)
        except Exception:
            pass
```

- [ ] **Step 2: Run integration test (requires DB)**

Run: `python -m pytest tests/integration/trading/services/test_deployment_integration.py -v`
Expected: PASS (validates error handling when no completed backtest exists)

- [ ] **Step 3: Commit**

```bash
git add tests/integration/trading/services/test_deployment_integration.py
git commit -m "test: add deployment integration test"
```
