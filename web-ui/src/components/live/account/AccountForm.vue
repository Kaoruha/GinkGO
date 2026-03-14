<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  DialogRoot,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from '@/components/ui/dialog'
import { X, AlertCircle } from 'lucide-vue-next'

// Props 定义
interface Account {
  uuid?: string
  name: string
  exchange: 'okx' | 'binance'
  environment: 'testnet' | 'production'
  api_key: string
  api_secret: string
  passphrase?: string
  description?: string
}

interface Props {
  open: boolean
  account?: Account
}

const props = withDefaults(defineProps<Props>(), {
  open: false,
})

const emit = defineEmits<{
  'update:open': [value: boolean]
  submit: [account: Account]
}>()

// 表单数据
const formData = reactive<Account>({
  name: '',
  exchange: 'okx',
  environment: 'testnet',
  api_key: '',
  api_secret: '',
  passphrase: '',
  description: ''
})

// 表单状态
const errors = ref<Record<string, string>>({})
const touched = ref<Record<string, boolean>>({})
const isSubmitting = ref(false)
const validationResult = ref<{ success: boolean; message: string } | null>(null)

// 是否为编辑模式
const isEdit = computed(() => !!props.account?.uuid)

// 监听 account 变化，填充表单
watch(() => props.account, (account) => {
  if (account) {
    Object.assign(formData, {
      uuid: account.uuid,
      name: account.name,
      exchange: account.exchange,
      environment: account.environment,
      description: account.description || '',
      api_key: '',
      api_secret: '',
      passphrase: account.passphrase || ''
    })
  } else {
    resetForm()
  }
}, { immediate: true })

// 监听 open 变化，重置表单
watch(() => props.open, (open) => {
  if (!open) {
    resetForm()
  }
})

// 表单验证
const validateField = (field: keyof Account): string | null => {
  const value = formData[field]

  switch (field) {
    case 'name':
      if (!value || typeof value !== 'string' || value.trim() === '') {
        return '请输入账号名称'
      }
      if (value.length > 50) {
        return '账号名称不能超过50个字符'
      }
      break

    case 'exchange':
      if (!value || (value !== 'okx' && value !== 'binance')) {
        return '请选择交易所'
      }
      break

    case 'environment':
      if (!value || (value !== 'testnet' && value !== 'production')) {
        return '请选择环境'
      }
      break

    case 'api_key':
      if (!value || typeof value !== 'string' || value.trim() === '') {
        return '请输入API Key'
      }
      break

    case 'api_secret':
      if (!value || typeof value !== 'string' || value.trim() === '') {
        return '请输入API Secret'
      }
      break

    case 'passphrase':
      if (formData.exchange === 'okx' && (!value || typeof value !== 'string' || value.trim() === '')) {
        return 'OKX需要Passphrase'
      }
      break
  }

  return null
}

const validateForm = (): boolean => {
  const fields: (keyof Account)[] = ['name', 'exchange', 'environment', 'api_key', 'api_secret', 'passphrase']
  let isValid = true

  fields.forEach(field => {
    const error = validateField(field)
    if (error) {
      errors.value[field] = error
      isValid = false
    }
  })

  return isValid
}

// 处理输入变化
const handleInput = (field: keyof Account, value: string) => {
  ;(formData as any)[field] = value
  touched.value[field] = true

  const error = validateField(field)
  if (error) {
    errors.value[field] = error
  } else {
    delete errors.value[field]
  }
}

// 处理失去焦点
const handleBlur = (field: keyof Account) => {
  touched.value[field] = true
  const error = validateField(field)
  if (error) {
    errors.value[field] = error
  }
}

// 重置表单
const resetForm = () => {
  Object.assign(formData, {
    uuid: undefined,
    name: '',
    exchange: 'okx',
    environment: 'testnet',
    api_key: '',
    api_secret: '',
    passphrase: '',
    description: ''
  })
  errors.value = {}
  touched.value = {}
  validationResult.value = null
}

// 提交表单
const handleSubmit = async () => {
  if (!validateForm()) {
    return
  }

  isSubmitting.value = true

  try {
    // 触发提交事件，父组件处理实际提交逻辑
    emit('submit', { ...formData })

    // 关闭对话框
    emit('update:open', false)
  } catch (error) {
    console.error('提交失败:', error)
  } finally {
    isSubmitting.value = false
  }
}

// 计算错误状态
const hasErrors = computed(() => Object.keys(errors.value).length > 0)
</script>

<template>
  <DialogRoot :open="open" @update:open="emit('update:open', $event)">
    <DialogPortal>
      <DialogOverlay />
      <DialogContent class="sm:max-w-[600px]">
        <button
          class="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
          @click="emit('update:open', false)"
        >
          <X class="h-4 w-4" />
          <span class="sr-only">关闭</span>
        </button>

        <DialogHeader>
          <DialogTitle>{{ isEdit ? '编辑账号' : '添加账号' }}</DialogTitle>
        </DialogHeader>

        <form @submit.prevent="handleSubmit" class="space-y-4">
          <!-- 账号名称 -->
          <div class="space-y-2">
            <Label for="name">账号名称 <span class="text-destructive">*</span></Label>
            <Input
              id="name"
              name="name"
              v-model="formData.name"
              placeholder="输入账号名称"
              :class="{ 'border-destructive': errors.name }"
              @blur="handleBlur('name')"
              @input="handleInput('name', $event)"
            />
            <p v-if="errors.name" class="text-sm text-destructive flex items-center gap-1">
              <AlertCircle class="h-3 w-3" />
              {{ errors.name }}
            </p>
          </div>

          <!-- 交易所 -->
          <div class="space-y-2">
            <Label for="exchange">交易所 <span class="text-destructive">*</span></Label>
            <div class="flex gap-2">
              <button
                type="button"
                :class="[
                  'flex-1 px-4 py-2 rounded-md border transition-colors',
                  formData.exchange === 'okx'
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-background border-input hover:bg-accent'
                ]"
                @click="handleInput('exchange', 'okx')"
              >
                OKX
              </button>
              <button
                type="button"
                :class="[
                  'flex-1 px-4 py-2 rounded-md border transition-colors',
                  formData.exchange === 'binance'
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-background border-input hover:bg-accent'
                ]"
                @click="handleInput('exchange', 'binance')"
              >
                Binance
              </button>
            </div>
          </div>

          <!-- 环境 -->
          <div class="space-y-2">
            <Label for="environment">环境 <span class="text-destructive">*</span></Label>
            <div class="flex gap-2">
              <button
                type="button"
                :class="[
                  'flex-1 px-4 py-2 rounded-md border transition-colors',
                  formData.environment === 'testnet'
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-background border-input hover:bg-accent'
                ]"
                @click="handleInput('environment', 'testnet')"
              >
                测试网
              </button>
              <button
                type="button"
                :class="[
                  'flex-1 px-4 py-2 rounded-md border transition-colors',
                  formData.environment === 'production'
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-background border-input hover:bg-accent'
                ]"
                @click="handleInput('environment', 'production')"
              >
                生产环境
              </button>
            </div>
            <p v-if="formData.environment === 'production'" class="text-sm text-warning flex items-center gap-1">
              <AlertCircle class="h-3 w-3" />
              生产环境使用真实资金进行交易，请谨慎操作
            </p>
          </div>

          <div class="border-t pt-4">
            <h4 class="text-sm font-medium mb-4">API凭证</h4>

            <!-- API Key -->
            <div class="space-y-2">
              <Label for="api_key">API Key <span class="text-destructive">*</span></Label>
              <Input
                id="api_key"
                name="api_key"
                v-model="formData.api_key"
                type="password"
                placeholder="输入API Key"
                :class="{ 'border-destructive': errors.api_key }"
                @blur="handleBlur('api_key')"
                @input="handleInput('api_key', $event)"
              />
              <p v-if="errors.api_key" class="text-sm text-destructive flex items-center gap-1">
                <AlertCircle class="h-3 w-3" />
                {{ errors.api_key }}
              </p>
            </div>

            <!-- API Secret -->
            <div class="space-y-2 mt-4">
              <Label for="api_secret">API Secret <span class="text-destructive">*</span></Label>
              <Input
                id="api_secret"
                name="api_secret"
                v-model="formData.api_secret"
                type="password"
                placeholder="输入API Secret"
                :class="{ 'border-destructive': errors.api_secret }"
                @blur="handleBlur('api_secret')"
                @input="handleInput('api_secret', $event)"
              />
              <p v-if="errors.api_secret" class="text-sm text-destructive flex items-center gap-1">
                <AlertCircle class="h-3 w-3" />
                {{ errors.api_secret }}
              </p>
            </div>

            <!-- Passphrase (OKX only) -->
            <div v-if="formData.exchange === 'okx'" class="space-y-2 mt-4">
              <Label for="passphrase">Passphrase <span class="text-destructive">*</span></Label>
              <Input
                id="passphrase"
                name="passphrase"
                v-model="formData.passphrase"
                type="password"
                placeholder="输入Passphrase (OKX需要)"
                :class="{ 'border-destructive': errors.passphrase }"
                @blur="handleBlur('passphrase')"
                @input="handleInput('passphrase', $event)"
              />
              <p v-if="errors.passphrase" class="text-sm text-destructive flex items-center gap-1">
                <AlertCircle class="h-3 w-3" />
                {{ errors.passphrase }}
              </p>
            </div>
          </div>

          <!-- 描述 -->
          <div class="space-y-2">
            <Label for="description">描述</Label>
            <textarea
              id="description"
              v-model="formData.description"
              rows="3"
              placeholder="账号描述（可选）"
              class="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            />
          </div>

          <!-- 按钮 -->
          <div class="flex justify-end gap-2 pt-4">
            <DialogClose as-child>
              <Button type="button" variant="outline">取消</Button>
            </DialogClose>
            <Button type="submit" :disabled="hasErrors || isSubmitting" :loading="isSubmitting">
              {{ isEdit ? '保存' : '创建' }}
            </Button>
          </div>
        </form>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

<style scoped>
/* 自定义样式补充 */
button:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: 2px;
}
</style>
