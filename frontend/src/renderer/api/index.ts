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
export type { StockInfo, BarData, DataStats, SyncHistoryRecord } from './modules/data'

// 组件模块
export { componentsApi } from './modules/components'

// 系统模块
export { systemApi } from './modules/system'
export type { SystemStatusResponse, WorkersResponse, WorkerInfo, WorkerTaskInfo, WorkerTasksResponse, ComponentCounts, InfrastructureStatus } from './modules/system'

// 验证模块 (Stage2)
export { validationApi } from './modules/validation'
export type { WalkForwardConfig, WalkForwardResult, MonteCarloConfig, MonteCarloResult, SensitivityConfig, SensitivityResult } from './modules/validation'

// 因子研究模块
export { researchApi } from './modules/research'
export type { ICAnalysisConfig, ICAnalysisResult, FactorLayeringConfig, FactorLayeringResult, FactorOrthogonalizeConfig, FactorOrthogonalizeResult, FactorCompareConfig, FactorCompareResult, FactorDecayConfig, FactorDecayResult } from './modules/research'

// 参数优化模块
export { optimizationApi } from './modules/optimization'
export type { GridSearchConfig, GridSearchResult, GeneticOptimizerConfig, GeneticOptimizerResult, BayesianOptimizerConfig, BayesianOptimizerResult } from './modules/optimization'

// 实盘账号模块
export { liveAccountApi } from './modules/live'
export type {
  LiveAccount,
  CreateLiveAccountRequest,
  UpdateLiveAccountRequest,
  ValidateAccountResponse,
  AccountStatusType,
  PaginationResponse
} from './modules/live'
// ExchangeType/EnvironmentType 定义源在 market(live 只是转发),barrel 从 market 导出

// 行情模块
export { marketApi } from './modules/market'
export type { ExchangeType, EnvironmentType, TradingPair, MarketSubscription, TickerData } from './modules/market'

// 订单/持仓模块
export { orderApi, positionApi } from './modules/order'
export type { Order, Position, PositionSummary, OrderListParams, PositionListParams } from './modules/order'

// 定时任务模块
export { taskTimerApi } from './modules/taskTimer'
export type { TaskTimerJob, TaskTimerExecution, ExecutionSummary } from './modules/taskTimer'

// API Key 模块
export { apiKeyApi } from './modules/apiKey'
export type { ApiKey, CreateApiKeyRequest, UpdateApiKeyRequest, PermissionType, ApiKeyStatus } from './modules/apiKey'

// 用户/用户组/通知管理模块
// UserInfo 别名 SystemUserInfo:auth.UserInfo 是登录会话用户,本模块是管理域用户实体
export { usersApi, userGroupsApi, notificationsApi } from './modules/users'
export type { UserInfo as SystemUserInfo, UserCreate, UserUpdate, UserGroupInfo, UserGroupCreate, NotificationTemplate, NotificationHistory, NotificationRecipient } from './modules/users'

// 部署模块
export { deploymentApi } from './modules/deployment'
export type { DeployRequest, DeployResponse, DeploymentInfo } from './modules/deployment'

// Broker 管理模块
export { brokerApi } from './modules/broker'
export type { BrokerInstance, BrokerState } from './modules/broker'

// 交易历史模块
export { tradeHistoryApi } from './modules/tradeHistory'
export type { TradeRecord, TradeStatistics, DailySummary, TradeHistoryParams } from './modules/tradeHistory'
