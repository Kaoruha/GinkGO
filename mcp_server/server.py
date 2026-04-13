# Upstream: CLI (ginkgo serve mcp)、Claude Desktop (MCP客户端)
# Downstream: GinkgoOKXTools (工具实现)、Ginkgo Services
# Role: MCP Server主入口，同时支持 Streamable HTTP（新规范）和旧 SSE 传输


"""
Ginkgo MCP Server - OKX交易能力

为AI智能体提供OKX交易能力的MCP服务器。

支持三种传输模式：
    1. stdio - 标准输入输出（默认，适用于本地进程调用）
    2. sse - HTTP模式，同时挂载旧SSE和Streamable HTTP
    3. streamable_http - 同sse，启动同一HTTP服务

环境变量：
    GINKGO_API_KEY: Ginkgo API Key（stdio模式必需，HTTP模式通过Header传递）

启动方式：
    # stdio模式（默认）
    ginkgo serve mcp
    GINKGO_API_KEY=xxx ginkgo serve mcp

    # HTTP模式（推荐）
    ginkgo serve mcp --transport sse --port 8001
"""

import asyncio
import contextlib
import contextvars
import json
import os
import sys
from typing import Any

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import TextContent

from ginkgo.libs import GLOG

# contextvars: 为 Streamable HTTP 多会话隔离不同的 API Key 工具实例
_current_tools: contextvars.ContextVar = contextvars.ContextVar('current_tools')


class GinkgoMCPServer:
    """Ginkgo MCP Server - 支持 stdio / SSE / Streamable HTTP 传输"""

    def __init__(self, transport: str = "stdio", port: int = 8001, host: str = "localhost"):
        """初始化MCP Server"""
        if transport not in ("stdio", "sse", "streamable_http"):
            raise ValueError(f"Unknown transport: {transport}. Use stdio, sse, or streamable_http")

        self.transport = transport
        self.port = port
        self.host = host
        self.server = Server("ginkgo-okx")
        self.tools = None
        self._session_manager = None

        # stdio模式需要启动时提供API KEY
        if transport == "stdio":
            self._api_key_value = os.getenv("GINKGO_API_KEY")
            if not self._api_key_value:
                GLOG.ERROR("GINKGO_API_KEY environment variable is required for stdio mode")
                raise ValueError(
                    "GINKGO_API_KEY environment variable is required. "
                    "Get one from: ginkgo api keys create --name \"MCP Key\" --permissions trade"
                )
            self._init_tools()
        else:
            # HTTP模式：API KEY从HTTP Header传递
            self._api_key_value = None
            GLOG.INFO(f"{transport} mode: API Key will be validated per-request via HTTP headers")

        self._init_services()

        if transport == "stdio":
            self._register_handlers_stdio()

    def _get_tools_for_api_key(self, api_key: str):
        """根据API KEY获取工具实例"""
        from mcp_server.tools import GinkgoOKXTools

        try:
            from ginkgo.data.crud.api_key_crud import ApiKeyCRUD
            from ginkgo.data.models.model_api_key import MApiKey
            crud = ApiKeyCRUD()
            key_hash = MApiKey.hash_key(api_key)
            result = crud.find(filters={"key_hash": key_hash, "is_del": False}, page=0, page_size=1)
            if not result or len(result) == 0:
                raise ValueError("Invalid API Key")
            api_key_obj = result[0]
            if not api_key_obj.is_active or api_key_obj.is_expired():
                raise ValueError("API Key is inactive or expired")

            # 创建tools实例
            real_tools = GinkgoOKXTools.__new__(GinkgoOKXTools)
            real_tools.api_key_value = api_key
            real_tools.default_account_id = None  # 初始化属性
            real_tools._api_key_info = {
                "uuid": api_key_obj.uuid,
                "name": api_key_obj.name,
                "user_id": api_key_obj.user_id,
                "permissions": api_key_obj.get_permissions_list()
            }
            real_tools._user_id = api_key_obj.user_id
            real_tools._accounts_cache = {}
            return real_tools
        except Exception as e:
            GLOG.ERROR(f"API Key validation failed: {e}")
            raise

    def _extract_api_key(self, headers: dict) -> str | None:
        """从HTTP请求头中提取API Key"""
        api_key = headers.get("x-api-key", "")
        if api_key:
            return api_key
        auth = headers.get("authorization", "")
        if auth and auth.startswith("Bearer "):
            return auth[7:]
        return None

    def _extract_headers_from_scope(self, scope: dict) -> dict:
        """从ASGI scope提取headers为dict"""
        header_dict = {}
        for name, value in scope.get("headers", []):
            header_dict[name.decode("latin-1").lower()] = value.decode("latin-1")
        return header_dict

    def _init_services(self):
        """初始化Ginkgo服务"""
        GLOG.INFO("Ginkgo services initialized")

    def _init_tools(self):
        """初始化工具集合"""
        try:
            from mcp_server.tools import GinkgoOKXTools
            self.tools = GinkgoOKXTools()
            GLOG.INFO(f"GinkgoOKXTools initialized for API Key: {self._api_key_value[:8]}...")
        except Exception as e:
            GLOG.ERROR(f"Failed to initialize tools: {e}")
            raise

    def _register_handlers_stdio(self):
        """注册stdio模式处理器"""
        @self.server.list_tools()
        async def list_tools():
            return self.tools.get_tool_definitions()

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            try:
                GLOG.DEBUG(f"Tool called: {name} with arguments: {arguments}")
                method = getattr(self.tools, name, None)
                if not method:
                    return [TextContent(type="text", text=f"错误: 未找到工具 '{name}'")]
                result = await method(**arguments)
                return result
            except Exception as e:
                GLOG.ERROR(f"Error calling tool {name}: {e}")
                return [TextContent(type="text", text=f"工具执行错误: {str(e)}")]

        GLOG.INFO("MCP handlers registered for stdio mode")

    async def run_stdio(self):
        """运行stdio模式"""
        GLOG.INFO("Starting Ginkgo MCP Server in stdio mode...")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

    async def _build_http_app(self):
        """构建 HTTP 应用（Streamable HTTP + 旧 SSE + 辅助端点）"""
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount
        from starlette.responses import Response

        get_tools_for_key = self._get_tools_for_api_key
        extract_key = self._extract_api_key
        extract_headers = self._extract_headers_from_scope

        # ---- 注册 contextvar 驱动的 tool handlers（Streamable HTTP 会话共用） ----

        @self.server.list_tools()
        async def list_tools():
            tools = _current_tools.get()
            return tools.get_tool_definitions()

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            try:
                GLOG.DEBUG(f"[StreamableHTTP] Tool called: {name}")
                tools = _current_tools.get()
                method = getattr(tools, name, None)
                if not method:
                    return [TextContent(type="text", text=f"错误: 未找到工具 '{name}'")]
                result = await method(**arguments)
                return result
            except Exception as e:
                GLOG.ERROR(f"Error calling tool {name}: {e}")
                return [TextContent(type="text", text=f"工具执行错误: {str(e)}")]

        # ---- Streamable HTTP SessionManager（遵循 SDK lifespan 模式） ----

        session_manager = StreamableHTTPSessionManager(
            app=self.server,
            stateless=False,
        )
        self._session_manager = session_manager

        # ---- /mcp ASGI handler（API Key 验证 → 委托 session_manager） ----

        async def mcp_asgi_handler(scope, receive, send):
            path = scope.get("path", "")
            if path not in ("/mcp", "/mcp/"):
                body = json.dumps({"error": "Not Found"}).encode()
                await send({"type": "http.response.start", "status": 404,
                            "headers": [[b"content-type", b"application/json"]]})
                await send({"type": "http.response.body", "body": body})
                return

            header_dict = extract_headers(scope)
            api_key = extract_key(header_dict)
            if not api_key:
                await send({"type": "http.response.start", "status": 401,
                            "headers": [[b"content-type", b"text/plain"]]})
                await send({"type": "http.response.body", "body": b"API Key required"})
                return

            try:
                tools = get_tools_for_key(api_key)
                token = _current_tools.set(tools)
                try:
                    await session_manager.handle_request(scope, receive, send)
                finally:
                    _current_tools.reset(token)
            except Exception as e:
                GLOG.ERROR(f"[StreamableHTTP] Error: {e}")
                body = json.dumps(
                    {"jsonrpc": "2.0", "error": {"code": -32001, "message": str(e)}}
                ).encode()
                await send({"type": "http.response.start", "status": 403,
                            "headers": [[b"content-type", b"application/json"]]})
                await send({"type": "http.response.body", "body": body})

        # ---- 旧 SSE 端点（兼容老客户端） ----

        sse_transport = SseServerTransport("/message")

        async def sse_handler(request):
            api_key = extract_key(dict(request.headers))
            if not api_key:
                return Response("X-API-Key or Authorization header required", status_code=401)
            try:
                tools = get_tools_for_key(api_key)
            except Exception as e:
                return Response(f"Invalid API Key: {str(e)}", status_code=403)

            client_ip = request.client.host if request.client else "unknown"
            GLOG.INFO(f"[SSE] New connection from {client_ip}")

            connection_server = Server("ginkgo-okx")

            @connection_server.list_tools()
            async def list_tools():
                return tools.get_tool_definitions()

            @connection_server.call_tool()
            async def call_tool(name: str, arguments: dict):
                GLOG.DEBUG(f"[SSE] Tool called: {name}")
                method = getattr(tools, name, None)
                if not method:
                    return [TextContent(type="text", text=f"错误: 未找到工具 '{name}'")]
                result = await method(**arguments)
                return result

            async with sse_transport.connect_sse(request.scope, request.receive, request._send) as streams:
                reader, writer = streams
                await connection_server.run(reader, writer, connection_server.create_initialization_options())
            return Response(status_code=200)

        async def message_asgi_app(scope, receive, send):
            await sse_transport.handle_post_message(scope, receive, send)

        # ---- 独立 HTTP JSON-RPC 端点 ----

        async def http_handler(request):
            from starlette.requests import Request

            api_key = extract_key(dict(request.headers))
            if not api_key:
                return Response(json.dumps({"error": "API Key required"}), status_code=401, media_type="application/json")

            try:
                tools = get_tools_for_key(api_key)
            except Exception as e:
                return Response(json.dumps({"error": f"Invalid API Key: {str(e)}"}), status_code=403, media_type="application/json")

            req = Request(request.scope, request.receive)
            body = await req.json()

            GLOG.DEBUG(f"[HTTP] Received request: {body}")
            method = body.get("method")
            params = body.get("params", {})
            request_id = body.get("id")

            if method == "tools/list":
                tool_defs = tools.get_tool_definitions()
                tools_list = [{"name": t.name, "description": t.description, "inputSchema": t.inputSchema} for t in tool_defs]
                result = {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools_list}}
                return Response(json.dumps(result), media_type="application/json")
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                GLOG.DEBUG(f"[HTTP] Calling tool: {tool_name} with args: {tool_args}")
                try:
                    tool_method = getattr(tools, tool_name, None)
                    if not tool_method:
                        result = {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}}
                    else:
                        tool_result = await tool_method(**tool_args)
                        content_list = [{"type": c.type, "text": c.text} if hasattr(c, "text") else {"type": c.type} for c in tool_result]
                        result = {"jsonrpc": "2.0", "id": request_id, "result": {"content": content_list}}
                except Exception as e:
                    GLOG.ERROR(f"[HTTP] Tool execution error: {e}")
                    result = {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": str(e)}}
                return Response(json.dumps(result), media_type="application/json")
            else:
                result = {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
                return Response(json.dumps(result), media_type="application/json")

        # ---- 辅助端点 ----

        async def health_handler(request):
            return Response(
                json.dumps({
                    "status": "ok",
                    "server": "ginkgo-okx",
                    "version": "0.2.0",
                    "transports": ["stdio", "sse", "streamable_http"],
                    "endpoints": {
                        "/mcp": "Streamable HTTP (MCP 2025-03-26, recommended)",
                        "/sse": "Legacy SSE (deprecated, backwards compatible)",
                        "/message": "Legacy JSON-RPC over SSE",
                        "/http": "Standalone JSON-RPC over HTTP"
                    },
                    "auth": "X-API-Key header or Authorization: Bearer"
                }),
                media_type="application/json"
            )

        async def root_handler(request):
            return Response(
                json.dumps({
                    "name": "Ginkgo OKX MCP Server",
                    "version": "0.2.0",
                    "transports": ["stdio", "sse", "streamable_http"],
                    "endpoints": {
                        "/mcp": "Streamable HTTP (recommended)",
                        "/sse": "Legacy SSE (backwards compatible)",
                        "/http": "Standalone JSON-RPC"
                    },
                    "auth": "X-API-Key: your-ginkgo-api-key"
                }),
                media_type="application/json"
            )

        # ---- 组装 Starlette app ----

        # lifespan: 启动/停止 Streamable HTTP session manager 的 task group
        @contextlib.asynccontextmanager
        async def lifespan(app):
            async with session_manager.run():
                yield

        starlette_app = Starlette(
            debug=False,
            routes=[
                # 注意: /mcp 不在这里注册，由外层 ASGI wrapper 拦截
                Route("/sse", sse_handler, methods=["GET"]),
                Route("/http", http_handler, methods=["POST"]),
                Mount("/message", app=message_asgi_app),
                Route("/health", health_handler, methods=["GET"]),
                Route("/", root_handler, methods=["GET"]),
            ],
            lifespan=lifespan,
        )

        # 外层 ASGI wrapper: /mcp 走 session_manager，其余走 Starlette
        async def app(scope, receive, send):
            if scope["type"] == "http" and scope.get("path", "") in ("/mcp", "/mcp/"):
                await mcp_asgi_handler(scope, receive, send)
            else:
                await starlette_app(scope, receive, send)

        return app

    async def run_sse(self):
        """运行 HTTP 模式（Streamable HTTP + 旧 SSE 共存）"""
        try:
            import uvicorn

            GLOG.INFO("Starting Ginkgo MCP Server (HTTP mode)...")
            GLOG.INFO(f"Server: http://{self.host}:{self.port}")
            GLOG.INFO(f"  /mcp  - Streamable HTTP (MCP 2025-03-26, recommended)")
            GLOG.INFO(f"  /sse  - Legacy SSE (backwards compatible)")
            GLOG.INFO(f"  /http - Standalone JSON-RPC")

            app = await self._build_http_app()

            config = uvicorn.Config(
                app,
                host=self.host,
                port=self.port,
                log_level="info",
                timeout_keep_alive=600,
                timeout_graceful_shutdown=30
            )
            server = uvicorn.Server(config)

            import signal
            def handle_shutdown(signum, frame):
                GLOG.INFO(f"Received signal {signum}, shutting down...")
                server.should_exit = True

            signal.signal(signal.SIGINT, handle_shutdown)
            signal.signal(signal.SIGTERM, handle_shutdown)

            await server.serve()

        except ImportError as e:
            GLOG.ERROR(f"HTTP mode requires additional packages: {e}")
            GLOG.ERROR("Install with: pip install uvicorn starlette")
            raise

    async def run(self):
        """根据配置运行对应模式"""
        if self.transport in ("sse", "streamable_http"):
            await self.run_sse()
        else:
            await self.run_stdio()


async def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description="Ginkgo MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse", "streamable_http"], default="stdio")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--host", type=str, default="localhost")

    args, _ = parser.parse_known_args()

    try:
        server = GinkgoMCPServer(
            transport=args.transport,
            port=args.port,
            host=args.host
        )

        if args.transport in ("sse", "streamable_http"):
            print(f"╔═════════════════════════════════════════╗")
            print(f"║   Ginkgo MCP Server (HTTP Mode)       ║")
            print(f"╚═════════════════════════════════════════╝")
            print(f"")
            print(f"Server: http://{args.host}:{args.port}")
            print(f"  /mcp  - Streamable HTTP (recommended)")
            print(f"  /sse  - Legacy SSE (backwards compatible)")
            print(f"  /http - Standalone JSON-RPC")
            print(f"")
            print(f"API Key: 通过 HTTP Header 传递")
            print(f"")
            print(f"Claude Desktop 配置:")
            config_url = f"http://{args.host}:{args.port}/mcp"
            print(f'  {{"name": "ginkgo-okx", "url": "{config_url}", "headers": {{"X-API-Key": "your-key"}}}}')
            print(f"")
            print(f"curl 示例:")
            print(f"  curl -X POST http://{args.host}:{args.port}/mcp \\")
            print(f"    -H 'X-API-Key: your-key' \\")
            print(f"    -H 'Content-Type: application/json' \\")
            print(f"    -H 'Accept: application/json, text/event-stream' \\")
            print(f"    -d '{{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",")
            print(f"         \"params\":{{\"protocolVersion\":\"2025-03-26\",")
            print(f"         \"capabilities\":{{}},\"clientInfo\":{{\"name\":\"test\"}}}}}}'")
            print(f"")
            print(f"Press Ctrl+C to stop")
            print(f"")

        await server.run()

    except KeyboardInterrupt:
        GLOG.INFO("MCP Server stopped by user (Ctrl+C)")
    except Exception as e:
        GLOG.ERROR(f"MCP Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
