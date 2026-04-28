# 架构缺陷修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 5 个架构缺陷（P0/P1/P2a/P2b/P3），恢复 DI 容器一致性和 Service/CRUD 分层边界。

**Architecture:** 分两批修复。批次 1 修 DI/容器层（P0+P2a+P3），批次 2 修分层边界（P1+P2b）。每批完成后运行测试验证无回归。

**Tech Stack:** Python 3.12, dependency_injector, pytest

---

## 批次 1：DI/容器层修复

### Task 1: 修复 ParamCRUD 重复方法定义

**Files:**
- Modify: `src/ginkgo/data/crud/param_crud.py:98-102`

- [ ] **Step 1: 删除重复的 `_convert_output_items` 定义**

ParamCRUD line 98-102 有第一个定义（无类型注解），line 104-108 有第二个（带类型注解）。删除第一个。

将 `param_crud.py` 中 line 98-102 替换为空（保留 line 104-108 的带类型注解版本）：

删除这段：
```python
    def _convert_output_items(self, items: List, output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert objects for business layer.
        """
        return items
```

保留这段（line 104-108）：
```python
    def _convert_output_items(self, items: List[MParam], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MParam objects for business layer.
        """
        return items
```

- [ ] **Step 2: 验证导入无报错**

Run: `cd /home/kaoru/Ginkgo && python -c "from ginkgo.data.crud.param_crud import ParamCRUD; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/data/crud/param_crud.py
git commit -m "fix(data): remove duplicate _convert_output_items in ParamCRUD"
```

---

### Task 2: ParamService 改为构造函数注入

**Files:**
- Modify: `src/ginkgo/data/services/param_service.py:20-39`
- Modify: `src/ginkgo/data/containers.py:237`

- [ ] **Step 1: 修改 ParamService 构造函数**

将 `param_service.py` 的 `__init__` 和 `_initialize_dependencies` 方法替换为：

```python
    def __init__(self, crud_repo=None):
        """
        初始化ParamService实例

        Args:
            crud_repo: ParamCRUD 实例（由容器注入）
        """
        if crud_repo is not None:
            super().__init__(crud_repo=crud_repo)
        else:
            super().__init__()
            self._crud_repo = ParamCRUD()
```

删除 `_initialize_dependencies` 方法（line 31-39），因为父类 `BaseService._initialize_dependencies` 会自动将 `crud_repo` 设置为 `self._crud_repo`。

- [ ] **Step 2: 更新容器注册**

将 `data/containers.py` line 237 从：
```python
    param_service = providers.Singleton(ParamService)
```
改为：
```python
    param_service = providers.Singleton(ParamService, crud_repo=param_crud)
```

- [ ] **Step 3: 验证导入无报错**

Run: `cd /home/kaoru/Ginkgo && python -c "from ginkgo.data.containers import container; ps = container.param_service(); print(type(ps._crud_repo).__name__)"`
Expected: `ParamCRUD`

- [ ] **Step 4: Commit**

```bash
git add src/ginkgo/data/services/param_service.py src/ginkgo/data/containers.py
git commit -m "fix(data): inject ParamCRUD via constructor in ParamService"
```

---

### Task 3: 创建 TradingContainer

**Files:**
- Create: `src/ginkgo/trading/containers.py`

- [ ] **Step 1: 创建 trading/containers.py**

```python
# Upstream: client/deploy_cli, api/deployment, api/saga_transaction, tests
# Downstream: DeploymentService (trading/services), data/containers (依赖获取)
# Role: trading 层依赖注入容器，管理交易相关服务的实例化

from dependency_injector import containers, providers


class TradingContainer(containers.DeclarativeContainer):
    deployment_service = providers.Singleton(object)


trading_container = TradingContainer()

_deployment_service_instance = None


def _get_deployment_service():
    """Lazy factory for DeploymentService."""
    global _deployment_service_instance
    if _deployment_service_instance is None:
        from ginkgo.data.containers import container
        from ginkgo.trading.services.deployment_service import DeploymentService

        _deployment_service_instance = DeploymentService(
            portfolio_service=container.portfolio_service(),
            mapping_service=container.portfolio_mapping_service(),
            file_service=container.file_service(),
            deployment_crud=container.deployment_crud(),
            broker_instance_crud=container.broker_instance_crud(),
            live_account_service=container.live_account_service(),
            mongo_driver=container.mongo_driver(),
            param_crud=container.cruds.param(),
        )
    return _deployment_service_instance


trading_container.deployment_service.override(
    providers.Singleton(_get_deployment_service)
)
```

- [ ] **Step 2: 验证导入**

Run: `cd /home/kaoru/Ginkgo && python -c "from ginkgo.trading.containers import trading_container; print(type(trading_container).__name__)"`
Expected: `TradingContainer`

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/trading/containers.py
git commit -m "feat(trading): add TradingContainer for deployment service"
```

---

### Task 4: DeploymentService 消除运行时 container import (P2a)

**Files:**
- Modify: `src/ginkgo/trading/services/deployment_service.py:15-31,255-269`

- [ ] **Step 1: 修改构造函数，增加 param_crud 参数**

将 `deployment_service.py` 构造函数替换为：

```python
    def __init__(
        self,
        portfolio_service=None,
        mapping_service=None,
        file_service=None,
        deployment_crud=None,
        broker_instance_crud=None,
        live_account_service=None,
        mongo_driver=None,
        param_crud=None,
    ):
        self._portfolio_service = portfolio_service
        self._mapping_service = mapping_service
        self._file_service = file_service
        self._deployment_crud = deployment_crud
        self._broker_instance_crud = broker_instance_crud
        self._live_account_service = live_account_service
        self._mongo_driver = mongo_driver
        self._param_crud = param_crud
```

- [ ] **Step 2: 修改 `_copy_params_raw` 使用注入的依赖**

将 `_copy_params_raw` 方法替换为：

```python
    def _copy_params_raw(self, old_mapping_id: str, new_mapping_id: str) -> None:
        """原始值复制参数，不经过 json 序列化/反序列化"""
        from ginkgo.data.models.model_param import MParam

        source_params = self._param_crud.find_by_mapping_id(old_mapping_id)
        for p in source_params:
            new_param = MParam(
                mapping_id=new_mapping_id,
                index=p.index,
                value=p.value,
                source=p.source,
            )
            self._param_crud.add(new_param)
```

注意：删除了 `from ginkgo.data.containers import container` 和 `param_crud = container.cruds.param()` 两行。

- [ ] **Step 3: 验证导入**

Run: `cd /home/kaoru/Ginkgo && python -c "from ginkgo.trading.services.deployment_service import DeploymentService; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/ginkgo/trading/services/deployment_service.py
git commit -m "fix(trading): inject param_crud into DeploymentService, remove runtime container import"
```

---

### Task 5: 从 data/containers.py 移除 DeploymentService 注册

**Files:**
- Modify: `src/ginkgo/data/containers.py`

- [ ] **Step 1: 删除 DeploymentService 相关代码**

删除以下代码块（共约 30 行）：

1. Line 316-317 的注释和 placeholder：
```python
    # Deployment service for one-click deploy (placeholder, set after Container instantiation)
    deployment_service = providers.Singleton(object)
```

2. Line 323-345 的 lazy factory：
```python
# Lazy-init deployment service to avoid circular import (trading.services → containers)
_deployment_service_instance = None


def _get_deployment_service():
    """Lazy factory for DeploymentService to break circular import."""
    global _deployment_service_instance
    if _deployment_service_instance is None:
        from ginkgo.trading.services.deployment_service import DeploymentService
        _deployment_service_instance = DeploymentService(
            portfolio_service=container.portfolio_service(),
            mapping_service=container.portfolio_mapping_service(),
            file_service=container.file_service(),
            deployment_crud=container.deployment_crud(),
            broker_instance_crud=container.broker_instance_crud(),
            live_account_service=container.live_account_service(),
            mongo_driver=container.mongo_driver(),
        )
    return _deployment_service_instance


# Override the placeholder with the lazy factory
container.deployment_service.override(providers.Singleton(_get_deployment_service))
```

- [ ] **Step 2: 更新所有调用方**

**`src/ginkgo/client/deploy_cli.py`** — 3 处 `container.deployment_service()` 改为从 trading container 获取：

在每个函数内部，将：
```python
from ginkgo.data.containers import container
```
改为：
```python
from ginkgo.trading.containers import trading_container
```

将所有 `container.deployment_service()` 改为 `trading_container.deployment_service()`。

涉及 3 个函数：`deploy()` (line 24, 43), `info()` (line 72, 74), `list_deployments()` (line 106, 108)。

**`api/api/deployment.py`** — `_get_deployment_service()` 函数：

```python
def _get_deployment_service():
    from ginkgo.trading.containers import trading_container
    return trading_container.deployment_service()
```

**`api/services/saga_transaction.py`** — line 699-702：

将：
```python
        from ginkgo.data.containers import container
        ...
        deployment_service = container.deployment_service()
```
改为：
```python
        from ginkgo.trading.containers import trading_container
        ...
        deployment_service = trading_container.deployment_service()
```

**`tests/integration/trading/services/test_deployment_integration.py`** — line 22, 25, 37, 38：

将：
```python
from ginkgo.data.containers import container
...
deployment_service = container.deployment_service()
```
改为：
```python
from ginkgo.trading.containers import trading_container
...
deployment_service = trading_container.deployment_service()
```

- [ ] **Step 3: 验证完整导入链**

Run: `cd /home/kaoru/Ginkgo && python -c "from ginkgo.trading.containers import trading_container; svc = trading_container.deployment_service(); print(type(svc).__name__)"`
Expected: `DeploymentService`

- [ ] **Step 4: 运行集成测试**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/integration/trading/services/test_deployment_integration.py -v --timeout=30 2>&1 | head -30`
Expected: 至少 `test_list_deployments_returns_list` 通过（另一个测试需要数据库）

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/data/containers.py src/ginkgo/client/deploy_cli.py api/api/deployment.py api/services/saga_transaction.py tests/integration/trading/services/test_deployment_integration.py
git commit -m "refactor: move DeploymentService registration to TradingContainer

- Remove deployment_service from data/containers.py
- All callers now use trading_container.deployment_service()
- Fixes P0 (position mismatch) and P2a (runtime container import)"
```

---

## 批次 2：分层边界修复

### Task 6: ParamService 新增薄封装方法

**Files:**
- Modify: `src/ginkgo/data/services/param_service.py`

- [ ] **Step 1: 在 ParamService 中新增 3 个薄封装方法**

在 `param_service.py` 文件末尾（`cleanup_by_names` 方法之后）添加：

```python
    # ==================== 薄封装方法（供其他 Service 调用） ====================

    def find_by_mapping_id(self, mapping_id: str):
        """
        查询指定映射的所有参数（按索引排序）

        Args:
            mapping_id: 映射 UUID

        Returns:
            ModelList[MParam]
        """
        return self._crud_repo.find_by_mapping_id(mapping_id)

    def add_param(self, mapping_id: str, index: int, value: str, source=None):
        """
        添加参数记录

        Args:
            mapping_id: 映射 UUID
            index: 参数索引
            value: 参数值（JSON 字符串）
            source: 数据源枚举值

        Returns:
            MParam 实例
        """
        from ginkgo.enums import SOURCE_TYPES

        m_param = MParam(
            mapping_id=mapping_id,
            index=index,
            value=value,
            source=source or SOURCE_TYPES.SIM,
        )
        return self._crud_repo.add(m_param)

    def remove_by_mapping(self, mapping_id: str) -> int:
        """
        删除指定映射的所有参数

        Args:
            mapping_id: 映射 UUID

        Returns:
            删除的记录数
        """
        return self._crud_repo.remove(filters={"mapping_id": mapping_id})

    def remove_by_uuid(self, uuid: str) -> int:
        """
        按 UUID 删除单个参数

        Args:
            uuid: 参数 UUID

        Returns:
            删除的记录数
        """
        return self._crud_repo.remove(filters={"uuid": uuid})
```

- [ ] **Step 2: 验证方法存在**

Run: `cd /home/kaoru/Ginkgo && python -c "from ginkgo.data.services.param_service import ParamService; ps = ParamService.__new__(ParamService); print([m for m in ['find_by_mapping_id','add_param','remove_by_mapping','remove_by_uuid'] if hasattr(ps, m)])"`
Expected: `['find_by_mapping_id', 'add_param', 'remove_by_mapping', 'remove_by_uuid']`

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/data/services/param_service.py
git commit -m "feat(data): add thin wrapper methods to ParamService for Service layer boundary"
```

---

### Task 7: PortfolioMappingService 改用 Service 层

**Files:**
- Modify: `src/ginkgo/data/services/portfolio_mapping_service.py`
- Modify: `src/ginkgo/data/containers.py:206-213`

- [ ] **Step 1: 修改构造函数和 import**

将文件头部 import 替换为：

```python
from typing import List, Optional, Dict, Any
import json
import uuid

from ginkgo.libs import GLOG, retry
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.crud.portfolio_file_mapping_crud import PortfolioFileMappingCRUD
from ginkgo.data.services.param_service import ParamService
from ginkgo.data.services.file_service import FileService
from ginkgo.data.models import MPortfolioFileMapping, MParam
from ginkgo.enums import FILE_TYPES, SOURCE_TYPES
from ginkgo.data.drivers.ginkgo_mongo import GinkgoMongo
```

注意：删除了 `from ginkgo.data.crud.param_crud import ParamCRUD` 和 `from ginkgo.data.crud.file_crud import FileCRUD`，改为导入 Service。

将构造函数替换为：

```python
    def __init__(
        self,
        mapping_crud: PortfolioFileMappingCRUD,
        param_service: ParamService,
        mongo_driver: GinkgoMongo,
        file_service: FileService,
    ):
        super().__init__(
            mapping_crud=mapping_crud,
            param_service=param_service,
            mongo_driver=mongo_driver,
            file_service=file_service,
        )
```

将类 docstring 中的 Attributes 更新为：

```python
    """
    投资组合映射服务
    ...
    Attributes:
        _mapping_crud: PortfolioFileMappingCRUD 实例
        _param_service: ParamService 实例
        _mongo_driver: GinkgoMongo 驱动实例
        _file_service: FileService 实例
    """
```

- [ ] **Step 2: 替换所有 `self._param_crud` 调用**

全局替换规则（共 9 处）：

| 位置 | 原调用 | 新调用 |
|------|--------|--------|
| `remove_file` ~line 309 | `self._param_crud.remove(filters={"mapping_id": mapping.uuid})` | `self._param_service.remove_by_mapping(mapping.uuid)` |
| `get_portfolio_mappings` ~line 407 | `self._param_crud.find_by_mapping_id(m.uuid)` | `self._param_service.find_by_mapping_id(m.uuid)` |
| `get_mapping_params` ~line 443 | `self._param_crud.find_by_mapping_id(mapping_uuid)` | `self._param_service.find_by_mapping_id(mapping_uuid)` |
| `_sync_mappings_from_files` ~line 652 | `self._param_crud.remove(filters={"mapping_id": existing_mapping.uuid})` | `self._param_service.remove_by_mapping(existing_mapping.uuid)` |
| `_sync_params_for_mapping` ~line 716 | `self._param_crud.find_by_mapping_id(mapping_uuid)` | `self._param_service.find_by_mapping_id(mapping_uuid)` |
| `_sync_params_for_mapping` ~line 720 | `self._param_crud.remove(filters={"uuid": p.uuid})` | `self._param_service.remove_by_uuid(p.uuid)` |
| `_sync_params_for_mapping` ~line 730 | `self._param_crud.add(m_param)` | `self._param_service.add_param(mapping_uuid=mapping_uuid, index=idx, value=param["value"], source=SOURCE_TYPES.SIM)` |
| `_get_params_for_mapping` ~line 825 | `self._param_crud.find_by_mapping_id(mapping_uuid)` | `self._param_service.find_by_mapping_id(mapping_uuid)` |

`_sync_params_for_mapping` line 730 需要额外注意：原代码创建 `MParam` 对象再 `add`，新代码改为调用 `add_param`。将整个 `_sync_params_for_mapping` 方法改为：

```python
    def _sync_params_for_mapping(
        self,
        mapping_uuid: str,
        params: Dict[str, Any],
    ) -> None:
        """
        同步参数到指定的 mapping

        Args:
            mapping_uuid: Mapping UUID
            params: 参数字典
        """
        # 将参数字典转换为扁平列表
        param_list = []
        for key, value in params.items():
            try:
                value_str = json.dumps(value, ensure_ascii=False)
            except Exception as e:
                GLOG.ERROR(f"序列化参数值失败: {e}")
                value_str = str(value)
            param_list.append({"key": key, "value": value_str})

        # 删除旧参数
        self._param_service.remove_by_mapping(mapping_uuid)

        # 添加新参数
        for idx, param in enumerate(param_list):
            self._param_service.add_param(
                mapping_uuid=mapping_uuid,
                index=idx,
                value=param["value"],
                source=SOURCE_TYPES.SIM,
            )
```

- [ ] **Step 3: 替换 `self._file_crud` 调用**

`_sync_graph_from_mappings` 中 ~line 776：

将：
```python
                file_obj = self._file_crud.get(mapping.file_id)
                if not file_obj:
                    continue
```
改为：
```python
                file_result = self._file_service.get_by_uuid(mapping.file_id)
                file_obj = file_result.data.get("file") if file_result.success else None
                if not file_obj:
                    continue
```

- [ ] **Step 4: 更新容器注册**

将 `data/containers.py` 中 `portfolio_mapping_service` 注册（~line 207-213）从：

```python
    portfolio_mapping_service = providers.Singleton(
        PortfolioMappingService,
        mapping_crud=portfolio_file_mapping_crud,
        param_crud=param_crud,
        mongo_driver=mongo_driver,
        file_crud=file_crud,
    )
```
改为：
```python
    portfolio_mapping_service = providers.Singleton(
        PortfolioMappingService,
        mapping_crud=portfolio_file_mapping_crud,
        param_service=param_service,
        mongo_driver=mongo_driver,
        file_service=file_service,
    )
```

- [ ] **Step 5: 验证导入链**

Run: `cd /home/kaoru/Ginkgo && python -c "from ginkgo.data.containers import container; svc = container.portfolio_mapping_service(); print(type(svc).__name__)"`
Expected: `PortfolioMappingService`

- [ ] **Step 6: Commit**

```bash
git add src/ginkgo/data/services/portfolio_mapping_service.py src/ginkgo/data/containers.py
git commit -m "refactor(data): PortfolioMappingService uses ParamService/FileService instead of CRUD

Fixes P1 (Service directly calling CRUD), maintains Service layer boundary."
```

---

### Task 8: 最终验证和清理

**Files:**
- 无新增文件

- [ ] **Step 1: 全量导入验证**

Run: `cd /home/kaoru/Ginkgo && python -c "
from ginkgo.data.containers import container
from ginkgo.trading.containers import trading_container
print('data container OK')
print('trading container OK')

# 验证关键服务可正常实例化
ps = container.param_service()
pms = container.portfolio_mapping_service()
ds = trading_container.deployment_service()
print(f'ParamService._crud_repo: {type(ps._crud_repo).__name__}')
print(f'PortfolioMappingService._param_service: {type(pms._param_service).__name__}')
print(f'DeploymentService._param_crud: {type(ds._param_crud).__name__}')
"`
Expected: 所有类型名称正确打印，无异常

- [ ] **Step 2: 检查无残留的运行时 container import**

Run: `cd /home/kaoru/Ginkgo && grep -n "from ginkgo.data.containers import container" src/ginkgo/data/services/param_service.py src/ginkgo/trading/services/deployment_service.py`
Expected: 无匹配（这两个文件不应再有运行时 container import）

注意：`param_service.py` 的 `cleanup_orphaned_params` 和 `cleanup_by_names` 方法仍然 import container（这是遗留问题，不在本次修复范围）。

- [ ] **Step 3: Push**

```bash
git push origin 001-feat/webui-navigation
```
