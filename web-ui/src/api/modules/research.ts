import request from '../request'
<<<<<<< HEAD
import type { APIResponse } from '@/types/api'

// 因子数据类型
export interface FactorValue {
  code: string
  date: string
  value: number
}

export interface FactorList {
  name: string
  label: string
  category: 'technical' | 'fundamental' | 'alternative'
  description?: string
}

export interface ICAnalysisRequest {
  factor_name: string
  start_date?: string
  end_date?: string
  periods?: number[]  // [1, 5, 10, 20]
}

export interface ICDataPoint {
  date: string
  ic: number
  rank_ic?: number
}

export interface ICStatistics {
  mean: number
  std: number
  icir: number
  t_stat: number
  pos_ratio: number  // 正IC占比
  abs_mean: number
}

export interface LayeringRequest {
  factor_name: string
  n_groups: number  // 3, 5, 10
  start_date?: string
  end_date?: string
}

export interface LayeringResult {
  date: string
  returns: Record<string, number>  // { group1: 0.01, group2: 0.02, ... }
  long_short?: number
}

export interface LayeringStatistics {
  long_short_return: number
  monotonicity_r2: number
  max_drawdown: number
}

export interface FactorComparisonRequest {
  factor_names: string[]
  start_date?: string
  end_date?: string
}

export interface FactorComparisonResult {
  factor_name: string
  ic_mean: number
  icir: number
  t_stat: number
  pos_ratio: number
  score: number
}

// API方法

/**
 * 获取因子列表
 */
export function getFactorList() {
  return request<APIResponse<FactorList[]>>({
    url: '/v1/factors',
    method: 'GET'
  })
}

/**
 * 获取因子详情
 */
export function getFactorDetail(factorName: string) {
  return request<APIResponse<{
    info: FactorList
    statistics: {
      mean: number
      std: number
      skew: number
      kurt: number
    }
  }>>({
    url: `/v1/factors/${factorName}`,
    method: 'GET'
  })
}

/**
 * 查询因子数据
 */
export function queryFactorData(params: {
  factor_name: string
  codes?: string[]
  start_date?: string
  end_date?: string
  limit?: number
}) {
  return request<APIResponse<FactorValue[]>>({
    url: '/v1/factors/data',
    method: 'GET',
    params
  })
}

/**
 * IC分析
 */
export function analyzeIC(data: ICAnalysisRequest) {
  return request<APIResponse<{
    timeseries: ICDataPoint[]
    statistics: ICStatistics
  }>>({
    url: '/v1/factors/analysis/ic',
    method: 'POST',
    data
  })
}

/**
 * 因子分层回测
 */
export function layeringBacktest(data: LayeringRequest) {
  return request<APIResponse<{
    results: LayeringResult[]
    statistics: LayeringStatistics
    groups: Array<{
      name: string
      return: number
      sharpe: number
      max_drawdown: number
    }>
  }>>({
    url: '/v1/factors/analysis/layering',
    method: 'POST',
    data
  })
}

/**
 * 因子对比
 */
export function compareFactors(data: FactorComparisonRequest) {
  return request<APIResponse<FactorComparisonResult[]>>({
    url: '/v1/factors/compare',
    method: 'POST',
    data
  })
}

/**
 * 因子正交化
 */
export function orthogonalizeFactors(data: {
  factor_names: string[]
  method?: 'gram-schmidt' | 'pca' | 'residual'
}) {
  return request<APIResponse<{
    orthogonalized_factors: Array<{
      name: string
      original_corr: number
      new_corr: number
    }>
  }>>({
    url: '/v1/factors/orthogonalize',
    method: 'POST',
    data
  })
}

/**
 * 因子衰减分析
 */
export function analyzeDecay(params: {
  factor_name: string
  max_lag?: number
}) {
  return request<APIResponse<{
    lag_returns: Array<{
      lag: number
      ic: number
    }>
    half_life: number
  }>>({
    url: `/v1/factors/${params.factor_name}/decay`,
    method: 'GET',
    params: { max_lag: params.max_lag }
  })
}

/**
 * 因子换手率分析
 */
export function analyzeTurnover(params: {
  factor_name: string
  rebalance_freq?: number  // 调仓频率(天)
}) {
  return request<APIResponse<{
    turnover_series: Array<{
      date: string
      turnover: number
    }>
    avg_turnover: number
  }>>({
    url: `/v1/factors/${params.factor_name}/turnover`,
    method: 'GET',
    params: { rebalance_freq: params.rebalance_freq }
  })
}

/**
 * 因子组合配置
 */
export interface FactorPortfolioConfig {
  name: string
  factors: Array<{
    name: string
    weight: number
  }>
  weight_target: 'equal' | 'long_only' | 'short_only' | 'market_neutral'
  max_single_weight?: number
  industry_neutral_weight?: number
  backtest_config?: {
    start_date: string
    end_date: string
    initial_cash: number
    rebalance_freq: 'daily' | 'weekly' | 'monthly'
  }
}

/**
 * 保存因子组合
 */
export function saveFactorPortfolio(data: FactorPortfolioConfig) {
  return request<APIResponse<{
    uuid: string
    name: string
  }>>({
    url: '/v1/factors/portfolios',
    method: 'POST',
    data
  })
}

/**
 * 获取已保存的因子组合列表
 */
export function getFactorPortfolios() {
  return request<APIResponse<Array<{
    uuid: string
    name: string
    factor_count: number
    created_at: string
  }>>({
    url: '/v1/factors/portfolios',
    method: 'GET'
  })
=======

/**
 * 因子研究模块 API
 * IC分析、因子分层、因子正交化、因子比较、因子衰减
 */

// ========== 类型定义 ==========

export interface ICAnalysisConfig {
  backtest_id: string
  return_period: number
}

export interface ICSeriesItem {
  date: string
  ic: number
  rank_ic: number
}

export interface ICAnalysisResult {
  ic_mean: number
  ic_std: number
  icir: number
  ic_positive_ratio: number
  ic_series: ICSeriesItem[]
}

export interface FactorLayeringConfig {
  backtest_id: string
  n_layers: number
  factor_name?: string
}

export interface LayerResult {
  layer: number
  return_mean: number
  return_std: number
  count: number
}

export interface FactorLayeringResult {
  n_layers: number
  layers: LayerResult[]
  monotonicity_score: number
}

export interface FactorOrthogonalizeConfig {
  backtest_id: string
  factors: string[]
  method: 'gram_schmidt' | 'pca' | 'residual'
}

export interface OrthogonalizedFactor {
  name: string
  ic: number
  correlation_with_original: Record<string, number>
}

export interface FactorOrthogonalizeResult {
  method: string
  factors: OrthogonalizedFactor[]
  explained_variance?: number[]
}

export interface FactorCompareConfig {
  backtest_id_1: string
  backtest_id_2: string
  metrics?: string[]
}

export interface FactorCompareResult {
  factor_1: {
    name: string
    ic: number
    icir: number
    turnover: number
  }
  factor_2: {
    name: string
    ic: number
    icir: number
    turnover: number
  }
  correlation: number
  combined_ic: number
}

export interface FactorDecayConfig {
  backtest_id: string
  max_lag: number
}

export interface DecayPoint {
  lag: number
  ic: number
  autocorrelation: number
}

export interface FactorDecayResult {
  half_life: number
  decay_series: DecayPoint[]
  optimal_rebalance_freq: number
}

// ========== API 方法 ==========

export const researchApi = {
  /**
   * IC 分析
   */
  icAnalysis(config: ICAnalysisConfig): Promise<ICAnalysisResult> {
    return request.post('/v1/research/ic', {
      backtest_id: config.backtest_id,
      return_period: config.return_period,
    })
  },

  /**
   * 因子分层
   */
  layering(config: FactorLayeringConfig): Promise<FactorLayeringResult> {
    return request.post('/v1/research/layering', {
      backtest_id: config.backtest_id,
      n_layers: config.n_layers,
      factor_name: config.factor_name,
    })
  },

  /**
   * 因子正交化
   */
  orthogonalize(config: FactorOrthogonalizeConfig): Promise<FactorOrthogonalizeResult> {
    return request.post('/v1/research/orthogonalize', {
      backtest_id: config.backtest_id,
      factors: config.factors,
      method: config.method,
    })
  },

  /**
   * 因子比较
   */
  compare(config: FactorCompareConfig): Promise<FactorCompareResult> {
    return request.post('/v1/research/compare', {
      backtest_id_1: config.backtest_id_1,
      backtest_id_2: config.backtest_id_2,
      metrics: config.metrics,
    })
  },

  /**
   * 因子衰减分析
   */
  decay(config: FactorDecayConfig): Promise<FactorDecayResult> {
    return request.post('/v1/research/decay', {
      backtest_id: config.backtest_id,
      max_lag: config.max_lag,
    })
  },
>>>>>>> 011-quant-research
}
