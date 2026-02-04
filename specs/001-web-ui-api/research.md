# Research & Technology Decisions

**Feature**: Web UI and API Server
**Date**: 2026-01-31
**Phase**: Phase 0 - Research & Technology Decisions

## Technology Decisions Summary

| 技术选型 | 决策 | 理由 | 备选方案 |
|---------|------|------|---------|
| 后端框架 | FastAPI | 现代异步框架、自动OpenAPI文档、原生WebSocket支持 | Flask, Django |
| 前端框架 | Vue 3 (Composition API) | 响应式设计、组件化开发、优秀生态 | React, Svelte |
| 构建工具 | Vite | 快速热更新、生产优化 | Webpack, esbuild |
| UI组件库 | Ant Design Vue | 丰富的企业级组件、Vue 3支持 | Element Plus, Naive UI |
| CSS框架 | TailwindCSS | 原子化CSS、无运行时CSS、高度可定制 | styled-components, Sass |
| 状态管理 | Pinia | Vue 3官方推荐、轻量级、TypeScript支持 | Vuex, Redux |
| K线图表 | Lightweight Charts | TradingView开源、专业金融图表、高性能 | ECharts K线图 |
| 统计图表 | ECharts | 功能全面、国内文档完善 | Chart.js, D3.js |
| 代码编辑器 | Monaco Editor | VS Code同款、Python语法高亮 | CodeMirror, Ace |
| WebSocket库 | native WebSocket (前端) / FastAPI WebSocket (后端) | 原生支持、无额外依赖 | Socket.IO |

## Decision 1: FastAPI as Backend Framework

**Decision**: 使用 FastAPI 作为 API Server 框架

**Rationale**:
- 现代异步Python框架，基于Starlette和Pydantic
- 自动生成OpenAPI 3.1文档（Swagger UI）
- 原生WebSocket支持
- 类型提示和数据验证
- 优秀的性能表现（与Go和Node.js相当）
- 活跃的社区和丰富的中间件生态

**Alternatives Considered**:
- **Flask**: 轻量级但需要手动添加很多功能，WebSocket需要额外库
- **Django**: 功能完整但过于重量级，实时性支持不如FastAPI
- **Falcon**: 性能优秀但生态较小，学习曲线陡峭

## Decision 2: Vue 3 + Vite + Pinia as Frontend Stack

**Decision**: 使用 Vue 3 (Composition API) + Vite + Pinia

**Rationale**:
- Vue 3 Composition API 提供更好的代码组织和类型推断
- Vite 提供极快的开发服务器启动和热更新
- Pinia 是Vue 3官方推荐的状态管理方案，类型友好
- 与Ant Design Vue有良好的集成

**Alternatives Considered**:
- **React**: 生态更大但学习曲线更陡，组件代码量更大
- **Svelte**: 性能优秀但生态较小，企业级组件库支持不足
- **Vuex**: Vue 3下不再推荐，Pinia是官方继任者

## Decision 3: TailwindCSS + Ant Design Vue for UI

**Decision**: 使用 TailwindCSS + Ant Design Vue

**Rationale**:
- TailwindCSS 提供原子化CSS，无运行时开销，高度可定制
- Ant Design Vue 提供丰富的企业级UI组件
- 两者结合既保证开发效率（使用组件库），又保持灵活性（TailwindCSS定制）

**Alternatives Considered**:
- **Element Plus**: 组件丰富但设计风格不如Ant Design现代
- **Naive UI**: 类型友好但生态较新，组件不够丰富
- **纯TailwindCSS**: 需要自己实现所有组件，开发效率低

## Decision 4: Lightweight Charts for K-Line Charts

**Decision**: 使用 Lightweight Charts (TradingView开源)

**Rationale**:
- TradingView官方开源，专为金融图表设计
- 高性能渲染，支持大量数据点
- 原生支持实时数据更新
- 轻量级（~200KB gzipped）
- 响应式设计，支持缩放和平移

**Alternatives Considered**:
- **ECharts K线图**: 功能强大但文件更大（~1MB），性能不如Lightweight Charts
- **Highcharts**: 商业库，需要付费，不适合开源项目

## Decision 5: ECharts for Statistical Charts

**Decision**: 使用 ECharts 作为通用统计图表库

**Rationale**:
- 功能全面，支持折线图、柱状图、饼图、散点图等
- 国内文档完善，中文社区活跃
- 与Vue 3有良好的集成（vue-echarts）
- 适合净值曲线、盈亏分析、持仓分布等统计图表

**Alternatives Considered**:
- **Chart.js**: 轻量但功能不如ECharts全面
- **D3.js**: 灵活但学习曲线陡，开发效率低

## Decision 6: Monaco Editor for Code Editor

**Decision**: 使用 Monaco Editor

**Rationale**:
- VS Code同款编辑器
- 完整的Python语法高亮和智能提示
- 支持代码格式化和错误检查
- 成熟稳定，广泛使用

**Alternatives Considered**:
- **CodeMirror**: 轻量但功能不如Monaco全面
- **Ace**: 功能不错但更新较少

## Decision 7: WebSocket Architecture

**Decision**:
- 后端: FastAPI原生WebSocket支持
- 前端: 浏览器原生WebSocket API
- 消息格式: JSON
- 连接管理: 连接池 + 心跳检测

**Rationale**:
- FastAPI原生支持WebSocket，无需额外依赖
- 原生WebSocket API性能最好，兼容性好
- JSON格式简单易解析，与REST API保持一致

**Alternatives Considered**:
- **Socket.IO**: 提供自动重连但增加了额外依赖，对于简单场景过于复杂
- **Server-Sent Events**: 单向通信，不支持客户端到服务器的消息

## Best Practices

### FastAPI Best Practices

1. **项目结构**
```python
apiserver/
├── main.py              # 应用入口
├── api/                 # 路由模块
├── models/              # Pydantic DTOs
├── services/            # 业务逻辑
├── middleware/          # 中间件
└── core/                # 核心配置
```

2. **依赖注入**
```python
# 通过ServiceHub访问Ginkgo核心服务
from ginkgo import service_hub

portfolio_service = service_hub.trading.portfolio_service
```

3. **错误处理**
```python
from fastapi import HTTPException

@app.get("/api/portfolio/{uuid}")
async def get_portfolio(uuid: str):
    portfolio = portfolio_service.get_by_id(uuid)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio
```

4. **WebSocket连接管理**
```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_json(message)
```

### Vue 3 Best Practices

1. **组合式函数模式**
```typescript
// composables/useTable.ts
export function useTable<T>(fetchFn: (params: any) => Promise<T[]>) {
  const data = ref<T[]>([])
  const loading = ref(false)

  const fetch = async (params?: any) => {
    loading.value = true
    data.value = await fetchFn(params)
    loading.value = false
  }

  return { data, loading, fetch }
}
```

2. **API封装模式**
```typescript
// api/request.ts
import axios from 'axios'

const service = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 请求拦截器
service.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// 响应拦截器
service.interceptors.response.use(
  response => response.data,
  error => {
    // 统一错误处理
    return Promise.reject(error)
  }
)
```

3. **TailwindCSS配置**
```javascript
// tailwind.config.js
export default {
  content: [
    './index.html',
    './src/**/*.{vue,ts}',
  ],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: '#1890ff', light: '#40a9ff', dark: '#096dd9' },
      },
    },
  },
}
```

### WebSocket Real-time Data Best Practices

1. **心跳机制**
```typescript
// 前端心跳
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ping' }))
  }
}, 30000)
```

2. **断线重连**
```typescript
function connectWebSocket() {
  ws = new WebSocket(url)

  ws.onclose = () => {
    setTimeout(connectWebSocket, 3000)  // 3秒后重连
  }
}
```

3. **消息格式**
```json
{
  "type": "portfolio_update",
  "data": {
    "uuid": "xxx",
    "net_value": 12345.67,
    "positions": [...]
  },
  "timestamp": "2026-01-31T10:00:00Z"
}
```

## Performance Considerations

### API Performance

1. **响应时间优化**
- 使用async/await异步处理
- 批量数据查询
- Redis缓存热点数据
- 数据库查询优化（索引、分页）

2. **并发处理**
- 使用uvicorn多worker部署
- 连接池管理
- 请求限流防止滥用

### Frontend Performance

1. **代码分割**
```typescript
// 路由懒加载
const Dashboard = () => import('./views/Dashboard/index.vue')
```

2. **组件懒加载**
```typescript
// MonacoEditor按需加载
const MonacoEditor = defineAsyncComponent(() =>
  import('./components/editors/MonacoEditor.vue')
)
```

3. **虚拟滚动**
- 大列表使用虚拟滚动（vue-virtual-scroller）

## Security Considerations

### API Security

1. **认证授权**
- JWT Token认证
- Token过期时间：24小时
- Refresh Token机制

2. **CORS配置**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 开发环境
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

3. **输入验证**
- Pydantic模型验证
- SQL注入防护（使用参数化查询）
- XSS防护（前端转义）

### Frontend Security

1. **Token存储**
- 存储在localStorage
- 自动刷新机制
- 退出时清除Token

2. **HTTPS**
- 生产环境强制HTTPS
- Cookie设置Secure和HttpOnly标志

## Deployment Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Nginx                            │
│  (反向代理、SSL终止、静态文件服务、WebSocket代理)      │
└────────────┬────────────────────────────────────────┘
             │
             ├──────────────┬──────────────┐
             ▼              ▼              ▼
     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
     │ API Server  │ │   Web UI     │ │ DataWorker  │
     │  (FastAPI)  │ │   (Vue 3)    │ │   (现有)    │
     └──────┬──────┘ └─────────────┘ └─────────────┘
            │
            ├──────────────┬──────────────┬──────────────┐
            ▼              ▼              ▼              ▼
      ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
      │ ClickHouse│ │  MySQL  │  │ MongoDB │  │  Redis  │
      └─────────┘  └─────────┘  └─────────┘  └─────────┘
            │
            ▼
      ┌─────────┐
      │  Kafka  │
      └─────────┘
```

## References

- FastAPI官方文档: https://fastapi.tiangolo.com/
- Vue 3官方文档: https://vuejs.org/
- TailwindCSS文档: https://tailwindcss.com/
- Ant Design Vue文档: https://antdv.com/
- Lightweight Charts文档: https://www.tradingview.com/lightweight-charts/
- ECharts文档: https://echarts.apache.org/
- Monaco Editor文档: https://microsoft.github.io/monaco-editor/
