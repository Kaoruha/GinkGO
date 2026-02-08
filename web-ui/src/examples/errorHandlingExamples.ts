/**
 * 错误处理使用示例
 *
 * 本文件展示了在各种场景下如何使用统一的错误处理机制
 */

import { ref } from 'vue'
import { message, Modal } from 'ant-design-vue'
import {
  useErrorHandler,
  useFormErrorHandler,
  useBatchErrorHandler
} from '@/composables/useErrorHandler'
import { handleApiError, withErrorHandling } from '@/utils/errorHandler'
import { portfolioApi } from '@/api/modules/portfolio'

// ============================================================================
// 示例 1: 基础数据加载
// ============================================================================

export function example1_BasicDataLoading() {
  const { loading, execute, error } = useErrorHandler()

  async function loadPortfolioList() {
    const result = await execute(async () => {
      return await portfolioApi.list()
    })

    if (result) {
      // 成功处理
      return result
    } else {
      // 错误已被自动处理（显示错误消息）
      console.error('加载失败', error.value)
      return null
    }
  }

  return { loading, loadPortfolioList }
}

// ============================================================================
// 示例 2: 表单提交
// ============================================================================

export function example2_FormSubmission() {
  const formData = ref({
    name: '',
    initial_cash: 100000,
    mode: 'BACKTEST'
  })

  const { loading, submit, reset } = useFormErrorHandler()

  async function handleSubmit() {
    // 表单验证
    if (!formData.value.name) {
      message.warning('请输入组合名称')
      return
    }

    const result = await submit(async () => {
      return await portfolioApi.create(formData.value)
    })

    if (result) {
      message.success('创建成功')
      reset()
      // 跳转到详情页
      // router.push(`/portfolio/${result.uuid}`)
    }
  }

  return { loading, handleSubmit, formData }
}

// ============================================================================
// 示例 3: 删除操作（带确认）
// ============================================================================

export function example3_DeleteWithConfirmation() {
  const { loading, execute } = useErrorHandler()

  function handleDelete(portfolio: { uuid: string; name: string }) {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除投资组合"${portfolio.name}"吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      onOk: async () => {
        const result = await execute(async () => {
          return await portfolioApi.delete(portfolio.uuid)
        })

        if (result) {
          message.success('删除成功')
          // 刷新列表
          // await loadData()
        }
      }
    })
  }

  return { loading, handleDelete }
}

// ============================================================================
// 示例 4: 批量操作
// ============================================================================

export function example4_BatchOperations() {
  const { loading, errors, executeAll, clearErrors } = useBatchErrorHandler(3)

  async function batchDelete(uuids: string[]) {
    const results = await executeAll(
      uuids.map(uuid => () => portfolioApi.delete(uuid))
    )

    // 统计结果
    const successCount = results.filter(r => r !== null).length
    const failCount = errors.filter(e => e !== null).length

    if (failCount > 0) {
      message.warning(`删除完成：成功 ${successCount} 个，失败 ${failCount} 个`)
    } else {
      message.success(`成功删除 ${successCount} 个投资组合`)
    }

    return { successCount, failCount }
  }

  return { loading, batchDelete, errors, clearErrors }
}

// ============================================================================
// 示例 5: 带参数的 API 调用
// ============================================================================

export function example5_ApiCallWithParams() {
  const { loading, execute } = useErrorHandler()

  async function loadPortfolioDetail(uuid: string) {
    return await execute(async () => {
      return await portfolioApi.get(uuid)
    })
  }

  async function updatePortfolio(uuid: string, data: any) {
    return await execute(async () => {
      return await portfolioApi.update(uuid, data)
    })
  }

  return { loading, loadPortfolioDetail, updatePortfolio }
}

// ============================================================================
// 示例 6: 自定义错误处理
// ============================================================================

export function example6_CustomErrorHandling() {
  const { loading, execute } = useErrorHandler()

  async function criticalOperation() {
    // 不自动显示错误消息，由调用方处理
    const result = await execute(
      async () => {
        return await portfolioApi.create({ name: 'test' })
      },
      false // 不显示错误消息
    )

    if (!result) {
      // 自定义错误处理
      Modal.error({
        title: '操作失败',
        content: '关键操作失败，请联系管理员'
      })
    }

    return result
  }

  return { loading, criticalOperation }
}

// ============================================================================
// 示例 7: 使用 withErrorHandling 包装函数
// ============================================================================

export function example7_FunctionWrapping() {
  // 创建一个带错误处理的 API 调用函数
  const safeGetPortfolio = withErrorHandling(
    async (uuid: string) => {
      return await portfolioApi.get(uuid)
    }
  )

  // 使用时自动处理错误
  async function loadAndDisplay(uuid: string) {
    try {
      const result = await safeGetPortfolio(uuid)
      if (result) {
        console.log('加载成功', result)
      }
    } catch (error) {
      // 错误已被自动处理，这里可以做一些额外处理
      console.log('加载失败（已自动显示错误消息）')
    }
  }

  return { loadAndDisplay }
}

// ============================================================================
// 示例 8: 条件错误处理
// ============================================================================

export function example8_ConditionalErrorHandling() {
  const { loading, execute } = useErrorHandler()

  async function loadWithFallback(uuid: string) {
    const result = await execute(async () => {
      return await portfolioApi.get(uuid)
    })

    if (!result) {
      // 失败时使用默认数据
      message.info('加载失败，显示默认数据')
      return {
        uuid,
        name: '默认组合',
        initial_cash: 100000,
        mode: 'BACKTEST'
      }
    }

    return result
  }

  return { loading, loadWithFallback }
}

// ============================================================================
// 示例 9: 重试机制
// ============================================================================

export function example9_RetryMechanism() {
  const { loading, execute } = useErrorHandler()

  async function loadWithRetry(uuid: string, maxRetries = 3) {
    for (let i = 0; i < maxRetries; i++) {
      const result = await execute(async () => {
        return await portfolioApi.get(uuid)
      })

      if (result) {
        if (i > 0) {
          message.success(`重试 ${i} 次后成功`)
        }
        return result
      }

      // 等待一段时间后重试
      if (i < maxRetries - 1) {
        await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)))
      }
    }

    return null
  }

  return { loading, loadWithRetry }
}

// ============================================================================
// 示例 10: 组合多个操作
// ============================================================================

export function example10_CombinedOperations() {
  const { loading, execute } = useErrorHandler()

  async function clonePortfolio(sourceUuid: string, newName: string) {
    // 第一步：加载源组合
    const source = await execute(async () => {
      return await portfolioApi.get(sourceUuid)
    })

    if (!source) {
      return null
    }

    // 第二步：创建新组合
    const result = await execute(async () => {
      return await portfolioApi.create({
        ...source,
        name: newName,
        uuid: undefined // 不复制 UUID
      })
    })

    if (result) {
      message.success(`成功克隆组合 "${newName}"`)
    }

    return result
  }

  return { loading, clonePortfolio }
}
