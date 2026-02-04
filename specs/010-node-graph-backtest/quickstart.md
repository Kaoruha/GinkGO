# Quickstart: 节点图拖拉拽配置回测功能

**Feature**: 节点图拖拉拽配置回测
**Date**: 2026-02-02

## 前置条件

1. **后端环境**:
   - Python 3.12.8
   - MySQL 5.7+ (启用 JSON 支持)
   - 依赖包已安装: `pip install -r apiserver/requirements.txt`

2. **前端环境**:
   - Node.js 18+
   - Vue 3 + TypeScript 项目

3. **数据库**:
   - 已创建 `ginkgo` 数据库
   - 已执行节点图表迁移脚本

## 安装步骤

### 1. 安装前端依赖

```bash
cd web-ui
npm install @vue-flow/core @vue-flow/background @vue-flow/controls @vue-flow/minimap
```

### 2. 创建数据库表

```bash
cd apiserver
mysql -u root -p ginkgo < migrations/create_node_graphs.sql
```

### 3. 启动后端服务

```bash
cd apiserver
python start.py
```

### 4. 启动前端开发服务

```bash
cd web-ui
npm run dev
```

## 快速开始

### 创建第一个节点图配置

1. **打开节点图编辑器**
   - 访问 `http://localhost:5173/backtest/graph-editor`
   - 或从回测列表页点击"节点图配置"按钮

2. **添加节点**
   - 从左侧节点库拖拽节点到画布：
     - 拖拽 `ENGINE` 节点到画布中心
     - 拖拽 `PORTFOLIO` 节点到画布
     - 拖拽 `STRATEGY` 节点到画布

3. **连接节点**
   - 从 ENGINE 节点的输出端口拖拽连线到 PORTFOLIO 的输入端口
   - 从 STRATEGY 节点的输出端口拖拽连线到 PORTFOLIO 的输入端口

4. **配置节点参数**
   - 点击 ENGINE 节点
   - 在右侧面板配置：
     - 开始日期: `2023-01-01`
     - 结束日期: `2023-12-31`
   - 点击 STRATEGY 节点
   - 在右侧面板选择策略类型和参数

5. **验证节点图**
   - 点击顶部工具栏的"验证"按钮
   - 查看验证结果，修复所有错误

6. **保存配置**
   - 点击"保存"按钮
   - 输入配置名称: `我的第一个回测配置`
   - 点击确认

7. **编译并创建回测任务**
   - 点击"编译"按钮
   - 预览生成的回测配置 JSON
   - 点击"创建回测任务"
   - 页面跳转到回测详情页

### 使用模板快速创建

1. **打开模板列表**
   - 点击"从模板创建"按钮

2. **选择模板**
   - 选择"双均线策略"模板
   - 点击"使用模板"

3. **修改配置**
   - 根据需要调整节点参数
   - 修改时间范围或策略参数

4. **保存为新配置**
   - 点击"保存"
   - 输入新的配置名称

## 节点连接规则

### 必须遵守的规则

1. **根节点**: 必须恰好有一个 ENGINE 节点
2. **投资组合**: 至少需要一个 PORTFOLIO 节点
3. **引擎连接**: ENGINE 必须连接到至少一个 PORTFOLIO
4. **禁止循环**: 不能创建循环依赖的连接

### 允许的连接

| 源节点 | 可连接的目标节点 |
|--------|----------------|
| ENGINE | PORTFOLIO |
| FEEDER | PORTFOLIO, STRATEGY, SELECTOR |
| BROKER | PORTFOLIO |
| STRATEGY | PORTFOLIO, SIZER, RISK_MANAGEMENT |
| SELECTOR | PORTFOLIO, SIZER |
| SIZER | PORTFOLIO, RISK_MANAGEMENT |
| RISK_MANAGEMENT | PORTFOLIO |
| ANALYZER | PORTFOLIO |

### 端口数据类型

| 端口名称 | 数据类型 | 说明 |
|---------|---------|------|
| portfolio | portfolio | 引擎到投资组合的连接 |
| data | data | 历史数据 |
| execution | execution | 券商交易执行 |
| signal | signal | 策略信号 |
| target | target | 选择器标的 |
| position | position | 规模器仓位 |
| adjusted | adjusted | 风控调整后的信号 |
| metrics | metrics | 分析器指标 |
| orders | orders | 订单输出 |
| fills | fills | 成交输出 |

## 常见问题

### Q: 为什么无法连接两个节点？

A: 检查以下情况：
- 端口数据类型是否匹配
- 是否违反连接规则（参考上表）
- 是否创建了循环依赖

### Q: 节点显示红色边框？

A: 节点配置有错误，点击节点查看错误详情：
- ENGINE 节点: 必须配置开始和结束日期
- PORTFOLIO 节点: 必须选择有效的投资组合
- 组件节点: 必须选择有效的组件

### Q: 如何删除节点或连接线？

A:
- 删除节点: 选中节点后按 Delete 键
- 删除连接线: 选中连接线后点击删除按钮

### Q: 如何撤销操作？

A:
- Windows/Linux: Ctrl + Z
- macOS: Cmd + Z
- 重做: Ctrl + Y / Cmd + Y

### Q: 节点图有大小限制吗？

A:
- 最多支持 100 个节点
- 画布可无限滚动
- 支持缩放 (10% - 200%)

## API 使用示例

### 创建节点图配置

```bash
curl -X POST http://localhost:8000/api/node-graphs \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "我的回测配置",
    "graph_data": {
      "nodes": [
        {
          "id": "engine-1",
          "type": "engine",
          "position": { "x": 100, "y": 100 },
          "data": {
            "label": "回测引擎",
            "config": {
              "start_date": "2023-01-01",
              "end_date": "2023-12-31"
            }
          }
        }
      ],
      "edges": []
    }
  }'
```

### 编译节点图为回测配置

```bash
curl -X POST http://localhost:8000/api/node-graphs/{uuid}/compile \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 验证节点图配置

```bash
curl -X POST http://localhost:8000/api/node-graphs/{uuid}/validate \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 下一步

- 查看 `data-model.md` 了解完整的数据模型
- 查看 `contracts/api.yaml` 了解完整的 API 文档
- 查看 `contracts/graph-schema.ts` 了解前端类型定义
