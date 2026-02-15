import { get, post } from '../common'
import type { APIResponse, PaginatedResponse } from '../../../types/common'

/**
 * 量化研究 API 模块
 * 封装因子研究相关的所有 API 调用
 */

// 因子数据类型
export interface FactorValue {
  code: string
  date: string
  value: number
}

export interface Factor {
  name: string
  label: string
  category: 'technical' | 'fundamental' | 'alternative'
}

export interface ICStatistics {
  mean: number
  std: number
  icir: number
  t_stat: number
  pos_ratio: number
  abs_mean: number
}

export interface ICDataPoint {
  date: string
  ic: number
  rank_ic?: number
}

/**
 * 获取因子列表
 */
export function getFactorList() {
  return get<Factor[]>('/v1/factors')
}

/**
 * 获取因子详情
 */
export function getFactorDetail(name: string) {
  return get<any>(`/v1/factors/${name}`)
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
  return get<FactorValue[]>('/v1/factors/data', params)
}

/**
 * IC 分析
 */
export function analyzeIC(data: {
  factor_name: string
  start_date?: string
  end_date?: string
  periods?: number[]
}) {
  return post<ICStatistics>('/v1/factors/analysis/ic', data)
}

/**
 * 因子分层回测
 */
export function layeringBacktest(data: {
  factor_name: string
  n_groups: number
  start_date?: string
  end_date?: string
}) {
  return post<any>('/v1/factors/analysis/layering', data)
}

/**
 * 因子对比
 */
export function compareFactors(data: {
  factor_names: string[]
  start_date?: string
  end_date?: string
}) {
  return post<any>('/v1/factors/compare', data)
}

/**
 * 因子正交化
 */
export function orthogonalizeFactors(data: {
  factor_names: string[]
  method?: 'gram-schmidt' | 'symmetric' | 'residual'
}) {
  return post<any>('/v1/factors/orthogonalize', data)
}

/**
 * 因子衰减分析
 */
export function analyzeDecay(params: {
  factor_name: string
  max_lag?: number
}) {
  return get<any>(`/v1/factors/${params.factor_name}/decay`, params)
}

/**
 * 因子换手率分析
 */
export function analyzeTurnover(params: {
  factor_name: string
  rebalance_freq?: number
}) {
  return get<any>(`/v1/factors/${params.factor_name}/turnover`, params)
}

/**
 * 保存因子组合
 */
export function saveFactorPortfolio(data: {
  name: string
  factors: Array<{
    name: string
    weight: number
  }>
  weight_target?: string
  max_single_weight?: number
  industry_neutral_weight?: number
  backtest_config?: {
    start_date: string
    end_date: string
    initial_cash: number
    rebalance_freq: 'daily' | 'weekly' | 'monthly'
  }
}) {
  return post<any>('/v1/factors/portfolios', data)
}

/**
 * 获取已保存的因子组合
 */
export function getFactorPortfolios() {
  return get<any[]>('/v1/factors/portfolios')
}
