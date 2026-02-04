# Data Model: 节点图拖拉拽配置回测功能

**Feature**: 节点图拖拉拽配置回测
**Date**: 2026-02-02

## 实体定义

### 1. NodeGraph (节点图配置)

用户创建的回测节点图配置，包含节点、连接和元数据。

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| uuid | VARCHAR(64) | 是 | - | 唯一标识符 |
| name | VARCHAR(255) | 是 | - | 配置名称 |
| description | TEXT | 否 | NULL | 配置描述 |
| graph_data | JSON | 是 | - | 节点图数据（节点、连接、画布状态） |
| user_uuid | VARCHAR(64) | 是 | - | 所有者用户 ID |
| version | INT | 是 | 1 | 版本号 |
| parent_uuid | VARCHAR(64) | 否 | NULL | 父版本 UUID（用于版本历史） |
| is_template | BOOLEAN | 是 | FALSE | 是否为模板 |
| is_public | BOOLEAN | 是 | FALSE | 是否公开共享 |
| created_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP ON UPDATE | 更新时间 |

#### graph_data JSON 结构

```json
{
  "nodes": [
    {
      "id": "node-1",
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
  "edges": [
    {
      "id": "edge-1",
      "source": "node-1",
      "target": "node-2",
      "sourceHandle": "portfolio",
      "targetHandle": "engine"
    }
  ],
  "viewport": {
    "x": 0,
    "y": 0,
    "zoom": 1
  }
}
```

### 2. NodeTemplate (节点图模板)

系统预设的节点图模板，用户可基于模板快速创建配置。

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| uuid | VARCHAR(64) | 是 | - | 唯一标识符 |
| name | VARCHAR(255) | 是 | - | 模板名称 |
| description | TEXT | 否 | NULL | 模板描述 |
| category | VARCHAR(100) | 否 | NULL | 分类（如：双均线、多因子） |
| graph_data | JSON | 是 | - | 预配置的节点图数据 |
| is_system | BOOLEAN | 是 | FALSE | 是否系统模板（不可删除） |
| created_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 是 | CURRENT_TIMESTAMP ON UPDATE | 更新时间 |

### 3. GraphNode (节点)

节点图中单个节点的数据结构（作为 graph_data 的一部分）。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 节点唯一标识 |
| type | NodeType | 是 | 节点类型（见下方枚举） |
| position | Position | 是 | 画布位置坐标 |
| data | NodeData | 是 | 节点数据和配置 |

#### NodeType 枚举

```typescript
enum NodeType {
  ENGINE = 'engine',           // 根节点：回测引擎配置
  FEEDER = 'feeder',           // 数据源：历史数据馈送
  BROKER = 'broker',           // 券商：交易执行
  PORTFOLIO = 'portfolio',     // 投资组合：策略容器
  STRATEGY = 'strategy',       // 策略：信号生成
  SELECTOR = 'selector',       // 选择器：标的筛选
  SIZER = 'sizer',             // 规模器：仓位计算
  RISK_MANAGEMENT = 'risk',    // 风控：风险管理
  ANALYZER = 'analyzer',       // 分析器：性能分析
}
```

#### NodeData 结构

```typescript
interface NodeData {
  label: string                 // 显示名称
  config: NodeConfig            // 节点配置参数
  componentUuid?: string        // 关联组件 UUID
  errors?: string[]             // 验证错误列表
  description?: string          // 节点描述
}

interface NodeConfig extends Record<string, any> {
  // Engine 节点配置
  start_date?: string
  end_date?: string

  // Broker 节点配置
  broker_type?: 'backtest' | 'okx'
  initial_cash?: number
  commission_rate?: number
  slippage_rate?: number
  broker_attitude?: number

  // Portfolio 节点配置
  portfolio_uuid?: string

  // Strategy/Selector/Sizer/Risk/Analyzer 节点配置
  component_uuid?: string
  component_params?: Record<string, any>
}
```

### 4. GraphEdge (连接线)

节点之间的连接关系（作为 graph_data 的一部分）。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 是 | 连接唯一标识 |
| source | string | 是 | 源节点 ID |
| target | string | 是 | 目标节点 ID |
| sourceHandle | string | 否 | 源端口名称 |
| targetHandle | string | 否 | 目标端口名称 |
| type | string | 否 | 边类型（默认、动画等） |
| animated | boolean | 否 | 是否动画效果 |

### 5. NodePort (节点端口)

节点的输入/输出端口定义。

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 端口名称 |
| type | 'input' \| 'output' | 端口类型 |
| dataType | string | 数据类型（用于验证连接） |
| required | boolean | 是否必需连接 |

#### 端口类型定义

每种节点类型的端口配置：

| 节点类型 | 输入端口 | 输出端口 |
|---------|---------|---------|
| ENGINE | 无 | portfolio |
| FEEDER | 无 | data |
| BROKER | 无 | execution |
| PORTFOLIO | engine, strategy, selector, sizer, risk, analyzer, data, execution | orders, fills |
| STRATEGY | data | signal |
| SELECTOR | data | target |
| SIZER | signal, target | position |
| RISK_MANAGEMENT | position, signal | adjusted |
| ANALYZER | orders, fills | metrics |

## 关系图

```
┌─────────────┐     ┌─────────────┐
│  User       │────<│ NodeGraph   │
│  (user_uuid)│     │ (user_uuid) │
└─────────────┘     └─────────────┘
                          │
                          | parent_uuid
                          │
                          v
                   ┌─────────────┐
                   │ NodeGraph   │
                   │ (previous)  │
                   └─────────────┘

┌─────────────┐
│NodeTemplate │
│(is_system)  │
└─────────────┘
       │
       | graph_data (复用结构)
       │
       v
┌─────────────────────────────┐
│      graph_data (JSON)      │
├─────────────────────────────┤
│ nodes: GraphNode[]          │
│   ├─ id, type, position    │
│   └─ data: NodeData        │
│ edges: GraphEdge[]          │
│   ├─ source, target        │
│   └─ sourceHandle, targetHandle │
│ viewport: {x, y, zoom}      │
└─────────────────────────────┘
```

## 验证规则

### 节点图级别验证

1. **必须恰好有一个 ENGINE 节点**
2. **至少有一个 PORTFOLIO 节点**
3. **ENGINE 必须连接到至少一个 PORTFOLIO**
4. **禁止循环依赖**
5. **所有必需端口必须连接**

### 节点级别验证

1. **Engine 节点**: 必须配置 start_date 和 end_date
2. **Portfolio 节点**: 必须选择有效的 portfolio_uuid
3. **Strategy/Risk 等组件节点**: 必须选择有效的 component_uuid

### 连接级别验证

1. **端口类型匹配**: sourceHandle 的数据类型必须兼容 targetHandle
2. **连接规则合规**: 遵循预定义的连接规则

## 状态转换

```
┌──────────┐  创建  ┌──────────┐
│   新建   │───────>│  草稿   │
└──────────┘        └──────────┘
                          │
                          │ 保存
                          v
                   ┌──────────┐
                   │  已保存  │
                   └──────────┘
                          │
                          │ 编译
                          v
                   ┌──────────┐
                   │  可运行  │─────> 创建回测任务
                   └──────────┘
```

## 数据库迁移脚本

```sql
-- 创建节点图表
CREATE TABLE IF NOT EXISTS node_graphs (
    uuid VARCHAR(64) PRIMARY KEY COMMENT '唯一标识符',
    name VARCHAR(255) NOT NULL COMMENT '配置名称',
    description TEXT COMMENT '配置描述',
    graph_data JSON NOT NULL COMMENT '节点图数据',
    user_uuid VARCHAR(64) NOT NULL COMMENT '所有者用户ID',
    version INT DEFAULT 1 COMMENT '版本号',
    parent_uuid VARCHAR(64) COMMENT '父版本UUID',
    is_template BOOLEAN DEFAULT FALSE COMMENT '是否为模板',
    is_public BOOLEAN DEFAULT FALSE COMMENT '是否公开共享',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_user_uuid (user_uuid),
    INDEX idx_is_template (is_template),
    INDEX idx_parent_uuid (parent_uuid),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='节点图配置表';

-- 创建节点图模板表
CREATE TABLE IF NOT EXISTS node_graph_templates (
    uuid VARCHAR(64) PRIMARY KEY COMMENT '唯一标识符',
    name VARCHAR(255) NOT NULL COMMENT '模板名称',
    description TEXT COMMENT '模板描述',
    category VARCHAR(100) COMMENT '分类',
    graph_data JSON NOT NULL COMMENT '预配置的节点图数据',
    is_system BOOLEAN DEFAULT FALSE COMMENT '是否系统模板',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_category (category),
    INDEX idx_is_system (is_system)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='节点图模板表';
```
