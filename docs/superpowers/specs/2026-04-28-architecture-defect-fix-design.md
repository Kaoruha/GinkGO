# 架构缺陷修复设计

## 背景

当前存在 5 个架构缺陷，违反 CLAUDE.md 规定的分层架构和依赖注入原则：

| 优先级 | 缺陷 | 说明 |
|--------|------|------|
| P0 | DeploymentService 位置错误 | 位于 `trading/services/` 但注册在 `data/containers.py` |
| P1 | Service 直接调用 CRUD | PortfolioMappingService 直接用 FileCRUD/ParamCRUD |
| P2a | 运行时依赖 container | DeploymentService._copy_params_raw() 内部调用 container |
| P2b | DeploymentCRUD 不完整 | 只有 3 个自定义查询方法 |
| P3 | ParamService 自我实例化 CRUD | `self._crud_repo = ParamCRUD()` 而非容器注入 |

附带问题：ParamCRUD `_convert_output_items` 重复定义（line 98 和 104）。

## 修复策略

分两批修复，逻辑分组清晰：

- **批次 1（DI/容器层）**：P0 + P2a + P3
- **批次 2（分层边界）**：P1 + P2b

## 批次 1：DI/容器层修复

### P0：DeploymentService 移入 trading 容器

**目标**：DeploymentService 留在 `trading/services/`，注册点也归 trading 层管理。

**改动**：

1. 创建 `src/ginkgo/trading/containers.py`：
   ```python
   class TradingContainer(containers.DeclarativeContainer):
       deployment_service = providers.Singleton(...)  # lazy factory 或直接注入
   trading_container = TradingContainer()
   ```

2. 从 `data/containers.py` 删除：
   - `deployment_service = providers.Singleton(object)` (line 317)
   - `_deployment_service_instance` 全局变量 (line 324)
   - `_get_deployment_service()` 函数 (line 327-341)
   - `container.deployment_service.override(...)` (line 345)

3. 调用方（`client/deploy_cli.py`、`data/services/portfolio_service.py` 等）改为：
   ```python
   from ginkgo.trading.containers import trading_container
   trading_container.deployment_service()
   ```

### P2a：消除 DeploymentService 运行时 container import

**目标**：`_copy_params_raw()` 不再内部 `from ginkgo.data.containers import container`。

**改动**：

1. DeploymentService 构造函数增加 `param_crud` 参数
2. `_copy_params_raw()` 改为使用 `self._param_crud`
3. trading/containers.py 注册时注入 `param_crud`（从 data container 获取）

### P3：ParamService 构造函数注入

**目标**：ParamService 不再自我实例化 ParamCRUD。

**改动**：

1. ParamService 构造函数改为接受 `crud_repo` 参数：
   ```python
   def __init__(self, crud_repo: ParamCRUD):
       super().__init__()
       self._crud_repo = crud_repo
   ```

2. `data/containers.py` line 237 改为：
   ```python
   param_service = providers.Singleton(ParamService, crud_repo=param_crud)
   ```

3. 修复 ParamCRUD `_convert_output_items` 重复定义：删除 line 98-103 的第一个定义。

## 批次 2：分层边界修复

### P1：PortfolioMappingService 通过 Service 层访问

**目标**：PortfolioMappingService 不再直接操作 ParamCRUD/FileCRUD，改用 ParamService/FileService。

**改动**：

1. 构造函数参数替换：
   - `param_crud: ParamCRUD` → `param_service: ParamService`
   - `file_crud: FileCRUD` → `file_service: FileService`

2. ParamService 需要新增的薄封装方法（当前缺失）：
   - `find_by_mapping_id(mapping_id) -> ModelList` — 查询 mapping 的参数
   - `add_param(mapping_id, index, value, source) -> MParam` — 添加参数
   - `remove_by_mapping(mapping_id) -> int` — 删除 mapping 的所有参数

3. PortfolioMappingService 内部调用映射：
   - `self._param_crud.find_by_mapping_id(id)` → `self._param_service.find_by_mapping_id(id)`
   - `self._param_crud.add(m_param)` → `self._param_service.add_param(...)`
   - `self._param_crud.remove(filters=...)` → `self._param_service.remove_by_mapping(...)`
   - `self._file_crud.get(file_id)` → `self._file_service.get(file_id)`

4. `data/containers.py` 注册更新：
   ```python
   portfolio_mapping_service = providers.Singleton(
       PortfolioMappingService,
       mapping_crud=portfolio_file_mapping_crud,
       param_service=param_service,
       mongo_driver=mongo_driver,
       file_service=file_service,
   )
   ```

### P2b：DeploymentCRUD

**结论**：暂不扩展。BaseCRUD 已提供 `find/remove/count/exists/modify` 等标准能力，现有 3 个自定义方法已覆盖 deployment 特有查询场景。

## 受影响文件清单

### 批次 1
- `src/ginkgo/trading/containers.py` — 新建
- `src/ginkgo/data/containers.py` — 删除 deployment 相关代码、修改 param_service 注册
- `src/ginkgo/trading/services/deployment_service.py` — 增加构造函数参数
- `src/ginkgo/data/services/param_service.py` — 改构造函数注入
- `src/ginkgo/data/crud/param_crud.py` — 删除重复方法定义
- `src/ginkgo/client/deploy_cli.py` — 改 import 路径
- 其他引用 `container.deployment_service` 的文件 — 改 import 路径

### 批次 2
- `src/ginkgo/data/services/portfolio_mapping_service.py` — 改依赖为 Service
- `src/ginkgo/data/services/param_service.py` — 新增薄封装方法
- `src/ginkgo/data/containers.py` — 更新 portfolio_mapping_service 注册

## 测试策略

- 每个批次完成后运行相关单元测试
- 手动验证 `ginkgo deploy` CLI 命令正常工作
- 手动验证 PortfolioMappingService 的图编辑器同步功能
