# ADR-013: Debug 模式改变 @retry 退避语义

**Status:** Accepted
**Date:** 2026-06-19

## Context

`@retry` 装饰器（`src/ginkgo/libs/utils/common.py`，经 `from ginkgo.libs import retry` 暴露）的重试退避策略**依赖全局 debug 开关 `GCONF.DEBUGMODE`**：

```python
if GCONF.DEBUGMODE:
    # Debug模式：跳过等待，立即重试
else:
    base_sleep = 30  # 基础等待时间30秒
    sleep_time = int(base_sleep * (actual_backoff_factor ** i))
```

- 正常模式：失败后 `30s × backoff_factor^i` 指数退避，最多 `max_try` 次。
- Debug 模式：**跳过全部等待，立即连续重试**。

这与 CLAUDE.md 的 debug 用途产生张力：数据库操作要求 debug ON（连 test 实例避污染，见 ADR-004）。但 `ginkgo_tushare.py` 的批量同步用 `@retry(max_try=11)`（:235）等高频远端调用——debug ON 下遇瞬时限流会**立即重试 5~11 次**，正是触发 tushare 远端封禁的行为模式。

单股单次同步（≤3yr = 1 次 API）retry 不触发，安全；批量同步（多股 × 多年）在 debug ON 下有封禁风险。

## Decision

1. **保留 debug 跳过退避的语义**（不改装饰器）：debug 模式本为加速测试反馈，退避会让单测/集成测试卡 `30s × N`。
2. **纪律约束（非代码强制）**：批量同步 tushare 等远端 API 前**关 debug**（或加显式 token-bucket 限流），禁止在 debug ON 下跑大批量同步。
3. 单股同步不受影响，无需特殊处理。

## Rationale

- **为何保留语义不改装饰器**：`@retry` 被 ~160 处使用（实测 `src/ginkgo` 下 163 处装饰器应用，覆盖 `tick_service`/`ginkgo_kafka`/`stockinfo`/`param`/`adjustfactor`/`tushare` 及各 driver/crud …），改 debug 分支牵动全系统；且 debug 下跳过退避是刻意的测试加速设计。
- **为何用纪律而非代码强制**：debug 是开发者手动开关（`ginkgo debug on`），批量同步也是手动操作；在装饰器层探测"是否批量远端调用"会引入运行时判断复杂度，得不偿失。
- **已排除 A：debug 下也退避**——单测/集成测试会卡 `30s × N`，破坏 debug 加速反馈的初衷。
- **已排除 B：装饰器加"远端 API 识别"自动限流**——跨切面耦合（装饰器要知道被调函数是否打远端），违背单一职责。

## Consequences

- **难逆转**：debug 改变 retry 语义是隐式跨系统耦合，~160 调用点依赖现状。
- **反直觉**：一个"调试开关"（debug）竟影响生产 API 封禁风险——本 ADR 即该反直觉行为的锚点，防未来把"debug 跳过退避"当 bug 误改。
- **验证方式**：批量同步遇瞬时限流时，debug ON 会让 `@retry` 立即重试 5~11 次加剧封禁——批量前关 debug 或加显式 token-bucket 限流；单股单次同步 retry 不触发，安全。
- **交叉引用**：ADR-004（Docker 双实例与 Debug 模式——debug 连 test DB 的用途）；本决策的 debug 即 ADR-004 的同一个 `GCONF.DEBUGMODE`。

## 判定标准自检

- ① **难逆转**：~160 调用点依赖现状——满足。
- ② **反直觉**：debug 开关有生产封禁副作用——满足。
- ③ **真实权衡**：debug 跳过退避（测试快）vs 退避（保护远端）——满足。
