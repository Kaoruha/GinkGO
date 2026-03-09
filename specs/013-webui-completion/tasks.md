# Implementation Tasks: Web UI 回测列表与详情修复

**Feature**: 013-webui-completion
**Branch**: `013-webui-completion`
**Generated**: 2026-03-08
**Tech Stack**: TypeScript 5.x + Vue 3 (Composition API) + Pinia + Ant Design Vue

---

## Phase 1: Setup & 基础组件

**目标**: 创建基础组件和工具函数，为后续开发提供支持

### 独立测试标准
- [ ] StatusTag 组件正确显示六种状态的中文标签
- [ ] useErrorHandler 正确处理 API 错误并显示友好提示
- [ ] 常量导出正确，无 TypeScript 类型错误

- [x] T001 [P] 创建 `StatusTag.vue` 组件在 `web-ui/src/components/common/StatusTag.vue`
- [x] T002 [P] 创建 `useErrorHandler.ts` composable 在 `web-ui/src/composables/useErrorHandler.ts`
- [x] T003 [P] 更新 `constants/backtest.ts` 添加六态配置在 `web-ui/src/constants/backtest.ts`
- [x] T004 [P] 更新 `constants/index.ts` 导出 backtest 常量在 `web-ui/src/constants/index.ts`

---

## Phase 2: Store 更新

**目标**: 增强 backtest store，添加权限检查、批量操作、WebSocket 降级逻辑

### 独立测试标准
- [ ] `canStartTask()` 正确判断是否可启动任务
- [ ] `canStopTask()` 正确判断是否可停止任务
- [ ] `batchStart()` 并行调用 API 并返回操作结果
- [ ] WebSocket 断开时自动切换到轮询模式
- [ ] 数据冲突时以最新时间戳为准

- [x] T005 添加权限检查方法在 `web-ui/src/stores/backtest.ts`
- [x] T006 添加批量操作方法在 `web-ui/src/stores/backtest.ts`
- [x] T007 添加 WebSocket 降级到轮询逻辑在 `web-ui/src/stores/backtest.ts`
- [x] T008 添加数据同步冲突处理在 `web-ui/src/stores/backtest.ts`

---

## Phase 3: 回测列表页实现 [US5]

**目标**: 修改 BacktestList.vue，添加复选框、批量操作栏、启动按钮、WebSocket 订阅

### 独立测试标准
- [ ] 列表显示任务状态中文标签
- [ ] 点击复选框选中任务，显示批量操作栏
- [ ] 全选复选框可选中/取消当前页所有任务
- [ ] 批量操作栏显示已选中数量，取消选择时隐藏
- [ ] 已完成/失败/已停止的任务显示"启动"按钮
- [ ] 进行中的任务显示"停止"按钮
- [ ] created/pending 状态的任务显示"取消"按钮
- [ ] 无权限的任务按钮禁用并显示 Tooltip
- [ ] WebSocket 连接成功时状态实时更新
- [ ] WebSocket 断开时自动降级到轮询

- [x] T009 [P] 添加表格复选框列在 `web-ui/src/views/Backtest/BacktestList.vue`
- [x] T010 添加选中状态管理在 `web-ui/src/views/Backtest/BacktestList.vue`
- [x] T011 [P] 添加批量操作栏组件在 `web-ui/src/views/Backtest/BacktestList.vue`
- [x] T012 更新操作按钮逻辑（启动/停止/取消）在 `web-ui/src/views/Backtest/BacktestList.vue`
- [x] T013 添加权限检查和 Tooltip 显示在 `web-ui/src/views/Backtest/BacktestList.vue`
- [x] T014 添加 WebSocket 订阅和实时更新在 `web-ui/src/views/Backtest/BacktestList.vue`
- [x] T015 添加手动刷新按钮在 `web-ui/src/views/Backtest/BacktestList.vue`

---

## Phase 4: 回测详情页实现 [US5]

**目标**: 修改 BacktestDetail.vue，添加启动/删除/复制按钮、权限检查、操作确认对话框

### 独立测试标准
- [ ] 详情页显示与列表页相同的操作按钮
- [ ] 已完成/失败/已停止的任务显示"重新运行"按钮
- [ ] 进行中的任务显示"停止"按钮
- [ ] 按钮状态与任务状态和权限正确匹配
- [ ] 停止/删除操作前显示确认对话框
- [ ] 点击"重新运行"后跳转到新任务详情页

- [x] T016 添加操作按钮区域在 `web-ui/src/views/Backtest/BacktestDetail.vue`
- [x] T017 添加权限检查和按钮状态控制在 `web-ui/src/views/Backtest/BacktestDetail.vue`
- [x] T018 添加操作确认对话框在 `web-ui/src/views/Backtest/BacktestDetail.vue`
- [x] T019 实现"重新运行"跳转新任务在 `web-ui/src/views/Backtest/BacktestDetail.vue`

---

## Phase 5: API 类型定义更新

**目标**: 更新 API 类型定义以支持六态模型和新增操作

### 独立测试标准
- [ ] TypeScript 编译无类型错误
- [ ] BacktestStatus 包含全部六种状态
- [ ] API 接口定义包含请求/响应类型

- [x] T020 [P] 更新 `api/modules/business/backtest.ts` 类型定义在 `web-ui/src/api/modules/business/backtest.ts`

---

## Phase 6: 集成测试

**目标**: 验证回测列表和详情页的完整功能流程

### 独立测试标准
- [ ] 用户可以查看回测任务列表
- [ ] 用户可以搜索和筛选回测任务
- [ ] 用户可以启动已完成/失败/已停止的回测
- [ ] 用户可以停止正在运行的回测
- [ ] 用户可以批量启动/停止回测任务
- [ ] 权限控制正常（普通用户 vs admin）
- [ ] WebSocket 实时更新任务状态
- [ ] WebSocket 断开时自动降级到轮询

- [x] T021 使用 Playwright E2E 测试回测列表完整流程
- [x] T022 使用 Playwright E2E 测试回测详情完整流程
- [x] T023 使用 Playwright E2E 测试批量操作功能
- [x] T024 使用 Playwright E2E 测试权限控制功能

---

## Dependencies

```
Phase 1 (Setup & 基础组件)
  ↓
Phase 2 (Store 更新)
  ↓
Phase 3 (列表页) ← Phase 6 (测试)
  ↓
Phase 4 (详情页) ← Phase 6 (测试)
  ↓
Phase 5 (API 类型更新)
```

**说明**:
- Phase 1、2、5 可以并行执行（标记 [P]）
- Phase 3、4 依赖 Phase 2 完成
- Phase 6 验证所有功能

---

## Parallel Execution Examples

### Phase 1 并行执行
```bash
# 可同时执行
npm run dev:component: StatusTag.vue
npm run dev:component: useErrorHandler.ts
npm run dev:constant: backtest.ts
npm run dev:constant: index.ts
```

### Phase 5 可与 Phase 3 并行
```bash
# 在更新列表页的同时，另一个人可以更新 API 类型
```

---

## Implementation Strategy

### MVP 范围 (最小可行产品)
- Phase 1: Setup & 基础组件
- Phase 2: Store 更新
- Phase 3: 回测列表页实现（核心功能）

### 增量交付顺序
1. **MVP**: 完成列表页的基本查看和操作功能
2. **增强**: 添加批量操作能力
3. **完善**: 实现详情页功能
4. **优化**: 集成测试和 bug 修复

---

## Task Count Summary

| Phase | Task Count | Parallel Tasks |
|-------|------------|---------------|
| Phase 1 | 4 | 4 |
| Phase 2 | 4 | 0 |
| Phase 3 | 7 | 0 |
| Phase 4 | 4 | 0 |
| Phase 5 | 1 | 1 |
| Phase 6 | 4 | 0 |
| **Total** | **24** | **5** |

---

## Format Validation

✅ 所有任务遵循 checklist 格式：
- 复选框 `- [ ]`
- 任务 ID (T001-T024)
- 并行标记 `[P]`（仅适用于可并行任务）
- 故事标签 `[US5]`（仅适用于用户故事阶段）
- 具体文件路径
- 清晰的描述

---

**Tasks Status**: Ready for implementation. Run `/speckit.implement` to begin execution.
