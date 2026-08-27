import request from '../request'

/**
 * 评估 API
 * 四级漏斗 (G0 回测可信 → G1 回测有效 → G2 模拟一致 → G3 实盘就绪)
 * 阈值与状态来自后端 gate_definitions 单一事实源, 前端不重复定义
 */

// ========== 类型定义 ==========

/** gate 定义 (与后端 GateDefinition 同形, 渲染阈值线用) */
export interface GateDefinition {
  id: string
  level: 'G0' | 'G1' | 'G2' | 'G3'
  name: string
  threshold: number
  /** "gte" 值≥阈值过 / "lte" 值≤阈值过 */
  direction: 'gte' | 'lte'
  unit: string
  severity: 'blocker' | 'warning'
  remediation: string
  requires: string
}

/** gate 求值结果四态 */
export type GateStatus = 'PASS' | 'FAIL' | 'INSUFFICIENT_DATA' | 'BLOCKED'

/** 单条 gate 求值结果 */
export interface GateResult {
  id: string
  level: string
  name: string
  status: GateStatus
  value: number | null
  threshold?: number
  direction?: string
  unit?: string
  detail?: string
  remediation?: string
}

/** 漏斗报告 */
export interface FunnelReport {
  portfolio_id: string
  task_id: string | null
  candidate_task_id: string | null
  /** 最高连续通过级 (G0/G1/G2/G3) 或 "未通过 G0" */
  level_reached: string
  gates: GateResult[]
  notes?: string[]
}

/** 一致性报告 (G2 五项) */
export interface ParityReport {
  baseline: string
  candidate: string
  overlap_days: number
  overlap_start?: string
  overlap_end?: string
  daily_return_corr: number | null
  cum_return_diff: number | null
  cum_return_band: number | null
  band_ratio: number | null
  turnover_deviation_pct: number | null
  drawdown_shape_corr: number | null
  notes?: string[]
}

/** 单条数据质量问题 (kind 后三类 code 为伪 code "(selector)"/"(universe)") */
export interface QualityIssue {
  code: string
  kind:
    | 'sparse'
    | 'gap'
    | 'calendar_misalign'
    | 'factor_reversal'
    | 'factor_missing'
    | 'selector_error'
    | 'selector_empty'
    | 'universe_empty'
    | 'universe_sparse'
  severity: 'blocker' | 'warning'
  detail: string
  remediation: string
}

/** 数据预检报告 */
export interface PreflightReport {
  portfolio_id: string
  start: string
  end: string
  codes: string[]
  coverage: Record<string, number>
  quality: Record<string, Record<string, number | string | string[] | null>>
  issues: QualityIssue[]
  /** 无 blocker issue (false = 先修数据再回测) */
  ok: boolean
  notes?: string[]
}

// ========== API ==========

export const evaluationApi = {
  /** gate 定义清单 (阈值线/徽章渲染) */
  getGates(): Promise<GateDefinition[]> {
    return request.get('/api/v1/evaluation/gates')
  },

  /** 四级漏斗报告 (实时计算) */
  getFunnel(params: {
    portfolio_id: string
    task_id?: string
    candidate_task_id?: string
    stability_window?: number
  }): Promise<FunnelReport> {
    return request.get('/api/v1/evaluation/funnel', { params })
  },

  /** 回测 vs 模拟盘一致性 (G2 五项) */
  getParity(params: {
    portfolio_id: string
    baseline_task_id: string
    candidate_task_id: string
  }): Promise<ParityReport> {
    return request.get('/api/v1/evaluation/parity', { params })
  },

  /** 数据质量预检 (G0 质量项) */
  runPreflight(params: {
    portfolio_id: string
    start: string
    end: string
    min_bars?: number
  }): Promise<PreflightReport> {
    return request.post('/api/v1/evaluation/preflight', null, { params })
  },
}
