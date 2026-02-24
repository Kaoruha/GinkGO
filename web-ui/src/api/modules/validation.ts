import request from '../request'

/**
 * 策略验证模块 API
 * Stage2: WalkForward, MonteCarlo, Sensitivity 分析
 */

// ========== 类型定义 ==========

export interface WalkForwardConfig {
  backtest_id: string
  n_folds: number
  window_type: 'expanding' | 'rolling'
  train_ratio?: number
}

export interface FoldResult {
  fold: number
  train_start: string
  train_end: string
  test_start: string
  test_end: string
  train_return: number
  test_return: number
}

export interface WalkForwardResult {
  avg_train_return: number
  avg_test_return: number
  degradation: number
  stability_score: number
  folds: FoldResult[]
}

export interface MonteCarloConfig {
  backtest_id: string
  n_simulations: number
  confidence_level?: number
}

export interface MonteCarloResult {
  simulations: Array<{
    simulation_id: number
    final_return: number
    max_drawdown: number
    sharpe_ratio: number
  }>
  statistics: {
    mean_return: number
    std_return: number
    var_95: number
    var_99: number
    expected_shortfall: number
  }
  percentiles: {
    p5: number
    p25: number
    p50: number
    p75: number
    p95: number
  }
}

export interface SensitivityConfig {
  backtest_id: string
  params: Record<string, { min: number; max: number; steps: number }>
}

export interface SensitivityResult {
  parameter_name: string
  sensitivity_score: number
  impact_analysis: Array<{
    param_value: number
    return_value: number
    sharpe_ratio: number
    max_drawdown: number
  }>
}

// ========== API 方法 ==========

export const validationApi = {
  /**
   * Walk-Forward 验证
   */
  walkForward(config: WalkForwardConfig): Promise<WalkForwardResult> {
    return request.post('/v1/validation/walkforward', {
      backtest_config: { backtest_id: config.backtest_id },
      n_folds: config.n_folds,
      window_type: config.window_type,
      train_ratio: config.train_ratio,
    })
  },

  /**
   * 蒙特卡洛模拟
   */
  monteCarlo(config: MonteCarloConfig): Promise<MonteCarloResult> {
    return request.post('/v1/validation/montecarlo', {
      backtest_config: { backtest_id: config.backtest_id },
      n_simulations: config.n_simulations,
      confidence_level: config.confidence_level,
    })
  },

  /**
   * 敏感性分析
   */
  sensitivity(config: SensitivityConfig): Promise<SensitivityResult[]> {
    return request.post('/v1/validation/sensitivity', {
      backtest_config: { backtest_id: config.backtest_id },
      params: config.params,
    })
  },
}
