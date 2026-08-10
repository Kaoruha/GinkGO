/**
 * 通用随机工具(登录页模拟数据/动画延时复用)。
 * 阶段 5 从 Login.vue 抽取:纯函数,无 reactive 依赖。
 */

/** [min, max] 闭区间随机整数 */
export const rand = (min: number, max: number): number =>
  Math.floor(Math.random() * (max - min + 1)) + min

/** 从数组随机取一元素 */
export const pick = <T>(arr: T[]): T =>
  arr[Math.floor(Math.random() * arr.length)]

/** [min, max) 随机浮点(打字机/动画延时用) */
export const randomRange = (min: number, max: number): number =>
  min + Math.random() * (max - min)
