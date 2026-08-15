import { reactive } from 'vue'

/** 右键菜单项(divider 为分隔线,其余字段见名知义) */
export interface MenuItem {
  label?: string
  danger?: boolean
  disabled?: boolean
  /** 分隔线占位项 */
  divider?: boolean
  /** 点击后弹确认框,确认才执行 action(危险操作免逐页写确认弹窗) */
  confirm?: string
  action?: () => void
}

interface ContextMenuState {
  visible: boolean
  /** 鼠标指针视口坐标 */
  x: number
  y: number
  items: MenuItem[]
}

// 模块级单例:全应用共享一个菜单实例(ContextMenu.vue 挂 App.vue)
const state = reactive<ContextMenuState>({ visible: false, x: 0, y: 0, items: [] })

/**
 * OS 风格右键菜单(一期:PortfolioList 落地,后续页面逐步迁移)。
 * 用法:在目标元素 @contextmenu="openCtx($event, items)"。
 * open 内部 preventDefault;未被拦截的 contextmenu 由 ContextMenu.vue 统一屏蔽浏览器默认菜单
 * (input/textarea 保留原生,以保住粘贴等输入体验)。
 */
export function useContextMenu() {
  const open = (e: MouseEvent, items: MenuItem[]) => {
    e.preventDefault()
    state.x = e.clientX
    state.y = e.clientY
    state.items = items
    state.visible = true
  }
  const close = () => { state.visible = false }
  return { state, open, close }
}
