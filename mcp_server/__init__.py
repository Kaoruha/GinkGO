"""
Ginkgo MCP Server

为AI智能体提供OKX交易能力的MCP服务器。

环境变量：
    GINKGO_ACCOUNT_ID: 实盘账号ID（必需）

使用方式：
    ginkgo serve mcp
    GINKGO_ACCOUNT_ID=xxx ginkgo serve mcp
"""

from ginkgo.config.package import VERSION as __version__  # 跟随主版本（#4969）
