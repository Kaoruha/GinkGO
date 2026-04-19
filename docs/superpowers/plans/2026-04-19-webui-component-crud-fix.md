# 组件 CRUD 修复计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复前端组件库的 CRUD 功能，使列表加载、创建、编辑、删除全部连通后端 API。

**Architecture:** 后端 API（`/api/v1/components/`）已完整实现，通过 Service 层操作。只需修前端：API 模块端点路径、列表页/详情页的 TODO 空壳替换为真实 API 调用、路由 props 传递。

**Tech Stack:** Vue 3 + TypeScript + Pinia

**Branch:** `001-feat/webui-navigation`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `web-ui/src/api/modules/components.ts` | **Rewrite** | 修正 API 端点路径，使用 `?component_type=` 查询参数 |
| `web-ui/src/views/components/ComponentListPage.vue` | **Rewrite** | 替换 TODO 空壳为真实 API 调用（list/create/delete） |
| `web-ui/src/views/components/ComponentDetail.vue` | **Rewrite** | 替换 TODO 空壳为真实 API 调用（load/save） |
| `web-ui/src/router/index.ts` | **Modify** | `/components/:type` 路由添加 props 传递 |

---

### Task 1: 修正前端 API 模块端点路径

**Files:**
- Rewrite: `web-ui/src/api/modules/components.ts`

后端 API 使用 `GET /api/v1/components/?component_type=strategy` 查询参数模式，不是子路径。

- [ ] **Step 1: 重写 components.ts API 模块**

读取当前文件内容，然后用 Write 工具替换为：

```typescript
import request from '../request'

const BASE = '/api/v1/components'

export const componentsApi = {
  /**
   * 获取组件列表
   * @param componentType 组件类型: strategy, analyzer, risk, sizer, selector
   */
  async list(componentType?: string) {
    const params: Record<string, string> = {}
    if (componentType) {
      params.component_type = componentType
    }
    return request.get(BASE, { params })
  },

  async get(uuid: string) {
    return request.get(`${BASE}/${uuid}`)
  },

  async create(data: { name: string; component_type: string; code: string; description?: string }) {
    return request.post(BASE, data)
  },

  async update(uuid: string, data: { name?: string; code?: string; description?: string }) {
    return request.put(`${BASE}/${uuid}`, data)
  },

  async delete(uuid: string) {
    return request.delete(`${BASE}/${uuid}`)
  },
}
```

- [ ] **Step 2: 验证编译**

Run: `cd /home/kaoru/Ginkgo/web-ui && npx vue-tsc --noEmit 2>&1 | head -20`

- [ ] **Step 3: Commit**

```bash
git add web-ui/src/api/modules/components.ts
git commit -m "fix(web-ui): correct component API endpoint paths to use query params"
```

---

### Task 2: 修复 ComponentListPage.vue

**Files:**
- Rewrite: `web-ui/src/views/components/ComponentListPage.vue`

当前 loadFiles/handleCreateConfirm/handleDelete 全是 TODO 空壳。需要替换为真实 API 调用。同时需要从路由参数 `:type` 推导 `fileType` 和 `componentType`。

- [ ] **Step 1: 重写 ComponentListPage.vue**

读取当前文件，然后用 Write 工具替换。核心改动：

1. 从路由 `route.params.type` 推导 `componentType`（如 `strategies` → `strategy`）
2. `loadFiles()` 调用 `componentsApi.list(componentType)`
3. `handleCreateConfirm()` 调用 `componentsApi.create()`
4. `handleDelete()` 调用 `componentsApi.delete()`
5. 保留现有 UI 结构（表格、创建弹窗、删除确认）

关键映射逻辑：
```typescript
// 路由 type 参数 -> API component_type
const routeTypeToApiType: Record<string, string> = {
  strategies: 'strategy',
  analyzers: 'analyzer',
  risks: 'risk',
  sizers: 'sizer',
  selectors: 'selector',
}
```

- [ ] **Step 2: 验证编译**

Run: `cd /home/kaoru/Ginkgo/web-ui && npx vue-tsc --noEmit 2>&1 | head -20`

- [ ] **Step 3: Commit**

```bash
git add web-ui/src/views/components/ComponentListPage.vue
git commit -m "fix(web-ui): wire component list page to real API calls"
```

---

### Task 3: 修复 ComponentDetail.vue

**Files:**
- Rewrite: `web-ui/src/views/components/ComponentDetail.vue`

当前 loadFile/handleSave 全是 TODO 空壳。需要替换为真实 API 调用。

- [ ] **Step 1: 重写 ComponentDetail.vue**

读取当前文件，然后用 Write 工具替换。核心改动：

1. `loadFile()` 调用 `componentsApi.get(route.params.id)`，填充 code、name、description
2. `handleSave()` 调用 `componentsApi.update(route.params.id, { name, code, description })`
3. 保留现有 UI 结构（代码编辑器、元信息面板）

- [ ] **Step 2: 验证编译**

Run: `cd /home/kaoru/Ginkgo/web-ui && npx vue-tsc --noEmit 2>&1 | head -20`

- [ ] **Step 3: Commit**

```bash
git add web-ui/src/views/components/ComponentDetail.vue
git commit -m "fix(web-ui): wire component detail page to real API calls"
```

---

### Task 4: 远端浏览器验证

**Files:** 无文件变更

- [ ] **Step 1: 确认 dev server 运行**

- [ ] **Step 2: 验证组件列表加载**

访问 `/components/strategies`，确认列表正常显示（不再空）。

- [ ] **Step 3: 验证组件详情**

点击任意组件，确认详情页显示代码内容和参数。

- [ ] **Step 4: 验证创建和删除**

测试创建新组件和删除组件（如测试环境允许）。

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore(web-ui): verify component CRUD fixes"
```

---

## Self-Review

**1. Spec coverage:**
- API 端点路径修正 ✅ Task 1
- 列表页真实 API 调用 ✅ Task 2
- 详情页真实 API 调用 ✅ Task 3
- 路由 props 传递 ✅ Task 2（从路由推导，不需要 props）
- 浏览器验证 ✅ Task 4

**2. Placeholder scan:** 无 TBD/TODO。

**3. Type consistency:** `componentsApi` 方法签名与 `ComponentCreate`/`ComponentUpdate` 后端模型匹配。`routeTypeToApiType` 映射与后端 `COMPONENT_FILE_TYPE_MAP` 一致。
