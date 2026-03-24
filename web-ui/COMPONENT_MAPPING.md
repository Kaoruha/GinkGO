# Ant Design Vue → shadcn-vue 组件映射表

本文档提供了从 Ant Design Vue 4.1 迁移到 shadcn-vue 的组件映射参考。

## 概述

- **策略**: 渐进式迁移，混合使用两套组件库
- **原则**: 新功能优先 shadcn-vue，复杂表格保留 Ant Design
- **兼容性**: 两套组件库可以无缝共存

---

## 核心组件映射

### 按钮组件

| Ant Design Vue | shadcn-vue | 迁移优先级 | 备注 |
|----------------|------------|-----------|------|
| `<a-button>` | `<Button>` | **高** | 样式和 API 高度一致 |
| type="primary" | variant="default" | - | 默认变体对应 |
| type="default" | variant="outline" | - | 次要按钮 |
| type="dashed" | variant="outline" + 样式 | - | 需自定义虚线边框 |
| danger | variant="destructive" | - | 危险操作 |
| loading | :loading="true" | - | 相同 API |

**示例对比**:
```vue
<!-- Ant Design Vue -->
<a-button type="primary" :loading="loading">提交</a-button>
<a-button danger>删除</a-button>

<!-- shadcn-vue -->
<Button variant="default" :loading="loading">提交</Button>
<Button variant="destructive">删除</Button>
```

---

### 输入组件

| Ant Design Vue | shadcn-vue | 迁移优先级 | 备注 |
|----------------|------------|-----------|------|
| `<a-input>` | `<Input>` | **高** | 基础输入框 |
| `<a-input-password>` | `<Input type="password">` | 高 | 密码输入 |
| `<a-input-textarea>` | `<textarea>` + 样式 | 中 | 需配合样式 |
| `<a-input-search>` | `<Input>` + Button | 低 | 需组合实现 |

**验证规则**: shadcn-vue 需配合验证库（如 VeeValidate 或 Zod）

---

### 标签组件

| Ant Design Vue | shadcn-vue | 迁移优先级 | 备注 |
|----------------|------------|-----------|------|
| `<a-tag>` | `<Badge>` | **高** | 标签显示 |
| color="blue" | variant="info" | - | 颜色映射 |
| color="green" | variant="success" | - | 成功状态 |
| color="red" | variant="destructive" | - | 危险/错误 |

---

### 模态框组件

| Ant Design Vue | shadcn-vue | 迁移优先级 | 备注 |
|----------------|------------|-----------|------|
| `<a-modal>` | `<Dialog>` | **中** | API 略有不同 |
| v-model:open | v-model:open | - | 相同 API |
| @ok | 需自定义按钮 | - | shadcn-vue 不提供 ok 事件 |
| @cancel | @update:open | - | 关闭事件 |

**差异**:
- `a-modal` 内置确定/取消按钮
- `Dialog` 需要手动添加按钮和逻辑

**示例对比**:
```vue
<!-- Ant Design Vue -->
<a-modal v-model:open="visible" title="标题" @ok="handleOk">
  <p>内容</p>
</a-modal>

<!-- shadcn-vue -->
<DialogRoot :open="visible" @update:open="visible = $event">
  <DialogContent>
    <DialogHeader>
      <DialogTitle>标题</DialogTitle>
    </DialogHeader>
    <p>内容</p>
    <div class="flex justify-end gap-2">
      <Button variant="outline" @click="visible = false">取消</Button>
      <Button @click="handleOk">确定</Button>
    </div>
  </DialogContent>
</DialogRoot>
```

---

### 卡片组件

| Ant Design Vue | shadcn-vue | 迁移优先级 | 备注 |
|----------------|------------|-----------|------|
| `<a-card>` | `<Card>` | **高** | 结构一致 |
| #title | `<CardHeader><CardTitle>` | - | 标题结构 |
| (default) | `<CardContent>` | - | 内容区 |

**示例对比**:
```vue
<!-- Ant Design Vue -->
<a-card title="标题">
  <p>内容</p>
</a-card>

<!-- shadcn-vue -->
<Card>
  <CardHeader>
    <CardTitle>标题</CardTitle>
  </CardHeader>
  <CardContent>
    <p>内容</p>
  </CardContent>
</Card>
```

---

### 表单组件

| Ant Design Vue | shadcn-vue | 迁移优先级 | 备注 |
|----------------|------------|-----------|------|
| `<a-form>` | `<form>` + 验证库 | **中** | 需配合验证库 |
| `<a-form-item>` | `<div>` + `<Label>` | - | 结构更灵活 |
| :rules | 验证库规则 | - | 需适配验证库 |

**推荐验证库**: VeeValidate 或 Zod + v-validate

---

### 表格组件

| Ant Design Vue | shadcn-vue | 迁移优先级 | 备注 |
|----------------|------------|-----------|------|
| `<a-table>` | **保留 Ant Design** | **低** | 功能差距大 |

**原因**: Ant Design Vue 表格功能强大（排序、筛选、分页、虚拟滚动等），shadcn-vue 表格较为基础

**建议**: 复杂表格继续使用 Ant Design Vue

---

### 下拉选择

| Ant Design Vue | shadcn-vue | 迁移优先级 | 备注 |
|----------------|------------|-----------|------|
| `<a-select>` | `<Select>` (Radix Vue) | **低** | 需手动封装 |
| `<a-select-option>` | `<SelectItem>` | - | API 不同 |

**建议**: 暂时保留 Ant Design Vue Select，待 shadcn-vue Select 封装完成后再迁移

---

### 通知组件

| Ant Design Vue | shadcn-vue | 迁移优先级 | 备注 |
|----------------|------------|-----------|------|
| `message` | `toast` (需自建) | **低** | 需配合 sonner 或自建 |
| `notification` | `toast` | - | 同上 |
| `Modal.confirm` | `AlertDialog` | - | 确认对话框 |

**推荐**: 继续使用 Ant Design Vue 的通知系统

---

## 颜色映射

| Ant Design | shadcn-vue (CSS 变量) | 用途 |
|------------|----------------------|------|
| #1890ff | hsl(var(--primary)) | 主色 |
| #52c41a | hsl(var(--success)) | 成功 |
| #faad14 | hsl(var(--warning)) | 警告 |
| #f5222d | hsl(var(--destructive)) | 危险/错误 |

---

## 图标库

| Ant Design Vue | shadcn-vue |
|----------------|------------|
| `@ant-design/icons-vue` | `lucide-vue-next` |

**迁移**: 需要重新引入图标，但命名习惯相似

---

## 迁移优先级总结

### 高优先级 (立即可迁移)
- Button
- Input (基础类型)
- Badge (Tag)
- Card

### 中优先级 (需要适配)
- Dialog/Modal
- Label
- Form (需要配合验证库)

### 低优先级 (暂不迁移)
- Table (保留 Ant Design)
- Select (待封装)
- Tree (保留 Ant Design)
- Upload (保留 Ant Design)
- Notification/Messaging (保留 Ant Design)

---

## 兼容性策略

### 样式隔离
- shadcn-vue 使用 CSS 变量
- Ant Design Vue 使用 Less 变量
- 两套系统互不干扰

### 主题切换
- shadcn-vue: 通过 `.dark` 类切换
- Ant Design Vue: 通过 ConfigProvider 设置

### 全局配置
```typescript
// main.ts
import { ConfigProvider } from 'ant-design-vue'

app.use(ConfigProvider, {
  theme: {
    primaryColor: '#1890ff'
  }
})
```

---

## 混合使用示例

```vue
<template>
  <div class="mixed-components-page">
    <!-- shadcn-vue 卡片 -->
    <Card>
      <CardHeader>
        <CardTitle>账号管理</CardTitle>
      </CardHeader>
      <CardContent>
        <!-- Ant Design Vue 表格 -->
        <a-table :columns="columns" :data-source="data">
          <template #bodyCell="{ column }">
            <!-- shadcn-vue Badge -->
            <Badge v-if="column.key === 'status'" :variant="getStatusVariant(record.status)">
              {{ record.status }}
            </Badge>
          </template>
        </a-table>
      </CardContent>
    </Card>
  </div>
</template>
```
