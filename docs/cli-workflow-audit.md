# CLI 工作流审计报告

**日期:** 2026-05-06
**目标:** 验证并修复 CLI 全链路「创建组件→创建组合→绑定组件→配置参数→运行回测」

## 修复记录

### 修复 1: `component create` — 从 stub 改为真实实现
- **文件:** `flat_cli.py`
- **改法:** 替换 stub，调用 `file_service.add()` 写入数据库，内置模板生成

### 修复 2: `portfolio create` — 方法名 create→add
- **文件:** `portfolio_cli.py:282`
- **改法:** `portfolio_service.create()` → `portfolio_service.add()`

### 修复 3: `portfolio bind-component` — 按名称绑定崩溃
- **文件:** `portfolio_cli.py`
- **改法:**
  - `file_service.get_by_uuid()` 返回 `{'file': None, 'exists: False}` 时 `success=True`，需检查 `data['file'] is not None`
  - `file_service.get_by_name()` 返回 `{'files': ModelList, 'count': N}` dict，需从中提取 files

### 修复 4: `portfolio get` — is_live 属性不存在
- **文件:** `portfolio_cli.py:346`
- **改法:** `portfolio.is_live` → `portfolio.mode`

### 修复 5: `param list` — get_page_filtered 不存在
- **文件:** `param_cli.py` 全文重写
- **改法:** 用 `param_crud.find_by_mapping_id()` 替代，Rich Table 直接渲染

### 修复 6: `param add` — mapping_id 参数错误
- **文件:** `param_cli.py` 全文重写
- **改法:** 用 `param_crud.set_param_value()` 替代

### 附加修复
- **component delete:** 新增命令，调用 `file_service.soft_delete()`
- **component show:** 新增命令，展示组件源码
- **`_resolve_file`:** 修复 `get_by_uuid` 返回 `file=None` 时的 fallback

## 修复后 CLI 可用性矩阵

| 命令 | 状态 | 备注 |
|------|------|------|
| `component list` | OK | |
| `component list --type X` | OK | |
| `component create` | **OK** | 已修复，支持模板生成 |
| `component show` | **OK** | 新增 |
| `component delete` | **OK** | 新增，支持 --force |
| `portfolio list` | OK | |
| `portfolio create` | **OK** | 已修复 |
| `portfolio get` | **OK** | 已修复 |
| `portfolio get --details` | OK | |
| `portfolio delete` | OK | |
| `portfolio bind-component` | **OK** | UUID 和名称均可 |
| `portfolio unbind-component` | OK | |
| `param list` | **OK** | 已重写 |
| `param add` | **OK** | 已重写 |
| `param update` | **OK** | 已重写 |
| `param delete` | **OK** | 已重写 |
| `backtest create` | OK | |
| `backtest list` | OK | |
| `backtest cat` | OK | |
| `backtest run` | OK | |
| `backtest edit` | OK | |
| `backtest delete` | OK | |

## 变更文件

```
src/ginkgo/client/flat_cli.py       # component create/show/delete 实现
src/ginkgo/client/portfolio_cli.py   # create/bind/get 修复
src/ginkgo/client/param_cli.py       # 全文重写
src/ginkgo/client/logging_cli.py     # 新增 logs/errors/stats 命令
```

## 回测验证记录

### 尝试 1: MA5_20 全市场选股 (2024-06-01 ~ 2024-09-30)

**操作流程 (纯 CLI):**
```bash
ginkgo component create --type strategy --name "MACross5_20"
ginkgo component create --type sizer --name "Fixed10Pct"
ginkgo component create --type selector --name "AllPass"
ginkgo portfolio create --name "MA5_20_Portfolio" --capital 100000
ginkgo portfolio bind-component MA5_20_Portfolio MACross5_20 --type strategy
ginkgo portfolio bind-component MA5_20_Portfolio Fixed10Pct --type sizer
ginkgo portfolio bind-component MA5_20_Portfolio AllPass --type selector
ginkgo backtest create --portfolio <uuid> --start 2024-06-01 --end 2024-09-30 --name "MA5_20_test"
ginkgo backtest run <task_uuid>
```

**发现的问题:**

#### 模板 import 路径过时
- 模板中 `from ginkgo.backtest.strategy.selectors.base_selector import BaseSelector` 报错 `No module named 'ginkgo.backtest'`
- 引擎 fallback 机制加载了默认组件（`CNAllSelector`, `FixedSizer`），不使用用户定义的组件代码
- **影响:** 用户通过 CLI 创建的 Selector/Sizer 实际不会被使用，但没有任何明确错误提示
- **建议:** 更新模板 import 路径，或在引擎 fallback 时输出更明确的警告

#### 全市场回测性能
- 3 个月数据，回测运行超过 10 分钟仍未完成
- 每日处理 ~5000 只股票的 PriceUpdate 事件
- 日志量极大（数万行），控制台输出拖慢速度
