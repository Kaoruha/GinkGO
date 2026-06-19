# ADR-010 Phase 4 尾部重新界定（4.4/4.5）

> **状态**：取代原计划 `2026-06-13-adr-010-entity-orm-dto-separation.md` 中 Task 4.3/4.4/4.5/4.6 的过时前提。
> **执行模型**：superpowers:subagent-driven-development（每任务一个执行者 + 两阶段审查）。
> **产生日期**：2026-06-14。基于对全仓 113 处 grep 命中的只读分类标注。

## 背景：为什么原计划 4.3-4.5 失真

| 原任务 | 原前提 | 实际（4.1/4.2 后） | 结论 |
|---|---|---|---|
| 4.3 to_entities→Mapper | 4 处 | 仅死文件 `.backup/.broken` + 1 docstring | **过时，跳过**（4.1 完整迁移已覆盖） |
| 4.4 to_dataframe→result.data | 63 处 | B 类真实迁移面 **26 处**（A 类 11 处合法保留） | **重界定** |
| 4.5 hasattr 鸭子探测 | 23 处 | E 类真实坏味道 **19 处**（F 类 2 处合法保留） | **重界定，排在 4.4 后** |
| 4.6 docstring 清理 | tick/base | 仍相关 | 保留，并入收尾 |

根因：4.1 走「完整迁移后删」（用户决策 A），把 4.3 折叠进 4.1；4.2 多出口又处理了部分 4.4 调用方。原计划的线性保守删序列失去前提。

## 分类体系（已标注，详见会话记录）

- **A. ModelList 合法 DF 出口**（11 处）：Service 内 `_crud_repo.find()`→DF、CRUD 链式转。**保留**。范例：`bar_service.py:781`、`stockinfo_service.py:444/584/655`（正是多出口正确实现）。
- **B. Service `result.data.to_dataframe()`**（26 处）：消费者绕多出口、拿 ModelList 再转。**迁移**。
- **C. 类型/存在性待定**（6 处）：其中 **4 处悬空死代码**（运行即 NameError/AttributeError）。
- **E. hasattr 鸭子探测坏味道**（19 处）：猜 ModelList 分支。**迁 4.4 后大多自然消失**。
- **F. 合法能力检查**（2 处 + 测试 ~27 处断言）：保留。

## 重新界定的执行切片（4 个，按依赖顺序）

### Slice R1：补 Service 多出口（前置，纯增量、零破坏）
为以下 Service 各加 `get_*_df() -> ServiceResult`（data 是 DataFrame），照 `BarService.get_bars_df` / `StockinfoService.get_stockinfos_df` 模板：
- `engine_service`、`portfolio_service`、`signal_service`、`order_service`、`position_service`、`analyzer_record_service`、`tick_service`、`adjustfactor_service`、`backtest_result_service`

**验收**：每个新出口返 `ServiceResult(data=pd.DataFrame)`；空→空 DataFrame；异常→`ServiceResult.failure/error`；补失败路径 + DeprecationWarning（如对应 `get()` 存在）测试。

### Slice R2：迁 client/ 层 B 类 14 处 + 清 CLI hasattr 9 处
按 CLI 文件分组（可拆小 PR）：`engine_cli`(×3)、`record_cli`(×5)、`portfolio_cli`(×2)、`data_cli`(bar/tick ×2)、`backtest_result_cli`、`flat_cli`。
- `result = svc.get(); result.data.to_dataframe()` → `result = svc.get_*_df()`（data 已是 DataFrame，删 `.to_dataframe()`）
- 配套 `hasattr(result.data,'to_dataframe')` 分支同步删（多出口契约固定类型后无需猜）
- **C 类前置定性**：`cli_utils.py:44/134`、`backtest_result_cli.py:119` 调的方法若 grep 无定义 → 先确认是否死代码，**不为死代码补出口**。

### Slice R3：迁 trading/ 层 B 类 8 处 + data/services 消费者 4 处
- `cn_all_selector`、`atr_sizer`、`ratio_sizer`、`base_feeder`、`backtest_feeder`、`data_preparer`(×3)、`engine_assembly_service`、`bar_adjustment`(×2)、`factor_service`、`portfolio_service`(内部)
- 顺带清 trading 层 hasattr 5 处（多数随迁移消失）

### Slice R4：收敛类型 + 清死代码（C/E 收尾）
- 消除 `isinstance+hasattr` 双分支（`adjustfactor_service:366/588`、`tick_service:518`、`bar_adjustment:40`、`factor_service:267`）
- 定性处理 4 处悬空死代码（`notifier_telegram.py:215/315` 的 `get_engines()`、`cli_utils.py:44/134`）——确认调用路径死活，死的删、活的补
- 清理 `test_bar_crud.py.backup/.broken` 死文件
- 4.6 docstring 清理（tick_crud/base_crud 残留 to_entities 提及）

## 关键约束（沿用）
- TDD；测试放 `tests/`；pytest 加 `-o addopts=""`；venv `/home/kaoru/.ginkgo/.venv/bin/python`
- 禁改 Base/BaseCRUD/BaseService；禁 sed；禁 ALTER；禁盲删死代码（先定性）
- 分支 `6107-docs/adr-claudemd-entry`；不直提 master；阶段性推送（HTTP/1.1 逐提交 + gh api 验 SHA）
- A 类（合法 DF 出口）**不动**，它是迁移 B 的参照范式

## 风险与待决策
1. **C 类 4 处悬空引用**：迁移前必须先定性死活。若 `get_engine_portfolio_mappings` 等是动态方法或已删，处理方式不同。
2. **Slice R1 出口数量**：9 个 Service 各加 `get_*_df()`，需确认每个 Service 的 `get()` 现有签名（filter 字段域不同，不能复制粘贴）。
3. **`portfolio_service.get_portfolio()` 当 DataFrame 直接用**（cli_utils:144 `portfolio_df.iloc[0]`）：无 `.to_dataframe()` 但依赖返回即 DF，与多出口冲突，需一并核查。
