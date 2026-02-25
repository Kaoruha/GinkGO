/**
<<<<<<< HEAD
 * 常量统一导出
 */

// Portfolio 常量
export * from './portfolio'
// Backtest 常量 - 使用命名导出避免 getStateColor 冲突
export {
  BACKTEST_STATES,
  type BacktestState,
  STATE_LABELS as BACKTEST_STATE_LABELS,
  STATE_COLORS as BACKTEST_STATE_COLORS,
  BROKER_ATTITUDES,
  BROKER_ATTITUDE_LABELS,
  getBrokerAttitudeLabel,
  getStateLabel as getBacktestStateLabel,
  getStateColor as getBacktestStateColor,
  getStateStatus as getBacktestStateStatus,
} from './backtest'
// Component 常量
export * from './component'
=======
 * 常量导出入口
 */

export * from './portfolio'
>>>>>>> 011-quant-research
