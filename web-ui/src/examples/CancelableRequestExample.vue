<!--
  可取消请求示例组件
  展示如何使用 useRequestCancelable 处理组件中的异步请求
-->
<template>
  <div class="cancelable-request-example">
    <a-card title="可取消请求示例" :bordered="false">
      <!-- 控制面板 -->
      <a-space direction="vertical" :size="16" style="width: 100%">
        <a-space>
          <a-button
            type="primary"
            :loading="loading"
            :disabled="loading"
            @click="loadData"
          >
            加载数据
          </a-button>
          <a-button
            v-if="loading"
            danger
            @click="cancelRequest"
          >
            取消请求
          </a-button>
          <a-button
            @click="clearData"
          >
            清空数据
          </a-button>
        </a-space>

        <!-- 状态显示 -->
        <a-alert
          v-if="error"
          type="error"
          :message="error.message"
          show-icon
          closable
          @close="error = null"
        />
        <a-alert
          v-else-if="!loading && portfolios.length === 0"
          type="info"
          message="点击"加载数据"按钮开始"
          show-icon
        />

        <!-- 数据列表 -->
        <a-spin :spinning="loading">
          <a-list
            v-if="portfolios.length > 0"
            :data-source="portfolios"
            :grid="{ gutter: 16, column: 3 }"
          >
            <template #renderItem="{ item }">
              <a-list-item>
                <a-card :title="item.name" size="small">
                  <template #extra>
                    <a-tag :color="getModeColor(item.mode)">
                      {{ getModeLabel(item.mode) }}
                    </a-tag>
                  </template>
                  <p>净值: {{ item.net_value.toFixed(3) }}</p>
                  <p>状态: {{ item.state }}</p>
                </a-card>
              </a-list-item>
            </template>
          </a-list>
        </a-spin>
      </a-space>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { useRequestCancelable } from '@/composables/useRequestCancelable'
import { portfolioApi } from '@/api/modules/portfolio'

// 使用可取消请求 Composable
const { loading, error, execute: loadPortfolios, cancel: cancelRequest } = useRequestCancelable()

// 数据状态
const portfolios = ref<any[]>([])

/**
 * 加载数据
 * 使用 useRequestCancelable 发起可取消的请求
 */
async function loadData() {
  await loadPortfolios(
    (signal) => portfolioApi.list(undefined, { signal }),
    {
      onSuccess: (response) => {
        portfolios.value = response.data || []
        message.success(`成功加载 ${response.data?.length || 0} 条数据`)
      },
      onError: (err) => {
        // 忽略取消操作的错误
        if (err.name !== 'AbortError') {
          message.error(`加载失败: ${err.message}`)
        }
      }
    }
  )
}

/**
 * 清空数据
 */
function clearData() {
  portfolios.value = []
  error.value = null
}

/**
 * 获取模式标签
 */
function getModeLabel(mode: string) {
  const labels: Record<string, string> = {
    BACKTEST: '回测',
    PAPER: '模拟',
    LIVE: '实盘'
  }
  return labels[mode] || mode
}

/**
 * 获取模式颜色
 */
function getModeColor(mode: string) {
  const colors: Record<string, string> = {
    BACKTEST: 'blue',
    PAPER: 'green',
    LIVE: 'orange'
  }
  return colors[mode] || 'default'
}
</script>

<style scoped>
.cancelable-request-example {
  padding: 24px;
}
</style>
