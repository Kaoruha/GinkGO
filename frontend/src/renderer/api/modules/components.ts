import request from '../request'
import type { PaginatedData } from '@/types/api'

const BASE = '/api/v1/components/'

// ========== 类型定义 ==========

/**
 * 组件实体(策略/分析器/风控/仓位/选择器)
 * 字段对齐后端 ComponentInfo DTO(api/api/components.py)
 */
export interface ComponentInfo {
  uuid: string
  name: string
  component_type: string  // strategy | analyzer | risk | sizer | selector
  file_type: number
  code?: string | null
  description?: string | null
  updated_at?: string | null
}

// ========== API 方法 ==========

export const componentsApi = {
  async list(componentType?: string, params?: Record<string, any>): Promise<PaginatedData<ComponentInfo>> {
    const p: Record<string, any> = {}
    if (componentType) {
      p.component_type = componentType
    }
    if (params) {
      Object.assign(p, params)
    }
    return request.get(BASE, { params: p })
  },

  async get(uuid: string): Promise<ComponentInfo> {
    return request.get(`${BASE}${uuid}`)
  },

  async create(data: { name: string; component_type: string; code: string; description?: string }): Promise<ComponentInfo> {
    return request.post(BASE, data)
  },

  async update(uuid: string, data: { name?: string; code?: string; description?: string }): Promise<ComponentInfo> {
    return request.put(`${BASE}${uuid}`, data)
  },

  async delete(uuid: string): Promise<void> {
    return request.delete(`${BASE}${uuid}`)
  },
}
