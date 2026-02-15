import request from '../request'
import type { APIResponse } from '@/types/api'

// 优化方法类型
export type OptimizationMethod = 'grid' | 'genetic' | 'bayesian' | 'random' | 'particle_swarm'

// 优化目标类型
export type OptimizationTarget = 'sharpe' | 'total_return' | 'max_drawdown' | 'calmar' | 'sortino'

// 参数定义
export interface ParameterDef {
  name: string
  label: string
  min: number
  max: number
  step: number
  type: 'int' | 'float' | 'categorical'
  options?: string[]  // 用于categorical类型
}

// 参数范围
export interface ParameterRange {
  name: string
  min: number | string
  max: number | string
  values?: string[]  // categorical的可选值
}

// 优化任务配置
export interface OptimizationConfig {
  strategy_uuid: string
  target: OptimizationTarget
  method: OptimizationMethod
  parameters: ParameterRange[]
  train_period: {
    start: string
    end: string
  }
  val_period: {
    start: string
    end: string
  }
  max_iterations?: number
  n_jobs?: number
  cv_folds?: number  // 交叉验证折数
}

// 优化结果
export interface OptimizationResult {
  rank: number
  parameters: Record<string, number | string>
  train_objective: number
  val_objective: number
  overfit: boolean
  improvement_pct?: number
}

// 样本外测试配置
export interface OutOfSampleConfig {
  strategy_uuid: string
  parameters: Record<string, number | string>
  train_size: number  // 训练期长度（天）
  test_size: number   // 测试期长度（天）
  step_size: number    // 滑动步长（天）
  min_train_samples?: number
}

// 走步验证结果
export interface WalkForwardResult {
  train_start: string
  train_end: string
  test_start: string
  test_end: string
  train_return: number
  test_return: number
  parameters: Record<string, number | string>
}

// 蒙特卡洛模拟配置
export interface MonteCarloConfig {
  strategy_uuid: string
  parameters: Record<string, number | string>
  base_returns: number[]  // 历史收益率序列
  n_simulations: number
  confidence_level?: number  // 置信水平 0.9
}

// 蒙特卡洛结果
export interface MonteCarloResult {
  mean: number
  std: number
  percentiles: {
    p5: number
    p25: number
    p50: number
    p75: number
    p95: number
  }
  distribution: Array<{
    value: number
    count: number
  }>
}

// 敏感性分析配置
export interface SensitivityConfig {
  strategy_uuid: string
  parameter: string  // 要分析的参数名
  base_value: number | string
  values: (number | string)[]  // 参数值列表
  other_params: Record<string, number | string>
  date_range: {
    start: string
    end: string
  }
}

// 敏感性分析结果
export interface SensitivityResult {
  parameter_value: number | string
  objective_value: number
  delta: number  // 相对于基准值的变化
  trades_count: number
  win_rate: number
}

// API方法

/**
 * 参数优化
 */
export function optimizeParameters(config: OptimizationConfig) {
  return request<APIResponse<{
    task_id: string
    status: 'running' | 'completed' | 'failed'
    results?: OptimizationResult[]
    best_result?: OptimizationResult
  }>>({
    url: '/v1/validation/optimization',
    method: 'POST',
    data: config
  })
}

/**
 * 获取优化任务状态
 */
export function getOptimizationStatus(taskId: string) {
  return request<APIResponse<{
    task_id: string
    status: 'running' | 'completed' | 'failed'
    progress: number
    current_best: OptimizationResult
    results: OptimizationResult[]
  }>>({
    url: `/v1/validation/optimization/${taskId}`,
    method: 'GET'
  })
}

/**
 * 样本外测试（走步验证）
 */
export function outOfSampleTest(config: OutOfSampleConfig) {
  return request<APIResponse<{
    task_id: string
    results: WalkForwardResult[]
    summary: {
      avg_train_return: number
      avg_test_return: number
      degradation: number  // 退化程度
      stability_score: number  // 稳定性得分
    }
  }>>({
    url: '/v1/validation/out-of-sample',
    method: 'POST',
    data: config
  })
}

/**
 * 蒙特卡洛模拟
 */
export function monteCarloSimulation(config: MonteCarloConfig) {
  return request<APIResponse<MonteCarloResult>>({
    url: '/v1/validation/monte-carlo',
    method: 'POST',
    data: config
  })
}

/**
 * 参数敏感性分析
 */
export function sensitivityAnalysis(config: SensitivityConfig) {
  return request<APIResponse<{
    parameter_name: string
    results: SensitivityResult[]
    summary: {
      most_sensitive: {
        value: number | string
        objective: number
      }
      least_sensitive: {
        value: number | string
        objective: number
      }
      monotonic: boolean  // 是否单调
    }
  }>>({
    url: '/v1/validation/sensitivity',
    method: 'POST',
    data: config
  })
}

/**
 * 交叉验证
 */
export function crossValidation(config: {
  strategy_uuid: string
  parameters: Record<string, number | string>
  n_folds: number
  date_range: {
    start: string
    end: string
  }
}) {
  return request<APIResponse<{
    folds: Array<{
      fold_num: number
      train_period: { start: string; end: string }
      val_period: { start: string; end: string }
      val_return: number
    }>
    summary: {
      mean_return: number
      std_return: number
      sharpe_ratio: number
    }
  }>>({
    url: '/v1/validation/cross-validation',
    method: 'POST',
    data: config
  })
}

/**
 * 获取策略可优化参数列表
 */
export function getStrategyParameters(strategyUuid: string) {
  return request<APIResponse<ParameterDef[]>>({
    url: `/v1/validation/strategies/${strategyUuid}/parameters`,
    method: 'GET'
  })
}
