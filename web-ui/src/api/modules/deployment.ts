import request from '../request'

// ========== 类型定义 ==========

export interface DeployRequest {
  portfolio_id: string
  mode: 'paper' | 'live'
  account_id?: string
  name?: string
}

export interface DeployResponse {
  portfolio_id: string
  deployment_id: string
  source_portfolio_id: string
}

export interface DeploymentInfo {
  deployment_id: string
  source_task_id: string | null
  target_portfolio_id: string
  source_portfolio_id: string
  mode: string
  account_id: string | null
  status: string
  create_at: string | null
}

// ========== API 方法 ==========

export const deploymentApi = {
  /**
   * 部署组合到模拟盘/实盘
   */
  deploy(params: DeployRequest) {
    return request.post('/api/v1/deploy/', params)
  },

  /**
   * 查询组合的部署信息
   */
  getStatus(portfolioId: string) {
    return request.get(`/api/v1/deploy/${portfolioId}`)
  },

  /**
   * 列出部署记录
   */
  list(portfolioId?: string) {
    const params: Record<string, string> = {}
    if (portfolioId) params.portfolio_id = portfolioId
    return request.get('/api/v1/deploy/', { params })
  },
}
