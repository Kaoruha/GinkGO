<template>
  <Teleport to="body">
    <Transition name="ctx">
      <div
        v-if="state.visible"
        ref="menuRef"
        class="context-menu"
        :style="{ left: pos.x + 'px', top: pos.y + 'px' }"
        data-testid="context-menu"
      >
        <template v-for="(item, i) in state.items" :key="i">
          <div v-if="item.divider" class="ctx-divider"></div>
          <button
            v-else
            class="ctx-item"
            :class="{ danger: item.danger }"
            :disabled="item.disabled"
            @click="invoke(item)"
          >{{ item.label }}</button>
        </template>
      </div>
    </Transition>

    <!-- 危险操作确认(item.confirm 非空时先确认再执行) -->
    <ConfirmDialog
      v-model:open="confirmOpen"
      :title="`确认${pendingItem?.label || '操作'}`"
      :description="pendingItem?.confirm"
      danger
      :confirm-text="pendingItem?.label || '确定'"
      @confirm="runPending"
    />
  </Teleport>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, onMounted, onUnmounted } from 'vue'
import { useContextMenu, type MenuItem } from '@/composables/useContextMenu'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const { state, close } = useContextMenu()
const menuRef = ref<HTMLElement>()
const pos = ref({ x: 0, y: 0 })

// confirm 菜单项:先弹确认,确认后执行 action
const confirmOpen = ref(false)
const pendingItem = ref<MenuItem | null>(null)
const runPending = () => {
  confirmOpen.value = false
  pendingItem.value?.action?.()
  pendingItem.value = null
}

// 弹出后测量实际尺寸做视口翻转(贴右缘翻左/贴下缘翻上),模拟 OS 菜单不溢出屏幕
watch(() => state.visible, async v => {
  if (!v) return
  await nextTick()
  const el = menuRef.value
  if (!el) return
  pos.value = {
    x: Math.max(8, Math.min(state.x, window.innerWidth - el.offsetWidth - 8)),
    y: Math.max(8, Math.min(state.y, window.innerHeight - el.offsetHeight - 8)),
  }
})

const invoke = (item: MenuItem) => {
  close()
  if (item.confirm) {
    pendingItem.value = item
    confirmOpen.value = true
    return
  }
  item.action?.()
}

const onWindowClick = () => close()
const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
const onViewportChange = () => close()

// 全站右键屏蔽:未被页面 open() 拦截的 contextmenu 到此统一处理。
// defaultPrevented = 页面已接管(开自定义菜单);输入类元素放行原生(复制/粘贴)
const onContextMenu = (e: MouseEvent) => {
  if (e.defaultPrevented) return
  const t = e.target as HTMLElement
  if (t.closest('input, textarea, [contenteditable="true"]')) return
  e.preventDefault()
  close()
}

onMounted(() => {
  window.addEventListener('click', onWindowClick)
  window.addEventListener('keydown', onKey)
  window.addEventListener('scroll', onViewportChange, true)
  window.addEventListener('resize', onViewportChange)
  window.addEventListener('contextmenu', onContextMenu)
})

onUnmounted(() => {
  window.removeEventListener('click', onWindowClick)
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('scroll', onViewportChange, true)
  window.removeEventListener('resize', onViewportChange)
  window.removeEventListener('contextmenu', onContextMenu)
})
</script>

<style scoped>
.context-menu {
  position: fixed;
  z-index: 2000;
  min-width: 168px;
  padding: 4px;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg);
  transform-origin: top left;
}

.ctx-item {
  width: 100%;
  padding: 6px 10px;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 13px;
  text-align: left;
  cursor: pointer;
}

.ctx-item:hover:not(:disabled) { background: hsl(var(--secondary)); }
.ctx-item:disabled { opacity: 0.4; cursor: not-allowed; }
.ctx-item.danger { color: hsl(var(--error)); }
.ctx-item.danger:hover:not(:disabled) { background: hsl(var(--error) / 0.1); }

.ctx-divider {
  height: 1px;
  margin: 4px 6px;
  background: hsl(var(--border));
}

/* OS 菜单式快速弹出 */
.ctx-enter-active {
  transition: opacity var(--dur-fast, 0.15s) var(--ease-out, ease-out),
              transform var(--dur-fast, 0.15s) var(--ease-out, ease-out);
}
.ctx-leave-active { transition: opacity 0.1s ease; }
.ctx-enter-from { opacity: 0; transform: scale(0.96); }
.ctx-leave-to { opacity: 0; }

@media (prefers-reduced-motion: reduce) {
  .ctx-enter-active, .ctx-leave-active { transition: none; }
}
</style>
