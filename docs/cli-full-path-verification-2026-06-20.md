# CLI 全链路验证报告：策略开发 → 回测 → 模拟交易 → 实盘

- **日期**：2026-06-20
- **ginkgo 版本**：0.8.1（`/home/kaoru/.local/bin/ginkgo`）
- **目的**：通过 CLI 走通「策略开发 → 回测 → 模拟交易 → 实盘」全路径，记录阻碍与文档偏差
- **结论一句话**：**策略开发 + 回测全通；模拟交易「部署」通但「执行」割裂（两条架构并存，仅 worker-paper 可用）；实盘受阻于券商账号 + stub。**

## 0. 阶段总览

| 阶段 | 路径 | 结果 | 关键阻碍 |
|---|---|---|---|
| 0 环境 | `status`/`debug`/`data` | ✅ 通过 | CLAUDE.md debug 命令偏差 |
| 1 策略开发 | `component create/show/edit` | ✅ 通过 | basic 模板有可疑代码行 |
| 2 回测 | `portfolio create → bind → backtest create/run/cat` | ✅ 通过 | 无 |
| 3 模拟交易 | `deploy -m paper` + `serve worker-paper` | ⚠️ 部分通过 | `execution load` 为 stub(#4637 关闭但仍在)；deploy 副作用多 |
| 4 实盘 | `deploy -m live --account` + `livecore` | ❌ 受阻 | 需券商账号；`livecore status`/`execution load` stub |

## 1. 阶段0：环境基线

- Debug=ON、Quiet=ON、8021 只股票就绪、Workers=0。
- **说明（非问题）**：`ginkgo` 经 PATH（`/home/kaoru/.local/bin`）可用；`/home/kaoru/.ginkgo/.venv/bin/python`（cpython 3.14）用于跑 Python 脚本，两者均有效，CLAUDE.md 的 Python 环境路径正确。
- **问题 P0-2（文档偏差）**：CLAUDE.md「Key Commands」写 `ginkgo system config set --debug on`。实际**无 `system config` 命令**，正确写法是 `ginkgo debug on`（参数 `MODE:{on|off}`）。

## 2. 阶段1：策略开发（component）

- 子命令：`list / create / delete / show / edit`。
- 验证：`ginkgo component create -t strategy -n verify_ma_cross -d "..."` 成功，UUID `c029e33c9f5740b0aa0961e28e442fe0`，basic 模板 1658 字节。
- 策略源码位于 `src/ginkgo/trading/strategies/*.py`（注意仓库前缀是 `src/ginkgo/`，非 `ginkgo/`），basic template 由 `src/ginkgo/data/seeding.py` 在 `ginkgo init` 时灌库。
- **问题 P1-1（模板代码可疑）**：basic strategy 模板含
  ```python
  if code not in self._closes:
      self._closes = deque(maxlen=self._long_window + 2)
  ```
  `code`（股票代码字符串）与 `self._closes`（收盘价 deque）做 `in` 比较，语义错误，会导致 deque 被反复重置。模板逻辑存疑，建议复核。
- **问题 P1-2（文档偏差）**：CLAUDE.md「可用组件」列出 Selector `fixed/cn_all`、Sizer `fixed/atr/ratio` 等短名，但 DB 实际名字带后缀：`fixed_selector`/`cn_all_selector`/`atr_sizer`/`ratio_sizer`/`fixed_sizer`。按文档短名绑定会查不到组件。
- **问题 P1-3（测试污染）**：组件库 405 个，大量 `my_custom_strategy`、`delete_test`(x11)、`empty_clone`(x9)、`e2e_*` 测试残留，干扰查找。dev 库需定期清理。

## 3. 阶段2：回测（portfolio → backtest）

全链路通过。验证组合：
- selector `fixed_selector`（codes=`000001.SZ,600519.SH`，参数 index 1；index 0 是 name）
- strategy `moving_average_crossover`（short=5, long=20）
- sizer `fixed_sizer`、risk `no_risk`

```bash
ginkgo portfolio create --name verify_e2e --capital 100000          # 9d77ac35...
ginkgo portfolio bind-component <PID> <FID> -t selector  --param '1:"000001.SZ,600519.SH"'
ginkgo portfolio bind-component <PID> <FID> -t strategy  --param 1:5 --param 2:20
ginkgo portfolio bind-component <PID> <FID> -t sizer
ginkgo portfolio bind-component <PID> <FID> -t risk
ginkgo backtest create --portfolio <PID> --start 2025-06-01 --end 2025-09-01 --name verify_bt --cash 100000
ginkgo backtest run <BID>     # 5 signals → 5 orders, status=completed
ginkgo backtest cat <BID>     # PnL -372.60, MaxDD 3.61%, Sharpe -0.72, WinRate 50%
```

事件链 `PriceUpdate → Strategy → Signal → Portfolio → Order → Fill` 全通。
- **说明**：`bind-component --type` 接受 `risk`（组件类型字段是 `riskmanager`，别名兼容）。
- **说明**：`backtest cat` 的 `Engine:` 字段为空，符合 `arch_backtest_id_boundary`（engine_id 仅在特定条件下坍缩回写）。

## 4. 阶段3：模拟交易（deploy → paper）

### 4.1 deploy 本身可用
```bash
ginkgo deploy deploy <PID> -m paper -n verify_paper
# 克隆新组合 9eb1df47..., Deployment d5bba20b..., 发 Kafka 部署指令到 localhost:9092
```
deploy = Clone 组合 + 建文件映射 + 建部署记录 + 发 Kafka 指令（符合 `project_deploy_clone_design`：Deploy=Clone+冻结）。

### 4.2 执行侧存在两套架构（关键认知）
| 路径 | 命令 | 状态 |
|---|---|---|
| **A. PaperTradingWorker**（可用） | `ginkgo serve worker-paper --id <node>` | ✅ 长驻进程，装配引擎，启动时装载**全部** paper 组合并消费 Kafka 每日循环 |
| **B. ExecutionNode 热加载**（不可用） | `ginkgo execution load <PID>` | ❌ STUB |

- 冒烟验证 A：`timeout 20 ginkgo serve worker-paper --id verify_paper_smoke` 成功启动，日志显示「Assembling engine → 装载 N 个 paper 组合 → 引擎完成: PaperTrading-...」。启动时还会把陈旧 RUNNING 组合重置为 STOPPED（清理孤儿）。
- 实际成交需 `serve worker-data`（行情）+ 开盘时段，本次在凌晨 3 点未跑出真实成交（超出 CLI 路径验证范围）。

### 4.3 阶段3 发现的问题
- **问题 P3-1（严重·stub 未实现）**：`execution load`/`unload`/`list-portfolios` 均为 STUB，提示「Portfolio 热加载/卸载/列表功能待开发，参见 #4637」。
  - **#4637 状态异常**：issue 标题「execution load 为空壳」，2026-06-07 **CLOSED**，评论称「PR #4652 修复待 review」；PR #4652（批量修 #4613-#4646）确已 **MERGED**。但 stub 在 0.8.1 仍在（仅改写了提示文案，功能仍空壳）。疑似修复不完整或回归——**issue 提前关闭，建议重开或核验 #4652 实际是否覆盖 execution load 实现**。
- **问题 P3-2（CLI 不一致）**：`deploy info <deployment_id>` 报「未找到部署记录」，必须传 **portfolio_id** 才成功。命令按 portfolio_id 查询，但参数名/语义暗示 deployment_id。
- **问题 P3-3（视图不一致）**：deploy 克隆出的 paper 组合，`portfolio get --details` 显示「No component bindings found」，但部署日志明确「添加文件映射」。deploy 用 Mapping 图模型，details 视图查直接绑定表，两套模型未对齐，用户无法用 details 确认绑定。
- **问题 P3-4（资金未继承）**：源回测组合资金 ¥100,000，克隆出的 paper 组合 Initial/Current/Cash 均为 ¥1,000,000。deploy 未继承源资金。
- **问题 P3-5（CLI 未实现）**：`ginkgo mapping list` 返回「Mapping listing not yet implemented」，部署创建的映射无法用 CLI 列出校验。
- **说明**：`ginkgo status` 的 Workers 计数不包含 paper worker（前台进程），易误判「无 worker 运行」。

## 5. 阶段4：实盘（live）

- **问题 P4-1（受阻·预期）**：`deploy -m live` 强制要求 `--account`（实盘账号 ID），无券商账号配置无法部署。属部署/配置前提，非 CLI bug。
- **问题 P4-2（stub）**：`ginkgo livecore status` 返回「Status tracking will be implemented in Phase 4」，状态查询未实现。
- **问题 P4-3（stub）**：同 P3-1，ExecutionNode 热加载路径不可用。实盘若走 ExecutionNode 架构同样受阻；若走 `serve livecore`/`serve execution` 前台进程路径需另行验证（本次未配置券商账号，未深入）。

## 6. 问题清单（按优先级）

| ID | 严重度 | 问题 | 建议动作 |
|---|---|---|---|
| P3-1 | 🔴 高 | `execution load/unload/list-portfolios` stub，#4637 关闭但 stub 在 | 核验 #4652 是否真覆盖；重开 issue 或补实现 |
| P3-3 | 🟠 中 | deploy 克隆组合在 details 视图无绑定（图模型 vs 绑定表） | details 视图兼容 Mapping，或 deploy 同时写绑定表 |
| P3-2 | 🟠 中 | `deploy info` 参数语义与实际不符 | 统一为 deployment_id，或在 help 标注用 portfolio_id |
| P1-1 | 🟠 中 | basic strategy 模板 `code not in self._closes` 逻辑可疑 | 复核并修正模板 |
| P4-2/P4-3 | 🟡 低 | `livecore status` stub；实盘 ExecutionNode 路径同 P3-1 | Phase 4 补全 |
| P3-4 | 🟡 低 | deploy 未继承源组合资金 | 克隆时携带 capital |
| P3-5 | 🟡 低 | `mapping list` 未实现 | 补 list 实现 |
| P0-2/P1-2 | 🟡 低 | CLAUDE.md debug 命令/组件名偏差 | 同步更新 CLAUDE.md |
| P1-3 | 🟢 提示 | 组件库测试残留污染 | dev 库定期清理 |

## 7. 可走通的最小全链路（策略→回测→模拟部署）

```bash
# 0 环境
ginkgo debug on
# 1 策略（复用 seeded moving_average_crossover: 109926e3288543e8835927b80269cb40）
# 2 回测
ginkgo portfolio create --name e2e --capital 100000
ginkgo portfolio bind-component <PID> f36bc4a30f1a4e11844302d08f0810d7 -t selector --param '1:"000001.SZ,600519.SH"'
ginkgo portfolio bind-component <PID> 109926e3288543e8835927b80269cb40 -t strategy --param 1:5 --param 2:20
ginkgo portfolio bind-component <PID> 159cb8422c194b88a39b32b49ac0d051 -t sizer
ginkgo portfolio bind-component <PID> ba02aaa777cf488488bc87f11e26d1e6 -t risk
ginkgo backtest create --portfolio <PID> --start 2025-06-01 --end 2025-09-01 --name bt --cash 100000
ginkgo backtest run <BID> && ginkgo backtest cat <BID>
# 3 模拟部署 + 执行 worker（前台另开终端）
ginkgo deploy deploy <PID> -m paper -n paper_e2e
ginkgo serve worker-paper --id paper_1   # 长驻，需配合 serve worker-data + 开盘
# 4 实盘：受阻，需 --account 券商账号
```

## 8. 验证产物（本次创建，可清理）

- 策略组件：`verify_ma_cross`（c029e33c9f5740b0aa0961e28e442fe0）
- 回测组合：`verify_e2e`（9d77ac35ed074fa8b1b08a3e7c6594b8）
- 回测任务：`verify_bt`（0db54af7bdf745b696db3302b4bf70d8）
- 模拟组合：`verify_paper`（9eb1df471f464026818be98939b4fc6c，Deployment d5bba20b796c4e229bc3ee797d05b3f5）
