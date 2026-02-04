/**
 * 节点图 API 模块
 * 提供节点图的 CRUD 操作、验证、编译等接口
 */

import request from '../request'
import type {
  NodeGraphSummary,
  NodeGraphDetail,
  NodeGraphCreate,
  NodeGraphUpdate,
  GraphData,
  ValidationResult,
  CompileResult,
} from '@/components/node-graph/types'

/**
 * 节点图 API
 */
export const nodeGraphApi = {
  /**
   * 获取节点图列表
   */
  list: (params?: {
    page?: number
    page_size?: number
    is_template?: boolean
    keyword?: string
  }) => {
    return request.get<{ items: NodeGraphSummary[]; total: number }>('/api/node-graphs', { params })
  },

  /**
   * 获取节点图详情
   */
  get: (uuid: string) => {
    return request.get<NodeGraphDetail>(`/api/node-graphs/${uuid}`)
  },

  /**
   * 创建节点图
   */
  create: (data: NodeGraphCreate) => {
    return request.post<NodeGraphDetail>('/api/node-graphs', data)
  },

  /**
   * 更新节点图
   */
  update: (uuid: string, data: NodeGraphUpdate) => {
    return request.put<NodeGraphDetail>(`/api/node-graphs/${uuid}`, data)
  },

  /**
   * 删除节点图
   */
  delete: (uuid: string) => {
    return request.delete(`/api/node-graphs/${uuid}`)
  },

  /**
   * 复制节点图
   */
  duplicate: (uuid: string, name: string) => {
    return request.post<NodeGraphDetail>(`/api/node-graphs/${uuid}/duplicate`, { name })
  },

  /**
   * 验证节点图
   */
  validate: (uuid: string, data: GraphData) => {
    return request.post<ValidationResult>(`/api/node-graphs/${uuid}/validate`, data)
  },

  /**
   * 编译节点图为回测配置
   */
  compile: (uuid: string, data: GraphData) => {
    return request.post<CompileResult>(`/api/node-graphs/${uuid}/compile`, data)
  },

  /**
   * 从回测配置创建节点图
   */
  fromBacktest: (backtestUuid: string) => {
    return request.post<NodeGraphDetail>(`/api/node-graphs/from-backtest/${backtestUuid}`)
  },
}
