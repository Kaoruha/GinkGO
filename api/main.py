"""
Ginkgo API Server
FastAPI应用入口，为Web UI和其他客户端提供REST API和WebSocket服务
"""

import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import settings
from core.logging import setup_logging
from middleware.auth import JWTAuthMiddleware
from middleware.error_handler import global_error_handler
from middleware.rate_limit import RateLimitMiddleware
from trailing_slash import strip_trailing_slash
from middleware.api_stats import ApiStatsMiddleware
from core.exceptions import APIError
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

    # 启动回测进度消费者（后台任务，不阻塞）
    try:
        from services.backtest_progress_consumer import get_progress_consumer
        progress_consumer = get_progress_consumer()
        # 创建后台任务，不等待
        asyncio.create_task(progress_consumer.start())
        logger.info("BacktestProgressConsumer started (background)")
    except Exception as e:
        logger.warning(f"Failed to start BacktestProgressConsumer: {e}")

    yield
    # 关闭时
    logger.info("Shutting down Ginkgo API Server...")

    # 停止回测进度消费者
    try:
        from services.backtest_progress_consumer import get_progress_consumer
        progress_consumer = get_progress_consumer()
        await progress_consumer.stop()
        logger.info("BacktestProgressConsumer stopped")
    except Exception as e:
        logger.warning(f"Failed to stop BacktestProgressConsumer: {e}")

    # 关闭 Redis 连接池
    try:
        from core.redis_client import close_redis_pool
        await close_redis_pool()
        logger.info("Redis pool closed")
    except Exception as e:
        logger.warning(f"Failed to close Redis pool: {e}")

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
    redirect_slashes=False,
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
app.add_middleware(ApiStatsMiddleware)
# trailing slash：strip 后路由匹配，禁 307 重定向避免 POST 丢 Auth header（#5389）
# 最后注册 → 栈顶最先执行，JWT/RateLimit 读到 strip 后 path
app.middleware("http")(strip_trailing_slash)

# 全局错误处理
app.exception_handler(Exception)(global_error_handler)
app.exception_handler(APIError)(global_error_handler)
# #5405: 显式注册 fastapi.HTTPException，否则 raise HTTPException 走 Starlette
# 内置默认处理器（针对父类 starlette.HTTPException 注册）返回 {detail} 无 trace_id。
# global_error_handler 已有 HTTPException 分支（error_handler.py:27-37），此处激活它。)
app.exception_handler(HTTPException)(global_error_handler)


@app.get("/health")
async def health_check():
    """健康检查接口（深度：联动 SystemService，核心模块出错时降级 unhealthy）"""
    from health import compute_health
    return compute_health()


@app.get("/api/health")
async def health_check_api():
    """健康检查接口（API路径，用于前端代理；深度检查同 /health）"""
    from health import compute_health
    return compute_health()


# 路由注册 - 统一使用 /api/v1 前缀
from api import auth, dashboard, portfolio, backtest, components, data, arena, node_graph, accounts, trading, validation, deployment
from api import live_trading
from api import file as file_router  # #5659: 文件管理 flat 适配路由（薄委托 FileService）
from api import signals as signal_router
from api import settings as settings_router
from api import system as system_router
from core.version import API_PREFIX

app.include_router(auth.router, prefix=f"{API_PREFIX}/auth", tags=["auth"])
app.include_router(dashboard.router, prefix=f"{API_PREFIX}/dashboards", tags=["dashboard"])
app.include_router(portfolio.router, prefix=f"{API_PREFIX}/portfolios", tags=["portfolio"])
app.include_router(backtest.router, prefix=f"{API_PREFIX}/backtests", tags=["backtest"])
app.include_router(components.router, prefix=f"{API_PREFIX}/components", tags=["components"])
# #5659: file 适配路由 flat 挂载在 /api/v1 下（/file_list、/file、/update_file、/file/{id}）
app.include_router(file_router.router, prefix=API_PREFIX, tags=["files"])
app.include_router(data.router, prefix=f"{API_PREFIX}/data", tags=["data"])
app.include_router(arena.router, prefix=f"{API_PREFIX}/arena", tags=["arena"])
app.include_router(settings_router.router, prefix=f"{API_PREFIX}/settings", tags=["settings"])
app.include_router(node_graph.router, prefix=f"{API_PREFIX}/node-graphs", tags=["node-graphs"])
app.include_router(accounts.router, prefix=f"{API_PREFIX}/accounts", tags=["accounts"])
app.include_router(trading.router, prefix=f"{API_PREFIX}/paper-trading", tags=["paper-trading"])
app.include_router(live_trading.router, prefix=f"{API_PREFIX}/live-trading", tags=["live-trading"])
app.include_router(signal_router.router, prefix=f"{API_PREFIX}/signals", tags=["signals"])
app.include_router(validation.router, prefix=f"{API_PREFIX}/validation", tags=["validation"])
app.include_router(deployment.router, prefix=f"{API_PREFIX}/deploy", tags=["deploy"])
app.include_router(system_router.router, prefix=f"{API_PREFIX}/system", tags=["system"])

# TaskTimer
from api import task_timer as task_timer_router
app.include_router(task_timer_router.router, prefix=f"{API_PREFIX}/task-timer", tags=["task-timer"])

# WebSocket路由
from websocket.handlers import portfolio_handler, system_handler

app.add_websocket_route("/ws/portfolio", portfolio_handler.websocket_endpoint)
app.add_websocket_route("/ws/system", system_handler.websocket_endpoint)


# 自定义 OpenAPI schema：注入 Bearer JWT securityScheme（#5714）
# 鉴权仍由 JWTAuthMiddleware 运行时负责，此处只补 spec 契约
from openapi_schema import build_openapi_schema


def custom_openapi():
    return build_openapi_schema(app)


app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
