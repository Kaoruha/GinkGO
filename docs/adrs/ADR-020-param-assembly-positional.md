# ADR-020: 组件参数纯位置装配（移除 name-skip + 打分启发式）

**Status:** Accepted
**Date:** 2026-07-02
**Related:** 订正 ADR-005 第 18/30 行（实例化优先 kwargs、index0=name 两条已废，核心「json 序列化对称」仍成立）；ADR-010（MParam 是 ORM 层）；bug 链 #5955 → #6032 → #6159 → #6481

## Context

#6481（MeanReversion 实例化崩溃）是整条 bug 链的末端，根因是「提取器 ↔ 装配」耦合：

- **#5955**：参数提取器（`ComponentParameterExtractor`）跳过构造器首参 `name`，让 `get_component_parameter_names()` 返回 `{0:'rsi_period', ...}`（假装 index0=首个业务参数）。但 `mapping_service.create_component_parameters` **透传** CLI 给的 index 不偏移 → DB 实存 `{0:name, 1:rsi_period, ...}`。提取器与 DB 的 index 语义**错配**。
- **#6032**：为补偿错配，装配端加 `resolve_param_kwargs` 运行时**打分启发式**（两轮：直接匹配 vs 偏移 -1，按 `mapped_count`/`zero_based_bonus`/`contiguous_bonus` 择优）猜每个组合是新（0 起）还是旧（1 起）。
- **#6159**：打分漏了「DB 存了 name 但提取器跳过 → param_names 比 component_params 少一项」的边界，打第一个补丁（`len(param_names) < len(component_params)` 强制偏移）。
- **#6481**：又一条漏网边界 → 崩。

考古旧 DB 数据证明早期就是**纯位置**：`{0:'channel_breakout'(name), 1:20, 2:10, ...}` 全参从 0 连续存，`component_class(*params)` 位置 splat 装配，**从不出错**。#5955 的「跳 name」是好心办坏事——它想让 `--param '0:value'` 对齐首个业务参数（CLI 人体工学），却把同一个 index 语义写成了两份（提取器跳 vs DB 不跳），打分启发式是必然的修补税，#6481 是这条路的必然终点。

用户裁定（2026-07-02）：**不做迁移、直接清理重建、不要「index0=name」默认约定、怎么存怎么装、尽可能简单**。

## Decision

1. **提取器镜像构造函数**：3 处提取方法（`_extract_via_dynamic_import` / `_extract_via_ast_analysis_content` / `_extract_via_ast_analysis`）不再跳过 `name` → `{0:'name', 1:'rsi_period', ...}` 与构造器位置 1:1。提取器从此**只服务 API/UI 展示**，不参与装配。
2. **装配纯位置 splat**：`component_class(*component_params)`，`component_params` 已在 `_resolve_component_params` 按 `MParam.index` 排序。装配路径**不再 import/调用提取器**。
3. **契约**：DB `MParam.index` = 构造器位置参数序号（`self` 之后），从 0 连续存。index0 喂构造器首参（通常 `name`）。
4. **CLI 写入只收整数 index**：`--param 0:MyStrategy --param 1:14`，移除关键字解析路径（`--param rsi_period:14`）——该路径依赖提取器，是耦合的入口。

## Considered Options

- **装配方式**：A 纯位置 splat（**本 ADR**，斩断耦合）/ B index→name→kwargs（保留关键字 CLI 路径，但装配仍依赖提取器，耦合不除）——用户选 A，接受关键字 CLI 路径退化为整数 index-only 的成本。
- **提取器 name 处理**：镜像构造器（**本 ADR**）/ 继续跳 name（否决——重燃 bug 链）。
- **旧 DB 数据**：直接清理重建（**本 ADR**，用户裁定）/ 写迁移脚本兼容（否决——数据非均匀：1262 映射里 691 name + 571 业务值混杂、96 个 1 起、2 个 2 起，迁移启发式比打分还脆，且保留打分=保留 bug 温床）。
- **CLI 关键字路径**：移除（**本 ADR**）/ 保留（否决——保留须保留提取器调用 + 装配端 kwargs 分支，耦合存活）。

## Rationale

- **斩断耦合是根治非治标**：#6032/#6159/#6481 每个都是在前一个补丁上打补丁。根因是「同一 index 语义写两处」。纯位置 splat 让装配完全不读提取器输出 → 这类 bug **物理不可能**复现。打分启发式的三个维度（命中数/0 起始/连续性）全是在猜「DB 到底从 0 还是 1 存」——约定写一份就无需猜。
- **还原早期逻辑=回归已验证路径**：早期纯位置装配从不出错（考古旧组合数据），#5955 是偏离。本 ADR 不是新设计，是回退到被验证过的简单模型。
- **「怎么存怎么装」是最小惊讶**：DB 存 `{0,1,2}`，装配就 splat `[v0,v1,v2]`。没有隐藏的偏移、跳过、打分。漏存 index0 的值会错绑到 name（日志可见怪 name），是契约成本但**非静默**。
- **关键字 CLI 路径不值得保留**：人体工学收益（`--param rsi_period:14` 比 `--param 1:14` 易读）小于它带来的耦合税（装配端必须读提取器 + 维护 kwargs 分支 + name-skip 约定）。提取器仍可用于 API **展示**参数名（只读，不参与装配语义），展示与装配解耦。

## Consequences

- **#5955 后创建的旧组合**（提取器跳了 name、DB 业务参从 0 存）会错位实例化 → **用户已接受重建**；**禁止**加偏移兼容（会重燃打分链）。
- **纯位置 + 漏存 index0**：值错绑 name（日志怪 name，非全静默）——契约成本。
- **提取器进程内缓存**：长跑 worker 的提取器缓存（旧形状 `{0:'rsi_period'}`）存活至重启；部署 ADR-020 即 worker 重启，记入部署清单。
- **CLI 负向契约**：`--param rsi_period:14` 现报「仅支持整数 index」——回归测试 `test_bind_rejects_keyword_param` 锁定。
- **ADR-005 订正**：ADR-005 第 18 行（实例化优先 kwargs）与第 30 行（index0=name 平移规则）已被本 ADR 取代，就地加交叉引用注，不全文 supersede（ADR-005 核心「json 序列化对称」仍成立）。
- **删除**：`resolve_param_kwargs` 全函数 + 嵌套 `_score_mapping` + `#6159` 偏移块；装配路径的 `get_component_parameter_names` import + kwargs 构建块；CLI 关键字解析分支；测试 `test_component_loader_param_compat.py`（10 例）+ `test_bind_with_keyword_params`。
- **代码 ↔ 决策双向链**：提取器三处注释、装配实例化注释、CLI 解析注释均引 ADR-020。

## 判定标准自检

- ① **难逆转**：契约变更（index0=name）影响所有既有组合的装配语义 + CLI 写入面 + 提取器输出 shape + 测试套件，回退需同步改四处——满足。
- ② **反直觉**：未来见 `component_class(*component_params)` 位置 splat / `--param 0:MyStrategy`（index0 喂 name）/ 提取器返回含 name / CLI 拒关键字，会问「为何不像别的框架用 kwargs」「为何 0 是 name」——满足（需本 ADR 解释 #5955 历史）。
- ③ **真实权衡**：纯位置 vs index→name→kwargs、镜像 vs 跳 name、重建 vs 迁移、移除 vs 保留关键字路径四轴均有真实备选且做了取舍——满足。
