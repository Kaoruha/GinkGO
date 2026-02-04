"""
Ginkgo API Server
FastAPI应用入口，为Web UI和其他客户端提供REST API和WebSocket服务
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import settings
from core.logging import setup_logging
from middleware.auth import JWTAuthMiddleware
from middleware.error_handler import global_error_handler
from middleware.rate_limit import RateLimitMiddleware
from websocket.manager import connection_manager

# 设置日志
logger = setup_logging()

# Ginkgo核心服务导入
try:
    from ginkgo import services
    from ginkgo.libs import GLOG, GCONF

    logger.info("Ginkgo core services loaded successfully")
except ImportError as e:
    logger.warning(f"Ginkgo core not available: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("Starting Ginkgo API Server...")
    await connection_manager.start()

    # TODO: 启动回测进度消费者（暂时禁用）
    # try:
    #     from services.backtest_progress_consumer import get_progress_consumer
    #     progress_consumer = get_progress_consumer()
    #     await progress_consumer.start()
    #     logger.info("BacktestProgressConsumer started")
    # except Exception as e:
    #     logger.warning(f"Failed to start BacktestProgressConsumer: {e}")

    yield
    # 关闭时
    logger.info("Shutting down Ginkgo API Server...")

    # TODO: 停止回测进度消费者
    # try:
    #     from services.backtest_progress_consumer import get_progress_consumer
    #     progress_consumer = get_progress_consumer()
    #     await progress_consumer.stop()
    #     logger.info("BacktestProgressConsumer stopped")
    # except Exception as e:
    #     logger.warning(f"Failed to stop BacktestProgressConsumer: {e}")

    await connection_manager.stop()


# 创建FastAPI应用
app = FastAPI(
    title="Ginkgo API Server",
    description="Ginkgo量化交易系统API接口",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 自定义中间件
app.add_middleware(JWTAuthMiddleware)
app.add_middleware(RateLimitMiddleware)

# 全局错误处理
app.exception_handler(Exception)(global_error_handler)


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "ginkgo-api-server"}


@app.get("/api/health")
async def health_check_api():
    """健康检查接口（API路径，用于前端代理）"""
    return {"status": "healthy", "service": "ginkgo-api-server"}


# 路由注册
from api import auth, dashboard, portfolio, backtest, components, data, arena, node_graph
from api import settings as settings_router

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
app.include_router(components.router, prefix="/api/components", tags=["components"])
app.include_router(data.router, prefix="/api/data", tags=["data"])
app.include_router(arena.router, prefix="/api/arena", tags=["arena"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["settings"])
app.include_router(node_graph.router, prefix="/api/node-graphs", tags=["node-graphs"])

# WebSocket路由
from websocket.handlers import portfolio_handler, system_handler

app.add_websocket_route("/ws/portfolio", portfolio_handler.websocket_endpoint)
app.add_websocket_route("/ws/system", system_handler.websocket_endpoint)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
