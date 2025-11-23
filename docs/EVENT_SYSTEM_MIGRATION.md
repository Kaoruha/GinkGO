# 事件系统迁移说明

## 问题描述

当前存在两套订单事件系统并行运行：

### 旧事件系统（待废弃）
- `order_filled.py` - EventOrderFilled
- `order_canceled.py` - EventOrderCancelled  
- `order_submitted.py` - EventOrderSubmitted
- `order_related.py` - EventOrderRelated

### 新事件系统（推荐）
- `order_lifecycle_events.py` - 完整的订单生命周期事件
  - EventOrderAck - 订单确认
  - EventOrderPartiallyFilled - 部分成交
  - EventOrderRejected - 订单拒绝
  - EventOrderExpired - 订单过期

## 影响分析

**当前使用新事件系统的模块：**
- `routing/broker_matchmaking.py`
- `portfolios/base_portfolio.py`

**当前使用旧事件系统的模块：**
- `portfolios/portfolio_live.py`
- `portfolios/t1backtest.py`

## 迁移建议

1. **短期**：保持两套系统并存，避免破坏现有功能
2. **中期**：逐步将旧事件使用迁移到新事件
3. **长期**：删除旧事件定义，统一使用新事件系统

## 迁移优先级

- 高：将Portfolio层统一迁移到新事件
- 中：更新相关的事件处理逻辑
- 低：清理旧事件文件

## 兼容性考虑

迁移过程中需要确保：
- 现有回测结果的一致性
- 实盘交易的稳定性
- 第三方扩展的兼容性