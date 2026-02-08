/**
 * 组件参数类型定义
 */

// ==================== 参数类型枚举 ====================

/**
 * 参数类型枚举
 */
export enum ParamType {
  INT = 'int',
  FLOAT = 'float',
  STRING = 'string',
  BOOL = 'bool',
  LIST = 'list',
  DICT = 'dict'
}

// ==================== 组件参数类型 ====================

/**
 * 组件参数定义
 */
export interface ComponentParameter {
  name: string                      // 参数名（代码中使用）
  display_name: string              // 显示名称（前端显示）
  type: ParamType                   // 参数类型
  default_value?: any               // 默认值
  description: string               // 参数描述
  required?: boolean                // 是否必需
  min_value?: number                // 最小值（数值类型）
  max_value?: number                // 最大值（数值类型）
  options?: any[]                   // 可选值（枚举类型）
}

/**
 * 组件配置（前后端共享）
 */
export interface ComponentConfig {
  component_uuid: string            // 组件 UUID
  component_name: string            // 组件名称
  component_type: string            // 组件类型（STRATEGY, SELECTOR, SIZER, RISKMANAGER, ANALYZER）
  parameters: Record<string, any>   // 参数键值对
}

// ==================== 组件摘要和详情 ====================

/**
 * 组件摘要
 */
export interface ComponentSummary {
  uuid: string
  name: string
  component_type: string            // strategy, analyzer, risk, sizer, selector
  file_type: number
  description?: string
  created_at: string
  updated_at?: string
  is_active: boolean
}

/**
 * 组件详情
 */
export interface ComponentDetail {
  uuid: string
  name: string
  component_type: string
  file_type: number
  code?: string
  description?: string
  parameters: Array<{ [key: string]: any }>
  created_at: string
  updated_at?: string
}

/**
 * 创建组件请求
 */
export interface ComponentCreate {
  name: string
  component_type: string            // strategy, analyzer, risk, sizer, selector
  code: string
  description?: string
}

/**
 * 更新组件请求
 */
export interface ComponentUpdate {
  name?: string
  code?: string
  description?: string
  parameters?: Record<string, any>
}

// ==================== 组件参数元数据映射 ====================

/**
 * 所有组件参数定义映射
 */
export type ComponentParameterDefinitions = Record<string, ComponentParameter[]>

/**
 * 验证错误项
 */
export interface ValidationError {
  field: string                     // 字段名
  message: string                   // 错误消息
  value?: any                       // 错误值
}

/**
 * 验证结果
 */
export interface ValidationResult {
  is_valid: boolean                 // 是否有效
  errors: ValidationError[]         // 错误列表
  warnings: string[]                // 警告列表
}
