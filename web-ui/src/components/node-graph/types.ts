export type NodeType = 'strategy' | 'selector' | 'sizer' | 'risk'

export interface GraphNode {
  id: string
  type: NodeType
  name: string
  componentId: string
  x: number
  y: number
  params?: any[]
  config?: Record<string, any>
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  sourceHandle?: string
  targetHandle?: string
}

export interface NodeTemplate {
  type: NodeType
  name: string
  componentId: string
  defaultParams?: any[]
}
