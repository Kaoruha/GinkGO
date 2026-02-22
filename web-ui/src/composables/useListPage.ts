/**
 * 列表页通用逻辑 Composable
 * 封装分页、加载、搜索、筛选等通用功能
 */
import { ref, computed, type Ref, type ComputedRef } from 'vue'

/**
 * 列表页配置选项
 */
export interface ListPageOptions<T, P extends Record<string, any>> {
  /** 数据获取函数 */
  fetchFn: (params: P) => Promise<{ data: T[]; total: number }>
  /** 默认每页条数 */
  defaultPageSize?: number
  /** 搜索过滤函数，返回 true 表示匹配 */
  searchFilter?: (item: T, keyword: string) => boolean
}

/**
 * 列表页返回值
 */
export interface ListPageReturn<T, P> {
  // 状态
  loading: Ref<boolean>
  data: Ref<T[]>
  total: Ref<number>
  page: Ref<number>
  size: Ref<number>
  searchKeyword: Ref<string>

  // 计算属性
  pagination: ComputedRef<{
    current: number
    pageSize: number
    total: number
    showSizeChanger: boolean
    showQuickJumper: boolean
    showTotal: (t: number) => string
  }>
  filteredData: ComputedRef<T[]>

  // 方法
  load: (extraParams?: Partial<P>) => Promise<void>
  handleTableChange: (pag: { current: number; pageSize: number }) => void
  createClickRow: (onClick: (record: T) => void) => (record: T) => { style: { cursor: string }; onClick: () => void }
  refresh: () => Promise<void>
}

/**
 * 列表页通用逻辑
 */
export function useListPage<T, P extends Record<string, any> = Record<string, any>>(
  options: ListPageOptions<T, P>
): ListPageReturn<T, P> {
  const {
    fetchFn,
    defaultPageSize = 20,
    searchFilter,
  } = options

  // 基础状态
  const loading = ref(false)
  const data = ref<T[]>([]) as Ref<T[]>
  const total = ref(0)
  const page = ref(0)
  const size = ref(defaultPageSize)
  const searchKeyword = ref('')

  // 分页配置 (Ant Design 格式)
  const pagination = computed(() => ({
    current: page.value + 1,
    pageSize: size.value,
    total: total.value,
    showSizeChanger: true,
    showQuickJumper: true,
    showTotal: (t: number) => `共 ${t} 条`,
  }))

  // 筛选后的数据
  const filteredData = computed(() => {
    if (!searchKeyword.value || !searchFilter) return data.value

    const keyword = searchKeyword.value.toLowerCase()
    return data.value.filter(item => searchFilter(item, keyword))
  })

  // 加载数据
  const load = async (extraParams?: Partial<P>) => {
    loading.value = true
    try {
      const params = {
        page: page.value,
        size: size.value,
        ...extraParams,
      } as P

      const result = await fetchFn(params)
      data.value = result.data || []
      total.value = result.total || 0
    } finally {
      loading.value = false
    }
  }

  // 表格变化处理
  const handleTableChange = (pag: { current: number; pageSize: number }) => {
    page.value = pag.current - 1
    size.value = pag.pageSize
    // 注意：这里不自动调用 load，需要在外部监听变化时手动调用
  }

  // 创建可点击行配置
  const createClickRow = (onClick: (record: T) => void) => {
    return (record: T) => ({
      style: { cursor: 'pointer' },
      onClick: () => onClick(record),
    })
  }

  // 刷新数据
  const refresh = async () => {
    await load()
  }

  return {
    loading,
    data,
    total,
    page,
    size,
    searchKeyword,
    pagination,
    filteredData,
    load,
    handleTableChange,
    createClickRow,
    refresh,
  }
}

/**
 * 搜索过滤器的常用实现
 */
export const commonSearchFilters = {
  /** 按名称和 UUID 搜索 */
  byNameAndUuid: <T extends { name?: string; uuid?: string; run_id?: string }>(item: T, keyword: string) => {
    return (
      item.name?.toLowerCase().includes(keyword) ||
      item.uuid?.toLowerCase().includes(keyword) ||
      item.run_id?.toLowerCase().includes(keyword)
    )
  },

  /** 按名称和描述搜索 */
  byNameAndDesc: <T extends { name?: string; desc?: string }>(item: T, keyword: string) => {
    return (
      item.name?.toLowerCase().includes(keyword) ||
      item.desc?.toLowerCase().includes(keyword)
    )
  },
}
