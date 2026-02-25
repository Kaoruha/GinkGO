<<<<<<< HEAD
/**
 * 节点图拖拉拽配置回测功能 - TypeScript 类型定义
 */

// ==================== 节点类型枚举 ====================

/**
 * 节点类型枚举
 */
export enum NodeType {
  ENGINE = 'engine',           // 根节点：回测引擎配置
  FEEDER = 'feeder',           // 数据源：历史数据馈送
  BROKER = 'broker',           // 券商：交易执行
  PORTFOLIO = 'portfolio',     // 投资组合：策略容器
  STRATEGY = 'strategy',       // 策略：信号生成
  SELECTOR = 'selector',       // 选择器：标的筛选
  SIZER = 'sizer',             // 规模器：仓位计算
  RISK_MANAGEMENT = 'risk',    // 风控：风险管理
  ANALYZER = 'analyzer',       // 分析器：性能分析
}

/**
 * 节点类型显示名称映射
 */
export const NODE_TYPE_LABELS: Record<NodeType, string> = {
  [NodeType.ENGINE]: '回测引擎',
  [NodeType.FEEDER]: '数据源',
  [NodeType.BROKER]: '券商',
  [NodeType.PORTFOLIO]: '投资组合',
  [NodeType.STRATEGY]: '策略',
  [NodeType.SELECTOR]: '选择器',
  [NodeType.SIZER]: '规模器',
  [NodeType.RISK_MANAGEMENT]: '风控',
  [NodeType.ANALYZER]: '分析器',
}

// ==================== 端口定义 ====================

/**
 * 端口类型
 */
export type PortType = 'input' | 'output'

/**
 * 端口数据类型
 */
export type PortDataType = 'portfolio' | 'data' | 'execution' | 'orders' | 'fills' | 'signal' | 'target' | 'position' | 'adjusted' | 'metrics'

/**
 * 节点端口定义
 */
export interface NodePort {
  name: string                  // 端口名称
  type: PortType                // 端口类型（输入/输出）
  dataType: PortDataType         // 数据类型
  required?: boolean             // 是否必需连接
  label?: string                 // 显示名称
}

/**
 * 各节点类型的端口配置
 */
export const NODE_PORTS: Record<NodeType, NodePort[]> = {
  [NodeType.ENGINE]: [
    { name: 'portfolio', type: 'output' as const, dataType: 'portfolio' as const, label: '连接到投资组合' },
  ],
  [NodeType.FEEDER]: [
    { name: 'data', type: 'output' as const, dataType: 'data' as const, label: '数据输出' },
  ],
  [NodeType.BROKER]: [
    { name: 'execution', type: 'output' as const, dataType: 'execution' as const, label: '交易执行' },
  ],
  [NodeType.PORTFOLIO]: [
    { name: 'engine', type: 'input' as const, dataType: 'portfolio' as const, required: true, label: '引擎连接' },
    { name: 'strategy', type: 'input' as const, dataType: 'signal' as const, label: '策略信号' },
    { name: 'selector', type: 'input' as const, dataType: 'target' as const, label: '选择器标的' },
    { name: 'sizer', type: 'input' as const, dataType: 'position' as const, label: '规模器仓位' },
    { name: 'risk', type: 'input' as const, dataType: 'adjusted' as const, label: '风控调整' },
    { name: 'analyzer', type: 'input' as const, dataType: 'metrics' as const, label: '分析器指标' },
    { name: 'data', type: 'input' as const, dataType: 'data' as const, label: '数据输入' },
    { name: 'execution', type: 'input' as const, dataType: 'execution' as const, label: '券商执行' },
    { name: 'orders', type: 'output' as const, dataType: 'orders' as const, label: '订单输出' },
    { name: 'fills', type: 'output' as const, dataType: 'fills' as const, label: '成交输出' },
  ],
  [NodeType.STRATEGY]: [
    { name: 'data', type: 'input' as const, dataType: 'data' as const, required: true, label: '数据输入' },
    { name: 'signal', type: 'output' as const, dataType: 'signal' as const, label: '信号输出' },
  ],
  [NodeType.SELECTOR]: [
    { name: 'data', type: 'input' as const, dataType: 'data' as const, required: true, label: '数据输入' },
    { name: 'target', type: 'output' as const, dataType: 'target' as const, label: '标的输出' },
  ],
  [NodeType.SIZER]: [
    { name: 'signal', type: 'input' as const, dataType: 'signal' as const, required: true, label: '信号输入' },
    { name: 'target', type: 'input' as const, dataType: 'target' as const, label: '标的输入' },
    { name: 'position', type: 'output' as const, dataType: 'position' as const, label: '仓位输出' },
  ],
  [NodeType.RISK_MANAGEMENT]: [
    { name: 'position', type: 'input' as const, dataType: 'position' as const, label: '仓位输入' },
    { name: 'signal', type: 'input' as const, dataType: 'signal' as const, label: '信号输入' },
    { name: 'adjusted', type: 'output' as const, dataType: 'adjusted' as const, label: '调整输出' },
  ],
  [NodeType.ANALYZER]: [
    { name: 'orders', type: 'input' as const, dataType: 'orders' as const, label: '订单输入' },
    { name: 'fills', type: 'input' as const, dataType: 'fills' as const, label: '成交输入' },
    { name: 'metrics', type: 'output' as const, dataType: 'metrics' as const, label: '指标输出' },
  ],
}

// ==================== 节点配置类型 ====================

/**
 * Engine 节点配置
 */
export interface EngineConfig {
  start_date: string             // 开始日期 YYYY-MM-DD
  end_date: string               // 结束日期 YYYY-MM-DD
}

/**
 * Broker 节点配置
 */
export interface BrokerConfig {
  broker_type: 'backtest' | 'okx'
  initial_cash: number
  commission_rate: number
  slippage_rate: number
  broker_attitude: 1 | 2 | 3      // 1=PESSIMISTIC, 2=OPTIMISTIC, 3=RANDOM
}

/**
 * Portfolio 节点配置
 */
export interface PortfolioConfig {
  portfolio_uuid: string         // 投资组合 UUID
}

/**
 * 组件节点配置（Strategy/Selector/Sizer/Risk/Analyzer）
 */
export interface ComponentConfig {
  component_uuid: string         // 组件 UUID
  component_params?: Record<string, any>  // 组件参数
}

/**
 * 节点配置联合类型
 */
export type NodeConfig = EngineConfig | BrokerConfig | PortfolioConfig | ComponentConfig

// ==================== 节点数据类型 ====================

/**
 * 节点数据
 */
export interface NodeData {
  label: string                  // 显示名称
  config: NodeConfig             // 节点配置参数
  componentUuid?: string         // 关联组件 UUID
  errors?: string[]              // 验证错误列表
  description?: string           // 节点描述
}

/**
 * 节点位置
 */
export interface NodePosition {
  x: number
  y: number
}

/**
 * 图节点
 */
export interface GraphNode {
  id: string                     // 节点唯一标识
  type: NodeType                 // 节点类型
  position: NodePosition         // 画布位置
  data: NodeData                 // 节点数据
}

// ==================== 连接线类型 ====================

/**
 * 边类型
 */
export type EdgeType = 'default' | 'straight' | 'step' | 'smooth'

/**
 * 图连接线
 */
export interface GraphEdge {
  id: string                     // 连接唯一标识
  source: string                 // 源节点 ID
  target: string                 // 目标节点 ID
  sourceHandle?: string          // 源端口名称
  targetHandle?: string          // 目标端口名称
  type?: EdgeType                // 边类型
  animated?: boolean             // 是否动画
  style?: Record<string, any>    // 自定义样式
}

// ==================== 画布类型 ====================

/**
 * 画布视口状态
 */
export interface Viewport {
  x: number
  y: number
  zoom: number                   // 0.1 - 2
}

/**
 * 画布状态
 */
export interface CanvasState {
  viewport: Viewport
  selectedNodes: string[]        // 选中的节点 ID 列表
  selectedEdges: string[]        // 选中的边 ID 列表
}

// ==================== 节点图类型 ====================

/**
 * 节点图数据
 */
export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  viewport?: Viewport
}

/**
 * 节点图配置（API 返回）
 */
export interface NodeGraph {
  uuid: string
  name: string
  description?: string
  graph_data: GraphData
  user_uuid: string
  version: number
  parent_uuid?: string
  is_template: boolean
  is_public: boolean
  created_at: string
  updated_at: string
}

/**
 * 节点图摘要（列表项）
 */
export interface NodeGraphSummary {
  uuid: string
  name: string
  description?: string
  is_template: boolean
  is_public: boolean
  version: number
  created_at: string
  updated_at: string
}

/**
 * 节点图详情（完整信息）
 */
export interface NodeGraphDetail extends NodeGraph {}

/**
 * 创建节点图请求
 */
export interface NodeGraphCreate {
  name: string
  description?: string
  graph_data: GraphData
  is_template?: boolean
  is_public?: boolean
}

/**
 * 更新节点图请求
 */
export interface NodeGraphUpdate {
  name?: string
  description?: string
  graph_data?: GraphData
  is_template?: boolean
  is_public?: boolean
}

// ==================== 模板类型 ====================

/**
 * 节点图模板
 */
export interface NodeTemplate {
  uuid: string
  name: string
  description?: string
  category?: string
  graph_data: GraphData
  is_system: boolean
  created_at: string
  updated_at: string
}

// ==================== 验证类型 ====================

/**
 * 验证错误
 */
export interface ValidationError {
  node_id?: string
  edge_id?: string
  message: string
  severity: 'error' | 'warning'
}

/**
 * 验证结果
 */
export interface ValidationResult {
  is_valid: boolean
  errors: ValidationError[]
  warnings: string[]
}

// ==================== 编译类型 ====================

/**
 * BacktestTaskCreate 配置（编译输出）
 */
export interface BacktestTaskCreate {
  name: string
  engine_uuid?: string
  portfolio_uuids: string[]
  engine_config: {
    start_date: string
    end_date: string
    broker_type: 'backtest' | 'okx'
    initial_cash: number
    commission_rate: number
    slippage_rate: number
    broker_attitude: number
  }
  component_config?: {
    max_position_ratio?: number
    stop_loss_ratio?: number
    take_profit_ratio?: number
    benchmark_return?: number
    frequency?: string
  }
}

/**
 * 编译结果
 */
export interface CompileResult {
  backtest_config: BacktestTaskCreate
  warnings: string[]
}

// ==================== 连接规则 ====================

/**
 * 连接规则定义
 */
export interface ConnectionRule {
  outputs: NodeType[]             // 允许连接的目标节点类型
  maxOutputs?: number             // 最大输出连接数
}

/**
 * 所有节点类型的连接规则
 */
export const CONNECTION_RULES: Record<NodeType, ConnectionRule> = {
  [NodeType.ENGINE]: {
    outputs: [NodeType.PORTFOLIO],
    maxOutputs: Infinity,
  },
  [NodeType.PORTFOLIO]: {
    outputs: [],
  },
  [NodeType.FEEDER]: {
    outputs: [NodeType.PORTFOLIO, NodeType.STRATEGY, NodeType.SELECTOR],
    maxOutputs: Infinity,
  },
  [NodeType.BROKER]: {
    outputs: [NodeType.PORTFOLIO],
    maxOutputs: 1,
  },
  [NodeType.STRATEGY]: {
    outputs: [NodeType.PORTFOLIO, NodeType.SIZER, NodeType.RISK_MANAGEMENT],
    maxOutputs: Infinity,
  },
  [NodeType.SELECTOR]: {
    outputs: [NodeType.PORTFOLIO, NodeType.SIZER],
    maxOutputs: Infinity,
  },
  [NodeType.SIZER]: {
    outputs: [NodeType.PORTFOLIO, NodeType.RISK_MANAGEMENT],
    maxOutputs: Infinity,
  },
  [NodeType.RISK_MANAGEMENT]: {
    outputs: [NodeType.PORTFOLIO],
    maxOutputs: Infinity,
  },
  [NodeType.ANALYZER]: {
    outputs: [NodeType.PORTFOLIO],
    maxOutputs: Infinity,
  },
}

/**
 * 验证两个节点是否可以连接
 */
export function canConnect(sourceType: NodeType, targetType: NodeType): boolean {
  const rule = CONNECTION_RULES[sourceType]
  return rule.outputs.includes(targetType)
}

/**
 * 获取节点的输入端口
 */
export function getInputPorts(nodeType: NodeType): NodePort[] {
  return NODE_PORTS[nodeType].filter(p => p.type === 'input')
}

/**
 * 获取节点的输出端口
 */
export function getOutputPorts(nodeType: NodeType): NodePort[] {
  return NODE_PORTS[nodeType].filter(p => p.type === 'output')
=======
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
>>>>>>> 011-quant-research
}
