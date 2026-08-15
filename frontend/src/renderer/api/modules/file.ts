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
   * 后端 GET /api/v1/file_list → paginated 信封
   * request 拦截器已拆包: 分页端点返回 { items, total, page, ... } (PaginatedData)
   */
  async list(query: string = '', page: number = 1, size: number = 100, type?: number): Promise<FileItem[]> {
    const res = await request.get('/api/v1/file_list', {
      params: { query, page, size, type }
    })
    return (res as any)?.items || []
  },

  /**
   * 获取单个文件
   * 后端 GET /api/v1/file/{id} → ok 信封, 拦截器拆包后 res 即 FileItem
   */
  async get(fileId: string): Promise<FileItem> {
    return request.get(`/api/v1/file/${fileId}`)
  },

  /**
   * 创建文件
   * 后端 POST /api/v1/file → ok(data={uuid,name}), 拦截器拆包后 res 即 { uuid, name }
   */
  async create(name: string, type: number, content: string = ''): Promise<{ status: string; uuid: string; name: string }> {
    const res: any = await request.post('/api/v1/file', {
      name,
      type,
      content
    })
    return { status: 'success', uuid: res?.uuid, name: res?.name }
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
