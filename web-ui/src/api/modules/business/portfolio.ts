import { get, post, put, del, getList } from '../common'
import type { APIResponse, PaginatedResponse } from '../../../types/common'

/**
 * 投资组合业务 API 模块
 * 封装投资组合相关的所有 API 调用
 */

// 投资组合模式
export type PortfolioMode = 'long_only' | 'short_only' | 'market_neutral' | 'custom'

/**
 * 获取投资组合列表
 */
export function getPortfolios(params?: {
  page?: number
  pageSize?: number
  keyword?: string
}) {
  return getList<PaginatedResponse<any>>('/v1/portfolios', params)
}

/**
 * 获取投资组合详情
 */
export function getPortfolioDetail(uuid: string) {
  return get<any>(`/v1/portfolios/${uuid}`)
}

/**
 * 创建投资组合
 */
export function createPortfolio(data: {
  name: string
  mode: PortfolioMode
  description?: string
  components?: Array<{
    uuid: string
    config?: Record<string, any>
  }>
}) {
  return post<any>('/v1/portfolios/', data)
}

/**
 * 更新投资组合
 */
export function updatePortfolio(uuid: string, data: {
  name?: string
  mode?: PortfolioMode
  description?: string
  components?: Array<{
    uuid: string
    config?: Record<string, any>
  }>
}) {
  return put<any>(`/v1/portfolios/${uuid}`, data)
}

/**
 * 删除投资组合
 */
export function deletePortfolio(uuid: string) {
  return del<any>(`/v1/portfolios/${uuid}`)
}

/**
 * 获取投资组合组件列表
 */
export function getComponents(portfolioUuid: string) {
  return get<any[]>(`/v1/portfolios/${portfolioUuid}/components`)
}

/**
 * 获取组件详情
 */
export function getComponentDetail(uuid: string) {
  return get<any>(`/v1/components/${uuid}`)
}

/**
 * 添加组件到投资组合
 */
export function addComponent(portfolioUuid: string, data: {
  component_uuid: string
  config?: Record<string, any>
}) {
  return post<any>(`/v1/portfolios/${portfolioUuid}/components`, data)
}

/**
 * 更新投资组合组件
 */
export function updateComponent(portfolioUuid: string, componentUuid: string, data: {
  config?: Record<string, any>
}) {
  return put<any>(`/v1/portfolios/${portfolioUuid}/components/${componentUuid}`, data)
}

/**
 * 删除投资组合组件
 */
export function removeComponent(portfolioUuid: string, componentUuid: string) {
  return del<any>(`/v1/portfolios/${portfolioUuid}/components/${componentUuid}`)
}
