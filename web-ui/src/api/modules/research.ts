import request from '../request'

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
}
