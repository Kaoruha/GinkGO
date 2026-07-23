# ADR-025: DTO 信使角色全面复位（Mapper 家族覆盖四边界）

**Status:** Accepted
**Date:** 2026-07-24
**关联:** ADR-010（三层角色分离，本文档推广其 Mapper 概念）· ADR-022（原则3 单一接缝 / 原则4 注册冲突检测）· `CONTEXT.md`（DTO / Mapper 术语）· Epic「DTO 信使复位」（本文档 + 后续四步 PR 序列）

## Context

ADR-010 把 **DTO** 定位为"跨边界、**隔离两个不耦合世界**的信使"，三亚型 `BusDTO`(Kafka) / `WebResponse`(HTTP) / `CacheEntry`(Redis)；并把 **Mapper** 定为"唯一转换点、独立于 CRUD"。但实测（2026-07-24，`src/ginkgo` 全量）落实程度仅 **1.5 / 4**：

| 边界 | ADR-010 期望 | 现状 |
|---|---|---|
| Kafka 出站 | 信使封装 wire 载荷 | ✅ 10 个 BusDTO 定义载荷，producer `model_dump` 序列化（`node.py:1072`） |
| Kafka 入站 | wire→DTO→Entity | ❌ **15/16 consumer 手抓 dict 重组 Event**，全 livecore/workers 仅 `portfolio_processor.py:499` 一处 `ControlCommandDTO(**data)` |
| HTTP 响应 | WebResponse | ❌ `api/` **0 个 `response_model`**，无统一响应 schema 层（仅 `backtest_task_schemas.py` 孤例） |
| Redis | CacheEntry | ❌ 通用 `redis_crud` 全程 `json.dumps/loads` 任意 dict；`CacheEntry` 仅 `data/streaming/cache/cache_manager.py:68` 局部用 |

**后果不止整洁**：DTO 从"信使"退化为"**出站发货单**"——只定义发什么，收货侧不认单子、直接拆裸 dict。drift 藏在缝里：`OrderFeedback` consumer 用 `filled_volume`/`fill_price`（错）而非 `filled_quantity`/`fill_price` 构造 `EventOrderPartiallyFilled` → `TypeError`（缺必需的 `order: Order`）→ 被 `node.py:932` `except` 静默吞，**整条 fill-feedback 路径从未跑通**。HTTP 无契约保护前端，Redis 无类型安全。

**根因**：ADR-010 §1 把 Mapper 定为唯一转换点，但只建了 **DB 边界 + Kafka 出站**。Mapper 概念未对称覆盖四边。

## Decision

### 原则 1 · Mapper 家族覆盖四边界（推广 ADR-010 §1）

每边一个亚型，都遵循"唯一转换点 + 独立于 CRUD"：

| 边界 | Mapper 亚型 | 转换 | 现状→目标 |
|---|---|---|---|
| DB | `XxxMapper`（ADR-010 已立） | ORM↔Entity↔DTO | §4 V1/V3/V9 收尾 |
| Kafka | `MessageMapper` | wire↔BusDTO↔Event | 出站✓ / 入站补全 |
| HTTP | `ResponseMapper` | Entity/ORM↔WebResponse | 从无到有 + `response_model` |
| Redis | `CacheMapper` | wire↔CacheEntry↔Entity | 从无到有，替 `json.dumps` 任意 dict |

`MessageMapper`/`ResponseMapper`/`CacheMapper` **不是新抽象层**，是 ADR-010 Mapper 概念在各自边界的实例——符合 ADR-022 原则 3（单一接缝：每边界一个权威转换点）。其中 `MessageMapper` 因带 wire 依赖（kafka-python）与纯类型转换的 `XxxMapper` 异质，承认 Mapper 家族含**纯转换 / IO 转换**两亚型，不硬塞纯转换家族。

### 原则 2 · 严格模式（呼应 CLAUDE.md「失败必须响亮」+ ADR-022 原则 4）

绕过 DTO / 手抓 dict 的旧路径不复保留为 deprecated 双轨：

- **注册期校验**：Mapper 注册 `(DTO, Event)` 对时校验字段对齐，drift（`symbol` vs `code`、`filled_volume` vs `filled_quantity`）**启动即报错**，非运行时静默。
- **运行时响亮失败**：未经 Mapper 的裸 dict 重组 / 裸 `json.dumps` 缓存写入 / 未声明 `response_model` 的端点，启动期或调用期失败，禁 `except` 吞 + `return` stub 兜底（#4652 同源教训）。
- **不取柔性双轨**：柔性（deprecated 并存）留 drift 漏洞，而 drift 正是本复位驱动力——留漏洞等于没解决。

### 原则 3 · 分阶段 PR 序列（非单 PR）

共享 Mapper 抽象，按边界拆，每 PR 独立可验证：

1. 本文档（ADR + `CONTEXT.md`）
2. Kafka 入站 `MessageMapper`（`OrderFeedback` drift 是活 bug，打头）
3. HTTP `ResponseMapper`
4. Redis `CacheMapper`
5. DB Mapper 收尾（ADR-010 §4 V1/V3/V9）

## Rationale

- **为何全面复位而非局部补 Kafka 入站**：DTO 角色落实 1.5/4，局部补只到 2.5/4，HTTP/Redis 空白仍在，drift 类风险（契约/类型不匹配）在另两边同样潜伏。半截复位让"信使"定义与实现长期背离，维护者须记"哪边认 DTO 哪边不认"——认知负担比全空更高。
- **为何严格而非柔性**：柔性留 drift 漏洞，而 drift 正是 `OrderFeedback` 死路径根因——留漏洞等于保留 bug 温床。严格模式把 drift 从"运行时静默"提前到"启动响亮"，一次性消灭。代价是迁移期痛，但分 PR 序列可承受。
- **为何复用 Mapper 家族而非新抽象（如独立 Codec 层）**：ADR-010 §1 Mapper 已是"唯一转换点"，推广到四边是概念的自然完备，非新增层。新建 Codec 会与 Mapper 形成"两个转换真相源"（ADR-022 原则 3 禁）。
- **三条全中**：① 难逆转（四边契约一旦立，回退即重新引入 drift）② 反直觉（1.5/4 还能跑？靠出站严格 + 入站手抓 + 动态语言容忍 + 前端配合凑合，代价是死路径与脆弱契约）③ 真实取舍（严格 vs 柔性 / 复用 Mapper vs 新抽象 / 单 PR vs 序列）。

## Consequences

- **五步 PR 序列**见原则 3。每步验收：对应边界 drift 在注册期被拦截 + 旧手抓/裸路径清零。
- **迁移影响**：③ HTTP 改 `response_model` 影响前端契约（web-ui `request.ts` 已 unwrap 一层，response 结构变更须同步前端）；④ Redis 改 `CacheEntry` 影响所有缓存读写（需迁移既有 json dict 缓存键）。
- **严格模式迁移期**：每边 PR 须把该边所有手抓/裸路径一次性改对，否则启动报错阻断。每边 PR 配该边全量冒烟（启动 + 关键路径）。
- **删除测试**：删 Mapper 家族任一亚型，该边复杂度（drift 风险 + 手抓重组 + 契约脆弱）回散至 N 调用方 = 在发挥作用，非 pass-through。
- **`CONTEXT.md` 同步**：新增 Mapper 词条（唯一转换点、覆盖四边、纯/IO 亚型）、强化 DTO 词条（信使双侧性，禁单侧）。
