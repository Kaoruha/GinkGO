export { default as request } from './request'

// 认证模块
export { authApi, isAuthenticated, getStoredUser, saveAuth, clearAuth } from './modules/auth'
export type { LoginRequest, LoginResponse, UserInfo } from './modules/auth'

// 组合模块
export { portfolioApi } from './modules/portfolio'
export type { Portfolio, PortfolioCreateRequest, PortfolioListParams } from './modules/portfolio'

// 回测模块
export { backtestApi } from './modules/backtest'
export type { BacktestTask, BacktestCreateRequest, BacktestListParams, BacktestNetValue, AnalyzerInfo, AnalyzerTimeseriesResponse, SignalRecord, OrderRecord, PositionRecord } from './modules/backtest'

// 数据模块
export { dataApi } from './modules/data'
export type { StockInfo, BarData, DataStats } from './modules/data'

// 组件模块
export { componentsApi } from './modules/components'
export type { ComponentSummary } from './modules/components'

// 系统模块
export { systemApi } from './modules/system'
export type { SystemStatusResponse, WorkersResponse, WorkerInfo, ComponentCounts, InfrastructureStatus } from './modules/system'

// 验证模块 (Stage2)
export { validationApi } from './modules/validation'
export type { WalkForwardConfig, WalkForwardResult, MonteCarloConfig, MonteCarloResult, SensitivityConfig, SensitivityResult } from './modules/validation'

// 因子研究模块
export { researchApi } from './modules/research'
export type { ICAnalysisConfig, ICAnalysisResult, FactorLayeringConfig, FactorLayeringResult, FactorOrthogonalizeConfig, FactorOrthogonalizeResult, FactorCompareConfig, FactorCompareResult, FactorDecayConfig, FactorDecayResult } from './modules/research'

// 参数优化模块
export { optimizationApi } from './modules/optimization'
export type { GridSearchConfig, GridSearchResult, GeneticOptimizerConfig, GeneticOptimizerResult, BayesianOptimizerConfig, BayesianOptimizerResult } from './modules/optimization'
