# Phase 6: User Story 4 - 实时风控执行 (P2)

**状态**: ⚪ 未开始
**依赖**: Phase 3完成
**任务总数**: 4
**User Story**: 作为风控管理员，我希望实盘中能够实时监控Portfolio状态，在触发风控条件时自动拦截订单或生成平仓信号

---

## 📋 验收标准

- [ ] 风控模块可以集成到Portfolio
- [ ] 订单提交前依次通过所有风控模块检查
- [ ] 风控可以拦截订单并调整订单量
- [ ] 风控可以生成平仓信号

---

## 📥 待办任务池 (4个)

### T057 [P] 扩展Portfolio添加apply_risk_managements()方法
**文件**: `src/ginkgo/core/portfolios/portfolio.py`
**并行**: 是
**描述**: 在Signal生成后调用，依次通过所有风控模块处理信号

### T058 [P] 扩展Portfolio添加apply_risk_to_order()方法
**文件**: `src/ginkgo/core/portfolios/portfolio.py`
**并行**: 是
**描述**: 在Order提交前调用，检查并调整订单量

### T059 实现Portfolio.generate_risk_signals()方法
**文件**: `src/ginkgo/core/portfolios/portfolio.py`
**依赖**: T057
**描述**: 风控主动生成平仓信号（止损、止盈等）

### T060 [P] 编写风控集成单元测试
**文件**: `tests/unit/live/test_risk_integration.py`
**依赖**: T057, T058, T059
**描述**: 验证风控拦截和平仓信号生成

---

## 📝 备注

- T057, T058可以并行（2个任务）
- 风控通知使用现有notification系统，不单独创建risk_logger

**文档版本**: 1.1.0 | **最后更新**: 2026-01-04 (移除risk_logger任务)
