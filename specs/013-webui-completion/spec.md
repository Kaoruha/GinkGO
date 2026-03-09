# Feature Specification: Web UI 回测列表与详情修复

**Feature Branch**: `013-webui-completion`
**Created**: 2026-03-01
**Status**: Draft
**Input**: User description: "继续完成webui"

## Clarifications

### Session 2026-03-01

- Q: 回测任务支持哪些操作？ → A: 查看 + 启动 + 停止 - 可重新运行已完成回测，可终止进行中回测
- Q: 回测任务有哪些状态及状态转换？ → A: 六态 - 待调度 / 排队中 / 进行中 / 已完成 / 已停止 / 失败
- Q: 批量操作支持？ → A: 批量停止 + 批量启动 - 支持批量停止和批量重新运行
- Q: 停止回测的权限限制？ → A: 所有者可操作 - 仅创建者可停止自己的回测
- Q: 列表刷新策略？ → A: WebSocket 智能 - 实时推送，断线时自动降级轮询

### Session 2026-03-01 (范围聚焦)

- Q: 本次任务的范围？ → A: 仅回测列表与详情 - 只实现/修复 User Story 5，其他4个用户故事延后
- Q: "修复"的具体含义？ → A: 全面修复 - bug修复 + 功能补充 + 重构优化
- Q: 状态筛选器与六态模型的匹配？ → A: 前端英文六态 - 前端使用 created/pending/running/completed/stopped/failed，UI显示中文标签
- Q: 详情页的启动功能？ → A: 详情页添加启动按钮，且详情页应拥有列表中支持的所有单任务操作
- Q: 批量操作的UI交互方式？ → A: 复选框+批量操作栏 - 每行复选框，选中后顶部/底部显示批量操作栏

### Session 2026-03-01 (实现细节澄清)

- Q: "启动"回测任务的语义？ → A: 创建全新实例 - 启动已完成/失败/已停止的回测时，创建新的回测实例（新UUID、新创建时间），原任务保持历史记录
- Q: 批量操作的 API 实现模式？ → A: 前端并行调用 - 前端使用 Promise.all 并行调用多个单任务 API，无需后端专用批量接口
- Q: 当前用户 ID 获取方式？ → A: Pinia auth store - 从 useAuthStore().userId 获取当前登录用户 ID
- Q: WebSocket 与轮询数据冲突处理？ → A: 接收时间戳 - 比较数据接收时的服务端时间戳，以最新的为准
- Q: 权限不足时的 UI 响应？ → A: 禁用+Tooltip - 按钮禁用并显示"仅创建者可操作"提示，admin 用户不受权限限制

## User Scenarios & Testing *(mandatory)*

### User Story 5 - 回测列表与详情 (Priority: P1)

用户可以查看所有回测任务列表，搜索和筛选历史回测，查看回测详情和完整报告。用户可以启动已完成的回测任务，或停止正在运行的回测任务。

**Why this priority**: 回测管理是策略研发的核心功能，列表和详情页是用户最常访问的页面。

**Independent Test**: 可通过访问回测列表页，验证任务列表加载、搜索、详情查看、启动、停止等功能。

**Acceptance Scenarios**:

1. **Given** 用户访问回测列表页面，**When** 页面加载，**Then** 显示所有回测任务（支持分页、按状态/时间筛选）
2. **Given** 用户搜索回测任务，**When** 输入任务名称或ID，**Then** 列表过滤显示匹配结果
3. **Given** 用户查看回测详情，**When** 点击某个回测任务，**Then** 显示完整的回测报告（配置参数、性能指标、净值曲线）
4. **Given** 用户选择已完成的回测任务，**When** 点击"启动"按钮，**Then** 系统重新执行该回测任务并更新状态为"created"（待调度）
5. **Given** 用户选择正在运行的回测任务，**When** 点击"停止"按钮，**Then** 系统终止回测执行并更新状态为"stopped"（已停止）
6. **Given** 回测任务状态为 created/pending/running，**When** 状态显示，**Then** 列表中禁用"启动"按钮，根据状态启用"停止"或"取消"按钮
7. **Given** 回测任务已完成/失败/已停止，**When** 状态显示，**Then** 列表中启用"启动"按钮，禁用"停止"按钮
8. **Given** 回测任务创建成功，**When** 初始状态显示，**Then** 状态为"created"（待调度），并在列表中正确显示
9. **Given** 用户选中多个 running/pending 的回测任务，**When** 点击"批量停止/取消"按钮，**Then** 系统停止/取消所有选中的任务并显示操作结果
10. **Given** 用户选中多个 completed/failed/stopped 的回测任务，**When** 点击"批量启动"按钮，**Then** 系统为每个任务创建新的回测实例并显示操作结果
11. **Given** 用户在回测详情页查看 completed/failed/stopped 状态的任务，**When** 操作区域显示，**Then** 显示"重新运行"、"停止"、"复制"、"删除"等操作按钮
12. **Given** 用户在回测详情页点击"重新运行"，**When** 操作执行，**Then** 系统创建新的回测实例并跳转到新任务的详情页
13. **Given** 用户在回测详情页进行破坏性操作（停止/删除），**When** 确认操作，**Then** 系统显示确认对话框并在执行后更新页面状态
14. **Given** 用户在回测列表页查看任务列表，**When** 点击表格行首的复选框，**Then** 选中该任务并显示顶部批量操作栏
15. **Given** 用户选中多个任务，**When** 查看批量操作栏，**Then** 显示"已选择 N 个任务"提示和可用操作按钮
16. **Given** 用户点击批量操作栏的"全选"复选框，**When** 执行全选，**Then** 当前页所有任务被选中
17. **Given** 用户取消所有选择，**When** 未选中任何任务，**Then** 批量操作栏自动隐藏

---

### Edge Cases

- **数据加载失败**: API调用失败时显示友好错误提示，提供重试按钮
- **大列表分页**: 回测列表超过100条记录时自动分页
- **空状态处理**: 无回测任务时显示空状态提示和操作指引
- **网络超时**: API请求超过10秒时提示用户检查网络连接
- **回测操作状态冲突**: 尝试停止已停止的回测时，按钮应处于禁用状态
- **回测停止确认**: 用户点击停止按钮时，弹出确认对话框防止误操作
- **并发回测限制**: 同时运行的回测任务超过系统限制时，启动操作失败并提示用户等待
- **状态转换限制**: created/pending 状态可取消，running 状态可停止，completed/failed/stopped 不可逆转
- **重启回测**: completed/failed/stopped 的回测可重新启动，创建新的任务实例（新UUID、新创建时间），原任务作为历史记录保留
- **批量操作部分失败**: 批量操作中部分任务失败时，显示成功/失败统计并提供失败任务详情
- **批量操作资源限制**: 批量启动超过系统资源限制时，显示警告并提供"排队"或"部分启动"选项
- **权限不足**: 普通用户尝试操作他人创建的回测任务时，按钮禁用并显示 Tooltip 提示"仅创建者可操作"，admin 用户不受限制
- **批量操作权限过滤**: 批量选择时对无权限的任务禁用按钮，admin 用户可操作所有任务
- **WebSocket 断线**: WebSocket 连接断开时，自动切换到轮询模式并显示连接状态提示
- **数据同步冲突**: WebSocket 推送与轮询获取的数据冲突时，以最新时间戳的数据为准
- **实时更新延迟**: 网络延迟导致状态更新滞后时，显示最后更新时间戳

## Requirements *(mandatory)*

### Functional Requirements

**Ginkgo 架构约束**:
- **FR-001**: 前端MUST 通过API与后端交互，不直接访问数据库
- **FR-002**: API调用MUST 使用统一的错误处理和loading状态管理
- **FR-003**: 组件MUST 支持响应式设计，适配桌面和移动设备

**回测列表需求**:
- **FR-016**: BacktestList MUST 调用API获取回测任务列表（支持分页、筛选）
- **FR-017**: BacktestList MUST 显示任务状态（created/pending/running/completed/stopped/failed）、创建时间、基本指标，使用中文标签显示
- **FR-019**: BacktestList MUST 支持"启动"操作，启动已完成/失败/已停止的回测时创建新的回测实例（新UUID、新创建时间），原任务保持历史记录
- **FR-020**: BacktestList MUST 支持"停止"操作，可终止进行中的回测任务
- **FR-021**: BacktestList MUST 支持"取消"操作，可取消待调度/排队中的回测任务
- **FR-022**: BacktestList MUST 根据任务状态动态启用/禁用操作按钮
- **FR-023**: BacktestList MUST 在停止/取消操作前显示确认对话框防止误操作
- **FR-024**: BacktestList MUST 支持批量选择回测任务（复选框）
- **FR-025**: BacktestList MUST 支持批量停止操作，使用 Promise.all 并行调用单任务停止 API
- **FR-026**: BacktestList MUST 支持批量启动操作，使用 Promise.all 并行调用单任务启动 API
- **FR-027**: BacktestList MUST 在批量操作前显示确认对话框（包含将受影响的任务数量）
- **FR-028**: BacktestList MUST 验证操作权限，仅创建者可启动/停止/取消自己创建的回测任务（admin 用户除外，拥有所有操作权限）
- **FR-029**: BacktestList MUST 对无权限的任务禁用操作按钮并显示 Tooltip 提示（如"仅创建者可操作"），admin 用户不受限制
- **FR-030**: BacktestList MUST 使用 WebSocket 接收实时任务状态更新
- **FR-031**: BacktestList MUST 在 WebSocket 断开时自动降级到轮询模式（5秒间隔）
- **FR-032**: BacktestList MUST 在 WebSocket 重连后自动切换回实时推送模式
- **FR-033**: BacktestList MUST 提供手动刷新按钮，允许用户主动刷新列表
- **FR-034**: StatusTag 组件 MUST 将英文状态码映射为中文标签（created→待调度、pending→排队中、running→进行中、completed→已完成、stopped→已停止、failed→失败）
- **FR-038**: BacktestList MUST 在表格每行添加复选框，支持多选任务
- **FR-039**: BacktestList MUST 在选中任务时显示顶部批量操作栏，包含批量启动/停止/取消按钮
- **FR-040**: BacktestList MUST 显示已选中任务数量，取消选择时隐藏批量操作栏
- **FR-041**: BacktestList MUST 支持"全选"功能，可一键选中/取消当前页所有任务

**回测详情需求**:
- **FR-018**: BacktestDetail MUST 显示完整的回测配置和结果报告
- **FR-035**: BacktestDetail MUST 提供与 BacktestList 相同的单任务操作按钮（启动/停止/删除/复制）
- **FR-036**: BacktestDetail MUST 根据任务状态动态启用/禁用操作按钮，与列表页保持一致
- **FR-037**: BacktestDetail MUST 在操作前显示确认对话框（停止、删除等破坏性操作）

**代码维护与文档需求**:
- **FR-042**: 新增API调用MUST 在 `src/api/modules/` 中定义接口
- **FR-043**: 新增页面组件MUST 包含完整的TypeScript类型定义
- **FR-044**: Code files MUST include three-line headers (Upstream/Downstream/Role)

### Key Entities *(include if feature involves data)*

**回测任务实体**:
- **BacktestTask**: 回测任务，包含taskId（任务ID）、name（任务名称）、status（状态码：created/pending/running/completed/stopped/failed，UI显示中文标签）、createTime（创建时间）、creatorId（创建者ID）、result（结果数据）

## Success Criteria *(mandatory)*

### Measurable Outcomes

**用户体验指标**:
- **SC-002**: 页面切换响应时间 < 500ms
- **SC-003**: API错误时用户看到友好错误提示

**功能完整性指标**:
- **SC-004**: 所有启动/停止/批量操作功能正常工作
- **SC-005**: 空数据状态下显示正确提示
- **SC-006**: 回测列表支持分页、搜索和状态筛选

**代码质量指标**:
- **SC-007**: 新增代码通过ESLint检查
- **SC-008**: API接口定义完整（包含请求/响应类型）

**实时更新指标**:
- **SC-009**: WebSocket 连接成功时，任务状态变化在1秒内反映到 UI
- **SC-010**: WebSocket 断开时，自动降级到轮询模式无明显延迟

## Assumptions

1. **后端API**: 后端API已存在，前端仅需调用现有接口
2. **认证状态**: 用户已登录，所有API请求携带有效token
3. **数据格式**: 后端返回的数据格式符合现有API规范
4. **组件库**: 继续使用Ant Design Vue组件库
5. **状态管理**: 继续使用Pinia进行状态管理
6. **用户角色**: 系统存在普通用户和 admin 两种角色，admin 拥有所有操作权限

## Dependencies

1. **现有Web UI项目**: `/home/kaoru/Ginkgo/web-ui/`
2. **API Server**: 后端API服务正常运行
3. **Ant Design Vue**: 前端UI组件库
4. **Pinia**: 状态管理库
5. **Vue Router**: 路由管理

## Out of Scope

- 后端API接口开发（假设已存在）
- 其他4个用户故事（仪表盘、数据管理、图编辑器、验证模块）延后实现
- 性能优化（仅保证功能可用）
- 移动端适配优化（响应式设计已满足）
