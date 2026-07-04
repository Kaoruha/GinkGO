import request from '../request'

export interface FileItem {
  uuid: string
  name: string
  type: number
  data: string
  create_at: string
  update_at: string
}

export const fileApi = {
  /**
   * 获取文件列表
   * 后端 GET /api/v1/file_list → { code, data: FileItem[], meta: { total, ... } }
   * request 拦截器已 return response.data（HTTP body），故 res 即 { code, data, meta }。
   */
  async list(query: string = '', page: number = 1, size: number = 100, type?: number): Promise<FileItem[]> {
    const res = await request.get<FileItem[]>('/api/v1/file_list', {
      params: { query, page, size, type }
    })
    return (res as any)?.data || []
  },

  /**
   * 获取单个文件
   * 后端 GET /api/v1/file/{id} → { code, data: FileItem }
   */
  async get(fileId: string): Promise<FileItem> {
    const res = await request.get<FileItem>(`/api/v1/file/${fileId}`)
    return (res as any)?.data
  },

  /**
   * 创建文件
   * 后端 POST /api/v1/file { name, type, content } → { code, data: { uuid, name } }
   */
  async create(name: string, type: number, content: string = ''): Promise<{ status: string; uuid: string; name: string }> {
    const res = await request.post('/api/v1/file', {
      name,
      type,
      content
    })
    const data = (res as any)?.data || {}
    return { status: 'success', uuid: data.uuid, name: data.name }
  },

  /**
   * 更新文件内容
   * 后端 POST /api/v1/update_file { file_id, content } → { code, message }
   */
  async update(fileId: string, content: string): Promise<{ status: string }> {
    await request.post('/api/v1/update_file', {
      file_id: fileId,
      content
    })
    return { status: 'success' }
  },

  /**
   * 删除文件
   * 后端 DELETE /api/v1/file/{id} → { code, message }
   */
  async delete(fileId: string): Promise<{ status: string }> {
    await request.delete(`/api/v1/file/${fileId}`)
    return { status: 'success' }
  }
}
