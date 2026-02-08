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
import type { RequestOptions } from '@/types/api-request'

/**
 * 节点图 API
 */
export const nodeGraphApi = {
  /**
   * 获取节点图列表
   * @param params 查询参数
   * @param options 请求选项（支持 signal 取消请求）
   */
  list: (params?: {
    page?: number
    page_size?: number
    is_template?: boolean
    keyword?: string
  }, options?: RequestOptions) => {
    return request.get<{ items: NodeGraphSummary[]; total: number }>('/v1/node-graphs/', { params, signal: options?.signal })
  },

  /**
   * 获取节点图详情
   * @param uuid 节点图 UUID
   * @param options 请求选项（支持 signal 取消请求）
   */
  get: (uuid: string, options?: RequestOptions) => {
    return request.get<NodeGraphDetail>(`/v1/node-graphs/${uuid}`, { signal: options?.signal })
  },

  /**
   * 创建节点图
   * @param data 节点图数据
   * @param options 请求选项（支持 signal 取消请求）
   */
  create: (data: NodeGraphCreate, options?: RequestOptions) => {
    return request.post<NodeGraphDetail>('/v1/node-graphs/', data, { signal: options?.signal })
  },

  /**
   * 更新节点图
   * @param uuid 节点图 UUID
   * @param data 更新数据
   * @param options 请求选项（支持 signal 取消请求）
   */
  update: (uuid: string, data: NodeGraphUpdate, options?: RequestOptions) => {
    return request.put<NodeGraphDetail>(`/v1/node-graphs/${uuid}`, data, { signal: options?.signal })
  },

  /**
   * 删除节点图
   * @param uuid 节点图 UUID
   * @param options 请求选项（支持 signal 取消请求）
   */
  delete: (uuid: string, options?: RequestOptions) => {
    return request.delete(`/v1/node-graphs/${uuid}`, { signal: options?.signal })
  },

  /**
   * 复制节点图
   * @param uuid 节点图 UUID
   * @param name 新名称
   * @param options 请求选项（支持 signal 取消请求）
   */
  duplicate: (uuid: string, name: string, options?: RequestOptions) => {
    return request.post<NodeGraphDetail>(`/v1/node-graphs/${uuid}/duplicate`, { name }, { signal: options?.signal })
  },

  /**
   * 验证节点图
   * @param uuid 节点图 UUID
   * @param data 图数据
   * @param options 请求选项（支持 signal 取消请求）
   */
  validate: (uuid: string, data: GraphData, options?: RequestOptions) => {
    return request.post<ValidationResult>(`/v1/node-graphs/${uuid}/validate`, data, { signal: options?.signal })
  },

  /**
   * 编译节点图为回测配置
   * @param uuid 节点图 UUID
   * @param data 图数据
   * @param options 请求选项（支持 signal 取消请求）
   */
  compile: (uuid: string, data: GraphData, options?: RequestOptions) => {
    return request.post<CompileResult>(`/v1/node-graphs/${uuid}/compile`, data, { signal: options?.signal })
  },

  /**
   * 从回测配置创建节点图
   * @param backtestUuid 回测 UUID
   * @param options 请求选项（支持 signal 取消请求）
   */
  fromBacktest: (backtestUuid: string, options?: RequestOptions) => {
    return request.post<NodeGraphDetail>(`/v1/node-graphs/from-backtest/${backtestUuid}`, {}, { signal: options?.signal })
  },
}
