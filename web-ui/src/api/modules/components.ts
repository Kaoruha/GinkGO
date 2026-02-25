import request from '../request'

export interface ComponentSummary {
  uuid: string
  name: string
  type: string
  component_type: 'strategy' | 'selector' | 'sizer' | 'risk' | 'analyzer'
  description?: string
  version?: string
  is_latest?: boolean
  params?: any[]
  parameters?: any[]
}

export const componentsApi = {
  /**
   * 获取所有组件列表
   */
  async list(): Promise<ComponentSummary[]> {
    const [strategies, selectors, risks, sizers, analyzers] = await Promise.all([
      this.getStrategies(),
      this.getSelectors(),
      this.getRisks(),
      this.getSizers(),
      this.getAnalyzers(),
    ])
    return [...strategies, ...selectors, ...risks, ...sizers, ...analyzers]
  },

  /**
   * 获取策略组件列表
   */
  async getStrategies(): Promise<ComponentSummary[]> {
    const res: any = await request.get('/v1/components/strategies')
    return (res.data || []).map((item: any) => ({ ...item, component_type: 'strategy', parameters: item.params }))
  },

  /**
   * 获取选股器组件列表
   */
  async getSelectors(): Promise<ComponentSummary[]> {
    const res: any = await request.get('/v1/components/selectors')
    return (res.data || []).map((item: any) => ({ ...item, component_type: 'selector', parameters: item.params }))
  },

  /**
   * 获取风控组件列表
   */
  async getRisks(): Promise<ComponentSummary[]> {
    const res: any = await request.get('/v1/components/risks')
    return (res.data || []).map((item: any) => ({ ...item, component_type: 'risk', parameters: item.params }))
  },

  /**
   * 获取仓位组件列表
   */
  async getSizers(): Promise<ComponentSummary[]> {
    const res: any = await request.get('/v1/components/sizers')
    return (res.data || []).map((item: any) => ({ ...item, component_type: 'sizer', parameters: item.params }))
  },

  /**
   * 获取分析器组件列表
   */
  async getAnalyzers(): Promise<ComponentSummary[]> {
    const res: any = await request.get('/v1/components/analyzers')
    return (res.data || []).map((item: any) => ({ ...item, component_type: 'analyzer', parameters: item.params }))
  },

  /**
   * 获取指定组件的所有版本
   */
  async getVersions(name: string, type: number): Promise<ComponentSummary[]> {
    const res: any = await request.get(`/v1/file/${name}/versions?type=${type}`)
    return (res.data || []).map((item: any) => ({ ...item, parameters: item.params }))
  },
}
