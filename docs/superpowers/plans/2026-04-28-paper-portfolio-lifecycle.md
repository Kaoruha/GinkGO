# Paper Portfolio Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 PAPER/LIVE portfolio deploy→run→stop→delete 完整生命周期链路断裂。

**Architecture:** ControlCommand DTO 统一 Kafka 消息格式，Service 层封装完整业务（含 Kafka 通知），Worker 侧负责 RUNNING/STOPPED 状态持久化。

**Tech Stack:** Python (dataclasses, Kafka), Vue 3 + Ant Design Vue

---

## File Structure

| File | Responsibility | Action |
|------|---------------|--------|
| `src/ginkgo/messages/control_command.py` | Kafka 控制命令 DTO，统一消息格式 | Rewrite |
| `src/ginkgo/trading/services/deployment_service.py` | deploy 后发 Kafka deploy 命令 | Modify |
| `src/ginkgo/data/services/portfolio_service.py` | 新增 stop()，delete() 加状态检查 | Modify |
| `src/ginkgo/workers/paper_trading_worker.py` | deploy/unload 后更新 DB state | Modify |
| `src/ginkgo/client/portfolio_cli.py` | 删除 Kafka 辅助函数，改用 Service | Modify |
| `api/api/portfolio.py` | 新增 start/stop 端点 | Modify |
| `api/api/trading.py` | start/stop 标记 deprecated，转发 Service | Modify |
| `web-ui/src/views/portfolio/PortfolioList.vue` | 删除按钮加状态检查 | Modify |
| `web-ui/src/views/portfolio/PortfolioDetail.vue` | PAPER/LIVE 组合显示停止按钮 | Modify |
| `tests/unit/messages/test_control_command.py` | ControlCommand 单元测试 | Create |
| `tests/unit/services/test_portfolio_service_lifecycle.py` | stop/delete 保护测试 | Create |

---

### Task 1: ControlCommand DTO 重写

**Files:**
- Rewrite: `src/ginkgo/messages/control_command.py`
- Create: `tests/unit/messages/test_control_command.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/messages/test_control_command.py
import pytest
from datetime import datetime


class TestControlCommand:
    def test_deploy_factory(self):
        from ginkgo.messages.control_command import ControlCommand
        cmd = ControlCommand.deploy("portfolio-123")
        d = cmd.to_dict()
        assert d["command"] == "deploy"
        assert d["params"]["portfolio_id"] == "portfolio-123"
        assert d["timestamp"] is not None

    def test_unload_factory(self):
        from ginkgo.messages.control_command import ControlCommand
        cmd = ControlCommand.unload("portfolio-456")
        d = cmd.to_dict()
        assert d["command"] == "unload"
        assert d["params"]["portfolio_id"] == "portfolio-456"

    def test_daily_cycle_factory(self):
        from ginkgo.messages.control_command import ControlCommand
        cmd = ControlCommand.daily_cycle()
        d = cmd.to_dict()
        assert d["command"] == "paper_trading"
        assert d["params"] == {}

    def test_from_dict_roundtrip(self):
        from ginkgo.messages.control_command import ControlCommand
        original = ControlCommand.deploy("abc-123")
        data = original.to_dict()
        restored = ControlCommand.from_dict(data)
        assert restored.command == "deploy"
        assert restored.params["portfolio_id"] == "abc-123"

    def test_from_dict_no_params(self):
        from ginkgo.messages.control_command import ControlCommand
        data = {"command": "paper_trading", "timestamp": datetime.now().isoformat()}
        cmd = ControlCommand.from_dict(data)
        assert cmd.command == "paper_trading"
        assert cmd.params == {}

    def test_to_dict_has_no_extra_keys(self):
        from ginkgo.messages.control_command import ControlCommand
        cmd = ControlCommand.deploy("x")
        d = cmd.to_dict()
        assert set(d.keys()) == {"command", "params", "timestamp"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/messages/test_control_command.py -v`
Expected: FAIL — `ControlCommand` has no `deploy` classmethod

- [ ] **Step 3: Rewrite ControlCommand**

```python
# src/ginkgo/messages/control_command.py
# Upstream: DeploymentService, PortfolioService, TaskTimer (构造控制命令)
# Downstream: PaperTradingWorker, ExecutionNode (消费控制命令)
# Role: 统一的 Kafka 控制命令 DTO，提供工厂方法和序列化

"""
Kafka 控制命令消息 DTO

所有 Kafka CONTROL_COMMANDS topic 的消息统一使用此类构造和解析。
发送方使用工厂方法（deploy/unload/daily_cycle），消费方使用 from_dict() 解析。
"""

import json
import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class ControlCommand:
    """Kafka 控制命令消息

    命令类型：
    - deploy: 加载 Portfolio 到引擎
    - unload: 从引擎卸载 Portfolio
    - paper_trading: 触发日循环
    """

    command: str
    params: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "params": self.params,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ControlCommand":
        return cls(
            command=data.get("command", ""),
            params=data.get("params", {}),
            timestamp=data.get("timestamp"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "ControlCommand":
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def deploy(cls, portfolio_id: str) -> "ControlCommand":
        return cls(command="deploy", params={"portfolio_id": portfolio_id})

    @classmethod
    def unload(cls, portfolio_id: str) -> "ControlCommand":
        return cls(command="unload", params={"portfolio_id": portfolio_id})

    @classmethod
    def daily_cycle(cls) -> "ControlCommand":
        return cls(command="paper_trading", params={})

    def __repr__(self) -> str:
        pid = self.params.get("portfolio_id", "")
        if pid:
            pid = pid[:8]
        return f"ControlCommand(command={self.command}, portfolio_id={pid}...)"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/messages/test_control_command.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/messages/control_command.py tests/unit/messages/test_control_command.py
git commit -m "refactor: rewrite ControlCommand DTO with factory methods and unified format"
```

---

### Task 2: DeploymentService deploy 后发 Kafka 通知

**Files:**
- Modify: `src/ginkgo/trading/services/deployment_service.py:192-210`

- [ ] **Step 1: 在 `_deploy_core()` 第 8 步之后添加第 9 步**

在 `_deploy_core()` 方法中，找到第 8 步更新 MDeployment 状态的代码块之后（约 line 203 `GLOG.INFO(...)` 之后），添加 Kafka deploy 通知：

```python
        # 9. 发送 Kafka deploy 命令通知 PaperTradingWorker
        try:
            from ginkgo.messages.control_command import ControlCommand
            from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
            from ginkgo.interfaces.kafka_topics import KafkaTopics

            cmd = ControlCommand.deploy(new_portfolio_id)
            producer = GinkgoProducer()
            success = producer.send(KafkaTopics.CONTROL_COMMANDS, cmd.to_dict())
            if success:
                GLOG.INFO(f"[DEPLOY] Kafka deploy command sent for {new_portfolio_id[:8]}")
            else:
                GLOG.WARN(f"[DEPLOY] Failed to send Kafka deploy command for {new_portfolio_id[:8]}")
        except Exception as e:
            GLOG.WARN(f"[DEPLOY] Kafka notification failed (non-fatal): {e}")
```

注意：Kafka 通知失败不影响 deploy 成功（已创建的 DB 记录有效），所以用 WARN 而非 raise。

- [ ] **Step 2: Commit**

```bash
git add src/ginkgo/trading/services/deployment_service.py
git commit -m "feat: send Kafka deploy command after DeploymentService.deploy()"
```

---

### Task 3: PortfolioService stop() + delete() 状态保护

**Files:**
- Modify: `src/ginkgo/data/services/portfolio_service.py`
- Create: `tests/unit/services/test_portfolio_service_lifecycle.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/services/test_portfolio_service_lifecycle.py
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_service():
    """创建带 mock 依赖的 PortfolioService"""
    from ginkgo.data.services.portfolio_service import PortfolioService
    service = PortfolioService.__new__(PortfolioService)
    service._crud_repo = MagicMock()
    service._portfolio_file_mapping_crud = MagicMock()
    service._deployment_crud = MagicMock()
    service._param_crud = MagicMock()
    return service


class TestPortfolioServiceStop:
    def test_stop_requires_paper_or_live_mode(self, mock_service):
        """BACKTEST 模式不允许 stop"""
        from ginkgo.data.services.base_service import ServiceResult
        mock_portfolio = MagicMock()
        mock_portfolio.mode = 0  # BACKTEST
        mock_service._crud_repo.find.return_value = [mock_portfolio]

        result = mock_service.stop("test-uuid")
        assert result.is_success() is False
        assert "BACKTEST" in result.error or "回测" in result.error

    def test_stop_rejects_already_stopped(self, mock_service):
        """STOPPED 状态不允许再次 stop"""
        from ginkgo.data.services.base_service import ServiceResult
        mock_portfolio = MagicMock()
        mock_portfolio.mode = 1  # PAPER
        mock_portfolio.state = 4  # STOPPED
        mock_service._crud_repo.find.return_value = [mock_portfolio]

        result = mock_service.stop("test-uuid")
        assert result.is_success() is False


class TestPortfolioServiceDeleteProtection:
    def test_delete_rejects_running_paper(self, mock_service):
        """RUNNING 的 PAPER portfolio 不允许删除"""
        from ginkgo.data.services.base_service import ServiceResult
        mock_portfolio = MagicMock()
        mock_portfolio.mode = 1  # PAPER
        mock_portfolio.state = 1  # RUNNING
        mock_service._crud_repo.find.return_value = [mock_portfolio]
        # exists check
        exists_result = ServiceResult.success({"exists": True})
        mock_service.exists = MagicMock(return_value=exists_result)

        result = mock_service.delete(portfolio_id="test-uuid")
        assert result.is_success() is False
        assert "运行" in result.error or "停止" in result.error

    def test_delete_rejects_stopping_paper(self, mock_service):
        """STOPPING 的 PAPER portfolio 不允许删除"""
        from ginkgo.data.services.base_service import ServiceResult
        mock_portfolio = MagicMock()
        mock_portfolio.mode = 1  # PAPER
        mock_portfolio.state = 3  # STOPPING
        mock_service._crud_repo.find.return_value = [mock_portfolio]
        exists_result = ServiceResult.success({"exists": True})
        mock_service.exists = MagicMock(return_value=exists_result)

        result = mock_service.delete(portfolio_id="test-uuid")
        assert result.is_success() is False

    def test_delete_allows_stopped_paper(self, mock_service):
        """STOPPED 的 PAPER portfolio 允许删除"""
        from ginkgo.data.services.base_service import ServiceResult
        mock_portfolio = MagicMock()
        mock_portfolio.mode = 1  # PAPER
        mock_portfolio.state = 4  # STOPPED
        mock_service._crud_repo.find.return_value = [mock_portfolio]
        mock_service._portfolio_file_mapping_crud.find.return_value = []
        exists_result = ServiceResult.success({"exists": True})
        mock_service.exists = MagicMock(return_value=exists_result)

        result = mock_service.delete(portfolio_id="test-uuid")
        assert result.is_success() is True

    def test_delete_allows_backtest_running(self, mock_service):
        """BACKTEST 模式不受状态限制"""
        from ginkgo.data.services.base_service import ServiceResult
        mock_portfolio = MagicMock()
        mock_portfolio.mode = 0  # BACKTEST
        mock_portfolio.state = 1  # RUNNING
        mock_service._crud_repo.find.return_value = [mock_portfolio]
        mock_service._portfolio_file_mapping_crud.find.return_value = []
        exists_result = ServiceResult.success({"exists": True})
        mock_service.exists = MagicMock(return_value=exists_result)

        result = mock_service.delete(portfolio_id="test-uuid")
        assert result.is_success() is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/services/test_portfolio_service_lifecycle.py -v`
Expected: FAIL — `PortfolioService` has no `stop` method

- [ ] **Step 3: Add stop() method to PortfolioService**

在 `portfolio_service.py` 的 `delete()` 方法之前添加：

```python
    def stop(self, portfolio_id: str) -> ServiceResult:
        """
        停止 PAPER/LIVE portfolio（发送 Kafka unload 命令）

        Args:
            portfolio_id: 投资组合UUID

        Returns:
            ServiceResult: 操作结果
        """
        try:
            if not portfolio_id or not portfolio_id.strip():
                return ServiceResult.error("投资组合ID不能为空")

            # 查询 portfolio 信息
            portfolios = self._crud_repo.find(filters={"uuid": portfolio_id})
            if not portfolios:
                return ServiceResult.error(f"投资组合不存在: {portfolio_id}")

            portfolio = portfolios[0]
            mode = getattr(portfolio, 'mode', -1)
            state = getattr(portfolio, 'state', 0)

            # 校验 mode
            if mode == PORTFOLIO_MODE_TYPES.BACKTEST.value:
                return ServiceResult.error("回测模式组合不支持 stop，请直接删除")

            # 校验 state
            if state == PORTFOLIO_RUNSTATE_TYPES.STOPPED.value:
                return ServiceResult.error("组合已停止")
            if state == PORTFOLIO_RUNSTATE_TYPES.STOPPING.value:
                return ServiceResult.error("组合正在停止中，请等待")

            # 更新 state 为 STOPPING
            self._crud_repo.modify(
                filters={"uuid": portfolio_id},
                updates={"state": PORTFOLIO_RUNSTATE_TYPES.STOPPING.value},
            )
            GLOG.INFO(f"Portfolio {portfolio_id[:8]} state -> STOPPING")

            # 发送 Kafka unload 命令
            from ginkgo.messages.control_command import ControlCommand
            from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
            from ginkgo.interfaces.kafka_topics import KafkaTopics

            cmd = ControlCommand.unload(portfolio_id)
            producer = GinkgoProducer()
            success = producer.send(KafkaTopics.CONTROL_COMMANDS, cmd.to_dict())

            if success:
                GLOG.INFO(f"[STOP] Kafka unload command sent for {portfolio_id[:8]}")
            else:
                GLOG.WARN(f"[STOP] Failed to send Kafka unload command for {portfolio_id[:8]}")

            return ServiceResult.success(
                {"portfolio_id": portfolio_id},
                "停止命令已发送"
            )

        except Exception as e:
            GLOG.ERROR(f"停止投资组合失败: {e}")
            return ServiceResult.error(f"停止投资组合失败: {str(e)}")
```

- [ ] **Step 4: Add state check to delete() method**

在 `portfolio_service.py` 的 `delete()` 方法中，在 `exists_result` 检查之后（约 line 412），添加状态保护：

```python
            # 检查 PAPER/LIVE 运行状态保护
            portfolios = self._crud_repo.find(filters={"uuid": portfolio_id})
            if portfolios:
                p = portfolios[0]
                mode = getattr(p, 'mode', -1)
                state = getattr(p, 'state', 0)
                if mode in (PORTFOLIO_MODE_TYPES.PAPER.value, PORTFOLIO_MODE_TYPES.LIVE.value):
                    if state in (PORTFOLIO_RUNSTATE_TYPES.RUNNING.value, PORTFOLIO_RUNSTATE_TYPES.STOPPING.value):
                        state_name = {v.value: k for k, v in PORTFOLIO_RUNSTATE_TYPES.__members__.items()}.get(state, str(state))
                        return ServiceResult.error(
                            f"组合正在{state_name}状态，请先停止后再删除"
                        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/services/test_portfolio_service_lifecycle.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add src/ginkgo/data/services/portfolio_service.py tests/unit/services/test_portfolio_service_lifecycle.py
git commit -m "feat: add PortfolioService.stop() and delete() running-state protection"
```

---

### Task 4: Worker 状态持久化（deploy→RUNNING, unload→STOPPED）

**Files:**
- Modify: `src/ginkgo/workers/paper_trading_worker.py`

- [ ] **Step 1: 在 `_handle_deploy()` 加载成功后更新 state=RUNNING**

在 `_handle_deploy()` 方法中，找到 `self._engine.add_portfolio(portfolio)` 之后（约 line 805），在 `GLOG.INFO(...)` 之后、`return True` 之前，添加：

```python
            # 更新 DB state 为 RUNNING
            try:
                portfolio_service = container.portfolio_service()
                portfolio_service.update(
                    portfolio_id=portfolio_id,
                    state=PORTFOLIO_RUNSTATE_TYPES.RUNNING,
                )
                GLOG.INFO(
                    f"[PAPER-WORKER] Portfolio {db_portfolio.code} "
                    f"state -> RUNNING"
                )
            except Exception as e:
                GLOG.WARN(
                    f"[PAPER-WORKER] Failed to update state for "
                    f"{portfolio_id[:8]}: {e}"
                )
```

注意：这里 `container` 变量已在 line 769 获取，`PORTFOLIO_RUNSTATE_TYPES` 已在文件顶部导入。`portfolio_service.update()` 内部会调用 `_crud_repo.modify()`，且 PAPER target 不会被 `is_portfolio_frozen()` 拦截。

- [ ] **Step 2: 在 `_handle_unload()` 卸载成功后更新 state=STOPPED**

在 `_handle_unload()` 方法中，找到 `self._engine.remove_portfolio(target_portfolio)` 之后（约 line 850），在 `GLOG.INFO(...)` 之后、`return True` 之前，添加：

```python
        # 更新 DB state 为 STOPPED
        try:
            from ginkgo import services
            portfolio_service = services.data.container.portfolio_service()
            portfolio_service.update(
                portfolio_id=portfolio_id,
                state=PORTFOLIO_RUNSTATE_TYPES.STOPPED,
            )
            GLOG.INFO(
                f"[PAPER-WORKER] Portfolio {portfolio_id[:8]} "
                f"state -> STOPPED"
            )
        except Exception as e:
            GLOG.WARN(
                f"[PAPER-WORKER] Failed to update state for "
                f"{portfolio_id[:8]}: {e}"
            )
```

- [ ] **Step 3: 改用 ControlCommand.from_dict() 解析消息**

在 `_consume_loop()` 方法中（约 line 936），将消息解析改为：

```python
                        try:
                            from ginkgo.messages.control_command import ControlCommand
                            event_data = message.value
                            cmd = ControlCommand.from_dict(event_data)

                            GLOG.INFO(
                                f"[PAPER-WORKER] Received command: {cmd.command}, "
                                f"params: {cmd.params}"
                            )

                            success = self._handle_command(cmd.command, cmd.params)
```

同时更新 `_send_response` 调用中的 params 引用（如果有的话），将 `params` 改为 `cmd.params`。

- [ ] **Step 4: Commit**

```bash
git add src/ginkgo/workers/paper_trading_worker.py
git commit -m "feat: Worker persists RUNNING/STOPPED state on deploy/unload"
```

---

### Task 5: API 端点 — portfolio start/stop + trading deprecated

**Files:**
- Modify: `api/api/portfolio.py`
- Modify: `api/api/trading.py`

- [ ] **Step 1: 在 `api/api/portfolio.py` 新增 start 和 stop 端点**

在 `delete_portfolio` 端点之前添加：

```python
@router.post("/{uuid}/start")
async def start_portfolio(uuid: str):
    """启动 PAPER/LIVE Portfolio（发送 Kafka deploy 命令）"""
    try:
        from ginkgo.messages.control_command import ControlCommand
        from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
        from ginkgo.interfaces.kafka_topics import KafkaTopics

        portfolio_service = get_portfolio_service()

        # 验证存在
        portfolios = portfolio_service._crud_repo.find(filters={"uuid": uuid})
        if not portfolios:
            raise NotFoundError("Portfolio", uuid)

        portfolio = portfolios[0]
        mode = getattr(portfolio, 'mode', -1)
        from ginkgo.enums import PORTFOLIO_MODE_TYPES
        if mode == PORTFOLIO_MODE_TYPES.BACKTEST.value:
            raise BusinessError("回测模式组合不支持 start，请使用新建回测")

        cmd = ControlCommand.deploy(uuid)
        producer = GinkgoProducer()
        success = producer.send(KafkaTopics.CONTROL_COMMANDS, cmd.to_dict())

        if not success:
            raise BusinessError("Failed to send deploy command via Kafka")

        logger.info(f"Start command sent for portfolio {uuid}")

        return ok(data={"success": True}, message="Start command sent")

    except NotFoundError:
        raise
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error starting portfolio {uuid}: {str(e)}")
        raise BusinessError(f"Error starting portfolio: {str(e)}")


@router.post("/{uuid}/stop")
async def stop_portfolio(uuid: str):
    """停止 PAPER/LIVE Portfolio"""
    try:
        portfolio_service = get_portfolio_service()
        result = portfolio_service.stop(portfolio_id=uuid)

        if not result.is_success():
            raise BusinessError(result.error)

        logger.info(f"Stop command sent for portfolio {uuid}")

        return ok(data=result.data, message=result.message or "Stop command sent")

    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"Error stopping portfolio {uuid}: {str(e)}")
        raise BusinessError(f"Error stopping portfolio: {str(e)}")
```

- [ ] **Step 2: 在 `api/api/trading.py` 的 start/stop 端点标记 deprecated**

将 `start_paper_trading` 和 `stop_paper_trading` 的 docstring 改为：

```python
@router.post("/{account_id}/start", deprecated=True)
async def start_paper_trading(account_id: str, data: StartPaperTradingRequest = None):
    """[DEPRECATED] Use POST /api/v1/portfolios/{uuid}/start instead"""
    ...


@router.post("/{account_id}/stop", deprecated=True)
async def stop_paper_trading(account_id: str):
    """[DEPRECATED] Use POST /api/v1/portfolios/{uuid}/stop instead"""
    ...
```

- [ ] **Step 3: Commit**

```bash
git add api/api/portfolio.py api/api/trading.py
git commit -m "feat: add portfolio start/stop endpoints, deprecate trading start/stop"
```

---

### Task 6: CLI 清理 — 删除 Kafka 辅助函数

**Files:**
- Modify: `src/ginkgo/client/portfolio_cli.py`

- [ ] **Step 1: 删除 `_send_deploy_notification()` 函数**

删除 `portfolio_cli.py` 中约 line 868-883 的 `_send_deploy_notification()` 函数定义。

- [ ] **Step 2: 删除 `_send_unload_command()` 函数**

删除 `portfolio_cli.py` 中约 line 886-902 的 `_send_unload_command()` 函数定义。

- [ ] **Step 3: 修改 `_deploy_paper_trading()` 中的调用**

将 line 792 的 `_send_deploy_notification(new_portfolio_id)` 调用删除，因为 `DeploymentService.deploy()` 已内置 Kafka 通知。

如果 `_deploy_paper_trading` 仍然直接创建 portfolio（不经过 DeploymentService），则改用 ControlCommand：

```python
    # 发送 deploy 通知
    from ginkgo.messages.control_command import ControlCommand
    from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
    from ginkgo.interfaces.kafka_topics import KafkaTopics

    cmd = ControlCommand.deploy(new_portfolio_id)
    producer = GinkgoProducer()
    producer.send(KafkaTopics.CONTROL_COMMANDS, cmd.to_dict())
```

- [ ] **Step 4: 修改 unload 命令中的调用**

将 unload 命令中调用 `_send_unload_command()` 的地方改为使用 `PortfolioService.stop()` 或 ControlCommand：

```python
    from ginkgo.messages.control_command import ControlCommand
    from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
    from ginkgo.interfaces.kafka_topics import KafkaTopics

    cmd = ControlCommand.unload(portfolio_id)
    producer = GinkgoProducer()
    success = producer.send(KafkaTopics.CONTROL_COMMANDS, cmd.to_dict())
```

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/client/portfolio_cli.py
git commit -m "refactor: remove CLI Kafka helpers, use ControlCommand DTO"
```

---

### Task 7: 前端 — 停止按钮 + 删除保护

**Files:**
- Modify: `web-ui/src/views/portfolio/PortfolioDetail.vue`
- Modify: `web-ui/src/views/portfolio/PortfolioList.vue`

- [ ] **Step 1: PortfolioDetail.vue 添加停止按钮**

在 `header-actions` div 中，在"部署"按钮之后、"新建回测"按钮之前，添加停止按钮：

```html
      <div class="header-actions">
        <button class="btn-secondary" @click="$router.push(`/portfolios/${portfolioId}/edit`)">编辑</button>
        <button v-if="portfolioStatus === 'idle'" class="btn-deploy" @click="openDeploy">部署</button>
        <button v-if="portfolioStatus === 'paper' || portfolioStatus === 'live'" class="btn-stop" @click="handleStop">停止</button>
        <button v-if="portfolioStatus === 'idle'" class="btn-primary" @click="startBacktest">新建回测</button>
      </div>
```

在 script setup 中添加 handleStop：

```typescript
async function handleStop() {
  try {
    await portfolioApi.stop(portfolioId.value)
    message.success('停止命令已发送')
    loadPortfolio()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '停止失败')
  }
}
```

添加 import：

```typescript
import portfolioApi from '@/api/modules/portfolio'
```

添加 CSS：

```css
.btn-stop {
  padding: 6px 16px;
  border-radius: 6px;
  border: 1px solid #faad14;
  background: #fffbe6;
  color: #d48806;
  cursor: pointer;
  font-size: 13px;
}
.btn-stop:hover {
  background: #fff1b8;
}
```

- [ ] **Step 2: PortfolioList.vue 删除按钮加状态检查**

在 `confirmDelete` 函数中添加状态检查：

```typescript
const confirmDelete = (record: any) => {
  const mode = record.mode
  const state = record.state
  if ((mode === 1 || mode === 2) && (state === 1 || state === 3)) {
    message.warning('请先停止该组合后再删除')
    return
  }
  deletingPortfolio.value = record
  deleteModalVisible.value = true
  activeMenu.value = null
}
```

- [ ] **Step 3: Commit**

```bash
git add web-ui/src/views/portfolio/PortfolioDetail.vue web-ui/src/views/portfolio/PortfolioList.vue
git commit -m "feat: add stop button and delete protection for PAPER/LIVE portfolios"
```
