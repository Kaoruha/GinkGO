# 测试基础设施修复计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复测试体系审计发现的 16 个问题，改善测试稳定性、可维护性和资源使用

**Architecture:** 按优先级分三个阶段执行。Phase 1 修复基础设施（conftest、配置、路径），影响面最小收益最大。Phase 2 修复分层边界问题。Phase 3 修复 E2E 问题。

**Tech Stack:** Python 3.12, pytest, Playwright

---

## Phase 1: 基础设施修复（问题 1-4, 13-15）

### Task 1: 清理根 conftest.py 死代码（问题 1）

**Files:**
- Modify: `tests/conftest.py`

删除以下未使用的 fixture（行 113-1031）和装饰器/辅助函数（行 660-1105）：

**删除的 fixture（15个）：**
- `test_timestamp` (115)
- `sample_stock_code` (121)
- `test_order` (127)
- `test_position` (150)
- `test_signal` (164)
- `price_update_event` (179)
- `test_portfolio_info` (198)
- `losing_portfolio_info` (219)
- `test_database` (242)
- `tdd_metrics` (282)
- `mock_strategy` (907)
- `mock_risk_manager` (934)
- `mock_portfolio` (962)
- `enhanced_event_context` (997)
- `event_sequence_test_data` (1010)

**删除的空操作钩子：**
- `pytest_runtest_setup` (293-298)
- `pytest_runtest_teardown` (301-304)

**删除的装饰器和辅助函数（14个）：**
- `create_market_scenario` (309)
- `assert_financial_precision` (339)
- `financial_precision_test` (662)
- `_validate_financial_precision` (692)
- `protocol_test` (717)
- `protocol_compatibility_test` (751)
- `_validate_protocol_methods` (784)
- `mixin_test` (798)
- `_validate_mixin_methods` (836)
- `tdd_phase` (854)
- `market_scenario` (879)
- `enhanced_framework_test` (1036)
- `time_travel_test` (1057)
- `event_trace_test` (1087)

**保留的代码：**
- `pytest_configure` (41-67) — DEBUG 模式检查 + marker 注册
- `check_debug_mode` (69-110) — 安全检查
- `configured_crud_cleanup` (353-501) — CRUD 自动清理（需修复路径，见 Task 2）
- `tick_crud_module_cleanup` (503-549) — TickCRUD 清理
- `auto_clean_test_data` (552-657) — 通用清理
- `mock_tushare_data_source` (1110-1138) — 全局 Mock（需修复路径，见 Task 2）

**同时清理不再需要的顶层 imports：**
- `sqlite3`, `tempfile` — 仅被 `test_database` 使用
- `Decimal` — 仅被被删除的 fixture 使用
- `warnings` — 检查是否仍被保留代码使用（`auto_clean_test_data` 用了）

- [ ] **Step 1: 删除死代码**

删除上述列出的所有 fixture、装饰器和辅助函数。保留 pytest_configure、check_debug_mode、三个 autouse fixture 和 mock_tushare_data_source。

- [ ] **Step 2: 清理无用 imports**

删除不再需要的 import 语句。保留被保留代码使用的 import。

- [ ] **Step 3: 验证测试仍可通过**

```bash
GINKGO_SKIP_DEBUG_CHECK=1 pytest tests/unit/enums/ -v --timeout=30 -x
```

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py
git commit -m "chore: remove dead code from root conftest.py

Remove 15 unused fixtures, 14 unused decorators/helpers, and
2 no-op hooks (~900 lines). These were superseded by fixtures
in subdirectory conftest files."
```

---

### Task 2: 修复导入路径错误（问题 2）

**Files:**
- Modify: `tests/conftest.py`

**修复 1：`mock_tushare_data_source` 路径（行 1122-1125）**

当前：
```python
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from test.mock_data.mock_ginkgo_tushare import MockGinkgoTushare
```

修改为：
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fixtures'))
from mock_data.mock_ginkgo_tushare import MockGinkgoTushare
```

**修复 2：`configured_crud_cleanup` 路径（行 393-396）**

当前：
```python
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "test" / "libs" / "utils"))
```

修改为：
```python
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "unit" / "libs" / "utils"))
```

- [ ] **Step 1: 修复两处导入路径**

- [ ] **Step 2: 验证 mock_tushare 生效**

```bash
GINKGO_SKIP_DEBUG_CHECK=1 pytest tests/unit/data/ -v --timeout=30 -x -k "tushare" 2>&1 | head -20
```

检查输出中是否出现 "全局Mock数据源已启用" 而非 "Mock数据源导入失败"。

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "fix: correct import paths for mock_tushare and async_cleanup

mock_tushare_data_source was importing from non-existent 'test/mock_data/'
instead of 'tests/fixtures/mock_data/'. configured_crud_cleanup was pointing
to 'test/libs/utils/' instead of 'tests/unit/libs/utils/'. Both errors were
silently swallowed by try-except, causing mock to never activate."
```

---

### Task 3: 统一 pytest 配置（问题 3）

**Files:**
- Delete: `pytest.ini`
- Modify: `pyproject.toml`

**合并策略：** 将 pytest.ini 中的有效配置合并到 pyproject.toml，然后删除 pytest.ini。

需要合并到 `pyproject.toml [tool.pytest.ini_options]` 的配置：
- `timeout = 300` — pytest.ini 有，toml 没有
- `console_output_style = "progress"` — pytest.ini 有
- `pythonpath = [".", "src"]` — pytest.ini 有
- `minversion = "7.0"` — pytest.ini 的值（比 toml 的 6.0 更准确）
- marker 定义需要合并（见 Task 8）

更新后的 `[tool.pytest.ini_options]`：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
minversion = "7.0"
pythonpath = [".", "src"]

addopts = [
    "-v",
    "--strict-markers",
    "--strict-config",
    "--tb=short",
    "--color=yes",
    "--durations=10",
    "--timeout=60",
]

markers = [
    # 见 Task 8 清理后的 marker 列表
]

filterwarnings = [
    "ignore::DeprecationWarning",
    "ignore::PendingDeprecationWarning",
    "ignore::UserWarning:ginkgo.*",
]

log_cli = true
log_cli_level = "INFO"
log_cli_format = "%(asctime)s [%(levelname)8s] %(message)s"
log_cli_date_format = "%Y-%m-%d %H:%M:%S"

timeout = 300
console_output_style = "progress"

required_plugins = ["pytest-cov"]
```

- [ ] **Step 1: 更新 pyproject.toml 的 pytest 配置**

合并 pytest.ini 的有效配置到 pyproject.toml（marker 列表暂用 pyproject.toml 现有的 12 个，Task 8 会进一步清理）。

- [ ] **Step 2: 删除 pytest.ini**

```bash
git rm pytest.ini
```

- [ ] **Step 3: 验证 pytest 读取正确配置**

```bash
GINKGO_SKIP_DEBUG_CHECK=1 pytest --co -q tests/unit/enums/ 2>&1 | head -5
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: unify pytest config into pyproject.toml, remove pytest.ini

pytest.ini took precedence over pyproject.toml, causing the latter's
--strict-config, --durations, and required_plugins to be silently ignored.
Merged all effective config into pyproject.toml and deleted pytest.ini."
```

---

### Task 4: 修复 sys.path 无限增长（问题 4）

**Files:**
- Modify: `tests/conftest.py` — configured_crud_cleanup 中去掉 sys.path.insert
- Modify: ~80 个测试文件 — 去掉模块顶层 `sys.path.insert`

**conftest.py 修复：**

在 `configured_crud_cleanup` 中（Task 2 已修复路径），将 `sys.path.insert` 改为去重版本：

```python
_path_to_add = str(project_root / "unit" / "libs" / "utils")
if _path_to_add not in sys.path:
    sys.path.insert(0, _path_to_add)
```

同样修复 `mock_tushare_data_source` 中的 `sys.path.append`。

**80+ 测试文件的 sys.path.insert：**

使用脚本批量查找并修复。这些文件的模式是：
```python
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
```

由于项目使用 `pip install -e .`，这些 insert 是多余的。但如果某些开发环境没有安装，需要保留。改为安全版本：

```python
_project_src = str(Path(__file__).parent.parent / "src")
if _project_src not in sys.path:
    sys.path.insert(0, _project_src)
```

- [ ] **Step 1: 找出所有包含 sys.path.insert 的测试文件**

```bash
grep -rn "sys.path.insert" tests/ --include="*.py" -l
```

- [ ] **Step 2: 修复 conftest.py 中的两处 sys.path.insert**

添加去重检查。

- [ ] **Step 3: 批量修复测试文件中的 sys.path.insert**

对每个匹配文件添加去重检查。

- [ ] **Step 4: 验证**

```bash
GINKGO_SKIP_DEBUG_CHECK=1 pytest tests/unit/enums/ -v --timeout=30 -x
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "fix: add dedup check to sys.path.insert in test files

Previously sys.path.insert was called per-test-function in autouse
fixtures and per-module in 80+ test files without dedup, causing
sys.path to grow to thousands of entries during full test runs."
```

---

### Task 5: 清理未使用的 pytest markers（问题 13）

**Files:**
- Modify: `pyproject.toml` — 更新 markers 列表
- Modify: `tests/conftest.py` — 更新 pytest_configure 中的 marker 注册
- Modify: 7 个子 conftest.py — 去重 marker 注册

**保留的 markers（基于使用频率）：**

高频（>50次）：`unit`, `database`, `tdd`, `cli`, `risk`, `integration`, `financial`
中频（10-50次）：`db_cleanup`, `e2e`, `critical`, `notifier`, `lab`, `indicator`, `performance`, `asyncio`, `backtest`, `live`, `slow`
低频（<10次但有使用）：`strategy`, `sizer`, `selector`, `protocol`, `enum`, `benchmark`, `kafka`, `error_handling`, `network`, `infrastructure`

**删除的 markers（35个，从未使用）：**
`fixtures`, `protocol_compliance`, `mixin_functionality`, `enhanced_financial`, `trading_scenario`, `framework_enhancement`, `events`, `construction`, `properties`, `time_handling`, `identification`, `price_update`, `capital_update`, `order_related`, `edge_cases`, `analyzer`, `data_con`, `position`, `order`, `component_collaboration`, `poc`, `complete_chain`, `performance_stress`, `real_world_scenarios`, `backtest_validation`, `init`, `feeder`, `quality`, `data_management`, `data_consistency`, `statistics`, `template_methods`, `deprecation`, `time_management`, `compatibility`

**合并 conftest pytest_configure：**

7 个子 conftest 中的 `pytest_configure` 大量重复注册 `unit`, `integration`, `slow` 等。删除子 conftest 中的重复注册，只在根 conftest 中注册一次。

- [ ] **Step 1: 更新 pyproject.toml 的 markers 列表**

替换为清理后的列表。

- [ ] **Step 2: 更新根 conftest.py 的 pytest_configure**

只注册保留的 markers。

- [ ] **Step 3: 清理 7 个子 conftest.py 的重复 marker 注册**

删除子 conftest 中与根 conftest 重复的 marker 注册，只保留子目录特有的。

- [ ] **Step 4: 验证 `--strict-markers` 不报错**

```bash
GINKGO_SKIP_DEBUG_CHECK=1 pytest tests/unit/enums/ -v --timeout=30 -x
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: remove 35 unused pytest markers, deduplicate marker registration

74 markers -> ~30 active markers. Remove 35 never-used markers and
deduplicate registration across 7 conftest files."
```

---

### Task 6: 修复 sys.modules 永久污染（问题 14）

**Files:**
- Modify: `tests/unit/data/crud/test_portfolio_config_crud_mock.py`

将直接 `sys.modules[...] = mock` 改为使用 pytest 的 `monkeypatch`：

当前代码（行 35-71）：
```python
MOCK_MODEL_REGISTERED = False

def _ensure_model_mock():
    global MOCK_MODEL_REGISTERED
    if MOCK_MODEL_REGISTERED:
        return
    ...
    sys.modules["ginkgo.data.models.model_portfolio_config"] = mock_model_module
    MOCK_MODEL_REGISTERED = True
```

改为使用 `autouse` fixture + `monkeypatch`：
```python
@pytest.fixture(autouse=True)
def _mock_model_module(monkeypatch):
    """确保 model_portfolio_config 模块可导入，使用 monkeypatch 自动清理"""
    if "ginkgo.data.models.model_portfolio_config" in sys.modules:
        yield
        return

    import types
    mock_model_module = types.ModuleType("ginkgo.data.models.model_portfolio_config")
    mock_model_module.__path__ = []

    from ginkgo.data.models.model_mongobase import MMongoBase

    class MockPortfolioConfig(MMongoBase):
        __collection__ = "portfolio_configs"
        portfolio_uuid: str = ""
        graph_data: str = "{}"
        mode: str = "BACKTEST"
        version: int = 1
        name: str = ""
        description: str = ""
        is_template: bool = False
        is_public: bool = False
        config_locked: bool = False
        initial_cash: float = 100000.0
        usage_count: int = 0
        tags: list = []
        parent_uuid: str | None = None
        user_uuid: str = ""

    mock_model_module.MPortfolioConfig = MockPortfolioConfig
    monkeypatch.setitem(sys.modules, "ginkgo.data.models.model_portfolio_config", mock_model_module)
    yield
```

删除 `MOCK_MODEL_REGISTERED` 全局变量和 `_ensure_model_mock` 函数。

- [ ] **Step 1: 重写 mock 注册逻辑**

- [ ] **Step 2: 验证测试通过**

```bash
GINKGO_SKIP_DEBUG_CHECK=1 pytest tests/unit/data/crud/test_portfolio_config_crud_mock.py -v --timeout=30
```

- [ ] **Step 3: Commit**

```bash
git add tests/unit/data/crud/test_portfolio_config_crud_mock.py
git commit -m "fix: use monkeypatch for sys.modules mock to prevent permanent pollution

Replace direct sys.modules assignment with pytest monkeypatch.setitem,
ensuring automatic cleanup in teardown."
```

---

### Task 7: 修复 SQLAlchemy Metadata 累积（问题 15）

**Files:**
- Modify: `tests/integration/database/drivers/test_drivers_init.py`

在模块顶层模型定义后，添加 teardown 清理。或者更好的方式：将模型定义移到 fixture 中，确保 scope 结束后清理 metadata。

添加模块级 fixture：
```python
@pytest.fixture(scope="module", autouse=True)
def _cleanup_test_models():
    """清理测试创建的 SQLAlchemy 模型"""
    yield
    # 模块结束后清理测试模型注册的表
    for table_name in list(TestClickModel.metadata.tables.keys()):
        if table_name.startswith("test_"):
            TestClickModel.metadata.remove(TestClickModel.metadata.tables[table_name])
    for table_name in list(TestMysqlModel.metadata.tables.keys()):
        if table_name.startswith("test_"):
            TestMysqlModel.metadata.remove(TestMysqlModel.metadata.tables[table_name])
```

- [ ] **Step 1: 添加 metadata 清理 fixture**

- [ ] **Step 2: 验证**

```bash
GINKGO_SKIP_DEBUG_CHECK=1 pytest tests/integration/database/drivers/test_drivers_init.py -v --timeout=60
```

- [ ] **Step 3: Commit**

```bash
git add tests/integration/database/drivers/test_drivers_init.py
git commit -m "fix: cleanup SQLAlchemy test model metadata after module scope

Add autouse fixture to remove test tables from MetaData after module
completes, preventing accumulation across test modules."
```

---

## Phase 2: 分层边界修复（问题 5-7）

### Task 8: 移动错放的单元测试到 unit 目录（问题 5）

**Files:**
- Move: `tests/integration/trading/engines/*.py` 中标记为 unit 的测试文件
- Move: `tests/integration/database/drivers/*_comprehensive.py` 等文件

**注意：** 这是最大的一个任务。需要逐一审查 45 个文件确认它们确实是纯单元测试（无 DB/网络依赖）后才移动。

**策略：**
1. 先用脚本识别所有 `tests/integration/` 中标记了 `@pytest.mark.unit` 的文件
2. 对每个文件快速检查是否有真实 DB 连接或网络调用
3. 确认是纯单元测试后，从 `tests/integration/` 移到对应的 `tests/unit/` 子目录
4. 更新 import 路径（如有需要）

**重点文件：**
- `tests/integration/trading/engines/test_engine_mode_management.py` (4284行) → `tests/unit/trading/engines/`
- `tests/integration/trading/engines/test_backtest_feeder.py` → `tests/unit/trading/engines/`
- `tests/integration/trading/engines/test_event_engine.py` → `tests/unit/trading/engines/`
- `tests/integration/database/drivers/*_comprehensive.py` (5个文件)

- [ ] **Step 1: 列出所有需要移动的文件**

```bash
grep -rl "@pytest.mark.unit" tests/integration/ --include="*.py"
```

- [ ] **Step 2: 逐个审查并移动文件**

对每个文件：检查 import 是否涉及真实 DB → 确认安全 → `git mv` 到对应 unit 目录

- [ ] **Step 3: 验证移动后测试通过**

```bash
GINKGO_SKIP_DEBUG_CHECK=1 pytest tests/unit/trading/engines/ -v --timeout=30 -x
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: move misplaced unit tests from integration/ to unit/

45 files in tests/integration/ were marked @pytest.mark.unit but had
no external dependencies. Moved to appropriate unit/ subdirectories."
```

---

### Task 9: 修复单元测试中的外部依赖（问题 6）

**Files:**
- Move: `tests/unit/data/collect_real_data_samples.py` → `scripts/` 或删除
- Modify: `tests/unit/libs/utils/test_health_check.py` — 添加 `@pytest.mark.integration` 或 mock socket
- Modify: `tests/unit/database/conftest.py` — 添加注释说明此处有真实 DB 依赖

**具体操作：**

1. `collect_real_data_samples.py` — 移到 `scripts/` 目录（非测试文件）
2. `test_health_check.py` — 改标记为 `@pytest.mark.integration` + `@pytest.mark.network`，或使用 mock socket
3. `tests/unit/database/` — 这些是数据库驱动的单元测试，确实需要连接。改标记为 `@pytest.mark.integration` + `@pytest.mark.database`，并在 README 或 conftest 中注明此目录需要 DB

- [ ] **Step 1: 移动非测试文件**

```bash
mkdir -p scripts
git mv tests/unit/data/collect_real_data_samples.py scripts/
```

- [ ] **Step 2: 修改 test_health_check.py 标记**

将 `@pytest.mark.unit` 改为 `@pytest.mark.integration`

- [ ] **Step 3: 给 tests/unit/database/ 中的 DB 测试加 integration 标记**

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "fix: correct test layering for external dependencies

- Move non-test data collection script to scripts/
- Mark health_check tests as integration (uses real sockets/DNS)
- Mark database unit tests as integration (requires real DB)"
```

---

### Task 10: 整合重复 fixture（问题 7）

**Files:**
- Modify: `tests/conftest.py`
- Modify: `tests/unit/trading/conftest.py`
- Modify: `tests/unit/lab/conftest.py`
- Modify: `tests/unit/backtest/conftest.py`
- Modify: `tests/unit/data/models/conftest.py`
- Modify: `tests/unit/database/conftest.py`
- Modify: `tests/unit/interfaces/conftest.py`
- Modify: `tests/integration/data/crud/conftest.py`
- Modify: `tests/integration/data/drivers/conftest.py`

**策略：**
1. 在根 conftest 中定义通用 fixture（已清理死代码后，根 conftest 很干净）
2. 子 conftest 只保留与根版本不同的 fixture

**需要统一的 fixture 及位置：**

| Fixture | 统一到 | 说明 |
|---------|--------|------|
| `ginkgo_config` | 根 conftest (session scope) | 统一为 session scope |
| `sample_bar_data` | 根 conftest | 各处实现略有差异，取最完整版 |
| `sample_stock_codes` | 根 conftest | 简单数据，无差异 |
| `mock_logger` | 根 conftest | 各处实现相同 |
| `mock_strategy` | 保留子 conftest 各自版本 | 子目录需要不同的 mock 行为 |
| `mock_engine` | 保留子 conftest 各自版本 | 同上 |
| `sample_portfolio_info` | 根 conftest | 取最完整版 |

**注意：** `mock_strategy`、`mock_portfolio`、`mock_engine` 等在不同子目录有不同的 mock 行为（trading 的 mock 和 lab 的 mock 不一样），这些保持各自定义不变。

- [ ] **Step 1: 在根 conftest 中添加通用 fixture**

添加 `ginkgo_config`(session scope)、`sample_bar_data`、`sample_stock_codes`、`mock_logger`

- [ ] **Step 2: 删除子 conftest 中的重复定义**

删除与根 conftest 完全相同的 fixture。保留有差异的版本。

- [ ] **Step 3: 统一 ginkgo_config scope**

确保所有使用点都能正确获取 session scope 版本

- [ ] **Step 4: 验证**

```bash
GINKGO_SKIP_DEBUG_CHECK=1 pytest tests/unit/trading/ tests/unit/lab/ -v --timeout=30 -x
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: deduplicate fixtures across conftest files

Move shared fixtures (ginkgo_config, sample_bar_data, sample_stock_codes,
mock_logger) to root conftest. Remove duplicates from 9 sub-conftest files.
Keep specialized mocks (mock_strategy, mock_engine) in sub-conftests."
```

---

## Phase 3: E2E 修复（问题 8-12, 16）

### Task 11: 统一 E2E 配置，消除硬编码 IP（问题 16）

**Files:**
- Modify: `tests/e2e/final_e2e_test.py`
- Modify: `tests/e2e/run_backtest_fixed.py`
- Modify: `tests/e2e/run_backtest_simple.py`
- Modify: `tests/e2e/run_backtest_e2e.py`
- Modify: `tests/e2e/test_portfolio_param_save_e2e.py`
- Modify: `tests/e2e/test_component_params_detailed_e2e.py`
- Modify: `tests/e2e/test_full_portfolio_backtest_e2e.py`

**统一修改：** 所有硬编码 `http://192.168.50.12:8000` 替换为从 config 读取：

```python
from config import config
api_base = config.api_base
```

- [ ] **Step 1: 逐个文件替换硬编码 IP**

- [ ] **Step 2: 验证 config 加载**

```bash
GINKGO_SKIP_DEBUG_CHECK=1 python -c "import sys; sys.path.insert(0, 'tests/e2e'); from config import config; print(config.api_base)"
```

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/
git commit -m "fix: use config.py for E2E API URLs instead of hardcoded IPs

7 files were bypassing config.py with hardcoded 192.168.50.12 addresses.
Now all E2E files use config.api_base, supporting env var overrides."
```

---

### Task 12: 删除重复的 E2E 测试文件（问题 10）

**Files:**
- Delete: `tests/e2e/run_backtest_fixed.py`
- Delete: `tests/e2e/run_backtest_simple.py`
- Delete: `tests/e2e/run_backtest_e2e.py`
- Delete: `tests/e2e/final_e2e_test.py`
- Keep: `tests/e2e/test_full_backtest_flow_e2e.py` (最完整的版本)

保留 `test_full_backtest_flow_e2e.py` 作为标准回测流程 E2E 测试，删除其余 4 个重复文件。

`test_full_backtest_flow.py` 和 `test_full_portfolio_backtest_e2e.py` 保留——前者测 backtest 创建流程，后者测 portfolio + backtest 组合流程，是不同场景。

- [ ] **Step 1: 删除 4 个重复文件**

```bash
git rm tests/e2e/run_backtest_fixed.py tests/e2e/run_backtest_simple.py tests/e2e/run_backtest_e2e.py tests/e2e/final_e2e_test.py
```

- [ ] **Step 2: Commit**

```bash
git commit -m "chore: remove 4 duplicate E2E backtest flow test files

Keep test_full_backtest_flow_e2e.py as the canonical backtest E2E test.
Removed run_backtest_fixed.py, run_backtest_simple.py, run_backtest_e2e.py,
and final_e2e_test.py which tested the same flow."
```

---

### Task 13: 修复 E2E 条件性断言（问题 12）

**Files:**
- Modify: `tests/e2e/test_login.py` — test_logout 方法
- Modify: `tests/e2e/test_dashboard.py` — TestNavigation 类

**test_login.py test_logout 修复：**

当前（静默通过）：
```python
if user_menu.is_visible():
    ...
    if logout_btn.is_visible():
        logout_btn.click()
```

修复为：
```python
user_menu = page.locator('[data-testid="user-menu"]')
expect(user_menu).to_be_visible(timeout=5000)
user_menu.click()
logout_btn = page.locator('[data-testid="logout-btn"]')
expect(logout_btn).to_be_visible(timeout=5000)
logout_btn.click()
expect(page).to_have_url(re.compile(r".*/login"), timeout=5000)
```

**test_dashboard.py TestNavigation 修复：**

将 `if ... .count() > 0` 条件改为直接 `expect(locator).to_be_visible()` 断言。

- [ ] **Step 1: 修复 test_login.py**

- [ ] **Step 2: 修复 test_dashboard.py**

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_login.py tests/e2e/test_dashboard.py
git commit -m "fix: replace conditional E2E assertions with proper expect()

test_logout and TestNavigation used if/is_visible() guards that silently
passed when elements were missing. Replaced with Playwright expect()
assertions that fail loudly when elements don't exist."
```

---

### Task 14: 修复 E2E 测试顺序依赖（问题 9）

**Files:**
- Modify: `tests/e2e/test_full_backtest_flow.py`

**策略：** 将 `self.` 属性传递改为 pytest fixture 或 class-scoped fixture。

```python
@pytest.fixture(scope="class")
def portfolio_setup(page, authenticated_page):
    """创建 portfolio 并返回名称"""
    portfolio_name = f"e2e_test_{uuid.uuid4().hex[:8]}"
    # ... 创建逻辑 ...
    yield {"portfolio_name": portfolio_name}
    # ... 清理逻辑 ...

class TestFullBacktestFlow:
    def test_01_create_portfolio(self, portfolio_setup):
        assert portfolio_setup["portfolio_name"] is not None

    def test_02_create_backtest(self, portfolio_setup, page):
        # 使用 portfolio_setup["portfolio_name"] 而非 self.portfolio_name
        pass
```

- [ ] **Step 1: 重构 test_full_backtest_flow.py 为 fixture 模式**

- [ ] **Step 2: Commit**

```bash
git add tests/e2e/test_full_backtest_flow.py
git commit -m "fix: replace self.* state passing with class-scoped fixture

Tests numbered test_01 through test_10 used self.* attributes to pass
state, causing cascading failures. Replaced with class-scoped fixture
that provides setup data to all tests in the class."
```

---

### Task 15: 改善 E2E 硬编码等待（问题 8）

**Files:**
- Modify: `tests/e2e/` 下 19 个文件（285 处 wait_for_timeout）

**策略：** 渐进式修复，优先替换最常见的模式。

**常见模式及替换：**

| 当前 | 替换为 |
|------|--------|
| `page.wait_for_timeout(2000)` 后跟 `page.click(...)` | `page.locator(...).click()` (Playwright auto-wait) |
| `page.wait_for_timeout(3000)` 后跟检查 `.is_visible()` | `expect(locator).to_be_visible(timeout=3000)` |
| `page.wait_for_timeout(1000)` 等待导航 | `page.wait_for_load_state("networkidle")` 或 `expect(page).to_have_url(...)` |

**优先修复的文件（wait_for_timeout 最多的）：**
1. `test_full_backtest_flow.py` (38处)
2. `test_portfolio_creation_webui_playwright.py` (35处)
3. `test_full_backtest_flow_e2e.py` (21处)

- [ ] **Step 1: 修复 test_full_backtest_flow.py 的硬编码等待**

- [ ] **Step 2: 修复 test_portfolio_creation_webui_playwright.py**

- [ ] **Step 3: 修复 test_full_backtest_flow_e2e.py**

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/
git commit -m "fix: replace hardcoded wait_for_timeout with Playwright auto-wait

Replace wait_for_timeout + is_visible/click patterns with Playwright's
built-in auto-wait (expect, locator.click, wait_for_load_state) in the
3 most affected E2E files (~94 wait_for_timeout calls)."
```

---

### Task 16: E2E 选择器脆弱性备注（问题 11）

**注意：** 此问题需要前后端协同修改（在 Vue 组件中添加 `data-testid` 属性），超出纯测试修复范围。

**最小可行修复：** 在 Playwright 测试的关键操作中，对最常用的选择器提取为常量：

```python
# tests/e2e/selectors.py
SELECTORS = {
    "modal": ".ant-modal",
    "table": ".ant-table",
    "select": ".ant-select",
    "btn_primary": ".ant-btn-primary",
    "menu_item": ".ant-menu-item",
}
```

这样 Ant Design 升级时只需修改一处。

- [ ] **Step 1: 创建 selectors.py 常量文件**

- [ ] **Step 2: 在最常用的 3 个 E2E 文件中引用常量**

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/selectors.py tests/e2e/
git commit -m "chore: extract Ant Design CSS selectors into constants

Centralize 263 Ant Design CSS class selectors into selectors.py to
simplify future updates. Full data-testid migration requires frontend
changes and is tracked separately."
```

---

## 执行顺序建议

1. **Task 1** → Task 2 → Task 3 → Task 4（Phase 1 基础，无依赖）
2. **Task 5** → Task 6 → Task 7（Phase 1 剩余，无依赖）
3. **Task 8** → Task 9 → Task 10（Phase 2，有依赖：先移文件再整合 fixture）
4. **Task 11** → Task 12 → Task 13 → Task 14 → Task 15 → Task 16（Phase 3 E2E）
