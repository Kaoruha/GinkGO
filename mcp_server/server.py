# Upstream: CLI (ginkgo serve mcp)、OpenClaw (MCP客户端)
# Downstream: GinkgoOKXTools (工具实现)、Ginkgo Services
# Role: MCP Server主入口，使用标准 MCP SseServerTransport 实现协议


"""
Ginkgo MCP Server - OKX交易能力

为AI智能体提供OKX交易能力的MCP服务器。

支持两种传输模式：
    1. stdio - 标准输入输出（默认，适用于本地进程调用）
    2. sse - HTTP/SSE（适用于远程连接，使用标准 MCP SseServerTransport）

环境变量：
    GINKGO_API_KEY: Ginkgo API Key（stdio模式必需，sse模式通过Header传递）

启动方式：
    # stdio模式（默认）
    ginkgo serve mcp
    GINKGO_API_KEY=xxx ginkgo serve mcp

    # HTTP/SSE模式
    ginkgo serve mcp --transport sse --port 8001
"""

import asyncio
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
from mcp.types import Tool, TextContent

from ginkgo.libs import GLOG


class GinkgoMCPServer:
    """Ginkgo MCP Server - 使用标准 MCP SseServerTransport"""

    def __init__(self, transport: str = "stdio", port: int = 8001, host: str = "localhost"):
        """初始化MCP Server"""
        self.transport = transport
        self.port = port
        self.host = host
        self.server = Server("ginkgo-okx")
        self.tools = None

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
            # SSE模式：API KEY从HTTP Header传递
            self._api_key_value = None
            GLOG.INFO("SSE mode: API Key will be validated per-request via HTTP headers")

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

    async def run_sse(self):
        """运行HTTP/SSE模式 - 使用标准 MCP SseServerTransport"""
        try:
            from starlette.applications import Starlette
            from starlette.routing import Route
            from starlette.responses import Response
            import uvicorn

            GLOG.INFO("Starting Ginkgo MCP Server in SSE mode (standard implementation)...")
            GLOG.INFO(f"Server: http://{self.host}:{self.port}/sse")

            # 保存对实例方法的引用，供嵌套函数使用
            get_tools_for_key = self._get_tools_for_api_key

            # 创建标准 MCP SSE transport
            sse_transport = SseServerTransport("/message")

            async def get_api_key_from_request(request):
                """从请求中获取API KEY"""
                api_key = request.headers.get("X-API-Key", "")
                if api_key:
                    return api_key
                auth = request.headers.get("Authorization", "")
                if auth and auth.startswith("Bearer "):
                    return auth[7:]
                return None

            async def validate_and_get_tools(request):
                """验证API KEY并返回tools实例"""
                api_key = await get_api_key_from_request(request)
                if not api_key:
                    return None, ("X-API-Key or Authorization header required", 401)

                try:
                    tools = get_tools_for_key(api_key)
                    return tools, None
                except Exception as e:
                    return None, (f"Invalid API Key: {str(e)}", 403)

            # SSE endpoint - Starlette Route 处理函数
            async def sse_handler(request):
                """处理 SSE 连接请求"""
                # 验证 API Key
                api_key = request.headers.get("X-API-Key", "")
                if not api_key:
                    auth = request.headers.get("Authorization", "")
                    if auth.startswith("Bearer "):
                        api_key = auth[7:]

                if not api_key:
                    return Response("X-API-Key or Authorization header required", status_code=401)

                # 验证 API Key 并获取 tools
                try:
                    tools = get_tools_for_key(api_key)
                except Exception as e:
                    return Response(f"Invalid API Key: {str(e)}", status_code=403)

                client_ip = request.client.host if request.client else "unknown"
                GLOG.INFO(f"New SSE connection from {client_ip}")

                # 为这个连接创建独立的 MCP Server
                connection_server = Server("ginkgo-okx")

                # 注册工具处理器
                @connection_server.list_tools()
                async def list_tools():
                    return tools.get_tool_definitions()

                @connection_server.call_tool()
                async def call_tool(name: str, arguments: dict):
                    GLOG.DEBUG(f"Tool called: {name}")
                    method = getattr(tools, name, None)
                    if not method:
                        return [TextContent(type="text", text=f"错误: 未找到工具 '{name}'")]
                    result = await method(**arguments)
                    return result

                # 使用 SSE transport 处理连接
                async with sse_transport.connect_sse(request.scope, request.receive, request._send) as streams:
                    reader, writer = streams
                    await connection_server.run(
                        reader,
                        writer,
                        connection_server.create_initialization_options()
                    )

                # 返回空响应（SSE 已经由 connect_sse 处理）
                return Response(status_code=200)

            # Message endpoint - ASGI 应用（不返回 Response）
            async def message_asgi_app(scope, receive, send):
                """ASGI 应用处理消息端点 - 直接委托给 MCP transport"""
                await sse_transport.handle_post_message(scope, receive, send)

            # HTTP endpoint - 独立的 JSON-RPC 端点（无会话）
            async def http_handler(request):
                """处理独立 HTTP JSON-RPC 请求（不需要 SSE 会话）"""
                from starlette.requests import Request
                import json

                tools, error = await validate_and_get_tools(request)
                if error:
                    return Response(json.dumps({"error": error[0]}), status_code=error[1], media_type="application/json")

                # 解析 JSON-RPC 请求
                req = Request(request.scope, request.receive)
                body = await req.json()

                GLOG.DEBUG(f"[HTTP] Received request: {body}")

                method = body.get("method")
                params = body.get("params", {})
                request_id = body.get("id")

                # 处理 tools/list
                if method == "tools/list":
                    tool_definitions = tools.get_tool_definitions()
                    # 将 Tool 对象转换为字典
                    tools_list = [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema
                        }
                        for tool in tool_definitions
                    ]
                    result = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {"tools": tools_list}
                    }
                    return Response(json.dumps(result), media_type="application/json")

                # 处理 tools/call
                elif method == "tools/call":
                    tool_name = params.get("name")
                    tool_args = params.get("arguments", {})

                    GLOG.DEBUG(f"[HTTP] Calling tool: {tool_name} with args: {tool_args}")

                    try:
                        tool_method = getattr(tools, tool_name, None)
                        if not tool_method:
                            result = {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}
                            }
                        else:
                            tool_result = await tool_method(**tool_args)
                            # 将 TextContent 对象转换为字典
                            content_list = [
                                {"type": c.type, "text": c.text} if hasattr(c, 'text') else {"type": c.type}
                                for c in tool_result
                            ]
                            result = {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "result": {"content": content_list}
                            }
                    except Exception as e:
                        GLOG.ERROR(f"[HTTP] Tool execution error: {e}")
                        result = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": -32603, "message": str(e)}
                        }

                    return Response(json.dumps(result), media_type="application/json")

                else:
                    result = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32601, "message": f"Method not found: {method}"}
                    }
                    return Response(json.dumps(result), media_type="application/json")

            # 辅助 endpoints
            async def health_handler(request):
                import json
                return Response(
                    json.dumps({
                        "status": "ok",
                        "server": "ginkgo-okx",
                        "version": "0.1.0",
                        "protocol": "MCP over HTTP/SSE",
                        "endpoints": {
                            "/sse": "SSE endpoint (requires session)",
                            "/message": "JSON-RPC over SSE (requires session)",
                            "/http": "JSON-RPC over HTTP (standalone, no session)"
                        },
                        "auth": "X-API-Key header or Authorization: Bearer"
                    }),
                    media_type="application/json"
                )

            async def root_handler(request):
                import json
                return Response(
                    json.dumps({
                        "name": "Ginkgo OKX MCP Server",
                        "version": "0.1.0",
                        "protocol": "MCP over HTTP/SSE",
                        "endpoints": {
                            "/sse": "SSE",
                            "/message": "JSON-RPC over SSE",
                            "/http": "JSON-RPC over HTTP"
                        },
                        "auth": "X-API-Key: your-ginkgo-api-key"
                    }),
                    media_type="application/json"
                )

            # 创建 Starlette 应用
            from starlette.routing import Mount

            app = Starlette(
                debug=False,
                routes=[
                    Route("/sse", sse_handler, methods=["GET"]),  # SSE 端点（需要会话）
                    Route("/http", http_handler, methods=["POST"]),  # HTTP 端点（无会话）
                    Mount("/message", app=message_asgi_app),  # Message 端点（ASGI 应用）
                    Route("/health", health_handler, methods=["GET"]),
                    Route("/", root_handler, methods=["GET"]),
                ]
            )

            # 启动服务器
            config = uvicorn.Config(
                app,
                host=self.host,
                port=self.port,
                log_level="info",
                timeout_keep_alive=600,  # 10分钟保持连接
                timeout_graceful_shutdown=30
            )
            server = uvicorn.Server(config)

            # 信号处理
            import signal
            def handle_shutdown(signum, frame):
                GLOG.INFO(f"Received signal {signum}, shutting down...")
                server.should_exit = True

            signal.signal(signal.SIGINT, handle_shutdown)
            signal.signal(signal.SIGTERM, handle_shutdown)

            await server.serve()

        except ImportError as e:
            GLOG.ERROR(f"HTTP/SSE mode requires additional packages: {e}")
            GLOG.ERROR("Install with: pip install uvicorn starlette")
            raise

    async def run(self):
        """根据配置运行对应模式"""
        if self.transport == "sse":
            await self.run_sse()
        else:
            await self.run_stdio()


async def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description="Ginkgo MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--host", type=str, default="localhost")

    args, _ = parser.parse_known_args()

    try:
        server = GinkgoMCPServer(
            transport=args.transport,
            port=args.port,
            host=args.host
        )

        if args.transport == "sse":
            print(f"╔═════════════════════════════════════════╗")
            print(f"║   🤖 Ginkgo MCP Server (SSE Mode)    ║")
            print(f"╚═════════════════════════════════════════╝")
            print(f"")
            print(f"🚀 Server starting...")
            print(f"📍 URL: http://{args.host}:{args.port}/sse")
            print(f"🔑 API Key: 通过HTTP Header传递")
            print(f"")
            print(f"OpenClaw配置:")
            print(f"  {{\"name\": \"ginkgo-okx\", \"transport\": \"http\",")
            print(f"   \"url\": \"http://{args.host}:{args.port}/sse\",")
            print(f"   \"headers\": {{\"X-API-Key\": \"your-key\"}}}}")
            print(f"")
            print(f"HTTP 调用示例:")
            print(f"  curl -X POST http://{args.host}:{args.port}/http \\")
            print(f"    -H \"X-API-Key: your-key\" \\")
            print(f"    -H \"Content-Type: application/json\" \\")
            print(f"    -d '{{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\"}}'")
            print(f"")
            print(f"ℹ Press Ctrl+C to stop")
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
