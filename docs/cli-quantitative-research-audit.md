# CLI 量化研究审计报告

> 2026-05-11，基于 821 个回测任务、486 个 completed 的实际使用经验，经过 5 轮深度分析

## 一、回测引擎核心问题

### 1. 非确定性 Bug（最高优先级）
同一 portfolio、同一参数、同一数据，连续运行结果完全不同：
- 成功：92 信号 → 54 订单 → 年化 15.4%
- 失败：330 信号 → 12 订单 → 年化 -0.1%
- 成功率约 33%（486 个 completed 中 26 个确认进入失败模式）

需专门分支排查，可能是：dict 迭代顺序、共享可变状态、或数据 feeder 返回顺序不一致。

### 2. 源码组件 ≠ 数据库组件 ⚠️
回测引擎从数据库 File 表加载组件源码，**不读取源码文件**。
- 修改 `ratio_sizer.py` 源码后回测仍用数据库中的空代码
- 必须通过 `ginkgo component edit` 更新数据库版本
- **建议**：添加 `ginkgo component sync` 命令，或在文档中明确说明

### 3. 回测状态未正确更新
已完成的回测（有 Completed 时间戳）仍显示 `Status: running`、`Progress: 0%`。

## 二、CLI 输出噪音（P0）

每次命令多 3-5 行无意义输出：

| 来源 | 示例 | 建议 |
|------|------|------|
| GCONF | `[GCONF] Config cache updated (mtime: ...)` ×2 | 设为 DEBUG 级别 |
| time_logger | `⚡ FUNCTION create_mysql_connection executed in 0.006s` | 非 DEBUG 模式抑制 |
| 缓存提示 | `缓存结果` | 改为 GLOG.DEBUG |

## 三、数据展示问题

| 问题 | 现状 | 期望 |
|------|------|------|
| 百分比 | `Annual Return: 0.1516` | `15.16%` |
| Progress | 完成后仍 `0%` | `100%` |
| Mode | `Mode: 0` | `BACKTEST` |
| Description | `0 portfolio: ttt` | `ttt` |

## 四、工作流效率

### 当前工作流（5 步）
```bash
ginkgo portfolio create --name "test" --capital 100000
ginkgo portfolio bind-component $PID $SELECTOR_UUID --type selector --param ...
ginkgo portfolio bind-component $PID $STRATEGY_UUID --type strategy --param ...
ginkgo portfolio bind-component $PID $SIZER_UUID --type sizer --param ...
ginkgo portfolio bind-component $PID $RISK_UUID --type riskmanager --param ...
ginkgo backtest create --portfolio $PID --start ... --end ...
ginkgo backtest run $BID
```

### 缺失的功能

| 功能 | 说明 | 优先级 |
|------|------|--------|
| `backtest compare <id1> <id2>` | 并排对比结果 | P1 |
| `portfolio clone <id>` | 克隆配置改参数 | P1 |
| `backtest quick` | 一步完成创建+运行 | P1 |
| `portfolio delete --prefix r4` | 批量清理 | P1 |
| `backtest delete --status failed` | 批量清理 | P1 |
| `component list --type strategy` | 按类型过滤 | P2 |
| `bind-component` 支持名称 | 免去 grep UUID | P2 |
| `ginkgo python -c "..."` | 快速 Python 访问 | P2 |

## 五、数据探索能力（严重不足）

所有数据查看命令均未实现：

```
ginkgo data get day           → "Bar data get not yet implemented"
ginkgo data get adjustfactor  → "not yet implemented"
ginkgo data get calendar      → "Unknown data type"
ginkgo data get sources       → "not yet implemented"
ginkgo data status            → "not yet implemented"
```

量化研究的第一步是数据探索，CLI 完全无法胜任。只能通过 Python API：
```python
/home/kaoru/.ginkgo/.venv/bin/python -c "from ginkgo.data.containers import container; ..."
```

## 六、未实现的命令（占位符）

以下命令出现在 `--help` 中但不可用：

| 命令 | 状态 |
|------|------|
| `mapping list` | "not yet implemented" |
| `result list` | "not yet implemented" + `-p` 参数冲突 |
| `data status` | "not yet implemented" |
| `eval stability` | ImportError |

建议：从 help 移除或标记 `[WIP]`。

## 七、486 个回测统计

| 模式 | 数量 | 占比 | 平均年化 |
|------|------|------|---------|
| 成功 | 151 | 31% | 5.9% |
| 非确定性失败 | 26 | 5% | -0.1% |
| 空信号 | 98 | 20% | 0% |
| 其他 | 211 | 44% | — |

Top 5（排除 B&H）：
1. E2E_参数验证: 51.7%（测试用，不可靠）
2. r53_verify_th20: 15.43%
3. r54_th22_v6: 15.41%
4. r50_mom10_th22: 15.36%
5. r54_th22_v4: 15.16%

B&H 基准（紫金矿业 3 年）：27.6% 年化，最佳主动策略仅捕获 56%。

## 八、改进路线图

### Phase 1：基础体验（影响所有用户）
1. 抑制 CLI 噪音日志（GCONF/time_logger）
2. 格式化百分比显示
3. 回测状态正确更新
4. 修复 Progress 显示

### Phase 2：量化研究基础设施
5. 实现数据查看命令（`data get day/calendar/adjustfactor`）
6. 添加 `ginkgo python` 命令
7. 实现 `result list` 和 `mapping list`
8. 修复 `eval stability` ImportError

### Phase 3：策略搜索效率
9. 实现 `backtest compare` 对比命令
10. 实现 `portfolio clone` 快速复用
11. 实现批量清理（按前缀/状态删除）
12. 添加 `component list --type` 过滤

### Phase 4：引擎可靠性
13. 排查并修复回测引擎非确定性 Bug
14. 添加 `component sync` 源码→数据库同步
15. 回测性能 profiling（3 年日线 7-8 分钟偏慢）

## 九、结论

### 做得好的
- **架构设计合理**：事件驱动引擎 + 组件化四件套（Selector/Strategy/Sizer/Risk）+ CRUD/Service 分层，扩展性强
- **CLI 覆盖面广**：portfolio/backtest/component/eval/serve 等命令齐全，基础回测流程可走通
- **CLI 可用性近期改善**：模糊 UUID 匹配、完整 UUID 显示、portfolio get --details 等已修复
- **数据层完整**：ClickHouse + MySQL + Redis + MongoDB 多库架构，Python API 数据访问能力强
- **风控体系设计良好**：双重机制（被动拦截 + 主动信号），多风控可组合

### 核心短板
1. **回测引擎不可靠**：非确定性 Bug 导致 5% 回测结果完全错误，这是信任基础问题——无法信任结果就无法做研究
2. **CLI 无法做数据探索**：所有 data get 子命令未实现，量化研究第一步就被卡住
3. **组件开发链路断裂**：源码修改不反映到回测执行，需手动同步数据库
4. **策略搜索效率低**：5 步重复操作、无对比工具、无批量清理，52 轮迭代成本极高

### 一句话总结
Ginkgo 的架构和组件设计已经成熟，但回测引擎的可靠性问题和 CLI 数据探索能力的缺失，使得它目前更适合作为 Python 库通过 API 使用，而非通过 CLI 独立完成量化研究全流程。修复引擎非确定性和补齐数据查看命令后，CLI 才能成为合格的研究工具。

## 十、已修复（029 分支）

- file_service.update() 自动编码 string→bytes
- backtest run 模糊 UUID 匹配（已实测验证）
- portfolio list 显示完整 UUID
- RatioSizer 源码实现（数据库版本待同步）
- 信号丢弃加 GLOG 日志
- portfolio get --details 文档更新
