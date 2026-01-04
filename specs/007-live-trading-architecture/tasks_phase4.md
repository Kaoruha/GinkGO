# Phase 4: User Story 2 - 多Portfolio并行运行 (P2)

**状态**: ⚪ 未开始
**依赖**: Phase 3完成
**任务总数**: 10
**User Story**: 作为基金经理，我希望在同一个ExecutionNode容器内运行多个独立的Portfolio

---

## 📋 验收标准

- [ ] ExecutionNode可以加载和运行3-5个Portfolio
- [ ] 每个Portfolio有独立的PortfolioProcessor线程
- [ ] InterestMap机制正确路由消息到对应的Portfolio
- [ ] Portfolio之间的状态完全隔离
- [ ] Backpressure机制正常工作（70%警告，95%丢弃）

---

## 📥 待办任务池 (10个)

### T031 [P] 创建InterestMap类
**文件**: `src/ginkgo/workers/execution_node/interest_map.py`
**并行**: 是
**描述**: 创建InterestMap类，包含interest_map字典和update_interest方法

### T032 实现InterestMap.add_portfolio()方法
**文件**: `src/ginkgo/workers/execution_node/interest_map.py`
**依赖**: T031
**描述**: 添加Portfolio及其订阅的股票代码到interest_map

### T033 实现InterestMap.get_portfolios()方法
**文件**: `src/ginkgo/workers/execution_node/interest_map.py`
**依赖**: T031
**描述**: 根据股票代码查询订阅的Portfolio列表（O(1)查询）

### T034 实现ExecutionNode.route_message()方法
**文件**: `src/ginkgo/workers/execution_node/node.py`
**依赖**: T031, T033
**描述**: 根据interest_map路由EventPriceUpdate到对应Portfolio的queue

### T035 [P] 创建BackpressureChecker类
**文件**: `src/ginkgo/workers/execution_node/backpressure.py`
**并行**: 是
**描述**: 创建BackpressureChecker类，监控queue使用率

### T036 实现BackpressureChecker.check_queue_status()方法
**文件**: `src/ginkgo/workers/execution_node/backpressure.py`
**依赖**: T035
**描述**: 70%发送警告，95%丢弃消息+告警

### T037 [P] 编写Backpressure单元测试
**文件**: `tests/unit/live/test_backpressure.py`
**依赖**: T035, T036
**描述**: 验证警告和丢弃逻辑

### T038 编写多Portfolio并行处理集成测试
**文件**: `tests/integration/live/test_multi_portfolio.py`
**依赖**: T031, T034
**描述**: 验证3个Portfolio同时处理不同股票

### T039 编写InterestMap路由测试
**文件**: `tests/integration/live/test_interest_map.py`
**依赖**: T031, T034
**描述**: 验证消息正确路由到订阅的Portfolio

### T040 编写状态隔离测试
**文件**: `tests/integration/live/test_state_isolation.py`
**依赖**: T031, T034
**描述**: 验证Portfolio A的订单不影响Portfolio B

---

## 📝 备注

- T031可以并行
- T032-T034依赖T031，需顺序执行
- T035可以并行
- T036依赖T035
- T038-T040可以并行编写，同时执行测试

**文档版本**: 1.0.0 | **最后更新**: 2026-01-04
