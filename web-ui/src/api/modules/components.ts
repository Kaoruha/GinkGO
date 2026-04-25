import request from '../request'

const BASE = '/api/v1/components/'

export const componentsApi = {
  async list(componentType?: string, params?: Record<string, any>) {
    const p: Record<string, any> = {}
    if (componentType) {
      p.component_type = componentType
    }
    if (params) {
      Object.assign(p, params)
    }
    return request.get(BASE, { params: p })
  },

  async get(uuid: string) {
    return request.get(`${BASE}${uuid}`)
  },

  async create(data: { name: string; component_type: string; code: string; description?: string }) {
    return request.post(BASE, data)
  },

  async update(uuid: string, data: { name?: string; code?: string; description?: string }) {
    return request.put(`${BASE}${uuid}`, data)
  },

  async delete(uuid: string) {
    return request.delete(`${BASE}${uuid}`)
  },
}
