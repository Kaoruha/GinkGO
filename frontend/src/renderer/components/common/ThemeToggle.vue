<script setup lang="ts">
/**
 * 主题切换按钮 (ADR-045 Codex 视觉语言)
 *
 * - icon button 形态,挂在 App.vue header-right
 * - 当前为 dark 显示月亮,当前为 light 显示太阳
 * - click → toggleTheme
 */
import { computed } from 'vue'
import { useTheme } from '@/composables/useTheme'

const { theme, toggleTheme } = useTheme()

const isDark = computed(() => theme.value === 'dark')

const title = computed(() => isDark.value ? '切换到浅色主题' : '切换到深色主题')
</script>

<template>
  <button
    class="theme-toggle"
    :class="{ 'is-dark': isDark }"
    :title="title"
    :aria-label="title"
    data-testid="theme-toggle"
    @click="toggleTheme"
  >
    <!-- 太阳 (light 主题时显示) -->
    <svg
      v-if="!isDark"
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <circle
        cx="12"
        cy="12"
        r="4"
      />
      <path d="M12 2v2" />
      <path d="M12 20v2" />
      <path d="m4.93 4.93 1.41 1.41" />
      <path d="m17.66 17.66 1.41 1.41" />
      <path d="M2 12h2" />
      <path d="M20 12h2" />
      <path d="m6.34 17.66-1.41 1.41" />
      <path d="m19.07 4.93-1.41 1.41" />
    </svg>
    <!-- 月亮 (dark 主题时显示) -->
    <svg
      v-else
      xmlns="http://www.w3.org/2000/svg"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
    </svg>
  </button>
</template>

<style scoped>
.theme-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  border-radius: var(--radius);
  cursor: pointer;
  transition: color 0.15s ease, background-color 0.15s ease;
}

.theme-toggle:hover {
  color: hsl(var(--foreground));
  background: hsl(var(--accent));
}
</style>
