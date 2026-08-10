/**
 * #6071: 从数据同步响应中提取失败的 code 数。
 *
 * 真实形状：dataApi.sync() 经 request.ts 响应拦截器 `return response.data`
 * 已剥掉 axios 外层，sendCommand 拿到的就是后端 ok() body：
 *   { code: 0, data: { type, codes, total, failed, success_count }, message, trace_id }
 *
 * DataSync.vue sendCommand 据此判断 success，不再硬编码 true。
 */
export function extractSyncFailed(response: any): number {
  const inner = response?.data
  return Number(inner?.failed ?? 0)
}
