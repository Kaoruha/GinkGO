import request from '../request'

/**
 * 参数优化模块 API
 * 网格搜索、遗传算法、贝叶斯优化
 */

// ========== 类型定义 ==========

export interface GridSearchConfig {
  strategy_id: string
  params: Record<string, number[] | string[]>
}

export interface GridSearchResult {
  total_combinations: number
  best_params: Record<string, number | string>
  best_score: number
  results: Array<{
    params: Record<string, number | string>
    score: number
    sharpe_ratio: number
    max_drawdown: number
    total_return: number
  }>
}

export interface GeneticOptimizerConfig {
  strategy_id: string
  params: Record<string, { min: number; max: number; type: 'int' | 'float' }>
  population_size?: number
  generations?: number
  mutation_rate?: number
  crossover_rate?: number
  fitness_metric?: 'sharpe' | 'return' | 'sortino'
}

export interface Individual {
  params: Record<string, number>
  fitness: number
  sharpe_ratio: number
  max_drawdown: number
}

export interface GeneticOptimizerResult {
  best_individual: Individual
  population: Individual[]
  generation_stats: Array<{
    generation: number
    best_fitness: number
    avg_fitness: number
    diversity: number
  }>
  converged: boolean
}

export interface BayesianOptimizerConfig {
  strategy_id: string
  params: Record<string, { min: number; max: number; type: 'int' | 'float' }>
  n_iterations?: number
  n_initial_points?: number
  acquisition_function?: 'ei' | 'pi' | 'ucb'
  fitness_metric?: 'sharpe' | 'return' | 'sortino'
}

export interface BayesianOptimizerResult {
  best_params: Record<string, number>
  best_score: number
  iterations: Array<{
    iteration: number
    params: Record<string, number>
    score: number
    uncertainty: number
  }>
  surrogate_model?: {
    type: string
    parameters: Record<string, number>
  }
}

// ========== API 方法 ==========

export const optimizationApi = {
  /**
   * 网格搜索
   */
  gridSearch(config: GridSearchConfig): Promise<GridSearchResult> {
    return request.post('/v1/optimization/grid', {
      strategy_id: config.strategy_id,
      params: config.params,
    })
  },

  /**
   * 遗传算法优化
   */
  genetic(config: GeneticOptimizerConfig): Promise<GeneticOptimizerResult> {
    return request.post('/v1/optimization/genetic', {
      strategy_id: config.strategy_id,
      params: config.params,
      population_size: config.population_size,
      generations: config.generations,
      mutation_rate: config.mutation_rate,
      crossover_rate: config.crossover_rate,
      fitness_metric: config.fitness_metric,
    })
  },

  /**
   * 贝叶斯优化
   */
  bayesian(config: BayesianOptimizerConfig): Promise<BayesianOptimizerResult> {
    return request.post('/v1/optimization/bayesian', {
      strategy_id: config.strategy_id,
      params: config.params,
      n_iterations: config.n_iterations,
      n_initial_points: config.n_initial_points,
      acquisition_function: config.acquisition_function,
      fitness_metric: config.fitness_metric,
    })
  },
}
