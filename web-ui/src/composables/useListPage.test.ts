/**
 * useListPage composable 单元测试
 */
import { describe, it, expect, vi } from 'vitest'
import { nextTick } from 'vue'
import { useListPage, commonSearchFilters } from './useListPage'

describe('useListPage', () => {
  const mockFetchFn = vi.fn()

  beforeEach(() => {
    mockFetchFn.mockClear()
  })

  it('应初始化默认状态', () => {
    mockFetchFn.mockResolvedValue({ data: [], total: 0 })

    const { loading, data, total, page, size, searchKeyword } = useListPage({
      fetchFn: mockFetchFn,
    })

    expect(loading.value).toBe(false)
    expect(data.value).toEqual([])
    expect(total.value).toBe(0)
    expect(page.value).toBe(0)
    expect(size.value).toBe(20)
    expect(searchKeyword.value).toBe('')
  })

  it('应支持自定义默认页面大小', () => {
    const { size } = useListPage({
      fetchFn: mockFetchFn,
      defaultPageSize: 50,
    })

    expect(size.value).toBe(50)
  })

  it('应生成正确的分页配置', () => {
    const { pagination, total, page, size } = useListPage({
      fetchFn: mockFetchFn,
    })

    total.value = 100
    page.value = 2
    size.value = 20

    expect(pagination.value.current).toBe(3) // page + 1
    expect(pagination.value.pageSize).toBe(20)
    expect(pagination.value.total).toBe(100)
    expect(pagination.value.showSizeChanger).toBe(true)
    expect(pagination.value.showQuickJumper).toBe(true)
  })

  it('load 应调用 fetchFn 并更新状态', async () => {
    const mockData = [{ id: 1, name: 'test' }]
    mockFetchFn.mockResolvedValue({ data: mockData, total: 1 })

    const { load, data, total, loading } = useListPage({
      fetchFn: mockFetchFn,
    })

    await load({ status: 'active' })

    expect(mockFetchFn).toHaveBeenCalledWith({
      page: 0,
      size: 20,
      status: 'active',
    })
    expect(data.value).toEqual(mockData)
    expect(total.value).toBe(1)
    expect(loading.value).toBe(false)
  })

  it('handleTableChange 应更新分页参数', () => {
    const { handleTableChange, page, size } = useListPage({
      fetchFn: mockFetchFn,
    })

    handleTableChange({ current: 3, pageSize: 50 })

    expect(page.value).toBe(2) // current - 1
    expect(size.value).toBe(50)
  })

  it('filteredData 应根据 searchFilter 过滤数据', async () => {
    const mockData = [
      { id: 1, name: 'Apple', uuid: 'a1' },
      { id: 2, name: 'Banana', uuid: 'b2' },
      { id: 3, name: 'Cherry', uuid: 'c3' },
    ]
    mockFetchFn.mockResolvedValue({ data: mockData, total: 3 })

    const { load, data, searchKeyword, filteredData } = useListPage({
      fetchFn: mockFetchFn,
      searchFilter: commonSearchFilters.byNameAndUuid,
    })

    await load()

    // 无搜索词时返回全部数据
    expect(filteredData.value.length).toBe(3)

    // 搜索 'apple'
    searchKeyword.value = 'apple'
    await nextTick()
    expect(filteredData.value.length).toBe(1)
    expect(filteredData.value[0].name).toBe('Apple')

    // 搜索 'a1' (uuid)
    searchKeyword.value = 'a1'
    await nextTick()
    expect(filteredData.value.length).toBe(1)
    expect(filteredData.value[0].uuid).toBe('a1')
  })

  it('createClickRow 应返回正确的行配置', () => {
    const { createClickRow } = useListPage({
      fetchFn: mockFetchFn,
    })

    const onClick = vi.fn()
    const record = { id: 1, name: 'test' }
    const rowConfig = createClickRow(onClick)(record)

    expect(rowConfig.style.cursor).toBe('pointer')
    rowConfig.onClick()
    expect(onClick).toHaveBeenCalledWith(record)
  })

  it('refresh 应重新加载数据', async () => {
    mockFetchFn.mockResolvedValue({ data: [], total: 0 })

    const { refresh } = useListPage({
      fetchFn: mockFetchFn,
    })

    await refresh()

    expect(mockFetchFn).toHaveBeenCalled()
  })
})

describe('commonSearchFilters', () => {
  describe('byNameAndUuid', () => {
    it('应匹配 name', () => {
      const item = { name: 'Apple', uuid: '123', run_id: 'r1' }
      expect(commonSearchFilters.byNameAndUuid(item, 'apple')).toBe(true)
      expect(commonSearchFilters.byNameAndUuid(item, 'ORANGE')).toBe(false)
    })

    it('应匹配 uuid', () => {
      const item = { name: 'Test', uuid: 'abc123', run_id: 'r1' }
      expect(commonSearchFilters.byNameAndUuid(item, 'abc')).toBe(true)
      expect(commonSearchFilters.byNameAndUuid(item, 'xyz')).toBe(false)
    })

    it('应匹配 run_id', () => {
      const item = { name: 'Test', uuid: '123', run_id: 'BT_2024' }
      expect(commonSearchFilters.byNameAndUuid(item, '2024')).toBe(true)
    })
  })

  describe('byNameAndDesc', () => {
    it('应匹配 name', () => {
      const item = { name: 'Portfolio A', desc: 'Description' }
      expect(commonSearchFilters.byNameAndDesc(item, 'portfolio')).toBe(true)
    })

    it('应匹配 desc', () => {
      const item = { name: 'Test', desc: 'This is a test portfolio' }
      expect(commonSearchFilters.byNameAndDesc(item, 'test')).toBe(true)
    })
  })
})
