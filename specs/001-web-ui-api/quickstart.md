# Quick Start Guide

**Feature**: Web UI and API Server
**Date**: 2026-01-31
**Phase**: Phase 1 - Design & Contracts

## Prerequisites

### System Requirements

- Python 3.12.8+
- Node.js 18+ (for pnpm)
- Docker & Docker Compose (for containerized deployment)
- ClickHouse, MySQL, MongoDB, Redis running

### Ginkgo Core Services

Ensure the following Ginkgo services are running:

```bash
# 启动所有依赖服务
cd /home/kaoru/Ginkgo/.conf
docker-compose up -d

# 验证服务状态
docker-compose ps
```

## Development Setup

### 1. API Server Setup

```bash
# 进入API Server目录
cd /home/kaoru/Ginkgo/apiserver

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
python main.py
```

API Server将在 `http://localhost:8000` 启动。

**验证安装**:
```bash
# 访问API文档
open http://localhost:8000/docs

# 测试健康检查接口
curl http://localhost:8000/health
```

### 2. Web UI Setup (用户手动执行)

```bash
# 进入Web UI目录
cd /home/kaoru/Ginkgo/web-ui

# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev
```

Web UI将在 `http://localhost:5173` 启动。

**验证安装**:
- 打开浏览器访问 `http://localhost:5173`
- 应该看到Ginkgo登录页面

### 3. 配置环境变量

创建 `.env` 文件（`/home/kaoru/Ginkgo/.conf/.env`）：

```bash
# Ginkgo配置
GINKGO_DB_MODE=mysql
GINKGO_MYSQLHOST=localhost
GINKGO_MYSQLPORT=3306
GINKGO_MYSQLUSER=ginkgoadm
GINKGO_MYSQLPASSWD=hellomysql
GINKGO_MONGODATABASE=ginkgo
GINKGO_MONGOHOST=localhost
GINKGO_MONGOPORT=27017
GINKGO_CLICKHOUSEHOST=localhost
GINKGO_CLICKHOUSEPORT=9000
GINKGO_REDISHOST=localhost
GINKGO_REDISPORT=6379

# Kafka配置
GINKGO_KAFKA_HOST=localhost
GINKGO_KAFKA_PORT=9092

# API Server配置
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS配置
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

## Docker Deployment

### 使用Docker Compose

```bash
# 进入配置目录
cd /home/kaoru/Ginkgo/.conf

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f api-server
docker-compose logs -f web-ui

# 停止服务
docker-compose down
```

### 访问服务

- **API Server**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **Web UI**: http://localhost:80 (Nginx代理)

## API Usage Examples

### 1. 用户认证

```bash
# 登录获取Token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# 响应
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2026-02-01T10:00:00Z",
  "user": {
    "uuid": "xxx",
    "name": "admin"
  }
}
```

### 2. 查询Portfolio列表

```bash
curl -X GET http://localhost:8000/api/portfolio \
  -H "Authorization: Bearer {token}"
```

### 3. 创建回测任务

```bash
curl -X POST http://localhost:8000/api/backtest \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "双均线策略回测",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "initial_cash": 100000,
    "components": {
      "strategy": "strategy-uuid",
      "selector": "selector-uuid",
      "sizer": "sizer-uuid",
      "risk_manager": "risk-manager-uuid"
    }
  }'
```

### 4. WebSocket连接

```javascript
// 连接Portfolio实时数据推送
const ws = new WebSocket('ws://localhost:8000/ws/portfolio?token={token}')

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  console.log('Portfolio update:', data)
}
```

## Frontend Development

### 项目结构

```
web-ui/
├── src/
│   ├── main.ts              # 应用入口
│   ├── App.vue             # 根组件
│   ├── views/              # 页面组件
│   ├── components/         # 通用组件
│   ├── stores/             # Pinia状态管理
│   ├── api/                # API封装
│   └── styles/             # 样式文件
├── public/                 # 静态资源
├── package.json
├── vite.config.ts
└── tsconfig.json
```

### 开发命令

```bash
# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev

# 构建生产版本（用户手动执行）
pnpm build

# 预览生产构建
pnpm preview
```

### 代码规范

```bash
# ESLint检查
pnpm lint

# ESLint修复
pnpm lint:fix

# 类型检查
pnpm type-check
```

## Testing

### API Server测试

```bash
# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行数据库测试
pytest tests/database/ -k "test_portfolio"

# 查看测试覆盖率
pytest --cov=apiserver --cov-report=html
```

### 前端测试

```bash
# 运行单元测试
pnpm test:unit

# 运行E2E测试
pnpm test:e2e

# 查看测试覆盖率
pnpm test:coverage
```

## Troubleshooting

### 常见问题

**1. API Server启动失败**
```bash
# 检查Ginkgo核心服务是否运行
docker-compose ps

# 检查环境变量
cat .conf/.env
```

**2. WebSocket连接失败**
```bash
# 检查Token是否有效
curl -X POST http://localhost:8000/api/auth/verify \
  -H "Authorization: Bearer {token}"

# 检查WebSocket端点
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  http://localhost:8000/ws/portfolio
```

**3. 前端无法连接API**
```bash
# 检查CORS配置
curl -H "Origin: http://localhost:5173" \
  -X OPTIONS http://localhost:8000/api/portfolio

# 检查API Server是否运行
curl http://localhost:8000/health
```

**4. 数据库连接失败**
```bash
# 检查MySQL连接
mysql -h localhost -u ginkgoadm -phellomysql ginkgo

# 检查ClickHouse连接
clickhouse-client --host localhost --port 9000

# 检查Redis连接
redis-cli -h localhost -p 6379 ping
```

## Production Deployment

### 环境变量

生产环境需要设置以下环境变量：

```bash
# 使用强密码
MYSQL_PASSWORD=<strong-password>
MONGO_INITDB_ROOT_PASSWORD=<strong-password>
SECRET_KEY=<strong-secret-key>

# 配置CORS
CORS_ORIGINS=https://your-domain.com

# 配置HTTPS
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
```

### Nginx配置

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /api/ {
        proxy_pass http://api-server:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws/ {
        proxy_pass http://api-server:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location / {
        root /var/www/web-ui;
        try_files $uri $uri/ /index.html;
    }
}
```

## Next Steps

1. **Phase 2**: 运行 `/speckit.tasks` 生成详细任务列表
2. **开始开发**: 按照任务列表逐个实现功能
3. **测试验证**: 运行测试确保功能正确
4. **部署上线**: 使用Docker Compose部署到生产环境

## Additional Resources

- [API文档](http://localhost:8000/docs) - 自动生成的OpenAPI文档
- [架构文档](./architecture.md) - 详细的架构设计
- [数据模型](./data-model.md) - 数据模型设计
- [研究文档](./research.md) - 技术选型调研
