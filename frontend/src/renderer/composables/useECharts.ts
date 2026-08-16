/**
 * ECharts 实例生命周期收敛(useECharts)
 *
 * 根因:四处页面/组件各自手写同一套样板——
 *   let chart / resizeObserver;
 *   initChart(){ dispose→echarts.init→ResizeObserver }
 *   updateChart(){ if(!chart) initChart(); chart.setOption(...) }
 *   watch(theme)→重绘; onUnmounted→dispose+disconnect
 * 拷贝四处、细节漂移(window resize vs ResizeObserver、重建 vs notMerge、
 * 空态 dispose vs 占位 title),改一处漏三处。
 *
 * 用法(单图,页面内):
 *   const chartRef = ref<HTMLDivElement>()
 *   const { update } = useECharts(() => chartRef.value, () => buildOption())
 *   watch(data, () => nextTick(update))
 *
 * 语义:
 *   - buildOption 返回 falsy → 释放画布(dispose):空数据不画,由页面 v-if 给占位
 *   - setOption 统一 notMerge=true 全量替换:主题切换后 buildOption 内
 *     cssColor() 重读 token(缓存按 data-theme 失效),一次替换即生效,
 *     不需要 dispose 重建
 *   - chart 实例存 shallowRef(深响应式对 canvas 实例既慢又易触发
 *     无效依赖,同 socket 实例处理)
 *
 * 动态多图(v-for 详情图,无法在 setup 循环调 hook)用底层
 * createChartController 手动管理,页面自持 Map + 卸载时逐个 dispose。
 */

import * as echarts from 'echarts'
import { shallowRef, watch, onUnmounted, nextTick } from 'vue'
import type { ShallowRef } from 'vue'
import { useChartTheme } from './useChartTheme'

export interface ChartController {
  /** 当前实例;未初始化/已释放为 null。shallowRef,勿深读 */
  chart: ShallowRef<echarts.ECharts | null>
  /** 渲染/刷新:el 就绪且 option 非空才画,幂等可重复调 */
  update: () => void
  /** 释放实例与 observer;update 可重新初始化 */
  dispose: () => void
}

export type ChartElGetter = () => HTMLElement | null | undefined

/**
 * 底层单图控制器:无组件生命周期钩子。
 * 适合动态集合(如按窗口数 v-for 的详情图)在运行期创建/销毁;
 * 单图场景直接用 useECharts(自动主题重绘+卸载清理)。
 */
export function createChartController(
  elGetter: ChartElGetter,
  buildOption: () => echarts.EChartsOption | null | undefined,
): ChartController {
  const chart = shallowRef<echarts.ECharts | null>(null)
  let resizeObs: ResizeObserver | null = null

  const dispose = () => {
    resizeObs?.disconnect()
    resizeObs = null
    chart.value?.dispose()
    chart.value = null
  }

  const update = () => {
    const el = elGetter()
    if (!el) return
    const option = buildOption()
    if (!option) {
      // 无可画内容:释放画布(页面用 v-if/EmptyState 给占位)
      dispose()
      return
    }
    if (!chart.value) {
      chart.value = echarts.init(el)
      resizeObs = new ResizeObserver(() => chart.value?.resize())
      resizeObs.observe(el)
    }
    chart.value.setOption(option, true)
  }

  return { chart, update, dispose }
}

/**
 * 单图 hook:在 controller 之上绑定
 *   - 主题切换 → nextTick 重绘(token 重读 + notMerge 全量替换)
 *   - onUnmounted → 自动 dispose
 * elGetter 惰性求值,模板 ref 未挂载时 update 是 no-op。
 */
export function useECharts(
  elGetter: ChartElGetter,
  buildOption: () => echarts.EChartsOption | null | undefined,
): ChartController {
  const controller = createChartController(elGetter, buildOption)
  const { theme } = useChartTheme()
  watch(theme, () => nextTick(controller.update))
  onUnmounted(controller.dispose)
  return controller
}
