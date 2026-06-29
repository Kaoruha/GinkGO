# 事件订阅契约归组件（@subscribes + __init_subclass__）

**Status**: Accepted
**Date**: 2026-06-23
**Related**: ADR-003（引擎二态）、S4 issue #6296

## Context

引擎按 `component.__class__.__name__` 字符串查表注册事件订阅（`time_controlled_engine.py:798` `component_event_mapping`，另 `:728` `hook_event_mapping` 管 Analyzers），订阅真相散落在 5 个站点（2 个 engine dict + `engine_assembly_service` / `infrastructure_factory` / `task_engine_builder` 共 7 处手动 `engine.register`）。

根因症状：
- `PortfolioLive`（真实类，`portfolio_live.py:51`）类名不匹配 dict key `"PortfolioT1Backtest"`，永远进不了 auto-register，被逼出 `_convert_to_backtest_portfolio`（`task_engine_builder.py:158`）克隆成 T1Backtest 的 hack——手抄 `_strategies/_sizer/_risk_managers` 私有属性，Live 多一个订阅方法/状态就漏。
- ORDERFILLED / INTERESTUPDATE 双重注册靠 `register` 的 dedup（`event_engine.py:478` 按 handler 对象去重）静默吞掉，改 handler 指向时埋重复调用 bug。
- `PortfolioLive.on_order_filled`（`:383`）是"一方法多 event"的转发壳（签名收 `EventOrderPartiallyFilled`，转发给 `on_order_partially_filled`）——旧模型不支持一方法多 event 的 workaround。

根因：`EngineBindableMixin.bind_engine` 只绑了出方向（`_engine_put = engine.put`），入方向（订阅）无落点，引擎只好反过来按类名猜。

## Decision

订阅真相归组件。引入 `@subscribes(*events)` 装饰器 + `SubscribableMixin.__init_subclass__`，在类创建期把声明合并进类属性 `_subscriptions: Dict[Event, str]`（event→方法名）；`bind_engine` 调 `register_handlers(engine)` 遍历 `_subscriptions`，按 `getattr(self, 方法名)` 解析 bound method（MRO 自然返回子类 override）。

- **契约在基类**：`PortfolioBase` 的抽象 handler（`raise NotImplementedError`）标 `@subscribes` 声明类族订阅契约；子类 override 同名方法不重标即继承。
- **合并规则**：子类声明覆盖父类同 event 的方法名 → 换映射免费（无需 unsubscribe）。
- **一方法多 event**：`@subscribes(E1, E2)` → registry 多键同值。
- **append / replace**：`__subscriptions_reset__ = True` 时丢弃父类全部，仅本类声明为唯一真相；默认 append。
- **reset 局部性**：reset 标志用 `vars(cls)` 读取（不沿 MRO 继承），否则后代意外继承祖先的 reset。

## Rationale

选数据化契约（`@subscribes` + registry dict）而非命令式 `register_handlers(self, engine)` 方法：

- **数据化可独立断言**：registry 是 `Dict[Event, str]`，测试直接断言映射，不起引擎；命令式要 mock `engine.register`。
- **换映射免费**：声明式合并在类创建期算出最终 registry，子类声明覆盖父类同 event；命令式 `super().register_handlers()` 执行后改不回，换 handler 要 `unregister` 补丁，且 `register` 的 dedup 按 handler 对象去重抓不住不同 handler → 双注册陷阱。
- **删 hack**：`PortfolioLive` 自带订阅直接进引擎，`_convert_to_backtest_portfolio` 可删；`on_order_filled` 转发壳被 `@subscribes(ORDERFILLED, ORDERPARTIALLYFILLED)` 取代。

## Considered Options

- **① `register_handlers(self, engine)` 命令式方法**：集中视图，最灵活。否决——改映射要 `unregister` 补丁 + dedup 双注册陷阱；测试要 mock engine；契约靠约定非声明。
- **收敛单一 dict（engine 侧 key 从 `__class__.__name__` 改 isinstance）**：治标——能让 PortfolioLive 注册，但 `_convert` hack 仍要留，新组件家族仍要动 engine。开闭原则差。

## Consequences

- 删 engine 双 dict（`component_event_mapping` + `hook_event_mapping`）+ 7 处手动 `engine.register`。
- `@unsubscribe(E)` 作为逐 event 负声明（部分移除），与 `__subscriptions_reset__` 全量清空互补；Portfolio 场景暂不发生，列为逃生舱。
- engine 自注册 TIME_ADVANCE / COMPONENT_TIME_ADVANCE（`tce:471`）合法，不迁。
- 迁移顺序：Portfolio 契约 → PortfolioT1Backtest 实现 → PortfolioLive（删 _convert + 转发壳）→ BacktestFeeder / TradeGateway → Analyzers。
