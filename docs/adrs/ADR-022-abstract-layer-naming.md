# ADR-022: 抽象层收敛（命名约定 + 死抽象判定）

**Status:** Accepted
**Date:** 2026-07-12
**关联 Epic:** [#6697](https://github.com/Kaoruha/GinkGO/issues/6697)（统一抽象层命名约定）
**关联子 issue:** #6689（本 ADR）、#6116、#6293、#6476、#6479

## Context

Ginkgo 抽象层长期**四套命名约定并存**，前缀与契约机制错误绑定，衍生死抽象与重复基类。实测（`src/ginkgo` 全量，2026-07-12）：

| 风格 | 形式 | 数量 | 代表 |
|---|---|---|---|
| `I*` ABC | `(ABC)` + `@abstractmethod`，nominal 契约 | 9 | `IBroker` `IEventRoutingCenter` `IDataFeeder` |
| `Base*` ABC | `(ABC)`，带共享实现 | 18 | `BaseStrategy` `BaseEngine` `BaseService` |
| `I*` + Protocol 混搭 | `class I*(Protocol)`，structural 却套 nominal 前缀 | 5 | `IStrategy(Protocol)` `IEngine(Protocol)` |
| `XxxMixin` | 后缀，实现片段复用 | 14 | `TimeMixin` `ContextMixin` |

**混乱根源**：同一个 `I*` 前缀下，`IBroker(ABC)` 是 nominal 契约、`IStrategy(Protocol)` 却是 structural 鸭子类型——前缀与子类型语义解耦，maintainer 面对一个 `I*` 类须同时回答"前缀归一"与"契约类型归一"两个正交问题。此外 `I*` 前缀是 Java/C# 遗存，PEP 8 不鼓励，Python 标准库从不用。

Epic A（#6697）的 5 个子 issue 是"抽象层收敛"同一主题的切面：#6689 命名约定、#6116 单实现 ABC、#6293 死抽象删除、#6476 多重工厂、#6479 operator 协议。本 ADR 一并裁定，作为整组重构的统一前提。

## Decision

### 原则 1 · 命名约定：四形态，删 `I*` 前缀

抽象层收敛为四种**正交**形态，各自承担明确语义，禁止 `I*` 前缀：

| 形态 | 命名 | 语义 | 例 |
|---|---|---|---|
| 带实现基类 | `Base*` | ABC，含共享实现 + 钩子，供继承复用 | `BaseStrategy` `BaseEngine` `BaseService` |
| 纯契约 | **无前缀** ABC | 仅 `@abstractmethod`，无实现，多实现者协议 | `LoadBalancer` `Broker` |
| 鸭子类型 | **无前缀** Protocol | structural，接受任何满足 shape 的对象 | `Metric` `PortfolioInfo` |
| 实现片段 | `XxxMixin` 后缀 | 多继承混入的实现片段，默认不带 ABC | `TimeMixin` `ContextMixin` |

**删 `I*` 前缀**。迁移示例：`IBroker`→`Broker`、`ILoadBalancer`→`LoadBalancer`、`IEventRoutingCenter`/`ICircuitBreaker`（单实现，见原则 2）→降级具体类、`IStrategy(Protocol)`→重新定性（并入 `BaseStrategy` 或留作去前缀 Protocol）。

根 `Base`（无前缀、带实现，如 `class Signal(TimeMixin, Base)`）是 `Base*` 家族的本体根，全仓唯一，不与"无前缀=纯契约"冲突。

### 原则 2 · 抽象存活门槛：≥2 实现者或扩展契约

抽象必须满足下列任一条件，否则删除：

- **≥2 个真实实现者**（`grep "class.*("` 全仓排除自身后有继承）；或
- **明确的第三方扩展契约**（文档化的用户扩展点，如 `LoadBalancer` 的多实现族预期）。

**判定法 · pass-through 测试**（可机械化，AST 检查类体）：类体仅剩 `super().__init__` / `__repr__` / 转发调用 = 死抽象，删。

应用：
- `core/interfaces/engine_interface.py`（388 行，Matrix/Hybrid/AUTO 四 mode 零真实继承）→ 删
- `BacktestBase`（类体空壳，ID/name/引擎绑定全移 Mixin）→ 删
- gateway 单实现 ABC（`IEventRoutingCenter`/`ICircuitBreaker` 各 1 实现）→ 降级为具体类（解锁 #6116）

### 原则 3 · 单一接缝：同类操作一个权威入口

每类操作（组件创建、运算求值、信号发射等）只能有**一个权威接缝**。平行抽象层 = 认知负担 + 漂移温床，禁止。

`# Upstream:` docstring 标注必须指向**真实创建者**；漂移（指向死层）视为缺陷。

应用：
- 组件创建唯一 `ComponentLoader.perform_component_binding`（#6476），删三死层 `ComponentFactoryService` / `core/factories/` / `AnalyzerRegistry`
- 算术运算双实现（`BinaryOpNode` if/elif 链 vs registry `add_operator`）收敛为单一实现
- 信号发射已先行：ADR-011 / ADR-019 的 `publish_price_update()` 是单一接缝范例

### 原则 4 · 注册冲突检测：默认拒绝同名

注册表（`@register_operator`、`@register` 类装饰器等）**默认拒绝同名注册**，重复 raise；需 override 时显式标记（如 `override=True`），**禁止静默覆盖**。

根因（#6479）：`Rank` 截面版静默覆盖滚动版 → 滚动版变死代码，`rank(close,5)` 双参失效且无报错。静默覆盖比"没实现"更危险——代码看似在、实际不可达。

通用原则，不止 operator。呼应 CLAUDE.md「失败必须响亮，禁止 `return`+stub 静默兜底」。

### 原则 5 · 模板集中化：重复 ≥3 次抽公共层

重复出现 ≥3 次（rule of three）的模板代码必须抽公共层（装饰器 / 基类 / helper），禁止逐字重抄。共享逻辑应在基类或装饰器，不散落各实现体。

应用（#6479）：
- 异常兜底 `try/except+GLOG.ERROR+return nan`（~74×）→ 抽 `@with_error_handling` 装饰器或 `BaseOperator`
- 窗口提取 `int(window.iloc[0]) if len(window)>0 else default`（41×）→ 抽 `_extract_window` helper

## Rationale

**为什么删 `I*`、留 `Base*` + 无前缀**：
1. **PEP 8 不鼓励装饰前缀**，标准库 `Sequence`/`IOBase`/`Protocol` 均无 `I` 前缀；`I*` 是 Java/C# 心智模型的误植。
2. **`I*` 必然撒谎**：ABC 常从纯契约演化为带实现，一旦 `I*` 带实现，前缀承诺（纯接口）即失真。`Base*` 从不承诺"纯契约"，既可纯抽象也可带实现，永远诚实。
3. **纯契约用无前缀**：纯接口 ABC 套 `Base*` 同样撒谎（`Base` 暗示有实现），故纯契约用无前缀，与带实现的 `Base*` 区分。
4. **量化库插槽本质 nominal**：Strategy/Selector/Risk 是框架插槽，用户显式继承才享基类逻辑 + `@abstractmethod` 强制实现。`@abstractmethod cal()` 是安全网——漏实现实例化即 TypeError，而非静默空跑（量化里"静默空跑"=亏钱）。Protocol 的鸭子类型在此场景几乎用不上。
5. **Protocol 留作例外**：仅用于真鸭子边界（`Metric`、`PortfolioInfo`），不强求第三方继承。

**为什么抽象需 ≥2 实现者**：抽象的成本是认知负担 + 间接层。单实现 ABC 是"假接缝"（YAGNI），pass-through 空壳是纯负担。门槛可机械化判定（grep 实现者 + AST 类体检查），不靠拍脑袋。

**为什么单一接缝**：多接缝 = 控制流分叉 = 多个并行"真相源"。#6476 的 docstring 指向 `ComponentFactoryService`、实际走 `ComponentLoader`，就是两套真相打架。单一接缝让"改一处即全局生效"。

**为什么注册必须冲突检测**：静默覆盖把可达代码变死代码，且无任何报错——比"没实现"更危险，因为它伪装成"已实现"。与 #4652 的 stub 教训同源。

**为什么模板 ≥3 次抽公共层**：复杂度外溢——74 个 operator 各抄异常模板，改兜底逻辑须改 74 处。集中化让实现体只表达"算什么"，不重抄"怎么兜底"。

## Consequences

**解锁执行**：
- **#6116**：gateway 单实现 ABC 降级为具体类（原则 2），保留 `LoadBalancer`（多实现族）
- **#6293**：删 `engine_interface.py` + `BacktestBase`（原则 2），原继承者直继承真实基类 + Mixin
- **#6476**：删三死工厂层，`ComponentLoader` 文档化为单一接缝，订正 10 处 docstring 漂移，修 `risk_managements` 复数 bug（原则 3）
- **#6479**：operator 协议层（原则 5）+ 注册冲突检测（原则 4）+ 算术运算单一化（原则 3）

**迁移影响**：
- 9 个 `I*` ABC 改名（`IBroker`→`Broker` 等）+ 全仓 import 同步
- 5 个 `I*Protocol` 重新定性（真鸭子保留去前缀 / 并入 `Base*`）
- 删除清单：`engine_interface.py`、`BacktestBase`、`ComponentFactoryService`、`core/factories/`、`AnalyzerRegistry`

**不在本 ADR 裁定**：
- #6479 因子引擎的求值解耦方案（`BinaryOpNode` 委托 registry vs 独立 visitor）属 expression 引擎专项架构，待 #6479 落地时另立 ADR
- `interfaces/` 目录的杂物归位（dtos/kafka_topics）属模块边界，随各子 issue 处理

**防回潮机制**：原则 2 的 pass-through 测试与原则 4 的注册冲突检测可沉淀为 CI 检查（死抽象扫描 + 注册冲突单元测试），防止死抽象与静默覆盖回潮。
