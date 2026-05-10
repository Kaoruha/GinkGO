# CLI 量化研究审计报告

> 2026-05-11，基于 821 个回测任务、数百个 Portfolio 的实际使用经验

## 1. CLI 输出噪音

### 1.1 GCONF 缓存日志
每次命令输出 3 行 GCONF 日志：
```
[GCONF] Config cache updated (mtime: 1778285525.705516)
[GCONF] Config cache updated (mtime: 1778285525.705516)
[GCONF] Secure cache updated (mtime: 1773427717.975172)
```
**影响**：每条命令多 3 行无意义输出，821 次回测 = 2463 行噪音。
**建议**：GCONF 缓存日志设为 DEBUG 级别，CLI 模式下不显示。

### 1.2 @time_logger 性能日志
```
⚡ FUNCTION create_mysql_connection executed in 0.00647 seconds
⚡ FUNCTION find executed in 0.02860 seconds
```
**影响**：CRUD 方法的 `@time_logger` 装饰器在 CLI 模式下暴露内部性能数据。
**建议**：非 DEBUG 模式下抑制 time_logger 输出，或改为 GLOG.DEBUG。

### 1.3 缓存提示
```
缓存结果
```
**影响**：无上下文的中文提示，用户无法理解含义。
**建议**：改为 GLOG.DEBUG 或提供有意义的上下文。

## 2. 数据展示问题

### 2.1 百分比未格式化
`backtest cat` 输出原始小数：
```
Annual Return: 0.1516    ← 应为 15.16%
Win Rate: 0.3846         ← 应为 38.46%
Max Drawdown: 0.2301     ← 应为 23.01%
```
**建议**：格式化为百分比，或同时显示两种格式。

### 2.2 Progress 始终为 0%
所有已完成的回测任务 Progress 列显示 `0%`，实际已完成。
**建议**：完成后更新 progress 为 100%。

### 2.3 Portfolio Mode 显示原始值
```
Mode: 0    ← 应为 BACKTEST
```
**建议**：将枚举值转为可读名称。

### 2.4 Description 字段异常
```
Description: 0 portfolio: ttt
```
"0 portfolio:" 前缀无意义，可能是创建时误设。

## 3. 工作流效率问题

### 3.1 无回测对比功能
经过 52 轮迭代，核心工作是比较不同参数的回测结果。当前只能逐个 `backtest cat` 查看，无法并排对比。
**建议**：添加 `ginkgo backtest compare <id1> <id2> ...` 命令，输出对比表格。

### 3.2 无批量清理功能
821 个回测任务 + 数百个 Portfolio 积累，无批量删除方式。逐个删除需交互确认，不可操作。
**建议**：
- `ginkgo portfolio delete --prefix r4 --confirm` 按前缀批量删除
- `ginkgo backtest delete --status failed --confirm` 按状态批量删除

### 3.3 组件列表噪音大
`component list` 输出大量 `my_custom_strategy`、`strategy_config.ini`、`auto_binding_*` 等测试/自动生成组件。
**建议**：
- 默认过滤掉 auto_binding 和测试组件
- 添加 `--user-only` 只显示用户创建的组件
- 添加 `--type strategy` 按类型过滤

### 3.4 无法快速复用 Portfolio 配置
每次测试新参数需创建新 Portfolio → 绑定 4 个组件 → 设参数 → 创建回测 → 运行，5 步操作耗时且重复。
**建议**：
- `ginkgo portfolio clone <id> --name new_name` 克隆 Portfolio 及其组件绑定
- `ginkgo backtest quick --strategy momentum --params '...' --run` 一步完成

## 4. 已修复的问题（029 分支）

- ~~file_service.update() 不接受 string~~ → 已修复自动编码
- ~~backtest run 需完整 UUID~~ → 已添加模糊匹配（实测验证通过：`ginkgo backtest run 4e25663b` 成功匹配）
- ~~portfolio list 截断 UUID~~ → 已显示完整 UUID
- ~~ratio_sizer 空占位~~ → 源码已实现，但数据库组件未同步（见 7.1）
- ~~信号静默丢弃~~ → 已添加 GLOG 日志
- ~~portfolio get --details 未文档化~~ → 已更新 CLAUDE.md

## 7. 架构级问题

### 7.1 数据库组件 vs 源码组件不同步 ⚠️ 关键发现
**现象**：修改 `ratio_sizer.py` 源码后，回测仍然使用数据库中的旧（空）组件代码。
```
🔥 [ddd3d4a6] No component class found in file. Available classes: []
🔥 [3eed5f06] Failed to instantiate sizer: No component class found in file.
```
**原因**：回测引擎通过 `ComponentFactoryService` 从数据库 File 表加载组件源码，动态实例化类。源码文件中的修改不会自动同步到数据库。
**影响**：
- 源码修改对已有数据库组件无效果
- 用户必须通过 `ginkgo component edit` 更新数据库版本
- 或者需要 `ginkgo component sync` 命令将源码同步到数据库

**建议**：
1. 添加 `ginkgo component sync` 命令，将 src/ 下的源码同步到数据库
2. 或在引擎装配时优先使用源码版本（当存在时）
3. 至少在文档中明确说明这个区别

### 7.2 组件查找依赖 grep
实际使用中查找组件 UUID 需要：
```bash
ginkgo component list 2>&1 | grep "momentum"
```
不能用 `ginkgo component list strategy`（不支持类型参数），也不能用名称直接查找。

### 7.3 bind-component 需要完整 file_id
`portfolio bind-component` 只接受 UUID，不能接受组件名称。需要先 list 再 grep 再复制 UUID。

## 8. 未实现的命令（占位符）

以下命令存在于 help 输出中但未实现：

| 命令 | 状态 |
|------|------|
| `ginkgo mapping list` | "Mapping listing not yet implemented" |
| `ginkgo result list` | "Result listing not yet implemented" |
| `ginkgo data status` | "Data status check not yet implemented" |
| `ginkgo eval stability` | ImportError: `BacktestEvaluator` 无法从 `ginkgo.trading.evaluation` 导入 |

**建议**：未实现的命令应从 help 中移除或标记为 `[WIP]`，避免用户踩坑。

## 9. 其他发现

### 9.1 result list 重复参数名
`ginkgo result list` 的 `-p` 同时用于 `--portfolio` 和 `--page`，触发 Typer 警告：
```
UserWarning: The parameter -p is used more than once. Remove its duplicate
```

### 9.2 回测状态未正确更新
r58 回测已完成（`Completed: 2026-05-10 22:29:44`），但 `Status: running`、`Progress: 0%`。
可能是异步运行时状态未回写。

### 9.3 component list 不支持类型参数
`ginkgo component list strategy` 报错 "Got unexpected extra argument"。
需改为 `ginkgo component list --type strategy`（但此选项也不存在）。

## 5. 待深入排查

- **回测引擎非确定性**：同一参数不同结果，成功率约 33%（需专门分支修复）
- **批量创建回测不稳定**：可能与 worker 回测上限有关
- **回测耗时长**：3 年日线单股 7-8 分钟，需 profiling

## 6. 优先级建议

| 优先级 | 问题 | 影响 |
|--------|------|------|
| P0 | CLI 输出噪音（GCONF/time_logger） | 每次使用都受影响 |
| P0 | 百分比格式化 | 数据可读性 |
| P1 | 回测对比命令 | 策略搜索核心需求 |
| P1 | 批量清理 | 数据库膨胀 |
| P1 | Portfolio 快速复用 | 工作流效率 |
| P2 | 组件列表过滤 | 组件管理体验 |
| P2 | Progress 显示 | 数据准确性 |
| P2 | Mode 枚举显示 | 可读性 |
