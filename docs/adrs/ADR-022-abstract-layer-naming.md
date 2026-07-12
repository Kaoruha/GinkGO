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
| `I*` + Protocol 混搭 | `class I*(Protocol)`，structural 却套 nominal 前缀 | 4 | `IStrategy(Protocol)` `IEngine(Protocol)` `IPortfolio(Protocol)` `IRiskManagement(Protocol)` |
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

**删 `I*` 前缀**。迁移示例：`IBroker`→`Broker`(async) / `SyncBroker`(sync)（同名双胞胎执行模型不同，分开设名，见原则 6）、`ILoadBalancer`→`LoadBalancer`、`IEventRoutingCenter`/`ICircuitBreaker`（单实现，见原则 2）→降级具体类、`IStrategy(Protocol)`→重新定性（并入 `BaseStrategy` 或留作去前缀 Protocol）。

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

### 原则 6 · 命名空间唯一性：类短名全局唯一

类短名（去模块前缀）**全局唯一**。禁止两种漂移，二者皆为认知负担 + `isinstance` 误判温床：

- **同名双胞胎**：两个不同模块定义同名类。`isinstance(x, BaseEngine)` 在两棵继承树间静默错判——`trade_gateway.py:62` 的 isinstance 用 `bases/` 版 `BaseBroker`，`ManualBroker`（`brokers/` 版子类）实例静默失败类型检查。
- **同义不同名**：同一概念多种命名。ML 策略基类 `BaseMLStrategy`/`MLStrategyBase`/`StrategyMLBase` 三变体分布 core/quant_ml/trading，维护者须记忆"三者等价"。

`as` 别名是**债务信号**而非消歧手段：出现 `from X import Y as Z` 消歧同名类，说明命名空间冲突，应消除冲突源（合并/改名），而非用别名掩盖。

**判定法**：
- 同名双胞胎：`grep -rn "^class <ShortName>" src/` 命中 >1 处 = 违反（可机械化，可沉淀为 CI 检查）。
- 同义不同名：人工判定概念等价（相同 Upstream 角色 + 相同继承契约）。

**收敛矩阵（6 项，2026-07-12 实测）**：

*A. 同名双胞胎（4 项，消除其一）*：

| 短名 | 定义点①（弱） | 定义点②（权威） | 收敛 |
|---|---|---|---|
| `BaseEngine` | `core/interfaces/engine_interface.py:37`（死 388 行·0 继承） | `trading/engines/base_engine.py:21`（8 继承者 + isinstance） | 删①留② |
| `BaseStrategy` | `core/interfaces/strategy_interface.py:26`（0 真策略继承） | `trading/strategies/strategy_base.py:21`（14 继承者） | 删①留② |
| `BaseBroker` | `trading/bases/base_broker.py:28`（Mixin 根·行情/持仓缓存） | `trading/brokers/base_broker.py:106`（订单/账户状态机） | ①降为 `BrokerCacheMixin`，②为唯一 `BaseBroker` 组合根 |
| `IBroker` | `trading/interfaces/broker_interface.py:128`（sync·回测/模拟） | `trading/brokers/interfaces.py:281`（async·实盘） | **不合**（async/sync 执行模型本质不同）：async 版去前缀为 `Broker(ABC)`（权威契约），sync 版去前缀为 `SyncBroker(ABC)`（不同名消歧） |

*B. 同义不同名（2 项，统一命名）*：

| 概念 | 变体 | 权威 | 收敛 |
|---|---|---|---|
| 组合基类 | `BasePortfolio`(core) vs `PortfolioBase`(trading·45 引用) | `PortfolioBase` | 删 core 版（随 core 下架） |
| ML 策略基类 | `BaseMLStrategy`(core) / `MLStrategyBase`(quant_ml) / `StrategyMLBase`(trading) | 单一权威 | 三变体统一为单一类名，归 `trading/strategies/ml_strategy_base.py` |

**消除同名双胞胎 ≠ 消除职责分工**：两个 `BaseBroker` 职责正交（行情缓存 vs 订单状态机），收敛方式是把弱侧降为 Mixin、强侧保留为组合根，而非揉成上帝对象。**类名唯一是约束，职责单一是设计**。

### core/ 整层下架（原则 6 的系统级应用）

`core/interfaces/` 自述"跨领域契约层"，但设计已双重失效，整层下架：

1. **反向依赖实现层**：`core/interfaces/portfolio_interface.py:19-22` import 了 trading 的 `BaseAnalyzer`/`BaseSizer`/`BaseSelector`/`BaseRiskManagement`——契约层依赖实现层，依赖方向倒挂，core 不再是"底层"。
2. **被同名架空**：core 定义的 `BaseEngine`/`BaseStrategy` 契约，trading 重新定义同名实现版（带 Mixin + ID 管理）、未继承 core 契约——core 契约对 trading 完全失效。
3. **唯一活契约归域**：`BaseModel`（36 继承者，服务 quant_ml 的 lightgbm/xgboost/sklearn ML 模型层）是 core 唯一活契约，但其领域归属是 ML 而非"核心"——移入 `quant_ml/models/base_model.py`，纠正"万物皆核心"的过度泛化。

**收敛后文件结构（核心目录 before → after）**：

```
【删除】core/interfaces/{engine,strategy,portfolio}_interface.py   ← 被 trading 同名架空
【删除】core/interfaces/__init__.py + core/interfaces/ 目录         ← 整层下架
【删除】core/adapters/（4 文件）                                    ← core 契约胶水层，契约没了胶水无用
【删除】core/factories/                                             ← #6476 死工厂层
【移动】core/interfaces/model_interface.py → quant_ml/models/base_model.py
        （BaseModel 归 ML 域；删死子类 BaseTimeSeriesModel/BaseEnsembleModel）
【改名】trading/bases/base_broker.py → trading/bases/broker_cache_mixin.py
        （BaseBroker 弱侧降为 BrokerCacheMixin）
【改名】trading/brokers/interfaces.py: `IBroker`→`Broker(ABC)`       ← async 版去前缀（权威契约，不合）
【改名】trading/interfaces/broker_interface.py: `IBroker`→`SyncBroker(ABC)`  ← sync 版去前缀，不同名消歧（async/sync 执行模型不同）
【保留】trading/brokers/base_broker.py                              ← 唯一 BaseBroker 组合根
```

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

**为什么命名空间唯一**：同名双胞胎让 `isinstance` 在两棵继承树间静默错判（`ManualBroker` 通过不了 `bases/BaseBroker` 的类型检查），且 IDE 跳转 / import 自动补全产生歧义；同义不同名让"同一概念"在 codebase 里不可 grep——查 ML 策略基类须同时搜三个名字。两者都打断了"维护者心智模型与代码结构"的对应。`core/` 下架是本原则的系统级推论：core 契约层已被 trading 同名架空 + 反向依赖 trading，存续只会制造"哪个 BaseEngine 是真的"的永久歧义；唯一活契约 `BaseModel` 归域（ML）后，core 失去存续理由。

## Consequences

**解锁执行**：
- **#6116**：gateway 单实现 ABC 降级为具体类（原则 2），保留 `LoadBalancer`（多实现族）
- **#6293**：删 `engine_interface.py` + `BacktestBase`（原则 2），原继承者直继承真实基类 + Mixin；**原则 6 扩展范围**：按通则收敛全部 6 个双胞胎/变体（见收敛矩阵）+ `core/` 整层下架 + Broker 契约分开设名（async/sync 不合）
- **#6476**：删三死工厂层，`ComponentLoader` 文档化为单一接缝，订正 10 处 docstring 漂移，修 `risk_managements` 复数 bug（原则 3）；**原则 6 连带**：`core/adapters/`（契约胶水层）随 core 下架一并删除
- **#6479**：operator 协议层（原则 5）+ 注册冲突检测（原则 4）+ 算术运算单一化（原则 3）

**迁移影响**：
- 9 个 `I*` ABC 改名 + 全仓 import 同步（`IBroker` 同名双胞胎因 async/sync 执行模型不同，分开设名：async→`Broker` / sync→`SyncBroker`，见原则 6）
- 4 个 `I*Protocol` 重新定性（真鸭子保留去前缀 / 并入 `Base*`）
- **原则 6 同名双胞胎收敛**：4 项同名双胞胎消除同名——前 3 项（`BaseEngine`/`BaseStrategy`/`BaseBroker`）删弱侧；`IBroker` 因两侧都活且 async/sync 执行模型不同，**双活改名**（async→`Broker` / sync→`SyncBroker`）+ 2 项同义不同名（`PortfolioBase`/ML 策略三变体）统一命名
- **core/ 整层下架**：删 `core/interfaces/`（除 model_interface）+ `core/adapters/` + `core/factories/`；`BaseModel` 移入 `quant_ml/models/`
- **Broker 契约分开设名（async/sync 不合）**：async `IBroker`→`Broker(ABC)`（权威契约）+ sync `IBroker`→`SyncBroker(ABC)`（消歧）+ `base_broker.py`（唯一组合根，#6715）+ `broker_cache_mixin.py`（原 bases/ 弱侧降级）
- 删除清单：`core/interfaces/{engine,strategy,portfolio}_interface.py`、`core/interfaces/__init__.py`、`core/adapters/`、`core/factories/`、`engine_interface.py`、`BacktestBase`、`ComponentFactoryService`、`AnalyzerRegistry`（`trading/brokers/interfaces.py` 与 `trading/interfaces/broker_interface.py` 改类名不删，async/sync 分开设名）

**不在本 ADR 裁定**：
- #6479 因子引擎的求值解耦方案（`BinaryOpNode` 委托 registry vs 独立 visitor）属 expression 引擎专项架构，待 #6479 落地时另立 ADR
- `interfaces/` 目录的杂物归位（dtos/kafka_topics）属模块边界，随各子 issue 处理

**防回潮机制**：原则 2 的 pass-through 测试与原则 4 的注册冲突检测可沉淀为 CI 检查（死抽象扫描 + 注册冲突单元测试），防止死抽象与静默覆盖回潮。
