# 四级漏斗评估体系设计（G0-G3）

> 状态：设计中（未实施）。方法论经讨论认可，本文档为后端能力 + 前端形态的落地设计。
> 日期：2026-08-26

## 0. 产品北极星

**评估工作台**：输入一个 portfolio，一眼看清它在"回测可信 → 回测有效 → 模拟一致 → 实盘就绪"漏斗中的位置。

四个产品要求（用户原话）的落点：

| 要求 | 落点 |
|---|---|
| 可观测 | 每级 gate 的指标卡：当前值、阈值线、通过/失败徽章、样本量 |
| 可操作 | 每个未过项附动作：`补数据` / `重跑回测` / `查执行偏差` / `查看缺口明细` |
| 信息层级明显 | 三层：漏斗总览（1 屏定位卡在哪级）→ gate 详情（哪几项没过）→ 原始指标（下钻时间序列） |
| 直观辅助判断 | 结论话术由系统生成："G1 已过，G2 样本仅 12 天（需 ≥20），继续观察"——人只做最终决策 |

## 1. 漏斗定义（gate 声明式，单一事实源）

四级 gate，指标与阈值**声明在代码里**（不是硬编码在页面），CLI/API/前端共用：

| 级 | gate 名 | 核心指标（阈值） | 现状 |
|---|---|---|---|
| G0 | 数据可信 | bar 缺口率=0；复权口径一致；退市股含于 universe；样本 ≥3 年 & ≥100 笔成交 | 覆盖检查有（#6282），质量检查缺，PIT 退市过滤缺 |

> G0 质量项的工程化（M2）：「缺口率=0」按 A 股停牌现实放为两档 — gap>20% 为 blocker（`g0_bar_gap` gate），5%~20% 为 warning（preflight issues 明细）；「复权口径一致」落为前复权因子无回跳（`g0_adjustfactor_consistency` gate，回跳>0 blocker）。基准日历取「窗口内出现率 ≥50% codes 的日期集合」（多数决，防单 code 异常污染基准）。这两条 gate 在 `eval preflight`（portfolio+窗口侧）求值，funnel（task 侧）不含——M3 service 层聚合。
| G1 | 回测有效 | Sharpe≥1.0；MDD 在承受线内；季度收益同号率≥60%；滚动平稳度不发散；参数邻域衰减 | stability/segment 已有；参数邻域缺 |
| G2 | 模拟一致 | 同窗 ≥20 交易日；日收益相关性≥0.8；累计收益差 ≤ 回测同窗波动 1.5×；换手偏差<20%；回撤形态同构 | **全缺，本设计核心增量** |
| G3 | 实盘就绪 | G2 连续通过 ≥4 周；kill switch 就位；小资金试运行 ≥2 周 | kill switch 缺（P1，独立线） |

阈值可配置（后续放 settings），第一版内置默认值。

## 2. 后端能力设计（按现有分层：CLI/API → Service → 领域层 → CRUD/DB）

### 2.1 领域层（`src/ginkgo/trading/analysis/evaluation/`，纯计算无 DB 依赖优先）

已有复用：`BacktestEvaluator`、`SliceDataManager`、`MetricStabilityCalculator`、`SlicePeriodOptimizer`。

新建：

| 模块 | 职责 | 依赖 |
|---|---|---|
| `gate_definitions.py` | 四级 gate 声明：`GateDefinition{id, level, metric, threshold, direction, severity, remediation}`；`ALL_GATES` 列表 = 单一事实源 | 无 |
| `funnel_evaluator.py` | 汇总：输入 portfolio_id（+可选 task_id/deployment_id），逐 gate 求值，输出 `FunnelReport{portfolio_id, level_reached, gates: [{id, status: PASS/FAIL/INSUFFICIENT_DATA/BLOCKED, value, detail}]}` | 下述各 calculator |
| `parity_calculator.py` | G2 核心：取回测 task 与模拟 deployment 的同窗日频序列（net_value 为主链），算 5 项一致性指标；序列经 `AnalysisEngine._load_data` 同一路径取数（避免第二套取数逻辑）；baseline 口径与 `live_deviation_detector` 对齐（见 §5） | analyzer_service |
| `preflight_checker.py` | G0 补齐：数据质量（缺口/复权一致）+ 样本量检查；扩展现有覆盖检查结论 | bar_service |
| `parameter_neighborhood.py`（M3） | G1 补齐轻量版：参数邻域衰减。依赖 optimize 接线（外部依赖，未接线前该 gate 返回 `BLOCKED(依赖未就绪)` 而非假装通过） | optimize 模块 |

**数据前提**：回测与模拟盘共用 Portfolio 内置分析器链（builtin_map），analyzer_record 按 task_id/engine_id 区分。模拟盘记录连续性需实测验证（M1 首个任务）。

### 2.2 Service 层（`src/ginkgo/trading/services/evaluation_service.py`）

`EvaluationService`（不暴露 CRUD 实例，符合分层规则）：

- `get_funnel_report(portfolio_id, task_id=None, deployment_id=None) -> FunnelReport`：编排领域层，处理跨源聚合
- `get_parity_report(task_id, deployment_id) -> ParityReport`
- `run_preflight(task_id) -> PreflightReport`
- 注册进 service container，API/CLI 统一 `xxx_container.evaluation_service()` 取用

### 2.3 API 层（`api/api/evaluation.py`，新建）

| 端点 | 语义 |
|---|---|
| `GET /evaluation/gates` | gate 定义清单（前端渲染阈值线用） |
| `GET /evaluation/funnel?portfolio_id=` | 漏斗报告（实时计算，不落库） |
| `GET /evaluation/parity?task_id=&deployment_id=` | parity 报告 |
| `POST /evaluation/preflight` | 触发数据预检（同步，量小） |

遵循现有模式：router + `_get_evaluation_service()` + 统一响应封装。

### 2.4 CLI 层（`client/evaluation_cli.py` 扩展）

- `ginkgo eval funnel <portfolio_id>`：漏斗总览（Rich 表：gate/状态/值/阈值）
- `ginkgo eval parity <deployment_id> --task <task_id>`：一致性报告
- 与已有 `stability/segment/rolling/monitor-*` 同居一个命令组

### 2.5 数据层

**零新建表、零 ALTER**。全部实时计算：读 `analyzer_record`（CH）+ `backtest_task`/`deployment`（MySQL）。gate 报告不落库（每次现算，快）；历史趋势如需再加 Model（走 `ginkgo init` 建表）。

### 2.6 G3 kill switch（独立线，不塞进本设计）

属 livecore 风控域：flatten/cancel-all 指令、daily loss 熔断字段激活、独立 kill switch 接口。本设计只在 funnel 报告里如实显示"G3 BLOCKED：kill switch 未就位"。另立 issue 推进。

## 3. 前端页面（第二阶段）

页面：`views/backtest/EvaluationWorkbench.vue`（评估工作台）

```
┌ Portfolio 选择器 ────────────────────────────────┐
│ [漏斗 Stepper]  G0 ✅ → G1 ✅ → G2 ⏳(12/20天) → G3 🔒 │  ← 一屏定位
├──────────────────────────────────────────────────┤
│ 当前级详情（G2）：                                  │
│  指标卡×5：日收益相关性 0.86 ✅ | 样本 12天 ⏳ | ...  │  ← 可观测
│  行动列表：继续运行模拟盘至 20 交易日（预计 8 天）      │  ← 可操作
│  [下钻] 双净值对比曲线（同窗对齐+偏差带）              │
└──────────────────────────────────────────────────┘
```

- 复用 `components/charts/` 折线、`EmptyState`、类型入 `types/`
- API 走 `api/modules/evaluation.ts`（request.ts 封装，注意信封拆解：`.data` 一层）
- 状态徽章四态对应后端 status：PASS/FAIL/INSUFFICIENT_DATA/BLOCKED

## 4. 里程碑

| 里程碑 | 内容 | 验收 |
|---|---|---|
| M1 | parity_calculator + funnel_evaluator 骨架 + `eval parity`/`eval funnel` CLI | 用 portfolio=1ff27ed7 的回测（task=9e0b4cdf）+ 模拟盘实测出首份对比报告；模拟盘分析记录连续性结论落地 |
| M2 | gate_definitions 统一 + preflight_checker（G0 质量检查） | `eval funnel` 全四级有状态（缺数据如实 INSUFFICIENT_DATA/BLOCKED） |
| M3 | EvaluationService + API 四端点 + 前端工作台 + parity 曲线页 | 浏览器端到端验证（含空数据/失败路径） |
| M4 | 参数邻域（依赖 optimize 接线）+ G3 kill switch 联动显示 | G1 补齐；G3 如实反映 kill switch 状态 |

## 5. 设计决策记录

- **gate 声明式单一事实源**：阈值改动一处生效三端（CLI/API/前端），防口径漂移
- **报告不落库**：评估是纯读时序的实时计算，落库引入陈旧问题（memory: 陈旧服务/陈旧报告教训）
- **BLOCKED ≠ FAIL**：依赖未就绪（如 optimize 未接线、kill switch 缺）时如实报 BLOCKED，不静默降级（归因纪律：宁可响亮）
- **parity 取数复用 `_load_data`**：单一取数路径，避免第二套口径（D/D+1 教训）
- **与在线偏差链路互补、口径共享**：`evaluation/` 已有 `DeviationChecker` + `LiveDeviationDetector`（paper worker 每日调用的 z-score 在线检测，Redis 基线、Kafka 告警、自动熔断）——那是**机器哨兵半边**（逐日盯、超阈值即告警/熔断）。`parity_calculator` 是**人看报告半边**（离线、同窗全期对比、相关性/收益差带宽/换手偏差/回撤形态）。两者 baseline（回测基准序列）取数口径必须一致，指标不重复实现：z-score 类检测留在 detector，相关性/带宽类汇总留在 calculator；分界=「逐日告警」vs「全期判断」

## 6. 扩展指南：新增一个 gate

以 M4 落地的 `g1_param_neighborhood` 为参照，新增 gate 改 **2 个文件 + 1 处测试**，前端与 API 零改动（卡片/行动列表/漏斗计数全部数据驱动，遍历 `gates` 自动渲染）。

### 第 1 步：声明（`gate_definitions.py`）

加一条 `GateDefinition` —— 这是单一事实源，CLI/API/前端三端自动读到：

```python
GateDefinition(
    id="g1_xxx",                    # 唯一标识, 前端 data-testid 也用它
    level="G1",                     # G0/G1/G2/G3
    name="指标名 ≥/≤ 阈值",          # 人类可读, 卡片直接展示
    threshold=0.3,                  # 判定阈值
    direction="lte",                # gte=值≥阈值过 / lte=值≤阈值过
    unit="衰减",                    # 展示单位 (可空)
    severity="blocker",             # blocker=未过卡级 / warning=仅提示
    remediation="未过时的建议动作",    # 前端行动列表直接展示
    requires="上游依赖说明",          # 可选: 依赖未就绪时报 BLOCKED 而非 FAIL
),
```

### 第 2 步：求值（`funnel_evaluator.py`）

在对应层级求值段（`_evaluate_g0_g1` / G2 parity 段 / G3 段）产出 `GateResult`：

- 数据可算：`self._mk(gate_id, value, detail)` —— 自动按 definition 的 direction/threshold 判 PASS/FAIL
- **数据算不出 → `INSUFFICIENT_DATA`**（不编数）
- **上游依赖未就绪 → `BLOCKED`** + detail 引用 requires 说明（照抄 g1_param_neighborhood 的做法）

复杂计算独立成模块（如 `parameter_neighborhood.py`、`kill_switch_probe.py`），evaluator 只做编排——纯函数好测，探针型 gate 在上游能力落地后自动翻转 PASS，评估侧零改动。

### 第 3 步：测试（`tests/unit/backtest/evaluation/`）

1. 计算模块独立单测（参照 `test_parameter_neighborhood.py`：空值/边界/PASS/FAIL 分支）
2. `test_evaluation_service.py` 的 gate id 集合断言补新 id（当前 15 条）
3. 漂移检查：若前端 E2E 断言了层级计数（如 G1 `1/4`），gate 增减后同步

### 纪律（扩展时不破坏漏斗诚实性）

| 场景 | 正确做法 | 反模式 |
|---|---|---|
| 数据不足 | INSUFFICIENT_DATA | 编 0 值凑判定 |
| 依赖未就绪 | BLOCKED + requires | 静默跳过或降级为 warning |
| 阈值不确定 | 先定初值再调，单一事实源改 | 三端各写一份阈值 |

> 调阈值更简单：只改 `gate_definitions.py` 的 `threshold` 即可，三端同步（现状为编译期常量，改后需重启 API；运行时覆盖层是预留演进方向，见 §5）。
