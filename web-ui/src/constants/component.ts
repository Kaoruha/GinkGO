/**
 * 组件相关常量
 */

/** 组件类型 */
export const COMPONENT_TYPES = {
  STRATEGY: 'STRATEGY',
  SELECTOR: 'SELECTOR',
  SIZER: 'SIZER',
  RISKMANAGER: 'RISKMANAGER',
  ANALYZER: 'ANALYZER'
} as const

export type ComponentType = typeof COMPONENT_TYPES[keyof typeof COMPONENT_TYPES]

/** 组件类型标签映射 */
export const COMPONENT_TYPE_LABELS: Record<string, string> = {
  STRATEGY: '策略',
  SELECTOR: '选股器',
  SIZER: 'Sizer',
  RISKMANAGER: '风控',
  ANALYZER: '分析器'
}

/** 组件类型颜色映射 */
export const COMPONENT_TYPE_COLORS: Record<string, string> = {
  STRATEGY: 'blue',
  SELECTOR: 'green',
  SIZER: 'orange',
  RISKMANAGER: 'red',
  ANALYZER: 'purple'
}

/** FILE_TYPES 到组件类型的映射 */
const FILE_TYPE_TO_COMPONENT: Record<string, string> = {
  '1': 'STRATEGY',
  '3': 'RISKMANAGER',
  '4': 'SELECTOR',
  '5': 'SIZER',
  '6': 'STRATEGY',
  STRATEGY: 'STRATEGY',
  SELECTOR: 'SELECTOR',
  SIZER: 'SIZER',
  RISKMANAGER: 'RISKMANAGER',
}

/**
 * 获取组件类型标签
 */
export function getComponentTypeLabel(type: string): string {
  return COMPONENT_TYPE_LABELS[type] || type
}

/**
 * 获取组件类型颜色
 */
export function getComponentTypeColor(type: string): string {
  return COMPONENT_TYPE_COLORS[type] || 'default'
}

/**
 * 从文件类型获取组件类型
 */
export function getComponentTypeFromFileType(fileType: string | number): string {
  const key = String(fileType)
  return FILE_TYPE_TO_COMPONENT[key] || 'UNKNOWN'
}
