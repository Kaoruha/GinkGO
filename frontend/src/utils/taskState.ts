/**
 * 任务状态相关的常量和工具函数
 * 用于统一任务状态判断逻辑
 */

/**
 * 任务状态枚举
 */
export enum TaskState {
  CREATED = 'CREATED',
  PENDING = 'PENDING',
  RUNNING = 'RUNNING',
  PAUSED = 'PAUSED',
  COMPLETED = 'COMPLETED',
  STOPPED = 'STOPPED',
  FAILED = 'FAILED',
  ERROR = 'ERROR'
}

/**
 * 活跃状态集合（任务正在进行中）
 */
const ACTIVE_STATES = [TaskState.RUNNING, TaskState.PENDING, TaskState.CREATED]

/**
 * 终止状态集合（任务已结束）
 */
const TERMINAL_STATES = [TaskState.COMPLETED, TaskState.FAILED, TaskState.STOPPED, TaskState.ERROR]

/**
 * 可停止状态集合
 */
const STOPPABLE_STATES = [TaskState.RUNNING, TaskState.PENDING, TaskState.CREATED]

/**
 * 可重启状态集合
 */
const RESTARTABLE_STATES = [TaskState.FAILED, TaskState.STOPPED, TaskState.ERROR]

/**
 * 判断任务是否处于活跃状态
 * @param state 任务状态
 * @returns 是否为活跃状态
 */
export function isTaskActive(state: string | number): boolean {
  return ACTIVE_STATES.includes(String(state).toUpperCase() as TaskState)
}

/**
 * 判断任务是否处于终止状态
 * @param state 任务状态
 * @returns 是否为终止状态
 */
export function isTaskTerminal(state: string | number): boolean {
  return TERMINAL_STATES.includes(String(state).toUpperCase() as TaskState)
}

/**
 * 判断任务是否可以停止
 * @param state 任务状态
 * @returns 是否可停止
 */
export function isTaskStoppable(state: string | number): boolean {
  return STOPPABLE_STATES.includes(String(state).toUpperCase() as TaskState)
}

/**
 * 判断任务是否可以重启
 * @param state 任务状态
 * @returns 是否可重启
 */
export function isTaskRestartable(state: string | number): boolean {
  return RESTARTABLE_STATES.includes(String(state).toUpperCase() as TaskState)
}

/**
 * 判断任务是否已完成
 * @param state 任务状态
 * @returns 是否已完成
 */
export function isTaskCompleted(state: string | number): boolean {
  return String(state).toUpperCase() === TaskState.COMPLETED
}

/**
 * 判断任务是否失败
 * @param state 任务状态
 * @returns 是否失败
 */
export function isTaskFailed(state: string | number): boolean {
  const stateUpper = String(state).toUpperCase()
  return stateUpper === TaskState.FAILED || stateUpper === TaskState.ERROR
}

/**
 * 获取任务的下一个合法状态转换
 * @param currentState 当前状态
 * @param action 操作类型 ('start', 'stop', 'pause', 'resume')
 * @returns 目标状态，如果转换不合法则返回 null
 */
export function getNextValidState(currentState: string | number, action: 'start' | 'stop' | 'pause' | 'resume'): TaskState | null {
  const state = String(currentState).toUpperCase() as TaskState

  switch (action) {
    case 'start':
      if (isTaskRestartable(state)) return TaskState.RUNNING
      break
    case 'stop':
      if (isTaskStoppable(state)) return TaskState.STOPPED
      break
    case 'pause':
      if (state === TaskState.RUNNING) return TaskState.PAUSED
      break
    case 'resume':
      if (state === TaskState.PAUSED) return TaskState.RUNNING
      break
  }

  return null
}

/**
 * 状态颜色映射（用于UI展示）
 */
export const STATE_COLORS: Record<string, string> = {
  [TaskState.RUNNING]: 'text-blue-600',
  [TaskState.PENDING]: 'text-yellow-600',
  [TaskState.CREATED]: 'text-gray-600',
  [TaskState.PAUSED]: 'text-orange-600',
  [TaskState.COMPLETED]: 'text-green-600',
  [TaskState.STOPPED]: 'text-gray-500',
  [TaskState.FAILED]: 'text-red-600',
  [TaskState.ERROR]: 'text-red-600'
}

/**
 * 获取状态对应的颜色类名
 * @param state 任务状态
 * @returns Tailwind CSS 类名
 */
export function getStateColor(state: string | number): string {
  return STATE_COLORS[String(state).toUpperCase()] || 'text-gray-600'
}