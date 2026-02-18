<template>
  <link href="https://fonts.googleapis.com/css2?family=Silkscreen:wght@400;700&display=swap" rel="stylesheet">

  <div class="login-container">
    <!-- 开机日志 - 左下角 -->
    <div class="boot-log">
      <div class="boot-line" v-for="(line, index) in displayLines" :key="index">
        <span class="boot-line-text">{{ line }}</span>
      </div>
      <span class="boot-cursor">_</span>
    </div>

    <!-- 像素网格背景 -->
    <div class="pixel-grid"></div>

    <!-- 浮动粒子 -->
    <div class="particles">
      <div v-for="i in 20" :key="i" class="particle" :style="getParticleStyle(i)"></div>
    </div>

    <!-- 股票代码滚动条 -->
    <div class="stock-ticker">
      <div class="ticker-content" :style="{ animationDuration: tickerDuration + 's' }">
        <span v-for="(stock, index) in stockList" :key="index" class="stock-item">
          <span class="stock-code">{{ stock.code }}</span>
          <span class="stock-price" :class="stock.change >= 0 ? 'up' : 'down'">
            {{ stock.price.toFixed(2) }}
          </span>
          <span class="stock-change" :class="stock.change >= 0 ? 'up' : 'down'">
            {{ stock.change >= 0 ? '+' : '' }}{{ stock.change.toFixed(2) }}%
          </span>
        </span>
      </div>
    </div>

    <!-- 登录卡片 -->
    <div class="login-card" @mousemove="handleCardMouseMove" @mouseleave="handleCardMouseLeave" :style="cardStyle">
      <div class="card-header">
        <div class="logo-wrapper">
          <div class="pixel-logo">
            <span class="letter">G</span>
          </div>
        </div>
        <h1 class="title" :class="{ 'glitching': isGlitching }">
          <span class="glitch-text" data-text="GINKGO">GINKGO</span>
        </h1>
        <div class="terminal-display">
          <span class="prompt">$</span>
          <span class="terminal-text">{{ displayText }}</span>
          <span class="cursor" :class="{ 'cursor-visible': showCursor }">_</span>
        </div>
      </div>

      <a-form :model="formState" layout="vertical" @finish="handleLogin" class="login-form">
        <div class="input-group">
          <label class="input-label">&gt; username</label>
          <a-form-item name="username" :rules="[{ required: true, message: 'required' }]">
            <div class="pixel-input-wrapper">
              <a-input
                v-model:value="formState.username"
                placeholder="enter username"
                autocomplete="off"
              />
            </div>
          </a-form-item>
        </div>

        <div class="input-group">
          <label class="input-label">&gt; password</label>
          <a-form-item name="password" :rules="[{ required: true, message: 'required' }]">
            <div class="pixel-input-wrapper">
              <a-input-password
                v-model:value="formState.password"
                placeholder="enter password"
              />
            </div>
          </a-form-item>
        </div>

        <a-button
          type="primary"
          html-type="submit"
          class="login-btn"
          :loading="loading"
        >
          <span v-if="!loading">[ EXECUTE ]</span>
          <span v-else>LOADING...</span>
        </a-button>
      </a-form>

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
import { message } from 'ant-design-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const loading = ref(false)
const formState = reactive({
  username: '',
  password: ''
})

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
  // 光条偏移：-15px 到 +15px
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

// 初始启动序列
const bootSequence = [
  '> BIOS v2.0.11 initialized',
  '> Memory check: 65536KB OK',
  '> Loading kernel modules...',
  '> Initializing neural network...',
  '> Connecting to market data feed...',
  '> Loading quantitative models...',
  '> System ready.',
]

// 随机事件池
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

function rand(min: number, max: number) {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)]
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
    // 开机完成或事件完成后，调度下一个随机事件
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
    // 逐字打出
    const lineIndex = displayLines.value.length - 1
    displayLines.value[lineIndex] = currentLine.slice(0, currentCharIndex + 1)
    currentCharIndex++
    bootTimer = window.setTimeout(typeCurrentLine, 8 + Math.random() * 17)
  } else {
    // 当前行完成，保持最多 8 行
    if (displayLines.value.length > 8) {
      displayLines.value.shift()
    }
    // 等待后打下一行
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
const stocks = [
  { code: 'AAPL', price: 185.92, change: 2.34 },
  { code: 'GOOGL', price: 141.80, change: -0.89 },
  { code: 'MSFT', price: 378.91, change: 1.56 },
  { code: 'TSLA', price: 248.50, change: -2.15 },
  { code: 'NVDA', price: 495.22, change: 3.78 },
  { code: 'AMZN', price: 178.25, change: 0.67 },
  { code: 'META', price: 505.95, change: 1.23 },
  { code: 'BRK.B', price: 408.32, change: -0.45 },
  { code: 'JPM', price: 198.45, change: 0.89 },
  { code: 'V', price: 279.30, change: 1.12 },
  { code: '000001.SZ', price: 12.85, change: 0.78 },
  { code: '600519.SH', price: 1756.00, change: -1.23 },
  { code: '000858.SZ', price: 168.50, change: 2.45 },
  { code: '601318.SH', price: 45.32, change: -0.56 },
]

const stockList = computed(() => {
  // 复制三份用于无缝滚动
  return [...stocks, ...stocks, ...stocks].map(s => ({
    ...s,
    price: s.price + (Math.random() - 0.5) * 2,
    change: s.change + (Math.random() - 0.5) * 0.5
  }))
})

const tickerDuration = computed(() => stockList.value.length * 0.5)

// ========== 终端打字机效果 ==========
const terminalMessages = [
  'Loading market data...',
  'Analyzing price patterns...',
  'Computing alpha signals...',
  'Backtesting strategy...',
  'Optimizing portfolio allocation...',
  'Monitoring real-time positions...',
  'Calculating risk metrics...',
  'Fetching tick data...',
]

const displayText = ref('')
const showCursor = ref(true)
let messageIndex = 0
let charIndex = 0
let isTyping = true
let typewriterTimer: number | null = null
let pauseTimer: number | null = null

function randomRange(min: number, max: number) {
  return min + Math.random() * (max - min)
}

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

function getParticleStyle(index: number) {
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

async function handleLogin() {
  loading.value = true
  try {
    await authStore.login(formState)
    message.success('Login successful!')
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch (error: any) {
    message.error(error.message || 'Authentication failed')
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
})
</script>

<style scoped>
/* ========== 开机日志 - 左下角 ========== */
.boot-log {
  position: fixed;
  bottom: 16px;
  left: 16px;
  font-family: 'Silkscreen', monospace;
  font-size: 11px;
  color: #00ff88;
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
  background: #0a0a0f;
  position: relative;
  overflow: hidden;
  padding-top: 40px;
}

/* ========== 像素网格背景 ========== */
.pixel-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(0, 255, 136, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 255, 136, 0.03) 1px, transparent 1px);
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
  background: #00ff88;
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
  background: rgba(10, 10, 15, 0.95);
  border-bottom: 1px solid #1a1a2e;
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
  color: #8a8a9a;
}

.stock-price {
  font-weight: bold;
}

.stock-price.up {
  color: #00ff88;
}

.stock-price.down {
  color: #ff4757;
}

.stock-change {
  font-size: 10px;
}

.stock-change.up {
  color: #00ff88;
}

.stock-change.down {
  color: #ff4757;
}

/* ========== 登录卡片 ========== */
.login-card {
  width: 380px;
  background: rgba(15, 15, 25, 0.9);
  border: 1px solid #2a2a3e;
  border-radius: 4px;
  padding: 40px;
  position: relative;
  z-index: 10;
  box-shadow:
    0 0 0 1px rgba(0, 255, 136, 0.1),
    0 20px 50px rgba(0, 0, 0, 0.5),
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
  background: linear-gradient(90deg, transparent, #00ff88, transparent);
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
    rgba(0, 255, 136, 0.06) 0%,
    transparent 50%
  );
  pointer-events: none;
  border-radius: 4px;
}

/* ========== 头部 ========== */
.card-header {
  text-align: center;
  margin-bottom: 32px;
}

.logo-wrapper {
  margin-bottom: 16px;
}

.pixel-logo {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #00ff88, #00cc6a);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  box-shadow:
    0 0 20px rgba(0, 255, 136, 0.3),
    inset 0 -2px 0 rgba(0, 0, 0, 0.2);
}

.pixel-logo .letter {
  font-size: 28px;
  font-weight: 700;
  color: #0a0a0f;
  font-family: 'Silkscreen', monospace;
}

/* ========== Logo 故障效果 ========== */
.title {
  font-size: 24px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: 8px;
  margin: 0;
  font-family: 'Silkscreen', monospace;
  text-shadow: 0 0 20px rgba(0, 255, 136, 0.5);
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
  color: #ff0080;
  animation: glitch-1 0.2s ease;
  clip-path: polygon(0 0, 100% 0, 100% 45%, 0 45%);
  transform: translateX(-3px);
}

.title.glitching .glitch-text::after {
  color: #00ffff;
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
  color: #00ff88;
  min-height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.terminal-display .prompt {
  margin-right: 8px;
}

.terminal-display .terminal-text {
  color: #8a8a9a;
}

.terminal-display .cursor {
  color: #00ff88;
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
}

.input-group {
  margin-bottom: 20px;
}

.input-label {
  display: block;
  color: #00ff88;
  font-family: 'Silkscreen', monospace;
  font-size: 12px;
  font-weight: 400;
  margin-bottom: 8px;
  letter-spacing: 1px;
}

.login-form :deep(.ant-form-item) {
  margin-bottom: 0;
}

.login-form :deep(.ant-form-item-explain-error) {
  color: #ff4757;
  font-family: 'Silkscreen', monospace;
  font-size: 10px;
  margin-top: 4px;
}

/* ========== 输入框 ========== */
.pixel-input-wrapper :deep(.ant-input) {
  background: #0d0d15 !important;
  border: 1px solid #3a3a4e !important;
  color: #ffffff !important;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 14px;
  height: 40px;
  padding: 0 12px;
  border-radius: 4px;
  transition: all 0.2s;
}

.pixel-input-wrapper :deep(.ant-input::placeholder) {
  color: #8a8a9a !important;
}

.pixel-input-wrapper :deep(.ant-input:focus) {
  border-color: #00ff88 !important;
  box-shadow: 0 0 0 2px rgba(0, 255, 136, 0.1) !important;
}

.pixel-input-wrapper :deep(.ant-input-affix-wrapper),
.pixel-input-wrapper :deep(.ant-input-password),
.pixel-input-wrapper :deep(span.ant-input-affix-wrapper) {
  background: #0d0d15 !important;
  border: 1px solid #3a3a4e !important;
  border-radius: 4px !important;
  padding: 0 10px 0 12px !important;
  height: 40px !important;
  line-height: 40px !important;
  transition: all 0.2s;
  display: flex !important;
  align-items: center !important;
  box-sizing: border-box !important;
}

.pixel-input-wrapper :deep(.ant-input-affix-wrapper:hover),
.pixel-input-wrapper :deep(.ant-input-password:hover) {
  border-color: #00ff88 !important;
}

.pixel-input-wrapper :deep(.ant-input-affix-wrapper-focused),
.pixel-input-wrapper :deep(.ant-input-affix-wrapper-focused .ant-input) {
  border-color: #00ff88 !important;
  box-shadow: 0 0 0 2px rgba(0, 255, 136, 0.1) !important;
}

.pixel-input-wrapper :deep(.ant-input-affix-wrapper .ant-input),
.pixel-input-wrapper :deep(.ant-input-password .ant-input) {
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  color: #ffffff !important;
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 14px;
  height: auto !important;
  line-height: normal !important;
  padding: 0 !important;
  flex: 1;
}

.pixel-input-wrapper :deep(.ant-input-affix-wrapper .ant-input::placeholder),
.pixel-input-wrapper :deep(.ant-input-password .ant-input::placeholder) {
  color: #8a8a9a !important;
}

.pixel-input-wrapper :deep(.anticon-eye),
.pixel-input-wrapper :deep(.anticon-eye-invisible) {
  color: #8a8a9a !important;
}

/* ========== 登录按钮 ========== */
.login-btn {
  width: 100%;
  height: 44px;
  background: linear-gradient(135deg, #00ff88, #00cc6a);
  border: none;
  border-radius: 4px;
  color: #0a0a0f;
  font-family: 'Silkscreen', monospace;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 2px;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 8px;
}

.login-btn:hover {
  background: linear-gradient(135deg, #00cc6a, #00aa55);
  transform: translateY(-1px);
  box-shadow: 0 4px 20px rgba(0, 255, 136, 0.3);
}

.login-btn:active {
  transform: translateY(0);
}

/* ========== 底部 ========== */
.card-footer {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #2a2a3e;
}

.terminal-output {
  font-family: 'Silkscreen', monospace;
  font-size: 11px;
}

.comment {
  color: #8a8a9a;
}

/* ========== 页脚 ========== */
.footer-text {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  font-family: 'Silkscreen', monospace;
  font-size: 10px;
  color: #8a8a9a;
  display: flex;
  gap: 12px;
}

.separator {
  color: #5a5a6a;
}
</style>
