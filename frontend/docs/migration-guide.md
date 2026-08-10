# shadcn-vue 迁移指南

本文档提供了从 Ant Design Vue 迁移到 shadcn-vue 的详细指南和最佳实践。

## 目录

1. [快速开始](#快速开始)
2. [组件迁移](#组件迁移)
3. [样式迁移](#样式迁移)
4. [常见问题](#常见问题)
5. [最佳实践](#最佳实践)

---

## 快速开始

### 1. 导入组件

shadcn-vue 组件采用按需导入方式：

```vue
<script setup lang="ts">
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
</script>

<template>
  <Card>
    <CardContent>
      <Input placeholder="输入内容" />
      <Button>提交</Button>
      <Badge>标签</Badge>
    </CardContent>
  </Card>
</template>
```

### 2. 统一导出

也可以从统一入口导入：

```vue
<script setup lang="ts">
import { Button, Card, Input, Label, Badge } from '@/components/ui'
</script>
```

---

## 组件迁移

### Button 按钮迁移

#### Ant Design Vue
```vue
<a-button type="primary" :loading="loading" @click="handleSubmit">
  提交
</a-button>
<a-button danger>删除</a-button>
<a-button type="dashed">虚线按钮</a-button>
<a-button disabled>禁用</a-button>
```

#### shadcn-vue
```vue
<Button variant="default" :loading="loading" @click="handleSubmit">
  提交
</Button>
<Button variant="destructive">删除</Button>
<Button variant="outline" class="border-dashed">虚线按钮</Button>
<Button disabled>禁用</Button>
```

#### 变体对照表

| Ant Design | shadcn-vue |
|------------|------------|
| type="primary" | variant="default" |
| type="default" | variant="outline" |
| type="text" | variant="ghost" |
| type="link" | variant="link" |
| danger | variant="destructive" |

---

### Input 输入框迁移

#### 基础输入框

**Ant Design Vue**:
```vue
<a-input v-model:value="value" placeholder="请输入" />
<a-input-password v-model:value="password" />
```

**shadcn-vue**:
```vue
<Input v-model="value" placeholder="请输入" />
<Input v-model="password" type="password" />
```

#### 输入框验证

**Ant Design Vue**:
```vue
<a-form-item label="用户名" name="username" :rules="[{ required: true }]">
  <a-input v-model:value="form.username" />
</a-form-item>
```

**shadcn-vue (配合 VeeValidate)**:
```vue
<FormField v-slot="{ componentField }" name="username">
  <FormItem>
    <FormLabel>用户名</FormLabel>
    <FormControl>
      <Input v-bind="componentField" />
    </FormControl>
    <FormMessage />
  </FormItem>
</FormField>
```

---

### Badge/Tag 标签迁移

#### Ant Design Vue
```vue
<a-tag color="blue">蓝色</a-tag>
<a-tag color="green">绿色</a-tag>
<a-tag color="red">红色</a-tag>
<a-tag color="orange">橙色</a-tag>
```

#### shadcn-vue
```vue
<Badge variant="info">蓝色</Badge>
<Badge variant="success">绿色</Badge>
<Badge variant="destructive">红色</Badge>
<Badge variant="warning">橙色</Badge>
```

---

### Modal/Dialog 对话框迁移

#### Ant Design Vue
```vue
<script setup>
import { ref } from 'vue'

const visible = ref(false)

const handleOk = () => {
  console.log('确定')
  visible.value = false
}
</script>

<template>
  <a-button @click="visible = true">打开</a-button>

  <a-modal
    v-model:open="visible"
    title="对话框"
    @ok="handleOk"
  >
    <p>对话框内容</p>
  </a-modal>
</template>
```

#### shadcn-vue (使用 SimpleDialog)
```vue
<script setup>
import { ref } from 'vue'

const visible = ref(false)

const handleOk = () => {
  console.log('确定')
  visible.value = false
}
</script>

<template>
  <Button @click="visible = true">打开</Button>

  <SimpleDialog
    v-model:open="visible"
    title="对话框"
  >
    <p>对话框内容</p>
    <template #footer>
      <div class="flex justify-end gap-2">
        <Button variant="outline" @click="visible = false">取消</Button>
        <Button @click="handleOk">确定</Button>
      </div>
    </template>
  </SimpleDialog>
</template>
```

---

### Card 卡片迁移

#### Ant Design Vue
```vue
<a-card title="标题" :bordered="false">
  <p>内容</p>
  <template #extra>
    <a-button>操作</a-button>
  </template>
</a-card>
```

#### shadcn-vue
```vue
<Card>
  <CardHeader>
    <div class="flex justify-between items-center">
      <CardTitle>标题</CardTitle>
      <Button>操作</Button>
    </div>
  </CardHeader>
  <CardContent>
    <p>内容</p>
  </CardContent>
</Card>
```

---

## 样式迁移

### 颜色系统

#### CSS 变量映射

```css
/* Ant Design Vue (Less) */
@primary-color: #1890ff;
@success-color: #52c41a;
@warning-color: #faad14;
@error-color: #f5222d;

/* shadcn-vue (CSS 变量) */
--primary: 221.2 83.2% 53.3%;    /* #1890ff */
--success: 142.1 76.2% 36.3%;    /* #52c41a */
--warning: 38 92% 50%;           /* #faad14 */
--destructive: 0 84.2% 60.2%;    /* #f5222d */
```

#### 使用方式

```vue
<!-- Tailwind 类名 -->
<div class="bg-primary text-primary-foreground">主色背景</div>
<div class="text-success">成功文本</div>
<div class="border-destructive">危险边框</div>
```

### 间距系统

shadcn-vue 使用 Tailwind 的间距系统，与 Ant Design 略有不同：

| Ant Design | Tailwind | 像素值 |
|------------|----------|--------|
| xs | gap-1 | 4px |
| sm | gap-2 | 8px |
| md | gap-4 | 16px |
| lg | gap-6 | 24px |
| xl | gap-8 | 32px |

### 圆角

shadcn-vue 使用 CSS 变量控制圆角：

```css
:root {
  --radius: 0.5rem; /* 默认圆角 */
}
```

使用时：
```vue
<div class="rounded-lg">大圆角</div>
<div class="rounded-md">中圆角</div>
<div class="rounded-sm">小圆角</div>
```

---

## 常见问题

### Q1: 如何处理表单验证？

**A**: shadcn-vue 本身不提供表单验证，推荐使用以下库之一：

1. **VeeValidate** - Vue 3 生态主流验证库
2. **Zod** + `vee-validate-zod` - 类型安全的验证

示例：
```vue
<script setup>
import { useForm } from 'vee-validate'
import { z } from 'zod'
import { toTypedSchema } from '@vee-validate/zod'

const schema = toTypedSchema(z.object({
  username: z.string().min(1, '请输入用户名'),
  email: z.string().email('请输入有效邮箱'),
}))

const { handleSubmit } = useForm({ validationSchema: schema })

const onSubmit = handleSubmit(values => {
  console.log(values)
})
</script>
```

### Q2: 如何实现表格组件？

**A**: 对于简单表格，可以使用 HTML `<table>` + Tailwind；对于复杂表格，建议继续使用 Ant Design Vue 的 Table 组件。

### Q3: 如何实现日期选择器？

**A**: shadcn-vue 提供了基于 Radix Vue 的 Calendar 组件，但功能有限。建议继续使用 Ant Design Vue 的 DatePicker，或考虑 `@vueuse/core` + `date-fns` 自建。

### Q4: 两套组件库样式会冲突吗？

**A**: 不会。shadcn-vue 使用 CSS 变量，Ant Design Vue 使用 Less 变量和作用域样式，互不干扰。

### Q5: 如何处理暗色模式？

**A**:
```vue
<script setup>
import { useDark } from '@vueuse/core'

const isDark = useDark()
</script>

<template>
  <div :class="{ dark: isDark }">
    <Card>内容</Card>
  </div>
</template>
```

---

## 最佳实践

### 1. 渐进式迁移

不要一次性重构整个应用，按模块逐步迁移：

1. 新功能优先使用 shadcn-vue
2. 重构时迁移相关组件
3. 保留复杂组件（Table、Select 等）

### 2. 组件封装

针对常用场景封装复合组件：

```vue
<!-- FormField.vue -->
<template>
  <div class="space-y-2">
    <Label>{{ label }}</Label>
    <Input v-model="innerValue" v-bind="$attrs" />
    <p v-if="error" class="text-sm text-destructive">{{ error }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps<{
  modelValue: string
  label: string
  error?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const innerValue = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})
</script>
```

### 3. 样式一致性

创建统一的设计令牌，确保两套组件库视觉一致：

```css
/* design-tokens.css */
:root {
  --primary: 221.2 83.2% 53.3%; /* 与 Ant Design #1890ff 一致 */
  /* ... 其他令牌 */
}
```

### 4. 可访问性

shadcn-vue 基于 Radix Vue，天然支持可访问性：

- 键盘导航
- ARIA 标签
- 焦点管理

确保自定义组件也遵循这些标准。

### 5. 性能优化

- 使用 `defineAsyncComponent` 按需加载组件
- 合理使用 `v-memo` 优化列表渲染
- 大表格使用虚拟滚动

---

## 参考资源

- [shadcn-vue 官方文档](https://www.shadcn-vue.com/)
- [Radix Vue 文档](https://www.radix-vue.com/)
- [Tailwind CSS 文档](https://tailwindcss.com/)
- [VueUse 文档](https://vueuse.org/)
