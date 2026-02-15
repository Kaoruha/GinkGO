import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useApiError } from '@/composables/useApiError'

/**
 * 通用 Store 基类
 * 提供统一的 CRUD 操作模式
 */

interface PaginationState {
  page: number
  pageSize: number
  total: number
}

interface ListState {
  keyword: string
  state?: string
}

export function useCrudStore<T>(apiModule: any, options?: {
    fetchListParams?: Record<string, any>
  }) {
  const { handleError, errorMessage, clearError } = useApiError()

  // ======================================
  // State - 状态定义
  // ======================================

  const items = ref<T[]>([])
  const loading = ref(false)
  const pagination = ref<PaginationState>({
    page: 1,
    pageSize: 20,
    total: 0
  })
  const listState = ref<ListState>({
    keyword: '',
    state: undefined
  })
  const selectedItem = ref<T | null>(null)

  // ======================================
  // Computed - 计算属性
  // ======================================

  const hasMore = computed(() => {
    return pagination.value.page * pagination.value.pageSize < pagination.value.total
  })

  const filteredItems = computed(() => {
    let result = items.value

    // 关键词筛选
    if (listState.value.keyword) {
      const keyword = listState.value.keyword.toLowerCase()
      result = result.filter(item => {
        const name = (item as any).name?.toLowerCase() || ''
        return name.includes(keyword)
      })
    }

    // 状态筛选
    if (listState.value.state) {
      result = result.filter(item => {
        return (item as any).state === listState.value.state
      })
    }

    return result
  })

  // ======================================
  // Actions - 操作方法
  // ======================================

  /**
   * 获取列表数据
   */
  const fetchList = async (params?: Record<string, any>) => {
    clearError()
    loading.value = true

    try {
      const result = await apiModule.getList(params || {
        page: pagination.value.page,
        pageSize: pagination.value.pageSize,
        ...listState.value
      })

      if (result.success && result.data) {
        if (params?.page === 1) {
          // 第一页，替换数据
          items.value = result.data.items
        } else {
          // 追加数据
          items.value.push(...result.data.items)
        }

        pagination.value.total = result.data.total
      }
    } catch (err) {
      handleError(err, '获取列表失败')
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取详情
   */
  const fetchDetail = async (uuid: string) => {
    clearError()
    loading.value = true

    try {
      const result = await apiModule.getDetail(uuid)

      if (result.success && result.data) {
        selectedItem.value = result.data
      }
    } catch (err) {
      handleError(err, '获取详情失败')
    } finally {
      loading.value = false
    }
  }

  /**
   * 创建
   */
  const create = async (data: any) => {
    clearError()
    loading.value = true

    try {
      const result = await apiModule.create(data)

      if (result.success && result.data) {
        items.value.unshift(result.data)
        pagination.value.total++
        selectedItem.value = null
      }
    } catch (err) {
      handleError(err, '创建失败')
    } finally {
      loading.value = false
    }
  }

  /**
   * 更新
   */
  const update = async (uuid: string, data: any) => {
    clearError()
    loading.value = true

    try {
      const result = await apiModule.update(uuid, data)

      if (result.success && result.data) {
        const index = items.value.findIndex(item => (item as any).uuid === uuid)
        if (index !== -1) {
          items.value[index] = { ...items.value[index], ...result.data }
        }
      }
    } catch (err) {
      handleError(err, '更新失败')
    } finally {
      loading.value = false
    }
  }

  /**
   * 删除
   */
  const remove = async (uuid: string) => {
    clearError()
    loading.value = true

    try {
      const result = await apiModule.delete(uuid)

      if (result.success) {
        items.value = items.value.filter(item => (item as any).uuid !== uuid)
        pagination.value.total--

        if (selectedItem.value?.uuid === uuid) {
          selectedItem.value = null
        }
      }
    } catch (err) {
      handleError(err, '删除失败')
    } finally {
      loading.value = false
    }
  }

  /**
   * 批量删除
   */
  const batchRemove = async (uuids: string[]) => {
    clearError()
    loading.value = true

    try {
      for (const uuid of uuids) {
        await apiModule.delete(uuid)
      }

      items.value = items.value.filter(item => !uuids.includes((item as any).uuid))
      pagination.value.total -= uuids.length

      selectedItem.value = null
    } catch (err) {
      handleError(err, '批量删除失败')
    } finally {
      loading.value = false
    }
  }

  /**
   * 设置筛选条件
   */
  const setFilter = (filter: Partial<ListState>) => {
    Object.assign(listState.value, filter)
    pagination.page = 1
  }

  /**
   * 重置筛选条件
   */
  const resetFilter = () => {
    listState.value = {
      keyword: '',
      state: undefined
    }
    pagination.page = 1
  }

  /**
   * 选择项目
   */
  const select = (item: T) => {
    selectedItem.value = item
  }

  /**
   * 取消选择
   */
  const unselect = () => {
    selectedItem.value = null
  }

  /**
   * 加载更多
   */
  const loadMore = async () => {
    if (!hasMore.value || loading.value) return

    pagination.page++
    await fetchList()
  }

  /**
   * 刷新列表
   */
  const refresh = async () => {
    pagination.page = 1
    await fetchList()
  }

  /**
   * 重置状态
   */
  const reset = () => {
    items.value = []
    selectedItem.value = null
    pagination.value = {
      page: 1,
      pageSize: 20,
      total: 0
    }
    listState.value = {
      keyword: '',
      state: undefined
    }
  }

  return {
    // State
    items,
    loading,
    pagination,
    listState,
    selectedItem,
    hasMore,

    // Computed
    filteredItems,

    // Actions
    fetchList,
    fetchDetail,
    create,
    update,
    remove,
    batchRemove,
    setFilter,
    resetFilter,
    select,
    unselect,
    loadMore,
    reset
  }
}
