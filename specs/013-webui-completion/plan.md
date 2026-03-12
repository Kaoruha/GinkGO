# Implementation Plan: Web UI 回测列表与详情修复

**Branch**: `013-webui-completion` | **Date**: 2026-03-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/home/kaoru/Ginkgo/specs/013-webui-completion/spec.md`

## Summary

修复和增强 Web UI 回测列表与详情功能，包括：
- **启动功能**: 为已完成/失败/已停止的回测添加启动按钮，创建新的回测实例
- **批量操作**: 支持批量启动/停止/取消回测任务
- **权限控制**: 基于创建者和 admin 角色的操作权限检查
- **实时更新**: WebSocket 实时推送任务状态，断线时降级到轮询
- **六态模型**: 支持 created/pending/running/completed/stopped/failed 状态

## Technical Context

**Language/Version**: TypeScript 5.x + Vue 3 (Composition API)
**Primary Dependencies**: Ant Design Vue, Pinia, Vue Router, WebSocket
**Storage**: 前端状态管理 (Pinia)，数据来自后端 API
**Testing**: Vitest + Vue Test Utils (组件测试)
**Target Platform**: Web 浏览器 (量化交易前端管理界面)
**Project Type**: single (Ginkgo 量化交易系统的 Web UI)
**Performance Goals**: 页面切换 < 500ms，WebSocket 更新延迟 < 1s
**Constraints**:
  - 必须通过 API 与后端交互，不直接访问数据库
  - 组件必须支持响应式设计
  - 所有 API 调用使用统一的错误处理
**Scale/Scope**: 支持分页加载回测列表，实时更新运行中任务状态

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 安全与合规原则 (Security & Compliance)
- [x] 所有代码提交前已进行敏感文件检查（前端无敏感文件）
- [x] API 密钥、数据库凭证等敏感信息通过环境变量管理（后端处理）
- [ ] 敏感配置文件已添加到.gitignore

### 架构设计原则 (Architecture Excellence)
- [ ] 设计遵循事件驱动架构（前端使用 WebSocket 接收后端事件）
- [ ] 使用 ServiceHub 统一访问服务（前端不适用）
- [x] 严格分离数据层、策略层、执行层、分析层和服务层职责

### 代码质量原则 (Code Quality)
- [ ] 使用 `@time_logger`、`@retry`、`@cache_with_expiration` 装饰器（前端不适用）
- [x] 提供类型注解，支持静态类型检查（TypeScript）
- [x] 禁止使用 hasattr 等反射机制回避类型错误
- [ ] 遵循既定命名约定（前端使用 Vue/TypeScript 约定）

### 测试原则 (Testing Excellence)
- [ ] 遵循 TDD 流程（组件测试）
- [ ] 测试按 unit、integration、database、network 标记分类
- [ ] 数据库测试使用测试数据库（前端无数据库）

### 性能原则 (Performance Excellence)
- [x] 数据操作使用批量方法（前端调用 API）
- [ ] 合理使用多级缓存（前端使用 Pinia 缓存）
- [x] 使用懒加载机制优化启动时间（路由懒加载）

### 任务管理原则 (Task Management Excellence)
- [x] 任务列表限制在最多 5 个活跃任务
- [ ] 已完成任务立即从活跃列表移除
- [x] 任务优先级明确
- [x] 任务状态实时更新

### 文档原则 (Documentation Excellence)
- [x] 文档和注释使用中文
- [ ] 核心 API 提供详细使用示例和参数说明
- [x] 重要组件有清晰的架构说明和设计理念文档

### 代码注释同步原则 (Code Header Synchronization)
- [x] 修改类的功能、添加/删除主要类或函数时，更新 Role 描述
- [x] 修改模块依赖关系时，更新 Upstream/Downstream 描述
- [ ] 在代码审查过程中检查头部信息的准确性
- [ ] 定期运行验证脚本检查头部与代码的一致性
- [ ] CI/CD 流程中包含头部准确性检查
- [ ] 使用脚本批量更新头部

### 验证完整性原则 (Verification Integrity)
- [ ] 配置类功能验证包含配置文件检查（前端无配置文件）
- [ ] 验证配置文件包含对应配置项
- [ ] 验证值从配置文件读取，而非代码默认值
- [ ] 验证用户可通过修改配置文件改变行为
- [ ] 验证缺失配置时降级到默认值
- [x] 外部依赖验证包含存在性、正确性、版本兼容性检查
- [ ] 禁止仅因默认值/Mock 使测试通过就认为验证完成

### DTO消息队列原则 (DTO Message Pattern)
- [ ] 所有 Kafka 消息发送使用 DTO 包装（前端不发送 Kafka 消息）
- [ ] 发送端使用 DTO.model_dump_json() 序列化
- [ ] 接收端使用 DTO(**data) 反序列化
- [ ] 使用 DTO.Commands 常量类定义命令/事件类型
- [ ] 使用 DTO.is_xxx() 方法进行类型判断
- [ ] 禁止直接发送字典或裸 JSON 字符串到 Kafka
- [ ] DTO 使用 Pydantic BaseModel 实现类型验证

**Constitution Check Notes**:
- 本功能为纯前端开发，部分后端相关原则不适用
- 需要更新项目头部注释规范以支持 TypeScript/Vue 文件
- 前端通过 WebSocket 接收后端事件，遵循事件驱动模式

## Project Structure

### Documentation (this feature)

```text
specs/013-webui-completion/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
web-ui/src/
├── api/modules/business/
│   └── backtest.ts              # 回测 API 接口定义
├── views/Backtest/
│   ├── BacktestList.vue         # 回测列表页面（需修改）
│   └── BacktestDetail.vue       # 回测详情页面（需修改）
├── components/
│   └── common/
│       └── StatusTag.vue        # 状态标签组件（需新增）
├── stores/
│   ├── backtest.ts              # 回测状态管理（需修改）
│   └── auth.ts                  # 认证状态管理（已存在）
├── composables/
│   └── useErrorHandler.ts      # 统一错误处理（需新增）
└── constants/
    ├── backtest.ts              # 回测常量（需修改）
    └── index.ts                 # 常量导出（需修改）
```

**Structure Decision**: 采用 Vue 3 + TypeScript + Pinia 的前端架构，按功能模块组织代码。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | - | - |

---

## Phase 0: Research & Technical Decisions

### Research Tasks

| # | Task | Status | Output |
|---|------|--------|--------|
| 1 | 研究 WebSocket 与轮询降级最佳实践 | ✅ Complete | research.md |
| 2 | 研究前端批量操作 API 调用模式 | ✅ Complete | research.md |
| 3 | 研究权限检查前端实现方案 | ✅ Complete | research.md |
| 4 | 研究六态模型状态转换规则 | ✅ Complete | research.md |

### Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| WebSocket 消息格式 | 使用 task_id 字段标识任务 | 与后端约定一致 |
| 批量操作实现 | 前端并行调用单任务 API | 简化后端，前端灵活控制 |
| 权限检查 | 从 useAuthStore 获取 user.id 和 isAdmin | 统一使用 Pinia 状态管理 |
| 状态映射 | StatusTag 组件统一处理英文→中文映射 | 复用性高，易于维护 |
| 数据同步冲突 | 比较服务端时间戳 | 简单可靠，不依赖额外字段 |

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](./data-model.md) for detailed entity definitions.

**Key Entities**:
- `BacktestTask`: 回测任务实体，包含六态支持
- `UserInfo`: 用户信息实体，包含 is_admin 标志

### API Contracts

See [contracts/](./contracts/) for detailed API specifications.

**New/Modified Endpoints**:
- `POST /v1/backtests/{uuid}/start` - 启动回测（已存在，需验证返回新任务 UUID）
- `POST /v1/backtests/{uuid}/stop` - 停止回测（已存在）
- `POST /v1/backtests/{uuid}/cancel` - 取消回测（需新增）
- `DELETE /v1/backtests/{uuid}` - 删除回测（已存在）
- `GET /v1/backtests` - 获取回测列表（已存在，需确认六态支持）
- `GET /v1/backtests/{uuid}` - 获取回测详情（已存在）

### Component Design

**StatusTag Component** (New):
```typescript
interface StatusTagProps {
  status: 'created' | 'pending' | 'running' | 'completed' | 'stopped' | 'failed'
}
```

**BatchActionBar Component** (New):
```typescript
interface BatchActionBarProps {
  selectedCount: number
  onStart: () => void
  onStop: () => void
  onCancel: () => void
}
```

### Store Updates

**backtest.ts** modifications:
1. 添加 `canStartTask(task)` 权限检查方法
2. 添加 `canStopTask(task)` 权限检查方法
3. 添加 `batchStart(uuids)` 批量启动方法
4. 添加 `batchStop(uuids)` 批量停止方法
5. 添加 `batchCancel(uuids)` 批量取消方法
6. 添加 WebSocket 自动降级到轮询的逻辑
7. 添加数据同步冲突处理

### Quickstart Guide

See [quickstart.md](./quickstart.md) for development setup instructions.

## Phase 2: Implementation Tasks (Generated by /speckit.tasks)

Run `/speckit.tasks` to generate the detailed task breakdown.

---

**Plan Status**: Phase 1 Complete. Ready for `/speckit.tasks` to generate implementation tasks.
