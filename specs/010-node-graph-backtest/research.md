# Research: 节点图拖拉拽配置回测功能

**Feature**: 节点图拖拉拽配置回测
**Date**: 2026-02-02
**Status**: Complete

## 研究任务 1: 前端节点图库选型

### 决策: 使用 `@vue-flow/core`

**Rationale**:
1. **原生 Vue 3 支持**: @vue-flow 是专为 Vue 3 设计的流程图库，完全支持 Composition API
2. **TypeScript 支持**: 完整的 TypeScript 类型定义，符合项目规范
3. **文档质量**: 官方文档完善，有丰富的示例代码
4. **生态系统**: 提供官方插件（background、controls、minimap）满足所有需求
5. **性能**: 基于 SVG 渲染，支持 60fps 流畅绘制
6. **社区活跃**: GitHub 4k+ stars，维护活跃

**替代方案评估**:

| 方案 | 优点 | 缺点 | 评分 |
|------|------|------|------|
| @vue-flow/core | 原生 Vue 3、TS 支持、文档完善 | 相对较新 | ⭐⭐⭐⭐⭐ |
| vue-dag | 轻量级 | 文档较少、更新慢 | ⭐⭐⭐ |
| react-flow + wrapper | 功能强大 | 需要适配层、性能损失 | ⭐⭐ |

### 安装命令

```bash
cd web-ui
npm install @vue-flow/core @vue-flow/background @vue-flow/controls @vue-flow/minimap
```

### 基础用法示例

```vue
<template>
  <VueFlow
    v-model:nodes="nodes"
    v-model:edges="edges"
    :default-viewport="{ zoom: 1, x: 0, y: 0 }"
    :min-zoom="0.1"
    :max-zoom="2"
    fit-view-on-init
  >
    <Background />
    <Controls />
    <MiniMap />
  </VueFlow>
</template>

<script setup lang="ts">
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'

const nodes = ref<Node[]>([])
const edges = ref<Edge[]>([])
</script>
```

## 研究任务 2: 节点图数据结构设计

### 节点类型定义

基于 Ginkgo Engine 装配逻辑，定义 9 种节点类型：

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

### 节点端口配置

每种节点类型定义输入/输出端口：

| 节点类型 | 输入端口 | 输出端口 | 说明 |
|---------|---------|---------|------|
| ENGINE | 无 | portfolio | 根节点，输出到 Portfolio |
| FEEDER | 无 | data | 数据源，输出到 Portfolio/Engine |
| BROKER | 无 | execution | 券商，输出到 Portfolio |
| PORTFOLIO | engine, strategy, selector, sizer, risk, analyzer | orders | 投资组合容器 |
| STRATEGY | data | signal | 策略，输出信号 |
| SELECTOR | data | target | 选择器，输出标的 |
| SIZER | signal | position | 规模器，输出仓位 |
| RISK_MANAGEMENT | position, signal | adjusted | 风控，输出调整后信号 |
| ANALYZER | orders, fills | metrics | 分析器，输出指标 |

### 节点数据结构

```typescript
interface GraphNode {
  id: string                    // 唯一标识
  type: NodeType                // 节点类型
  position: { x: number; y: number }  // 画布位置
  data: {
    label: string              // 显示名称
    config: Record<string, any>  // 节点配置参数
    componentUuid?: string     // 关联组件 UUID
    errors?: string[]          // 验证错误
  }
}

interface GraphEdge {
  id: string                    // 唯一标识
  source: string               // 源节点 ID
  target: string               // 目标节点 ID
  sourceHandle?: string        // 源端口名称
  targetHandle?: string        // 目标端口名称
  type?: string                // 边类型（默认、动画等）
}
```

### 连接规则验证

```typescript
// 允许的连接规则
const CONNECTION_RULES: Record<NodeType, {
  outputs: NodeType[];      // 允许连接的目标类型
  maxOutputs?: number;      // 最大输出连接数
}> = {
  [NodeType.ENGINE]: {
    outputs: [NodeType.PORTFOLIO],
    maxOutputs: Infinity,  // 一个 Engine 可以连接多个 Portfolio
  },
  [NodeType.PORTFOLIO]: {
    outputs: [],  // Portfolio 是容器，不是输出节点
  },
  [NodeType.STRATEGY]: {
    outputs: [NodeType.PORTFOLIO],
  },
  [NodeType.RISK_MANAGEMENT]: {
    outputs: [NodeType.PORTFOLIO],
  },
  // ... 其他节点类型
}

// 循环依赖检测算法
function detectCycles(nodes: GraphNode[], edges: GraphEdge[]): GraphEdge[] {
  const graph = new Map<NodeType, NodeType[]>()
  // 构建邻接表
  // 使用 DFS 检测环
  // 返回构成环的边列表
}
```

### 撤销/重做历史存储

使用命令模式实现撤销/重做：

```typescript
interface GraphCommand {
  execute(): void
  undo(): void
}

class AddNodeCommand implements GraphCommand {
  constructor(private node: GraphNode, private store: GraphStore) {}
  execute() { this.store.addNode(this.node) }
  undo() { this.store.removeNode(this.node.id) }
}

class HistoryManager {
  private undoStack: GraphCommand[] = []
  private redoStack: GraphCommand[] = []

  execute(command: GraphCommand) {
    command.execute()
    this.undoStack.push(command)
    this.redoStack = []  // 清空 redo 栈
    if (this.undoStack.length > 20) {
      this.undoStack.shift()  // 限制历史记录为 20 步
    }
  }

  undo() {
    const command = this.undoStack.pop()
    if (command) {
      command.undo()
      this.redoStack.push(command)
    }
  }

  redo() {
    const command = this.redoStack.pop()
    if (command) {
      command.execute()
      this.undoStack.push(command)
    }
  }
}
```

## 研究任务 3: 后端编译服务设计

### Engine 装配逻辑分析

通过分析 `src/ginkgo/core/engine_assembly_service.py`，Engine 装配遵循以下流程：

1. **TimeControlledEventEngine**: 时间控制的事件引擎
2. **BacktestDataFeeder**: 历史数据馈送器
3. **Broker**: 券商接口（SimBroker 或 OkxBroker）
4. **Portfolio**: 投资组合（包含多个组件）
   - Strategy: 策略
   - Selector: 选择器
   - Sizer: 规模器
   - RiskManagement: 风控管理器
   - Analyzer: 分析器

### 节点图到 BacktestTaskCreate 映射规则

```python
class GraphCompiler:
    """节点图编译服务"""

    def compile(self, graph_data: dict) -> BacktestTaskCreate:
        """
        将节点图编译为 BacktestTaskCreate 配置

        映射规则:
        1. ENGINE 节点 → engine_config
        2. BROKER 节点 → engine_config.broker_*
        3. FEEDER 节点 → engine_config 时间范围（覆盖 Engine）
        4. PORTFOLIO 节点 → portfolio_uuids
        5. STRATEGY/SELECTOR/SIZER/RISK/ANALYZER → component_config
        """
        nodes = graph_data['nodes']
        edges = graph_data['edges']

        # 查找 Engine 节点
        engine_node = self._find_node_by_type(nodes, 'engine')
        if not engine_node:
            raise ValueError("必须有一个 ENGINE 节点")

        # 查找 Broker 节点（如果存在）
        broker_node = self._find_node_by_type(nodes, 'broker')

        # 查找 Portfolio 节点
        portfolio_nodes = self._find_nodes_by_type(nodes, 'portfolio')
        if not portfolio_nodes:
            raise ValueError("至少需要一个 PORTFOLIO 节点")

        # 构建 engine_config
        engine_config = {
            'start_date': engine_node['config'].get('start_date'),
            'end_date': engine_node['config'].get('end_date'),
            'initial_cash': broker_node['config'].get('initial_cash', 100000) if broker_node else 100000,
            'commission_rate': broker_node['config'].get('commission_rate', 0.0003) if broker_node else 0.0003,
            'slippage_rate': broker_node['config'].get('slippage_rate', 0.0001) if broker_node else 0.0001,
            'broker_attitude': broker_node['config'].get('broker_attitude', 2) if broker_node else 2,
            'broker_type': broker_node['config'].get('broker_type', 'backtest') if broker_node else 'backtest',
        }

        # 构建 portfolio_uuids
        portfolio_uuids = [p['config']['uuid'] for p in portfolio_nodes]

        # 构建 component_config（从连接到 Portfolio 的组件节点）
        component_config = self._build_component_config(nodes, edges, portfolio_nodes)

        return BacktestTaskCreate(
            name=graph_data.get('name', 'Node Graph Backtest'),
            engine_config=engine_config,
            portfolio_uuids=portfolio_uuids,
            component_config=component_config,
        )
```

### DTO 确认

**结论**: 不需要新的 DTO 类型。节点图编译后的结果是现有的 `BacktestTaskCreate` 格式，通过 `/api/backtest` 接口发送。节点图本身的存储使用 JSON 格式，不需要 DTO。

## 研究任务 4: 数据库设计验证

### MySQL JSON 字段性能

**测试结果**:
- MySQL 5.7+ 的 JSON 字段支持索引（通过虚拟列）
- 对于 < 1MB 的 JSON 文档，查询性能优秀
- 适合存储节点图配置（预计 < 100KB）

**结论**: 使用 JSON 字段存储节点图数据是可行的。

### 节点图版本历史预留字段

```sql
CREATE TABLE node_graphs (
    uuid VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    graph_data JSON NOT NULL,
    user_uuid VARCHAR(64),

    -- 版本历史预留字段
    version INT DEFAULT 1,
    parent_uuid VARCHAR(64),      -- 父版本 UUID
    is_template BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_user_uuid (user_uuid),
    INDEX idx_is_template (is_template),
    INDEX idx_parent_uuid (parent_uuid)
);
```

### 索引策略

| 索引 | 字段 | 用途 | 类型 |
|------|------|------|------|
| PRIMARY | uuid | 主键查询 | BTREE |
| idx_user_uuid | user_uuid | 用户的配置列表 | BTREE |
| idx_is_template | is_template | 模板列表 | BTREE |
| idx_parent_uuid | parent_uuid | 版本历史 | BTREE |

## 技术选型总结

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 前端节点图库 | @vue-flow/core | 原生 Vue 3、完整 TS 支持 |
| 状态管理 | Pinia | 项目已使用，保持一致 |
| 后端框架 | FastAPI | 项目已使用，扩展现有 API |
| 数据库 | MySQL JSON | 性能足够、支持索引 |
| 编译输出 | BacktestTaskCreate | 复用现有 API，无需新 DTO |

## 待解决的技术问题

1. **节点图验证规则**: 需要完整的端口类型匹配规则
2. **组件配置获取**: 需要调用 `/api/components` 获取可用组件列表
3. **模板数据初始化**: 需要设计 5 个预设模板的节点图数据
4. **并发编辑冲突**: 初期不支持，未来可使用乐观锁
