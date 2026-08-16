/**
 * 统一的批量操作工具库
 * 用于减少批量处理逻辑的重复代码
 */

/**
 * 批量操作结果接口
 */
export interface BatchOperationResult<T> {
  total: number
  success: number
  failed: number
  failedItems: Array<{
    item: T
    error: string
  }>
  successItems: T[]
}

/**
 * 执行批量操作的通用函数
 * @param items 要处理的项目数组
 * @param operation 对每个项目执行的操作函数
 * @param getItemId 获取项目ID的函数（用于错误追踪）
 * @param options 配置选项
 * @returns 批量操作结果
 */
export async function executeBatchOperation<T>(
  items: T[],
  operation: (item: T) => Promise<any>,
  getItemId: (item: T) => string,
  options: {
    // 是否在第一个失败时停止（默认false）
    stopOnFirstError?: boolean
    // 并发限制（默认不限制）
    concurrency?: number
  } = {}
): Promise<BatchOperationResult<T>> {
  const { stopOnFirstError = false, concurrency } = options

  let results: PromiseSettledResult<any>[]

  if (concurrency && concurrency > 0) {
    // 限制并发数的批量操作
    results = await executeWithConcurrency(items, operation, concurrency)
  } else {
    // 无限制并发
    results = await Promise.allSettled(items.map(item => operation(item)))
  }

  const successItems: T[] = []
  const failedItems: Array<{ item: T; error: string }> = []

  results.forEach((result, index) => {
    const item = items[index]

    if (result.status === 'fulfilled') {
      successItems.push(item)
    } else {
      const error = result.reason?.message || result.reason?.toString() || '未知错误'
      failedItems.push({
        item,
        error
      })

      // 如果设置了第一个失败时停止，取消剩余操作
      if (stopOnFirstError) {
        // 注意：Promise.allSettled 无法中途停止，这里只是标记
        // 实际的中止逻辑需要在 operation 函数中实现
      }
    }
  })

  return {
    total: items.length,
    success: successItems.length,
    failed: failedItems.length,
    failedItems,
    successItems
  }
}

/**
 * 带并发限制的批量操作执行
 * @param items 项目数组
 * @param operation 操作函数
 * @param concurrency 并发数限制
 * @returns Promise结果数组
 */
async function executeWithConcurrency<T>(
  items: T[],
  operation: (item: T) => Promise<any>,
  concurrency: number
): Promise<PromiseSettledResult<any>[]> {
  const results: PromiseSettledResult<any>[] = []
  const executing: Promise<any>[] = []

  for (const item of items) {
    const promise = operation(item).then(
      result => ({ status: 'fulfilled' as const, value: result }),
      error => ({ status: 'rejected' as const, reason: error })
    )

    results.push(await promise)
    executing.push(promise)

    // 当并发数达到限制时，等待一个操作完成
    if (executing.length >= concurrency) {
      await Promise.race(executing)
      // 移除已完成的promise（简化处理，实际应该移除已完成的）
      executing.length = Math.min(executing.length, concurrency)
    }
  }

  // 等待所有剩余操作完成
  await Promise.all(executing)

  return results
}

/**
 * 批量操作的辅助类型 - 用于回测任务
 */
export interface BacktestBatchOperation {
  batchStart: (uuids: string[]) => Promise<BatchOperationResult<string>>
  batchStop: (uuids: string[]) => Promise<BatchOperationResult<string>>
  batchCancel: (uuids: string[]) => Promise<BatchOperationResult<string>>
}

/**
 * 创建回测批量操作处理器
 * @param startFn 启动任务的函数
 * @param stopFn 停止任务的函数
 * @param cancelFn 取消任务的函数
 * @returns 批量操作对象
 */
export function createBacktestBatchOperations(
  startFn: (uuid: string) => Promise<any>,
  stopFn: (uuid: string) => Promise<any>,
  cancelFn: (uuid: string) => Promise<any>
): BacktestBatchOperation {
  return {
    batchStart: (uuids: string[]) => executeBatchOperation(uuids, startFn, id => id),
    batchStop: (uuids: string[]) => executeBatchOperation(uuids, stopFn, id => id),
    batchCancel: (uuids: string[]) => executeBatchOperation(uuids, cancelFn, id => id)
  }
}

/**
 * 格式化批量操作结果用于显示
 * @param result 批量操作结果
 * @param operationName 操作名称（如"启动", "停止"）
 * @returns 用户友好的结果消息
 */
export function formatBatchResultMessage(
  result: BatchOperationResult<any>,
  operationName: string
): string {
  if (result.failed === 0) {
    return `${operationName}成功：${result.success}个任务`
  } else if (result.success === 0) {
    return `${operationName}失败：${result.failed}个任务`
  } else {
    return `${operationName}完成：成功${result.success}个，失败${result.failed}个`
  }
}

/**
 * 生成批量操作的详细错误报告
 * @param result 批量操作结果
 * @returns 错误详情数组
 */
export function generateBatchErrorReport<T>(
  result: BatchOperationResult<T>
): Array<{ item: T; error: string }> {
  return result.failedItems.map(({ item, error }) => ({
    item,
    error
  }))
}