# ADR-019: Feeder 价格发布统一 Seam（publish_price_update）

**Status:** Accepted
**Date:** 2026-06-29
**Related:** ADR-011（信号发射 seam，同族"统一入口藏跨切关注点"）、ADR-010（EventPriceUpdate 是 Entity）、ADR-001（组件单向流，feeder→engine 出方向不变）；候选源自 `/improve-codebase-architecture` 评审 + 拷问；TDD Planning 阶段读源码后两处订正（见 Rationale/Consequences）

## Context

EventPriceUpdate（价格事件 Entity）的**发布**散落在 6 个 feeder 文件的 **7 个 emit 点**，每个 feeder 各自手搓 publish，三个跨切关注点静默漂移。经 grep/Read 核实（master base，行号实测）：

7 个 emit 点（EventPriceUpdate 构造 + 发布）：

- `live_feeder.py:574` 构造 → `:582-584` 发布
- `okx_data_feeder.py:631`（bar）/ `:715`（tick）构造 → `:636`/`:720` 经 `_publish_event(:727)`
- `eastmoney_feeder.py:176` → `:184-186`；`alpaca_feeder.py:177` → `:189-191`；`fushu_feeder.py:213` → `:225-227`（三者继承 LiveDataFeeder）
- `backtest_feeder.py:263` 构造 → `:162-163` 发布

三个跨切关注点漂移：

| 关注点 | live 系（live/eastmoney/alpaca/fushu） | okx_data | backtest |
|---|---|---|---|
| 发布通道 | `self.event_publisher`（公开，live:201，override set:321-323） | `self._event_publisher`（私有，:86，set:205-212）+ `_publish_event`(:727) | `self.event_publisher`(:60) + **`self.put=publisher` 桥接绕过**（set:115-119） |
| 统计 | `stats['events_published']`（live:224 init，:584 inc；三子类继承） | **无** | **无** |
| 错误契约 | 无 try/except，上抛（fail-fast） | try/except **吞**（:727-738） | 无（engine.put 入队，基本不抛） |

**已建半个 seam owner**：`EngineBindableMixin.publish_event`（engine_bindable_mixin.py:61-75）已被 TradeGateway 等使用，但 feeder 没统一接——`BacktestFeeder` 虽继承它，却用 `self.put=publisher`（:119）桥接绕过；live 系/okx 完全用自己的字段。

**冗余第二份**：`BaseFeeder`（base_feeder.py）自带完整 `_engine_put`(:29)/`put`(:44-51)/`set_event_publisher`(:38-42)，与 `EngineBindableMixin` 字段/方法**全冗余**。`put` 仅被 backtest 的桥接（:119）引用（grep `self.put` 全 feeder 唯一命中）。

**继承拓扑（TDD Planning 核实）**：feeder 两根——`BaseFeeder(TimeMixin,NamedMixin,Base)` ← Backtest/OKXMarket；`LiveDataFeeder(ILiveDataFeeder)` ← Alpaca/EastMoney/FuShu；OKXData 独立。`LiveDataFeeder.__init__`(live_feeder.py:183) grep 无 `super().__init__()` → 装 mixin 后 mixin.`__init__` 不触发，须补 super 协 MRO。

**None-guard 隐藏依赖（TDD Planning 发现，订正原锚点）**：`publish_event` None-guard 走 `hasattr(self,'log')` 分支（engine_bindable_mixin.py:70）——有 log→:71 `GLOG.ERROR`，无 log→:73 `GLOG.INFO`。6 个 feeder **全无 log 属性**（grep 空）→ 当前 None-binding 落 INFO 非 ERROR。原 ADR 草拟"@68 loud ERROR"锚点错（:68 是 if 行，:71 才 ERROR，且依赖 log）。

**删除测试**：删 `publish_price_update` → 7 emit 点在「通道/统计/错误契约」三关注点上重新分裂 → 复杂度重现 → 物有所值（非透传）。

判定三条全中（难逆转/反直觉/真实取舍），立本 ADR。

## Decision

把 feeder 价格发布深化为**统一 seam `publish_price_update(event)`**——单一入口（`FeederPublishMixin` 拥有），背后藏三件事，7 emit 点只见业务 event：

1. **发布通道** → `self.publish_event(event)`（经 EngineBindableMixin；`FeederPublishMixin.__init__` 设 `self.log=GLOG`，使 `_engine_put is None` 时走 engine_bindable_mixin.py:71 loud `GLOG.ERROR`——**订正**：feeder 原无 log 属性会落 :73 INFO，加 log 让 ERROR 生效）
2. **统计** → 成功 `stats['events_published'] += 1`；失败 `stats['publish_errors'] += 1`（**新增**，关掉今天无人统计 publish 失败的静默缺口）
3. **错误契约（E1）** → `try/except` 包 `publish_event`；runtime 抛 → `publish_errors += 1` + `GLOG.ERROR`（韧性地不杀 WS 流）；`_engine_put is None` → 走 `publish_event` loud ERROR（`self.log` 已设），不计 `events_published`

### Wrapper 宿主：FeederPublishMixin（用户裁定：抽 mixin 消重复）

新建 `FeederPublishMixin`（`src/ginkgo/trading/feeders/mixins/feeder_publish_mixin.py`），单一实现：`publish_price_update(event)` + `__init__` 设 `stats={'events_published':0,'publish_errors':0}` + `self.log=GLOG`。`BaseFeeder`/`LiveDataFeeder`/`OKXDataFeeder` 三根均装 `EngineBindableMixin` + `FeederPublishMixin`，6 feeder 经继承自动获 wrapper。**订正原 Rationale「不抽共享 mixin」**——用户裁定：消除 3 份样板重复 + stats/log 语义集中 > 强耦合顾虑。

### Home（归属）：EngineBindableMixin

- 三根装 `EngineBindableMixin`：`BaseFeeder`（Fork B 顺带）、`LiveDataFeeder`（**补 live_feeder.py:183 `__init__` 缺失的 `super().__init__()` 协 MRO 链**）、`OKXDataFeeder`
- `BacktestFeeder` 已有 EngineBindableMixin，停止 `set_event_publisher`(:115-119) 双桥接（删 `self.put=publisher` 与自有 `event_publisher` 字段:60），emit `:162-163` 改调 `publish_price_update`
- 删各 feeder 自有字段/override：live `event_publisher`(:201)/override(:321-323)、okx `_event_publisher`(:86)/`_publish_event`(:727-738)/set(:205-212)

### Fork B（清 BaseFeeder）

`BaseFeeder` 装 `EngineBindableMixin`+`FeederPublishMixin`，删冗余 `_engine_put`(:29)/`put`(:44-51)/`set_event_publisher`(:38-42)。用户裁定 `BaseFeeder`（交易层）不在 CLAUDE.md「勿触 Base（BaseCRUD/BaseService）」保护集。

## Considered Options

- **Home（归属）**：Home1 采用 EngineBindableMixin（**本 ADR**，复用已有半个 seam owner）/ Home2 feeder 层独立 publish trait（否决——重复造轮，两份 seam owner 更乱）
- **Wrapper 宿主**：3 处重复定义（循 ADR-011「不抽 mixin」，否决——3 份~8行样板 + stats 散）/ **抽 FeederPublishMixin 两根都装（本 ADR，用户裁定）** / 模块级纯函数（否决——stats 挂实例带 self 参数怪）
- **Seam 形态**：S1 每 feeder 内联整理（否决——漂移原样存活）/ S3 统一 `publish_price_update` wrapper（**本 ADR**，7 emit 点一处契约）
- **错误契约**：E1 韧性+可观测（**本 ADR**）/ E2 fail-fast 上抛（否决——WS 高频流单 tick 抛出可能杀接收循环；接线 bug 由 None-guard loud ERROR 兜住已可见）
- **None-binding 级别**：接受 INFO 订正 ADR（否决——配置 bug 仅 INFO 生产易淹）/ **feeder 加 self.log 让 :71 ERROR 生效（本 ADR，用户裁定）** / 改 publish_event 去 log 依赖（否决——影响所有 EngineBindableMixin 用户，面太大）
- **BaseFeeder**：清冗余（**本 ADR**）/ 留（否决——两份 seam owner 字段全冗余，BacktestFeeder 迁移后 `put` 零引用）

## Rationale

- **两个 publish 方法分化非混淆**：`publish_event`（EngineBindableMixin，引擎层原语，通吃 selector/sizer/gateway）vs `publish_price_update`（feeder 层领域 wrapper，多 own 统计+错误契约+log）。前者是「怎么投递」，后者是「feeder 该对一次报价发布负责什么」——同 ADR-011「两份 create_signal 同结构不同关注点」的分化。
- **抽 FeederPublishMixin 而非 3 处重复（用户裁定，订正原「不抽」判断）**：feeder 继承链两根。原拟循 ADR-011「不抽 mixin」走 3 处重复，但用户裁定抽 FeederPublishMixin：6 feeder 经继承自动获 wrapper，消除 3 份样板，stats/log 初始化语义集中一处。两根本就要装 EngineBindableMixin，多装一个自包含的 publish mixin（只持 publish 行为+stats 计数+log 标记，无外部状态耦合）增量耦合可控——**偏离 ADR-011 在此值得**：ADR-011 那边 config mixin 牵动 worker 内部状态主体耦合重；本 mixin 自包含，性质不同。
- **E1 三层分明**：`_engine_put is None`（接线/配置 bug）→ loud ERROR（可见，因 self.log 已设）；runtime 抛（传输/接收 bug）→ `publish_errors`+ERROR（可观测但不杀流）；成功 → `events_published`+1。契合项目传输错误哲学（`GinkgoProducer.send` 返 bool 非 raise）。
- **BacktestFeeder 桥接删除是免费深化**：它已持 EngineBindableMixin 却用 `self.put=publisher`+自有 `event_publisher` 双桥接（装了门又爬窗）。删桥接让它与其余 feeder 走同一条 `publish_price_update`——局部性回收。
- **BacktestFeeder `put` 桥接的唯一引用是它自己**（:119）：grep `self.put` 全 feeder 仅 backtest:119 一处赋值，删 BaseFeeder.put 不破其他调用方。

## Consequences

- **新建**：`src/ginkgo/trading/feeders/mixins/feeder_publish_mixin.py`（`FeederPublishMixin`：`publish_price_update` + stats init + `self.log=GLOG`）。
- **删**：live `event_publisher` 字段(:201)+override(:321-323)；okx `_event_publisher`(:86)+`_publish_event`(:727-738)+set override(:205-212)；backtest `event_publisher`(:60)+set override 双桥接(:115-119)；BaseFeeder `_engine_put`(:29)/`put`(:44-51)/`set_event_publisher`(:38-42)；7 emit 点的内联 publish 样板。
- **行为变更（难逆转）**：7 emit 点统一经 `publish_price_update`；新增 `publish_errors` 统计；okx 的「吞」语义扩散为全 feeder 默认（runtime 抛→计数+log 非杀流）；live 系从「上抛」改「韧性吞+计数」（**有意**，4 WS feeder 一个坏 tick 不再拖垮连接；可观测性由 `publish_errors` 弥补）；None-binding 从 INFO 升 ERROR（feeder 加 self.log）。
- **测试面（replace 不 layer）**：7 emit 点内联 publish 断言成废料；新测试落 `FeederPublishMixin.publish_price_update` 接口面（`test_trade_gateway.py` 为模板）：成功→`events_published`+1 & engine.put 收到 event；runtime 抛→`publish_errors`+1 & 不抛；`_engine_put is None`→loud ERROR & 不计 `events_published`。
- **迁移门（单分支 `6469-refactor/feeder-publish-seam`，TDD 每步先测试，垂直切片）**：
  ① Home1：三根（BaseFeeder/LiveDataFeeder/OKXDataFeeder）装 EngineBindableMixin（补 LiveDataFeeder:183 super MRO）；BacktestFeeder 删桥接。门：各 feeder `publish_event` 可达、`_engine_put` 经 bind_engine/set_event_publisher 注入
  ② FeederPublishMixin：新建 mixin（publish_price_update + stats + E1 + self.log）+ 三根装 + 7 emit 改调。门：成功/失败/None-binding 三态测试绿
  ③ Fork B：BaseFeeder 删冗余 put/_engine_put/set_event_publisher。门：grep `self.put`/BaseFeeder `_engine_put` 零残留、全 feeder 测试绿
  ④ 测试面：删 7 内联断言、补接口面测试
- **风险**：MRO 手术（LiveDataFeeder 多继承链 + ILiveDataFeeder ABC）须验证 `super().__init__()` 协作链不破 TimeMixin/NamedMixin/Base 初始化；4 WS feeder「上抛→吞」是行为变更，须确认无测试依赖上抛语义；`self.log=GLOG` 设值须不与既有属性冲突。
- **README 索引**：master 索引漏 ADR-017（#6441 合并时未补行），本 ADR 顺手补 ADR-017 + 加 ADR-019；ADR-018 在 PR#6461 待合并，索引行留该 PR 补。
- **交叉引用**：ADR-011（信号发射 seam 同族；本 ADR 偏离其「不抽 mixin」并说明理由）、ADR-010（EventPriceUpdate 是 Entity）、ADR-001（feeder→engine 出方向不变）、ADR-017（backtest_feeder:274 注释「入方向订阅」与本 ADR「出方向发布」对称）。

## 判定标准自检

- ① **难逆转**：7 emit 点 + 新 mixin + 2 类 MRO 装载 + BaseFeeder 重构，契约 shape 承诺跨多文件，回退需重散——满足。
- ② **反直觉**：未来见 `publish_price_update`+`publish_event` 两方法 / publish 默认吞异常 / `publish_errors` 统计 / feeder `self.log` 属性，会问「为何两方法」「为何不抛」「log 哪来」——满足。
- ③ **真实权衡**：Home1/Home2、3处重复/抽mixin/纯函数、S1/S3、E1/E2、INFO/ERROR/改mixin、清/留六轴均有真实备选——满足。
