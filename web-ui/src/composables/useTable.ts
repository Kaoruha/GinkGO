import { ref, computed } from 'vue'

export interface TableColumn {
  key: string
  title: string
  width?: number
  align?: 'left' | 'center' | 'right'
  render?: (value: unknown, record: Record<string, unknown>) => unknown
}

export interface TableFetchParams {
  page: number
  page_size: number
  [key: string]: unknown
}

export function useTable<T>(fetchFn: (params: TableFetchParams) => Promise<{ items: T[]; total: number }>) {
  const data = ref<T[]>([])
  const total = ref(0)
  const loading = ref(false)
  const currentPage = ref(1)
  const pageSize = ref(20)

  const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

  async function fetch(params?: Record<string, unknown>) {
    loading.value = true
    try {
      const result = await fetchFn({
        page: currentPage.value,
        page_size: pageSize.value,
        ...params
      })
      data.value = result.items as T[]
      total.value = result.total
    } finally {
      loading.value = false
    }
  }

  function changePage(page: number) {
    currentPage.value = page
    fetch()
  }

  function changeSize(size: number) {
    pageSize.value = size
    currentPage.value = 1
    fetch()
  }

  function refresh() {
    fetch()
  }

  return {
    data,
    total,
    loading,
    currentPage,
    pageSize,
    totalPages,
    fetch,
    changePage,
    changeSize,
    refresh
  }
}
