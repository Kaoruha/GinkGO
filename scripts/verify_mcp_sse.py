#!/usr/bin/env python3
"""
MCP SSE 协议验证脚本

验证 SSE 连接是否符合 MCP 协议规范：
1. GET /sse 返回 text/event-stream
2. 第一条消息是 event: endpoint\ndata: /message\n\n
3. POST /message 接受 JSON-RPC 请求
"""

import asyncio
import sys
from urllib.parse import urlparse

# 检查依赖
try:
    import aiohttp
except ImportError:
    print("请安装 aiohttp: pip install aiohttp")
    sys.exit(1)


class MCPValidator:
    """MCP SSE 协议验证器"""

    def __init__(self, url: str, api_key: str = None):
        self.url = url
        self.api_key = api_key
        self.session = None
        self.headers = {}
        if api_key:
            self.headers["X-API-Key"] = api_key

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    def print_result(self, test_name: str, passed: bool, details: str = ""):
        """打印测试结果"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if details:
            print(f"    {details}")

    async def check_sse_endpoint(self):
        """检查 SSE endpoint"""
        print("\n### 检查 SSE Endpoint ###")
        try:
            async with self.session.get(self.url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                # 检查状态码
                if resp.status != 200:
                    self.print_result("HTTP 状态码", False, f"期望 200，实际 {resp.status}")
                    return False

                # 检查 Content-Type
                content_type = resp.headers.get("Content-Type", "")
                if "text/event-stream" not in content_type:
                    self.print_result("Content-Type", False, f"期望 text/event-stream，实际 {content_type}")
                    return False

                self.print_result("HTTP 状态码", True, f"{resp.status}")
                self.print_result("Content-Type", True, content_type)

                # 读取前几条消息
                data = b""
                message_count = 0
                endpoint_received = False
                endpoint_url = None

                # 读取数据（最多5秒）
                try:
                    async for chunk in resp.content.iter_chunked(1024):
                        data += chunk
                        text = data.decode("utf-8", errors="ignore")

                        # 检查是否有 endpoint 事件
                        if "event: endpoint" in text:
                            endpoint_received = True
                            # 提取 endpoint URL
                            for line in text.split("\n"):
                                if line.startswith("data: "):
                                    endpoint_url = line[6:].strip()
                                    break

                        message_count += 1
                        if message_count > 5 or endpoint_received:
                            break

                        # 避免读取太多
                        if len(data) > 4096:
                            break

                except asyncio.TimeoutError:
                    pass

                self.print_result("返回 SSE 流", True)
                self.print_result("endpoint 事件", endpoint_received,
                                 f"URL: {endpoint_url}" if endpoint_url else "未收到")

                return endpoint_received

        except Exception as e:
            self.print_result("SSE 连接", False, str(e))
            return False

    async def check_message_endpoint(self, connection_id: str):
        """检查 message endpoint（使用 connectionId）"""
        print("\n### 检查 Message Endpoint ###")
        try:
            # 构建完整 URL
            parsed = urlparse(self.url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            full_message_url = f"{base_url}/message?connectionId={connection_id}"

            # 测试 tools/list 请求
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }

            async with self.session.post(
                full_message_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    self.print_result("HTTP 状态码", False, f"期望 200，实际 {resp.status}")
                    return False

                # 解析响应
                result = await resp.json()

                # 检查 JSON-RPC 响应格式
                if "jsonrpc" not in result or result.get("jsonrpc") != "2.0":
                    self.print_result("JSON-RPC 版本", False, f"期望 jsonrpc: 2.0")
                    return False

                if "id" not in result:
                    self.print_result("JSON-RPC id", False, "缺少 id 字段")
                    return False

                # 检查 result
                if "result" not in result:
                    self.print_result("JSON-RPC result", False, f"响应: {result}")
                    return False

                tools = result["result"].get("tools", [])
                self.print_result("HTTP 状态码", True, f"{resp.status}")
                self.print_result("JSON-RPC 响应格式", True)
                self.print_result("工具列表", True, f"找到 {len(tools)} 个工具")

                # 显示工具列表
                if tools:
                    print("\n    可用工具:")
                    for tool in tools[:5]:  # 只显示前5个
                        print(f"      - {tool.get('name', 'unknown')}: {tool.get('description', '')[:50]}")
                    if len(tools) > 5:
                        print(f"      ... 还有 {len(tools) - 5} 个工具")

                return True

        except Exception as e:
            self.print_result("Message 连接", False, str(e))
            return False

    async def check_health_endpoint(self):
        """检查健康检查 endpoint"""
        print("\n### 检查 Health Endpoint ###")
        try:
            parsed = urlparse(self.url)
            health_url = f"{parsed.scheme}://{parsed.netloc}/health"

            async with self.session.get(health_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status != 200:
                    self.print_result("Health 检查", False, f"状态码: {resp.status}")
                    return False

                data = await resp.json()
                self.print_result("Health 检查", True, f"状态: {data.get('status', 'unknown')}")

                return True

        except Exception as e:
            self.print_result("Health 检查", False, str(e))
            return False

    async def run_all_checks(self):
        """运行所有检查"""
        print("=" * 60)
        print("MCP SSE 协议验证")
        print("=" * 60)
        print(f"服务器: {self.url}")
        print(f"API Key: {'已设置' if self.api_key else '未设置'}")
        print("=" * 60)

        results = []
        connection_id = None

        # 1. 检查 SSE endpoint 并获取 connectionId
        sse_ok, connection_id = await self.check_sse_endpoint_with_id()
        results.append(("SSE Endpoint", sse_ok))

        # 2. 检查 health endpoint
        health_ok = await self.check_health_endpoint()
        results.append(("Health Endpoint", health_ok))

        # 3. 检查 message endpoint（使用获取的 connectionId）
        if connection_id:
            self.print_result("获取 connectionId", True, connection_id)
            message_ok = await self.check_message_endpoint(connection_id)
            results.append(("Message Endpoint", message_ok))
        else:
            self.print_result("获取 connectionId", False, "未能从 SSE 获取")
            results.append(("Message Endpoint", False))

        # 总结
        print("\n" + "=" * 60)
        print("验证总结")
        print("=" * 60)

        all_passed = True
        for test_name, passed in results:
            status = "✅" if passed else "❌"
            print(f"{status} {test_name}")
            if not passed:
                all_passed = False

        print("=" * 60)

        if all_passed:
            print("\n🎉 所有检查通过！MCP SSE 协议实现正确。")
            return 0
        else:
            print("\n⚠️  部分检查失败，请检查服务器实现。")
            return 1

    async def check_sse_endpoint_with_id(self):
        """检查 SSE endpoint 并返回 connectionId"""
        print("\n### 检查 SSE Endpoint ###")
        connection_id = None
        try:
            async with self.session.get(self.url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                # 检查状态码
                if resp.status != 200:
                    self.print_result("HTTP 状态码", False, f"期望 200，实际 {resp.status}")
                    return False, None

                # 检查 Content-Type
                content_type = resp.headers.get("Content-Type", "")
                if "text/event-stream" not in content_type:
                    self.print_result("Content-Type", False, f"期望 text/event-stream，实际 {content_type}")
                    return False, None

                self.print_result("HTTP 状态码", True, f"{resp.status}")
                self.print_result("Content-Type", True, content_type)

                # 读取 SSE 流并提取 connectionId
                endpoint_received = False
                data = b""

                async for chunk in resp.content.iter_chunked(512):
                    data += chunk
                    text = data.decode("utf-8", errors="ignore")

                    # 检查 endpoint 事件
                    if "event: endpoint" in text:
                        endpoint_received = True
                        # 提取 endpoint URL 和 connectionId
                        for line in text.split("\n"):
                            if line.startswith("data: "):
                                endpoint_data = line[6:].strip()
                                # 解析 /message?connectionId=xxx
                                if "connectionId=" in endpoint_data:
                                    connection_id = endpoint_data.split("connectionId=")[1]
                                    break
                        break

                    if len(data) > 4096:  # 避免读取太多
                        break

                if endpoint_received:
                    self.print_result("endpoint 事件", True, f"connectionId: {connection_id}")
                else:
                    self.print_result("endpoint 事件", False, "未收到 endpoint 事件")
                    return False, None

                return True, connection_id

        except Exception as e:
            self.print_result("SSE 连接", False, str(e))
            return False, None

    async def check_sse_endpoint(self):
        """检查 SSE endpoint（兼容旧接口）"""
        passed, _ = await self.check_sse_endpoint_with_id()
        return passed


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="MCP SSE 协议验证工具")
    parser.add_argument("url", help="SSE endpoint URL (如: http://localhost:8001/sse)")
    parser.add_argument("--api-key", help="API Key (可选)")
    parser.add_argument("--insecure", action="store_true", help="跳过 SSL 证书验证")

    args = parser.parse_args()

    # 添加默认 scheme
    url = args.url
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"http://{url}"

    async with MCPValidator(url, args.api_key) as validator:
        return await validator.run_all_checks()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
