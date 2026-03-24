# Upstream: MCP Server (tool定义)、Ginkgo Services (ApiKeyService, LiveAccountService)
# Downstream: OKX交易所
# Role: MCP工具定义，为AI智能体提供OKX交易能力（支持多账号）


"""
MCP工具定义 - OKX交易接口

通过Ginkgo API Key验证身份，支持多实盘账号操作。

环境变量：
    GINKGO_API_KEY: Ginkgo API Key（必需）
    GINKGO_LIVE_ACCOUNT_ID: 默认实盘账号ID（可选）

工具说明：
    - 不指定account_id时使用默认账号（环境变量或用户设置的）
    - 指定account_id时操作特定账号
    - list_live_accounts() 可查看所有可用账号
"""

import os
from typing import List, Optional
from mcp.types import Tool, TextContent

from ginkgo.data.containers import container
from ginkgo.libs import GLOG


class GinkgoOKXTools:
    """Ginkgo OKX交易工具集合（支持多账号）"""

    def __init__(self):
        """初始化工具集合"""
        self.api_key_value = os.getenv("GINKGO_API_KEY")
        self.default_account_id = os.getenv("GINKGO_LIVE_ACCOUNT_ID")

        if not self.api_key_value:
            raise ValueError("GINKGO_API_KEY environment variable is required")

        # 验证API Key并获取用户信息
        self._api_key_info = self._verify_api_key()
        self._user_id = self._api_key_info.get("user_id") if self._api_key_info else None

        # 缓存账号列表
        self._accounts_cache = {}

    def _verify_api_key(self) -> dict:
        """验证Ginkgo API Key并返回API Key信息"""
        try:
            from ginkgo.data.crud.api_key_crud import ApiKeyCRUD
            from ginkgo.data.models.model_api_key import MApiKey

            crud = ApiKeyCRUD()
            key_hash = MApiKey.hash_key(self.api_key_value)

            result = crud.find(
                filters={"key_hash": key_hash, "is_del": False},
                page=0,
                page_size=1
            )

            if not result or len(result) == 0:
                raise ValueError("Invalid or expired GINKGO_API_KEY")

            api_key = result[0]

            # 检查状态和权限
            if not api_key.is_active:
                raise ValueError("API Key is not active")
            if api_key.is_expired():
                raise ValueError("API Key is expired")
            if not api_key.check_permission("trade"):
                raise ValueError("API Key lacks 'trade' permission")

            # 更新最后使用时间（简化处理，不依赖可能有问题的方法）
            from datetime import datetime
            crud.modify(filters={"uuid": api_key.uuid}, updates={"last_used_at": datetime.now()})

            return {
                "uuid": api_key.uuid,
                "name": api_key.name,
                "user_id": api_key.user_id,
                "permissions": api_key.get_permissions_list()
            }

        except ImportError:
            raise ImportError("ApiKeyCRUD not available")
        except Exception as e:
            raise RuntimeError(f"Failed to verify API Key: {e}")

    def _get_live_accounts(self) -> dict:
        """获取用户的所有实盘账号"""
        try:
            if self._accounts_cache:
                return self._accounts_cache

            from ginkgo.data.crud.live_account_crud import LiveAccountCRUD

            crud = LiveAccountCRUD()
            result = crud.get_live_accounts_by_user(self._user_id, page=1, page_size=100)

            # 转换为字典缓存
            for acc in result.get("accounts", []):
                self._accounts_cache[acc.uuid] = {
                    "uuid": acc.uuid,
                    "name": acc.name,
                    "exchange": acc.exchange,
                    "environment": acc.environment,
                    "status": acc.status,
                    "is_enabled": acc.is_enabled(),
                    "is_default": getattr(acc, 'is_default', False)
                }

            return self._accounts_cache

        except Exception as e:
            GLOG.ERROR(f"Failed to get live accounts: {e}")
            return {}

    def _resolve_account_id(self, account_id: Optional[str] = None) -> str:
        """
        解析要操作的账号ID

        优先级：
        1. 参数指定的account_id
        2. 环境变量GINKGO_LIVE_ACCOUNT_ID
        3. 用户设置的默认账号（is_default=True）
        4. 第一个enabled账号
        """
        if account_id:
            return account_id

        if self.default_account_id:
            return self.default_account_id

        # 查找用户设置的默认账号
        accounts = self._get_live_accounts()
        for acc_id, acc_info in accounts.items():
            if acc_info.get("is_default") and acc_info.get("is_enabled"):
                return acc_id

        # 使用第一个enabled账号
        for acc_id, acc_info in accounts.items():
            if acc_info.get("is_enabled"):
                return acc_id

        raise ValueError("No available live account found. Please enable an account or specify account_id.")

    def _get_okx_credentials(self, account_id: str) -> dict:
        """获取实盘账号的OKX凭证"""
        try:
            from ginkgo.data.crud.live_account_crud import LiveAccountCRUD

            crud = LiveAccountCRUD()
            account = crud.get_live_account_by_uuid(account_id, include_credentials=True)

            if not account:
                raise ValueError(f"Live account not found: {account_id}")

            if not account.is_enabled():
                raise ValueError(f"Live account is not enabled: {account_id}")

            # 解密凭证
            credentials = crud.get_decrypted_credentials(account_id)

            if not credentials:
                raise ValueError(f"Failed to decrypt credentials for account: {account_id}")

            return credentials

        except Exception as e:
            GLOG.ERROR(f"Failed to get OKX credentials: {e}")
            raise

    def _get_okx_client(self, account_id: str):
        """获取OKX API客户端（使用指定账号的凭证）"""
        try:
            credentials = self._get_okx_credentials(account_id)

            from okx.Account import AccountAPI as OKXAccount
            from okx.Trade import TradeAPI as OKXTrade
            from okx.PublicData import PublicAPI

            # 确定环境
            environment = "testnet" if credentials.get("environment") == "testnet" else "production"
            domain = "https://www.okx.com"
            flag = "1" if environment == "testnet" else "0"

            # 创建客户端
            okx_account = OKXAccount(
                api_key=credentials["api_key"],
                api_secret_key=credentials["api_secret"],
                passphrase=credentials["passphrase"],
                domain=domain,
                flag=flag,
                debug=False
            )

            okx_trade = OKXTrade(
                api_key=credentials["api_key"],
                api_secret_key=credentials["api_secret"],
                passphrase=credentials["passphrase"],
                domain=domain,
                flag=flag,
                debug=False
            )

            okx_public = PublicAPI(domain=domain, flag=flag, debug=False)

            return {
                "account": okx_account,
                "trade": okx_trade,
                "public": okx_public,
                "environment": environment
            }

        except ImportError:
            raise ImportError("python-okx not installed. Run: pip install python-okx")
        except Exception as e:
            raise RuntimeError(f"Failed to create OKX client: {e}")

    # ==================== 工具定义 ====================

    async def list_live_accounts(self) -> List[TextContent]:
        """
        列出用户的所有实盘账号

        返回所有账号的状态，便于Agent选择要操作的账号。
        """
        try:
            accounts = self._get_live_accounts()

            if not accounts:
                return [TextContent(type="text", text="未找到任何实盘账号")]

            text = f"实盘账号列表（共{len(accounts)}个）：\n\n"

            for acc_id, acc in accounts.items():
                default_mark = " [默认]" if acc.get("is_default") else ""
                status_mark = "✓" if acc.get("is_enabled") else "✗"
                text += f"{status_mark} {acc['name']}{default_mark}\n"
                text += f"   UUID: {acc_id}\n"
                text += f"   交易所: {acc['exchange']} ({acc['environment']})\n\n"

            return [TextContent(type="text", text=text)]

        except Exception as e:
            GLOG.ERROR(f"Error listing accounts: {e}")
            return [TextContent(type="text", text=f"错误: {str(e)}")]

    async def get_balance(self, account_id: Optional[str] = None) -> List[TextContent]:
        """
        获取账户余额信息

        Args:
            account_id: 实盘账号ID（可选，不指定则使用默认账号）
        """
        try:
            target_account_id = self._resolve_account_id(account_id)
            client = self._get_okx_client(target_account_id)

            result = client["account"].get_account_balance()

            if result and result.get('code') == '0':
                data = result.get('data', [{}])[0] if result.get('data') else {}
                details = data.get('details', [])

                # 获取账号名称用于显示
                accounts = self._get_live_accounts()
                account_name = accounts.get(target_account_id, {}).get('name', target_account_id)

                text = f"""账户余额 [{account_name}]：
总权益: {data.get('totalEq', '0')} USDT
可用余额: {data.get('availEq', '0')} USDT

币种余额：
"""
                for d in details:
                    if float(d.get('eq', 0)) > 0:
                        text += f"  {d.get('ccy', '')}: {d.get('eq', '0')} (可用: {d.get('availBal', '0')})\n"

                return [TextContent(type="text", text=text)]
            else:
                error_msg = result.get('msg', 'Unknown error')
                return [TextContent(type="text", text=f"获取余额失败: {error_msg}")]

        except Exception as e:
            GLOG.ERROR(f"Error getting balance: {e}")
            return [TextContent(type="text", text=f"错误: {str(e)}")]

    async def get_positions(self, account_id: Optional[str] = None) -> List[TextContent]:
        """
        获取当前持仓信息

        Args:
            account_id: 实盘账号ID（可选）
        """
        try:
            target_account_id = self._resolve_account_id(account_id)
            client = self._get_okx_client(target_account_id)

            result = client["account"].get_account_balance()

            if result and result.get('code') == '0':
                data = result.get('data', [{}])[0] if result.get('data') else {}
                details = data.get('details', [])

                accounts = self._get_live_accounts()
                account_name = accounts.get(target_account_id, {}).get('name', target_account_id)

                # 现货持仓 = 币种余额（除USDT）
                positions = []
                for d in details:
                    ccy = d.get('ccy', '')
                    avail = float(d.get('availBal', '0') or '0')
                    if avail > 0 and ccy != 'USDT':
                        positions.append({
                            'symbol': f"{ccy}-USDT",
                            'amount': avail,
                            'value_usd': d.get('eqUsd', '0')
                        })

                if not positions:
                    return [TextContent(type="text", text=f"账号 [{account_name}] 当前无现货持仓")]

                text = f"账号 [{account_name}] 持仓：\n\n"
                for p in positions:
                    text += f"  {p['symbol']}: {p['amount']} (价值 ${p['value_usd']} USDT)\n"

                return [TextContent(type="text", text=text)]
            else:
                error_msg = result.get('msg', 'Unknown error')
                return [TextContent(type="text", text=f"获取持仓失败: {error_msg}")]

        except Exception as e:
            GLOG.ERROR(f"Error getting positions: {e}")
            return [TextContent(type="text", text=f"错误: {str(e)}")]

    async def get_open_orders(self, account_id: Optional[str] = None) -> List[TextContent]:
        """获取当前挂单信息"""
        try:
            target_account_id = self._resolve_account_id(account_id)
            client = self._get_okx_client(target_account_id)

            result = client["trade"].get_order_list(instType="SPOT")

            if result and result.get('code') == '0':
                orders = [o for o in result.get('data', []) if o.get('state') in ['live', 'partially_filled']]

                accounts = self._get_live_accounts()
                account_name = accounts.get(target_account_id, {}).get('name', target_account_id)

                if not orders:
                    return [TextContent(type="text", text=f"账号 [{account_name}] 当前无挂单")]

                text = f"账号 [{account_name}] 挂单：\n\n"
                for o in orders:
                    text += f"  订单ID: {o.get('ordId', '')}\n"
                    text += f"  标的: {o.get('instId', '')} | {o.get('side', '')} {o.get('sz', '')}\n"
                    text += f"  状态: {o.get('state', '')}\n\n"

                return [TextContent(type="text", text=text)]
            else:
                error_msg = result.get('msg', 'Unknown error')
                return [TextContent(type="text", text=f"获取挂单失败: {error_msg}")]

        except Exception as e:
            GLOG.ERROR(f"Error getting open orders: {e}")
            return [TextContent(type="text", text=f"错误: {str(e)}")]

    async def place_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        account_id: Optional[str] = None,
        order_type: str = "market"
    ) -> List[TextContent]:
        """
        下单

        Args:
            symbol: 交易标的 (如 BTC-USDT)
            side: 方向 (buy/sell)
            amount: 数量
            account_id: 实盘账号ID（可选，不指定则使用默认）
            order_type: 类型 (market/limit，目前只支持market)
        """
        try:
            target_account_id = self._resolve_account_id(account_id)
            client = self._get_okx_client(target_account_id)

            # 参数验证
            if side not in ["buy", "sell"]:
                return [TextContent(type="text", text="错误: side必须是buy或sell")]
            if order_type != "market":
                return [TextContent(type="text", text="错误: 目前只支持市价单(market)")]
            if amount <= 0:
                return [TextContent(type="text", text="错误: amount必须大于0")]

            order_params = {
                "instId": symbol,
                "tdMode": "cash",
                "side": side,
                "ordType": "market",
                "sz": str(amount)
            }

            result = client["trade"].place_order(**order_params)

            if result and result.get('code') == '0':
                data = result.get('data', [{}])[0]
                order_id = data.get('ordId', '')

                accounts = self._get_live_accounts()
                account_name = accounts.get(target_account_id, {}).get('name', target_account_id)

                return [TextContent(
                    type="text",
                    text=f"账号 [{account_name}] 下单成功！\n订单ID: {order_id} | {symbol} {side} {amount}"
                )]
            else:
                error_msg = result.get('msg', 'Unknown error')
                return [TextContent(type="text", text=f"下单失败: {error_msg}")]

        except Exception as e:
            GLOG.ERROR(f"Error placing order: {e}")
            return [TextContent(type="text", text=f"错误: {str(e)}")]

    async def cancel_order(
        self,
        order_id: str,
        account_id: Optional[str] = None
    ) -> List[TextContent]:
        """
        撤销订单

        Args:
            order_id: 订单ID
            account_id: 实盘账号ID（可选）
        """
        try:
            target_account_id = self._resolve_account_id(account_id)
            client = self._get_okx_client(target_account_id)

            result = client["trade"].cancel_order(ordId=order_id)

            if result and result.get('code') == '0':
                return [TextContent(type="text", text=f"撤单成功！订单ID: {order_id}")]
            else:
                error_msg = result.get('msg', 'Unknown error')
                return [TextContent(type="text", text=f"撤单失败: {error_msg}")]

        except Exception as e:
            GLOG.ERROR(f"Error cancelling order: {e}")
            return [TextContent(type="text", text=f"错误: {str(e)}")]

    async def get_ticker(self, symbol: str) -> List[TextContent]:
        """获取交易对行情（公共接口，无需账号）"""
        try:
            # 使用默认环境或第一个可用账号的环境
            accounts = self._get_live_accounts()
            environment = "testnet"
            if accounts:
                # 使用第一个账号的环境设置
                for acc in accounts.values():
                    if acc.get("is_enabled"):
                        environment = acc.get("environment", "testnet")
                        break

            from okx.PublicData import PublicAPI

            domain = "https://www.okx.com"
            flag = "1" if environment == "testnet" else "0"
            public_api = PublicAPI(domain=domain, flag=flag, debug=False)

            response = public_api.get('/api/v5/market/ticker', params={'instId': symbol})
            result = response.json()

            if result and result.get('code') == '0':
                data = result.get('data', [{}])[0] if result.get('data') else {}
                return [TextContent(
                    type="text",
                    text=f"""{symbol} 行情：
最新价: ${data.get('last', 'N/A')}
24h最高: ${data.get('high24h', 'N/A')}
24h最低: ${data.get('low24h', 'N/A')}
24h成交量: {data.get('vol24h', 'N/A')}
24h成交额: ${data.get('volCcy24h', 'N/A')}"""
                )]
            else:
                return [TextContent(type="text", text=f"获取行情失败: {symbol}")]

        except Exception as e:
            GLOG.ERROR(f"Error getting ticker: {e}")
            return [TextContent(type="text", text=f"错误: {str(e)}")]

    async def get_top_volume_pairs(self, top_n: int = 10) -> List[TextContent]:
        """获取成交量前N的交易对（公共接口）"""
        try:
            if top_n > 50:
                return [TextContent(type="text", text="错误：最多只能获取前50个交易对")]
            if top_n <= 0:
                return [TextContent(type="text", text="错误：top_n必须大于0")]

            # 使用默认环境
            accounts = self._get_live_accounts()
            environment = "testnet"
            if accounts:
                for acc in accounts.values():
                    if acc.get("is_enabled"):
                        environment = acc.get("environment", "testnet")
                        break

            from okx.PublicData import PublicAPI

            domain = "https://www.okx.com"
            flag = "1" if environment == "testnet" else "0"
            public_api = PublicAPI(domain=domain, flag=flag, debug=False)

            response = public_api.get('/api/v5/market/tickers', params={'instType': 'SPOT'})
            result = response.json()

            if result and result.get('code') == '0':
                tickers = result.get('data', [])
                sorted_pairs = sorted(tickers, key=lambda x: float(x.get('volCcy24h', 0) or 0), reverse=True)[:top_n]

                text = f"成交量前{top_n}交易对（24小时）：\n\n"
                for i, p in enumerate(sorted_pairs, 1):
                    text += f"{i}. {p.get('instId', '')} - 成交额: ${p.get('volCcy24h', '0')} - 最新价: ${p.get('last', '0')}\n"

                return [TextContent(type="text", text=text)]
            else:
                return [TextContent(type="text", text="获取交易对数据失败")]

        except Exception as e:
            GLOG.ERROR(f"Error getting top volume pairs: {e}")
            return [TextContent(type="text", text=f"错误: {str(e)}")]

    # ==================== MCP工具列表定义 ====================

    @staticmethod
    def get_tool_definitions() -> List[Tool]:
        """获取所有工具定义"""
        return [
            Tool(
                name="list_live_accounts",
                description="列出用户的所有实盘账号，包含状态和默认标记",
                inputSchema={"type": "object", "properties": {}}
            ),
            Tool(
                name="get_balance",
                description="获取账户余额。可指定account_id操作特定账号，不指定则使用默认账号",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account_id": {"type": "string", "description": "实盘账号ID（可选）"}
                    }
                }
            ),
            Tool(
                name="get_positions",
                description="获取当前持仓信息。可指定account_id操作特定账号",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account_id": {"type": "string", "description": "实盘账号ID（可选）"}
                    }
                }
            ),
            Tool(
                name="get_open_orders",
                description="获取当前挂单信息。可指定account_id操作特定账号",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account_id": {"type": "string", "description": "实盘账号ID（可选）"}
                    }
                }
            ),
            Tool(
                name="place_order",
                description="下单。支持市价单，可指定account_id操作特定账号",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "交易标的 (BTC-USDT)"},
                        "side": {"type": "string", "enum": ["buy", "sell"], "description": "方向"},
                        "amount": {"type": "number", "description": "数量"},
                        "account_id": {"type": "string", "description": "实盘账号ID（可选，使用默认账号）"},
                        "order_type": {"type": "string", "enum": ["market", "limit"], "description": "类型"}
                    },
                    "required": ["symbol", "side", "amount"]
                }
            ),
            Tool(
                name="cancel_order",
                description="撤销订单。可指定account_id操作特定账号",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string", "description": "订单ID"},
                        "account_id": {"type": "string", "description": "实盘账号ID（可选）"}
                    },
                    "required": ["order_id"]
                }
            ),
            Tool(
                name="get_ticker",
                description="获取交易对行情（公共接口，无需账号）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "交易对"}
                    },
                    "required": ["symbol"]
                }
            ),
            Tool(
                name="get_top_volume_pairs",
                description="获取成交量前N的交易对（最多50个）",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "top_n": {"type": "number", "description": "前N个，默认10"}
                    }
                }
            ),
        ]
