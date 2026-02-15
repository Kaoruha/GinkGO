import request from '../request'
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
}
