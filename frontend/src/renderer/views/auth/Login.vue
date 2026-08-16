<template>
  <link
    href="https://fonts.googleapis.com/css2?family=Silkscreen:wght@400;700&display=swap"
    rel="stylesheet"
  >

  <div class="login-container">
    <!-- 开机日志 - 左下角 -->
    <div class="boot-log">
      <div
        v-for="(line, index) in displayLines"
        :key="index"
        class="boot-line"
      >
        <span class="boot-line-text">{{ line }}</span>
      </div>
      <span class="boot-cursor">_</span>
    </div>

    <!-- 像素网格背景 -->
    <div class="pixel-grid" />

    <!-- 浮动粒子 -->
    <div class="particles">
      <div
        v-for="i in 20"
        :key="i"
        class="particle"
        :style="getParticleStyle(i)"
      />
    </div>

    <!-- 股票代码滚动条 -->
    <div class="stock-ticker">
      <div
        class="ticker-content"
        :style="{ animationDuration: tickerDuration + 's' }"
      >
        <span
          v-for="(stock, index) in stockList"
          :key="index"
          class="stock-item"
        >
          <span class="stock-code">{{ stock.code }}</span>
          <span
            class="stock-price"
            :class="stock.change >= 0 ? 'up' : 'down'"
          >
            {{ stock.price.toFixed(2) }}
          </span>
          <span
            class="stock-change"
            :class="stock.change >= 0 ? 'up' : 'down'"
          >
            {{ stock.change >= 0 ? '+' : '' }}{{ stock.change.toFixed(2) }}%
          </span>
        </span>
      </div>
    </div>

    <!-- 登录卡片 -->
    <div
      class="login-card"
      :style="cardStyle"
      @mousemove="handleCardMouseMove"
      @mouseleave="handleCardMouseLeave"
    >
      <div class="login-card-header">
        <div class="logo-wrapper">
          <div class="pixel-logo">
            <span class="letter">G</span>
          </div>
        </div>
        <h1
          class="title"
          :class="{ 'glitching': isGlitching }"
        >
          <span
            class="glitch-text"
            data-text="GINKGO"
          >GINKGO</span>
        </h1>
        <div class="terminal-display">
          <span class="prompt">$</span>
          <span class="terminal-text">{{ displayText }}</span>
          <span
            class="cursor"
            :class="{ 'cursor-visible': showCursor }"
          >_</span>
        </div>
      </div>

      <form
        class="login-form"
        data-testid="login-form"
        @submit.prevent="handleLogin"
      >
        <div class="input-group">
          <label
            class="input-label"
            for="username"
          >&gt; username</label>
          <div class="pixel-input-wrapper">
            <input
              id="username"
              v-model="formState.username"
              type="text"
              placeholder="enter username"
              autocomplete="off"
              :class="{ 'has-error': errors.username }"
              data-testid="username-input"
            >
          </div>
          <span
            v-if="errors.username"
            class="error-message"
            data-testid="username-error"
          >{{ errors.username }}</span>
        </div>

        <div class="input-group">
          <label
            class="input-label"
            for="password"
          >&gt; password</label>
          <div class="pixel-input-wrapper password-wrapper">
            <input
              id="password"
              v-model="formState.password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="enter password"
              :class="{ 'has-error': errors.password }"
              data-testid="password-input"
            >
            <button
              type="button"
              class="password-toggle"
              :aria-label="showPassword ? 'Hide password' : 'Show password'"
              data-testid="password-toggle"
              @click="showPassword = !showPassword"
            >
              <svg
                v-if="showPassword"
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
                <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
                <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
                <line
                  x1="2"
                  x2="22"
                  y1="2"
                  y2="22"
                />
              </svg>
              <svg
                v-else
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
                <circle
                  cx="12"
                  cy="12"
                  r="3"
                />
              </svg>
            </button>
          </div>
          <span
            v-if="errors.password"
            class="error-message"
            data-testid="password-error"
          >{{ errors.password }}</span>
        </div>

        <button
          type="submit"
          class="login-btn"
          :disabled="loading"
          data-testid="login-submit"
        >
          <span v-if="!loading">[ EXECUTE ]</span>
          <span v-else>LOADING...</span>
        </button>
      </form>

      <!-- Toast 消息 -->
      <div
        v-if="toastMessage"
        class="toast-message"
        :class="toastType"
        data-testid="toast"
      >
        {{ toastMessage }}
      </div>

      <div class="card-footer">
        <div class="terminal-output">
          <span class="comment">// Demo: admin / admin123</span>
        </div>
      </div>
    </div>

    <!-- 底部装饰 -->
    <div class="footer-text">
      <span class="version">v0.11.0</span>
      <span class="separator">|</span>
      <span class="copyright">© 2024 Ginkgo Quant</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { rand, pick, randomRange } from '@/utils/random'
import { bootSequence, stocks, terminalMessages } from './loginConstants'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const loading = ref(false)
const showPassword = ref(false)
const formState = reactive({
  username: '',
  password: ''
})
const errors = reactive({
  username: '',
  password: ''
})

// Toast 消息
const toastMessage = ref('')
const toastType = ref<'success' | 'error'>('success')
let toastTimer: number | null = null

function showToast(message: string, type: 'success' | 'error' = 'success') {
  toastMessage.value = message
  toastType.value = type
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => {
    toastMessage.value = ''
  }, 3000)
}

// 卡片鼠标追踪
const mouseX = ref(50)
const mouseY = ref(50)
const lightOffset = ref(0)

const cardStyle = computed(() => ({
  '--mouse-x': `${mouseX.value}%`,
  '--mouse-y': `${mouseY.value}%`,
  '--light-offset': `${lightOffset.value}px`,
}))

function handleCardMouseMove(e: MouseEvent) {
  const target = e.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  const xPercent = ((e.clientX - rect.left) / rect.width) * 100
  mouseX.value = xPercent
  mouseY.value = ((e.clientY - rect.top) / rect.height) * 100
  lightOffset.value = (xPercent - 50) * 0.3
}

function handleCardMouseLeave() {
  mouseX.value = 50
  lightOffset.value = 0
}

// ========== 开机日志 ==========
const displayLines = ref<string[]>([])
let currentLine = ''
let currentCharIndex = 0
let pendingLines: string[] = []
let bootTimer: number | null = null
let isBootComplete = false

const randomEvents = [
  () => `> Heartbeat OK [${timestamp()}]`,
  () => `> Market data stream: ${rand(800, 1500)} msg/s`,
  () => `> Cache hit rate: ${rand(90, 98)}.${rand(0, 9)}%`,
  () => `> Strategy Alpha-V3: scanning ${rand(1000, 2000)} symbols...`,
  () => `> Signal detected: ${pick(['AAPL', 'GOOGL', 'MSFT', 'NVDA', 'TSLA'])} ${pick(['LONG', 'SHORT'])}`,
  () => `> Backtest progress: ${rand(10, 99)}.${rand(0, 9)}%`,
  () => `> Factor IC updated: ${(rand(1, 5) * 0.01).toFixed(4)}`,
  () => `> Order filled: ${rand(100, 500)} shares @ ${rand(100, 500)}.${rand(0, 99)}`,
  () => `> Position rebalanced: ${pick(['+', '-'])}${pick(['AAPL', 'GOOGL', 'TSLA', 'NVDA'])}`,
  () => `> Risk check passed: exposure ${rand(60, 95) / 100}`,
  () => `> CPU: ${rand(15, 45)}% | MEM: ${rand(3, 6)}.${rand(0, 9)}GB`,
  () => `> Worker pool: ${rand(3, 4)}/4 active`,
  () => `> Network latency: ${rand(1, 15)}ms`,
]

function timestamp() {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')} ${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`
}

function startBootLog() {
  pendingLines = [...bootSequence]
  typeNextLine()
}

function typeNextLine() {
  if (pendingLines.length === 0) {
    if (!isBootComplete) {
      isBootComplete = true
    }
    scheduleRandomEvent()
    return
  }

  currentLine = pendingLines.shift()!
  currentCharIndex = 0
  displayLines.value.push('')
  typeCurrentLine()
}

function typeCurrentLine() {
  if (currentCharIndex < currentLine.length) {
    const lineIndex = displayLines.value.length - 1
    displayLines.value[lineIndex] = currentLine.slice(0, currentCharIndex + 1)
    currentCharIndex++
    bootTimer = window.setTimeout(typeCurrentLine, 8 + Math.random() * 17)
  } else {
    if (displayLines.value.length > 8) {
      displayLines.value.shift()
    }
    bootTimer = window.setTimeout(typeNextLine, isBootComplete ? 1500 + Math.random() * 3000 : 100 + Math.random() * 200)
  }
}

function scheduleRandomEvent() {
  bootTimer = window.setTimeout(() => {
    const event = randomEvents[rand(0, randomEvents.length - 1)]()
    pendingLines.push(event)
    typeNextLine()
  }, 1500 + Math.random() * 3000)
}

// ========== Logo 故障效果 ==========
const isGlitching = ref(false)
let glitchTimer: number | null = null

function triggerGlitch() {
  if (Math.random() < 0.3) {
    isGlitching.value = true
    setTimeout(() => {
      isGlitching.value = false
    }, 100 + Math.random() * 200)
  }
  glitchTimer = window.setTimeout(triggerGlitch, 2000 + Math.random() * 5000)
}

// ========== 股票代码滚动 ==========
const stockList = computed(() => {
  return [...stocks, ...stocks, ...stocks].map(s => ({
    ...s,
    price: s.price + (Math.random() - 0.5) * 2,
    change: s.change + (Math.random() - 0.5) * 0.5
  }))
})

const tickerDuration = computed(() => stockList.value.length * 0.5)

// ========== 终端打字机效果 ==========
const displayText = ref('')
const showCursor = ref(true)
let messageIndex = 0
let charIndex = 0
let isTyping = true
let typewriterTimer: number | null = null
let pauseTimer: number | null = null

function startTypewriter() {
  function type() {
    if (isTyping) {
      if (charIndex < terminalMessages[messageIndex].length) {
        displayText.value += terminalMessages[messageIndex][charIndex]
        charIndex++
        typewriterTimer = window.setTimeout(type, randomRange(80, 200))
      } else {
        isTyping = false
        pauseTimer = window.setTimeout(() => {
          clearText()
        }, randomRange(1500, 4000))
      }
    }
  }

  function clearText() {
    function erase() {
      if (displayText.value.length > 0) {
        displayText.value = displayText.value.slice(0, -1)
        typewriterTimer = window.setTimeout(erase, randomRange(10, 25))
      } else {
        messageIndex = (messageIndex + 1) % terminalMessages.length
        charIndex = 0
        isTyping = true
        typewriterTimer = window.setTimeout(type, randomRange(300, 800))
      }
    }
    erase()
  }

  type()
}

function getParticleStyle(_index: number) {
  const left = Math.random() * 100
  const delay = Math.random() * 20
  const duration = 15 + Math.random() * 10
  const size = 2 + Math.random() * 4
  return {
    left: `${left}%`,
    animationDelay: `${delay}s`,
    animationDuration: `${duration}s`,
    width: `${size}px`,
    height: `${size}px`,
  }
}

function validateForm(): boolean {
  let isValid = true
  errors.username = ''
  errors.password = ''

  if (!formState.username.trim()) {
    errors.username = 'required'
    isValid = false
  }

  if (!formState.password) {
    errors.password = 'required'
    isValid = false
  }

  return isValid
}

async function handleLogin() {
  if (!validateForm()) {
    return
  }

  loading.value = true
  try {
    await authStore.login(formState)
    showToast('Login successful!', 'success')
    const redirect = (route.query.redirect as string) || '/'
    setTimeout(() => {
      router.push(redirect)
    }, 500)
  } catch (error: any) {
    showToast(error.message || 'Authentication failed', 'error')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  startBootLog()
  startTypewriter()
  triggerGlitch()
})

onUnmounted(() => {
  if (bootTimer) clearTimeout(bootTimer)
  if (typewriterTimer) clearTimeout(typewriterTimer)
  if (pauseTimer) clearTimeout(pauseTimer)
  if (glitchTimer) clearTimeout(glitchTimer)
  if (toastTimer) clearTimeout(toastTimer)
})
</script>

<style>
/* ========== 登录页双主题 CSS 变量 (ADR-045 §5 登录页双主题) ========== */
/* 与 ThemeToggle / useTheme 协作: 切 document.documentElement.classList 的 .dark */
/* 结构保留: BIOS/粒子/跑马灯/故障字/终端/像素输入 class 全部不动,仅调色 */

/* 深色版默认 (ADR-045 §1 深色优先) */
html {
  --login-bg: #0a0a0f;
  --login-fg: #ffffff;
  --login-title-fg: #ffffff;
  --login-card-bg: rgba(15, 15, 25, 0.9);
  --login-card-border: #2a2a3e;
  --login-input-bg: #0d0d15;
  --login-input-border: #3a3a4e;
  --login-muted: #8a8a9a;
  /* 霓虹色降饱和: 保留色相识别(绿仍是绿/红仍是红),只降饱和度+调亮度向 Codex 中性灰靠
     用户约束 "登录页风格尽可能保留" — 不极端去色,保留赛博朋克终端结构
     具体色值待用户截图校准 (ADR-045 Consequences) */
  --login-neon: #3ddc89;          /* 原 #00ff88 hsl(150 100% 50%) → hsl(149 69% 55%) */
  --login-neon-alt: #2db878;      /* 原 #00cc6a hsl(150 100% 40%) → hsl(152 61% 45%) */
  --login-neon-end: #238f5d;      /* 原 #00aa55 hsl(150 100% 33%) → hsl(152 61% 35%) */
  --login-neon-rgb: 61, 220, 137;
  --login-error: #e5536b;         /* 原 #ff4757 hsl(355 100% 64%) → hsl(350 74% 61%) */
  --login-error-rgb: 229, 83, 107;
  --login-accent-magenta: #c960a6;/* 原 #ff0080 hsl(330 100% 50%) → hsl(320 49% 58%) */
  --login-accent-cyan: #4cb8c0;   /* 原 #00ffff hsl(180 100% 50%) → hsl(184 48% 53%) */
  --login-ticker-bg: rgba(10, 10, 15, 0.95);
  --login-ticker-border: #1a1a2e;
  --login-separator: #5a5a6a;
  --login-card-shadow-bg: rgba(0, 0, 0, 0.5);
}

/* 浅色版: html 上无 .dark 时(用户主动切浅色,终端风浅色化) */
html:not(.dark) {
  --login-bg: #f6f7f8;
  --login-fg: #1f2328;
  --login-title-fg: #1f2328;
  --login-card-bg: rgba(255, 255, 255, 0.92);
  --login-card-border: #d0d7de;
  --login-input-bg: #ffffff;
  --login-input-border: #d0d7de;
  --login-muted: #57606a;
  /* 浅色版终端风: 降饱和绿/红/紫/蓝,在浅 bg 上仍可读(更深主色) */
  --login-neon: #1a7f4e;          /* 浅 bg 上的深绿(降饱和保留绿相) */
  --login-neon-alt: #2da566;
  --login-neon-end: #207a55;
  --login-neon-rgb: 26, 127, 78;
  --login-error: #cf222e;         /* Codex 浅色红 */
  --login-error-rgb: 207, 34, 46;
  --login-accent-magenta: #8250df;/* Codex 紫(替代品红,浅 bg 友好) */
  --login-accent-cyan: #0969da;   /* Codex 蓝(替代青,浅 bg 友好) */
  --login-ticker-bg: rgba(255, 255, 255, 0.95);
  --login-ticker-border: #d0d7de;
  --login-separator: #8c959f;
  --login-card-shadow-bg: rgba(0, 0, 0, 0.08);
}
</style>

<style scoped>
/* ========== 头部 ========== */
.login-card-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

/* ========== 开机日志 - 左下角 ========== */
.boot-log {
  position: fixed;
  bottom: 16px;
  left: 16px;
  font-family: 'Silkscreen', monospace;
  font-size: 11px;
  color: var(--login-neon);
  text-align: left;
  z-index: 100;
  opacity: 0.35;
  pointer-events: none;
}

.boot-line {
  margin-bottom: 4px;
}

.boot-line-text {
  opacity: 0;
  animation: fadeIn 0.3s forwards;
}

.boot-cursor {
  animation: blink 0.5s infinite;
}

@keyframes fadeIn {
  to { opacity: 1; }
}

/* ========== 主容器 ========== */
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--login-bg);
  position: relative;
  overflow: hidden;
  padding-top: 40px;
}

/* ========== 像素网格背景 ========== */
.pixel-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(var(--login-neon-rgb), 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(var(--login-neon-rgb), 0.03) 1px, transparent 1px);
  background-size: 20px 20px;
  pointer-events: none;
}

/* ========== 浮动粒子 ========== */
.particles {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.particle {
  position: absolute;
  bottom: -10px;
  background: var(--login-neon);
  opacity: 0;
  animation: float-up linear infinite;
}

@keyframes float-up {
  0% {
    opacity: 0;
    transform: translateY(0) scale(1);
  }
  10% {
    opacity: 0.6;
  }
  90% {
    opacity: 0.2;
  }
  100% {
    opacity: 0;
    transform: translateY(-100vh) scale(0.5);
  }
}

/* ========== 股票代码滚动条 ========== */
.stock-ticker {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 28px;
  background: var(--login-ticker-bg);
  border-bottom: 1px solid var(--login-ticker-border);
  overflow: hidden;
  display: flex;
  align-items: center;
  z-index: 100;
}

.ticker-content {
  display: flex;
  gap: 40px;
  animation: ticker-scroll linear infinite;
  white-space: nowrap;
}

@keyframes ticker-scroll {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(-33.33%);
  }
}

.stock-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'Silkscreen', monospace;
  font-size: 11px;
}

.stock-code {
  color: var(--login-muted);
}

.stock-price {
  font-weight: bold;
}

.stock-price.up {
  color: var(--login-neon);
}

.stock-price.down {
  color: var(--login-error);
}

.stock-change {
  font-size: 10px;
}

.stock-change.up {
  color: var(--login-neon);
}

.stock-change.down {
  color: var(--login-error);
}

/* ========== 登录卡片 ========== */
.login-card {
  width: 380px;
  background: var(--login-card-bg);
  border: 1px solid var(--login-card-border);
  border-radius: var(--radius-sm);
  padding: 40px;
  position: relative;
  z-index: 10;
  box-shadow:
    0 0 0 1px rgba(var(--login-neon-rgb), 0.1),
    0 20px 50px var(--login-card-shadow-bg),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  --mouse-x: 50%;
  --mouse-y: 50%;
  --light-offset: 0px;
}

.login-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--login-neon), transparent);
  transform: translateX(var(--light-offset));
  opacity: 0.8;
  transition: transform 0.15s ease-out;
}

.login-card::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(
    circle 200px at var(--mouse-x) var(--mouse-y),
    rgba(var(--login-neon-rgb), 0.06) 0%,
    transparent 50%
  );
  pointer-events: none;
  border-radius: var(--radius-sm);
}

/* ========== 头部 ========== */

.logo-wrapper {
  margin-bottom: 16px;
}

.pixel-logo {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, var(--login-neon), var(--login-neon-alt));
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  box-shadow:
    0 0 20px rgba(var(--login-neon-rgb), 0.3),
    inset 0 -2px 0 rgba(0, 0, 0, 0.2);
}

.pixel-logo .letter {
  font-size: 28px;
  font-weight: 700;
  color: var(--login-bg);
  font-family: 'Silkscreen', monospace;
}

/* ========== Logo 故障效果 ========== */
.title {
  font-size: 24px;
  font-weight: 700;
  color: var(--login-title-fg);
  letter-spacing: 8px;
  margin: 0;
  font-family: 'Silkscreen', monospace;
  text-shadow: 0 0 20px rgba(var(--login-neon-rgb), 0.5);
  position: relative;
}

.glitch-text {
  position: relative;
  display: inline-block;
}

.title.glitching .glitch-text {
  animation: glitch 0.3s ease;
}

.title.glitching .glitch-text::before,
.title.glitching .glitch-text::after {
  content: attr(data-text);
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.title.glitching .glitch-text::before {
  color: var(--login-accent-magenta);
  animation: glitch-1 0.2s ease;
  clip-path: polygon(0 0, 100% 0, 100% 45%, 0 45%);
  transform: translateX(-3px);
}

.title.glitching .glitch-text::after {
  color: var(--login-accent-cyan);
  animation: glitch-2 0.2s ease;
  clip-path: polygon(0 55%, 100% 55%, 100% 100%, 0 100%);
  transform: translateX(3px);
}

@keyframes glitch {
  0%, 100% { transform: translateX(0); }
  20% { transform: translateX(-2px); }
  40% { transform: translateX(2px); }
  60% { transform: translateX(-1px); }
  80% { transform: translateX(1px); }
}

@keyframes glitch-1 {
  0%, 100% { transform: translateX(-3px); opacity: 0.8; }
  50% { transform: translateX(2px); opacity: 0.5; }
}

@keyframes glitch-2 {
  0%, 100% { transform: translateX(3px); opacity: 0.8; }
  50% { transform: translateX(-2px); opacity: 0.5; }
}

/* ========== 终端显示 ========== */
.terminal-display {
  margin-top: 20px;
  font-family: 'Silkscreen', monospace;
  font-size: 14px;
  color: var(--login-neon);
  min-height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.terminal-display .prompt {
  margin-right: 8px;
}

.terminal-display .terminal-text {
  color: var(--login-muted);
}

.terminal-display .cursor {
  color: var(--login-neon);
  margin-left: 2px;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* ========== 表单 ========== */
.login-form {
  margin-top: 24px;
  position: relative;
}

.input-group {
  margin-bottom: 20px;
}

.input-label {
  display: block;
  color: var(--login-neon);
  font-family: 'Silkscreen', monospace;
  font-size: 12px;
  font-weight: 400;
  margin-bottom: 8px;
  letter-spacing: 1px;
}

.error-message {
  display: block;
  color: var(--login-error);
  font-family: 'Silkscreen', monospace;
  font-size: 10px;
  margin-top: 4px;
}

/* ========== 输入框 ========== */
.pixel-input-wrapper {
  position: relative;
}

.pixel-input-wrapper input {
  width: 100%;
  background: var(--login-input-bg);
  border: 1px solid var(--login-input-border);
  color: var(--login-fg);
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 14px;
  height: 40px;
  padding: 0 12px;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
  box-sizing: border-box;
}

.pixel-input-wrapper input::placeholder {
  color: var(--login-muted);
}

.pixel-input-wrapper input:focus {
  outline: none;
  border-color: var(--login-neon);
  box-shadow: 0 0 0 2px rgba(var(--login-neon-rgb), 0.1);
}

.pixel-input-wrapper input.has-error {
  border-color: var(--login-error);
}

.pixel-input-wrapper input.has-error:focus {
  box-shadow: 0 0 0 2px rgba(var(--login-error-rgb), 0.1);
}

/* 密码输入框 */
.pixel-input-wrapper.password-wrapper {
  display: flex;
  align-items: center;
}

.pixel-input-wrapper.password-wrapper input {
  flex: 1;
  padding-right: 40px;
}

.password-toggle {
  position: absolute;
  right: 8px;
  background: none;
  border: none;
  padding: 8px;
  cursor: pointer;
  color: var(--login-muted);
  transition: color 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.password-toggle:hover {
  color: var(--login-neon);
}

.password-toggle svg {
  width: 16px;
  height: 16px;
}

/* ========== Toast 消息 ========== */
.toast-message {
  position: absolute;
  top: -60px;
  left: 0;
  right: 0;
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  font-family: 'Silkscreen', monospace;
  font-size: 12px;
  text-align: center;
  animation: slideDown 0.3s ease;
  z-index: 10;
}

.toast-message.success {
  background: rgba(var(--login-neon-rgb), 0.9);
  color: var(--login-bg);
}

.toast-message.error {
  background: rgba(var(--login-error-rgb), 0.9);
  color: var(--login-fg);
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ========== 登录按钮 ========== */
.login-btn {
  width: 100%;
  height: 44px;
  background: linear-gradient(135deg, var(--login-neon), var(--login-neon-alt));
  border: none;
  border-radius: var(--radius-sm);
  color: var(--login-bg);
  font-family: 'Silkscreen', monospace;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 2px;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 8px;
}

.login-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, var(--login-neon-alt), var(--login-neon-end));
  transform: translateY(-1px);
  box-shadow: 0 4px 20px rgba(var(--login-neon-rgb), 0.3);
}

.login-btn:active:not(:disabled) {
  transform: translateY(0);
}

.login-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* ========== 底部 ========== */

.terminal-output {
  font-family: 'Silkscreen', monospace;
  font-size: 11px;
}

.comment {
  color: var(--login-muted);
}

/* ========== 页脚 ========== */
.footer-text {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  font-family: 'Silkscreen', monospace;
  font-size: 10px;
  color: var(--login-muted);
  display: flex;
  gap: 12px;
}

.separator {
  color: var(--login-separator);
}
</style>
