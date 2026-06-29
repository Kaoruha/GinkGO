# Ginkgo CLI 全链路审计报告

> 日期：2026-06-22 ｜ ginkgo 0.8.1 ｜ Debug ON
> 流程：策略构建 → 回测验证 → 模拟盘 → 实盘
> 方法：CLI 实跑 + 源码核对 + DB 直查

## 结论速览

| 阶段 | 可用性 | 关键问题 |
|---|---|---|
| 策略构建 | ✅ 可用 | — |
| 回测验证 | ⚠️ 可用但有数据陷阱 | 无数据预检，0交易定位难 |
| 模拟盘 | ❌ 不可用 | deploy 克隆丢组件绑定 |
| 实盘 | ❌ 不可用 | 无 CLI 建账户，链路断 |

---

## Phase 1 策略构建 ✅

`portfolio create` / `component list` / `portfolio bind-component --type --param 'index:value'` 全部工作。

- 组件源码可见（`component show`），参数索引可查
- FixedSelector 源码已明确标注"后视偏差，仅回测用"——但 CLI 层无此提示

## Phase 2 回测验证 ⚠️

实测：MA(5,20) on 600000.SH，2025-01~2026-01，**13 信号 → 11 订单**，事件链 `Selector→Strategy→Sizer→Risk→Order→Fill` 完整。

### 缺失 [高] 回测前无数据可用性预检
- 000001.SZ 在 Test 库仅 **3 天数据**（2023-12-01/04/05），回测返回 `Final Value=100000` + 模糊警告 "selector may have returned empty symbols"
- 用户需跑完整个回测（~分钟级）才知道 0 交易，且警告归因不准（暗示 selector，实为数据）
- **建议**：`backtest create/run` 前按 selector codes + 日期窗口预查 bar 数据量，不足时前置报错

### 缺失 [中] 数据覆盖严重不均
| 股票 | 2025 日线条数 |
|---|---|
| 000001.SZ | 3（仅 2023-12） |
| 000002.SZ | 1 |
| 600036.SH | 244 |
| 600000.SH | 244 |
| 600519.SH | 3880 |

主流股票大面积数据空洞，回测选股需先手动 `data get day` 探活。

### 缺失 [低] 回测无进度反馈
本地同步执行 ~4 分钟（244 天），无进度条/日志流。

## Phase 3 模拟盘 ❌

`deploy deploy <pid> --mode paper` 返回"部署成功"+建记录+发 Kafka，但 **worker 实际装配失败**。

### BUG [严重] deploy 克隆未完整复制组件绑定
- 部署日志只显示复制 2/4 映射（risk + selector），strategy + sizer 丢失
- PaperTradingWorker 装配时 `Strategies: 0` → `CRITICAL No strategy found` → `Component binding failed, skipping`
- 同一组合回测 13 信号成功，部署后却 0 策略——**回测 OK ≠ 部署 OK**
- 定位：`deployment_service.py` 的 `_copy_graph` / 文件映射复制逻辑漏抄部分绑定

### BUG [高] deploy 输出 Portfolio ID 截断
- `deploy deploy` 输出 `f918a74bc99249f5af0ac74a45b8f6e`（**31 位，丢字符**）
- 库内真实 UUID `f918a74bc99249f5af0ac74a454b8f6e`（32 位）
- 用户复制输出 ID 查 `deploy info` 必返回"未找到部署记录"
- 用真实 32 位 ID 查询正常 → 确为输出展示 bug

### 缺失 [中] deploy info 输出问题
- `状态: 1`（原始 int，非"已部署"）
- `源回测任务` 字段空（未关联 source backtest task）

### 缺失 [中] 装配失败静默
PaperTradingWorker 对失败组合仅 `skipping`，deploy 端无回环感知，用户以为部署成功。

## Phase 4 实盘 ❌

### 缺失 [严重] 无 CLI 创建实盘账户
- 顶层无 `account` 命令（`ginkgo --help | grep -c account` = 0）
- `MLiveAccount` 表 0 条记录
- `deploy --mode live --account <id>` 必填 account_id，但无 CLI 产生该 ID
- 实盘链路从账户管理第一公里即断

### BUG [高] 假 account_id 触发裸 SQL 错误
`deploy --mode live --account <假id>` → 裸 `pymysql.err.OperationalError (1054, Unknown column 'portfolio.live_account_id AS portfolio_live_account_id')`，非优雅"账户不存在"。
- 定位：`broker_instance_crud.get_broker_by_live_account` 的 ORM/列映射问题

## 跨阶段问题

- **[高]** 回测与部署无一致性校验：组件绑定可在 deploy 克隆中静默丢失
- **[中]** Worker 参数风格不统一：`worker-backtest -id`（单横线，CLAUDE.md 记载）vs `worker-paper --id`（双横线）；`-id` 在 typer 下解析为 `-i -d` 报 "No such option: -i"
- **[中]** `ginkgo` 是 bash 包装脚本（`/home/kaoru/.local/bin/ginkgo`），对 `serve nohup` 特殊处理，增加调试复杂度

## 建议优先级
1. 修 deploy 克隆丢组件绑定（Phase3 严重 bug）——模拟盘才能走通
2. 修 deploy 输出 UUID 截断 + deploy info 状态枚举
3. 加回测前数据预检（改善最常见"0交易"体验）
4. 补 CLI 实盘账户管理 + deploy live 错误兜底
5. 统一 worker 参数风格
