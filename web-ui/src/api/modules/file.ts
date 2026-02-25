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
   */
  async list(query: string = '', page: number = 0, size: number = 100, type?: number): Promise<FileItem[]> {
    const res = await request.get<FileItem[]>('/v1/file_list', {
      params: { query, page, size, type }
    })
    // request 拦截器已经返回 response.data，所以 res 就是数据
    return (res as any) || []
  },

  /**
   * 获取单个文件
   */
  async get(fileId: string): Promise<FileItem> {
    const res = await request.get<FileItem>(`/v1/file/${fileId}`)
    return res as any
  },

  /**
   * 创建文件
   */
  async create(name: string, type: number, content: string = ''): Promise<{ status: string; uuid: string; name: string }> {
    const res = await request.post('/v1/file', {
      name,
      type,
      content
    })
    return res as any
  },

  /**
   * 更新文件内容
   */
  async update(fileId: string, content: string): Promise<{ status: string }> {
    const res = await request.post('/v1/update_file', {
      file_id: fileId,
      content
    })
    return res as any
  },

  /**
   * 删除文件
   */
  async delete(fileId: string): Promise<{ status: string }> {
    const res = await request.delete(`/v1/file/${fileId}`)
    return res as any
  }
}
