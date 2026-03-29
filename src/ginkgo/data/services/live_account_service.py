# Upstream: Web UI/API Endpoints (实盘账号管理接口)
# Downstream: LiveAccountCRUD (数据持久化)、python-okx (API验证)、EncryptionService (凭证加密)
# Role: LiveAccountService实盘账号业务服务提供账号创建/验证/状态管理等业务逻辑


from typing import Optional, Dict, Any, List
from datetime import datetime

from ginkgo.data.services.base_service import BaseService
from ginkgo.data.services.encryption_service import get_encryption_service
from ginkgo.data.crud.live_account_crud import LiveAccountCRUD
from ginkgo.data.models.model_live_account import MLiveAccount, AccountStatusType, ExchangeType
from ginkgo.libs import GLOG, time_logger, retry, GCONF


class LiveAccountService(BaseService):
    """
    实盘账号业务服务

    提供实盘账号管理的业务逻辑：
    - 创建账号并验证API凭证
    - 验证API连接和权限
    - 更新账号状态
    - 获取账户余额信息
    """

    # OKX API 域名，从 GCONF 统一管理
    OKX_DOMAIN = "https://www.okx.com"  # fallback，由 __init__ 从 GCONF 覆盖

    def __init__(self, live_account_crud: Optional[LiveAccountCRUD] = None):
        """
        初始化LiveAccountService

        Args:
            live_account_crud: LiveAccountCRUD实例（可选，用于依赖注入）
        """
        super().__init__()
        self._crud = live_account_crud or LiveAccountCRUD()
        self._encryption_service = get_encryption_service()
        self.OKX_DOMAIN = GCONF.OKX_DOMAIN

    @time_logger
    def create_account(
        self,
        user_id: str,
        exchange: str,
        name: str,
        api_key: str,
        api_secret: str,
        passphrase: Optional[str] = None,
        environment: str = "testnet",
        description: Optional[str] = None,
        auto_validate: bool = False
    ) -> Dict[str, Any]:
        """
        创建实盘账号

        Args:
            user_id: 用户ID
            exchange: 交易所类型 (okx/binance)
            name: 账号名称
            api_key: API Key
            api_secret: API Secret
            passphrase: Passphrase (OKX需要)
            environment: 环境 (production/testnet)
            description: 账号描述
            auto_validate: 是否自动验证API凭证

        Returns:
            Dict: {
                "success": bool,
                "data": {"account_uuid": str} or None,
                "message": str,
                "error": str
            }
        """
        try:
            # 验证参数
            if not user_id:
                return self._error_result("user_id is required")
            if not exchange:
                return self._error_result("exchange is required")
            if not name:
                return self._error_result("name is required")
            if not api_key:
                return self._error_result("api_key is required")
            if not api_secret:
                return self._error_result("api_secret is required")

            # 验证交易所类型
            if exchange not in [ExchangeType.OKX, ExchangeType.BINANCE]:
                return self._error_result(f"Unsupported exchange: {exchange}")

            # 验证环境类型
            if environment not in ["production", "testnet"]:
                return self._error_result(f"Invalid environment: {environment}")

            # 检查账号名称是否重复
            existing_accounts = self._crud.get_live_account_by_user_id(
                user_id=user_id,
                include_deleted=False
            )
            for acc in existing_accounts:
                if acc.name == name:
                    return self._error_result(f"Account name already exists: {name}")

            # OKX需要passphrase
            if exchange == ExchangeType.OKX and not passphrase:
                return self._error_result("passphrase is required for OKX")

            # 方案1：验证前置 - 先验证凭证，再创建账号
            validation_result = None
            if auto_validate:
                GLOG.INFO(f"Pre-validating credentials before creating account...")
                validation_result = self._validate_credentials_temporarily(
                    exchange=exchange,
                    api_key=api_key,
                    api_secret=api_secret,
                    passphrase=passphrase,
                    environment=environment
                )
                if not validation_result["success"]:
                    # 验证失败，直接返回错误，不创建账号
                    error_msg = validation_result.get("error", "Validation failed")
                    GLOG.WARN(f"Account creation rejected due to validation failure: {error_msg}")
                    return self._error_result(f"API validation failed: {error_msg}")

            # 验证通过后，创建账号
            account = self._crud.add_live_account(
                user_id=user_id,
                exchange=exchange,
                name=name,
                api_key=api_key,
                api_secret=api_secret,
                passphrase=passphrase,
                environment=environment,
                description=description
            )

            GLOG.INFO(f"Live account created: {account.uuid} (user={user_id}, exchange={exchange})")

            return {
                "success": True,
                "data": {
                    "account_uuid": account.uuid,
                    "validation_result": validation_result
                },
                "message": "Live account created successfully"
            }

        except Exception as e:
            GLOG.ERROR(f"Failed to create live account: {e}")
            return self._error_result(f"Failed to create live account: {str(e)}")

    def _validate_credentials_temporarily(
        self,
        exchange: str,
        api_key: str,
        api_secret: str,
        passphrase: Optional[str],
        environment: str
    ) -> Dict[str, Any]:
        """
        临时验证API凭证（不创建数据库记录）

        这是 create_account 方法的前置验证步骤，确保凭证有效后才创建账号。

        Args:
            exchange: 交易所类型 (okx/binance)
            api_key: API Key
            api_secret: API Secret
            passphrase: Passphrase (OKX需要)
            environment: 环境 (production/testnet)

        Returns:
            Dict: {
                "success": bool,
                "message": str,
                "error": str (if failed)
            }
        """
        try:
            if exchange == ExchangeType.OKX:
                return self._temp_validate_okx(api_key, api_secret, passphrase, environment)
            elif exchange == ExchangeType.BINANCE:
                return self._temp_validate_binance(api_key, api_secret, environment)
            else:
                return self._error_result(f"Unsupported exchange: {exchange}")

        except Exception as e:
            GLOG.ERROR(f"Temporary validation error: {e}")
            return self._error_result(f"Validation error: {str(e)}")

    def _temp_validate_okx(
        self,
        api_key: str,
        api_secret: str,
        passphrase: str,
        environment: str
    ) -> Dict[str, Any]:
        """临时验证OKX凭证（不涉及数据库）"""
        try:
            from okx.Account import AccountAPI as OKXAccount

            # 确定API端点
            domain = self.OKX_DOMAIN
            flag = "1" if environment == "testnet" else "0"

            if not passphrase:
                return self._error_result("Passphrase is required for OKX")

            # 创建API实例并验证
            account_api = OKXAccount(
                api_key=api_key,
                api_secret_key=api_secret,
                passphrase=passphrase,
                domain=domain,
                flag=flag,
                debug=False  # 生产模式关闭调试
            )

            # 调用API验证凭证
            result = account_api.get_account_balance()

            if result and result.get("code") == "0":
                balance_data = result.get("data", [{}])[0] if result.get("data") else {}
                total_equity = balance_data.get("totalEq", "0")

                GLOG.INFO(f"OKX credentials validation successful (environment={environment})")

                return {
                    "success": True,
                    "message": "API validation successful",
                    "account_info": {
                        "balance": total_equity,
                        "environment": environment,
                        "exchange": "okx"
                    }
                }
            else:
                error_msg = result.get("msg", "Unknown error") if result else "No response"
                error_code = result.get("code", "Unknown") if result else "Unknown"

                GLOG.WARN(f"OKX credentials validation failed: {error_msg} (code: {error_code})")

                return {
                    "success": False,
                    "error": f"API validation failed: {error_msg} (code: {error_code})"
                }

        except Exception as e:
            GLOG.ERROR(f"OKX temporary validation error: {e}")
            return self._error_result(f"OKX validation error: {str(e)}")

    def _temp_validate_binance(
        self,
        api_key: str,
        api_secret: str,
        environment: str
    ) -> Dict[str, Any]:
        """临时验证Binance凭证（待实现）"""
        # TODO: 实现Binance临时验证逻辑
        return self._error_result("Binance validation not yet implemented")

    @time_logger
    @retry(max_try=3)
    def validate_account(self, account_uuid: str) -> Dict[str, Any]:
        """
        验证实盘账号API凭证

        Args:
            account_uuid: 账号UUID

        Returns:
            Dict: {
                "success": bool,
                "valid": bool,
                "message": str,
                "account_info": dict or None
            }
        """
        try:
            # 获取账号
            account = self._crud.get_live_account_by_uuid(account_uuid, include_credentials=True)
            if not account:
                return self._error_result(f"Account not found: {account_uuid}")

            # 解密API凭证
            credentials = self._crud.get_decrypted_credentials(account_uuid)
            if not credentials:
                return self._error_result("Failed to decrypt credentials")

            # 根据交易所类型调用不同的验证逻辑
            if account.is_okx():
                return self._validate_okx_account(account, credentials)
            elif account.is_binance():
                return self._validate_binance_account(account, credentials)
            else:
                return self._error_result(f"Unsupported exchange: {account.exchange}")

        except Exception as e:
            GLOG.ERROR(f"Failed to validate account {account_uuid}: {e}")
            # 更新验证状态为失败
            self._crud.update_status(
                account_uuid,
                AccountStatusType.ERROR,
                validation_message=f"Validation failed: {str(e)}"
            )
            return self._error_result(f"Validation failed: {str(e)}")

    def _validate_okx_account(
        self,
        account: MLiveAccount,
        credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """验证OKX账号API凭证"""
        try:
            # 动态导入python-okx（避免硬依赖）
            try:
                from okx.Account import AccountAPI as OKXAccount
            except ImportError:
                return self._error_result("python-okx package not installed. Run: pip install python-okx")

            # 确定API端点
            if account.is_testnet():
                # OKX测试网配置
                domain = self.OKX_DOMAIN  # OKX使用相同域名，通过flag区分
                flag = "1"  # 测试网标记
            else:
                domain = self.OKX_DOMAIN
                flag = "0"  # 生产环境标记

            # 创建API实例
            api_key = credentials["api_key"]
            api_secret = credentials["api_secret"]
            passphrase = credentials.get("passphrase", "")

            if not passphrase:
                return self._error_result("Passphrase is required for OKX")

            # 验证API凭证 - 获取账户余额
            account_api = OKXAccount(
                api_key=api_key,
                api_secret_key=api_secret,
                passphrase=passphrase,
                domain=domain,
                flag=flag,
                debug=True
            )

            # 尝试获取余额来验证凭证
            result = account_api.get_account_balance()

            if result and result.get("code") == "0":
                # 验证成功
                balance_data = result.get("data", [{}])[0] if result.get("data") else {}
                total_equity = balance_data.get("totalEq", "0")

                # 更新账号状态为已验证
                self._crud.update_status(
                    account.uuid,
                    AccountStatusType.ENABLED,
                    validation_message="API validation successful"
                )

                GLOG.INFO(f"OKX account validated successfully: {account.uuid}")

                return {
                    "success": True,
                    "valid": True,
                    "message": "API validation successful",
                    "account_info": {
                        "balance": total_equity,
                        "environment": account.environment,
                        "exchange": "okx"
                    }
                }
            else:
                # 验证失败
                error_msg = result.get("msg", "Unknown error") if result else "No response"
                error_code = result.get("code", "Unknown") if result else "Unknown"

                # 更新账号状态为错误
                self._crud.update_status(
                    account.uuid,
                    AccountStatusType.ERROR,
                    validation_message=f"Validation failed: {error_msg} (code: {error_code})"
                )

                return {
                    "success": False,
                    "valid": False,
                    "message": f"API validation failed: {error_msg}",
                    "error_code": error_code
                }

        except Exception as e:
            GLOG.ERROR(f"OKX validation error: {e}")
            # 更新验证状态
            self._crud.update_status(
                account.uuid,
                AccountStatusType.ERROR,
                validation_message=f"Validation error: {str(e)}"
            )
            return self._error_result(f"OKX validation error: {str(e)}")

    def _validate_binance_account(
        self,
        account: MLiveAccount,
        credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """验证Binance账号API凭证（待实现）"""
        # TODO: 实现Binance验证逻辑
        return self._error_result("Binance validation not yet implemented")

    @time_logger
    def update_account_status(
        self,
        account_uuid: str,
        status: str
    ) -> Dict[str, Any]:
        """
        更新账号状态

        Args:
            account_uuid: 账号UUID
            status: 新状态 (enabled/disabled)

        Returns:
            Dict: {
                "success": bool,
                "message": str,
                "data": dict or None
            }
        """
        try:
            # 验证状态值
            valid_statuses = [AccountStatusType.ENABLED, AccountStatusType.DISABLED]
            if status not in valid_statuses:
                return self._error_result(f"Invalid status: {status}")

            # 检查账号是否存在
            account = self._crud.get_live_account_by_uuid(account_uuid)
            if not account:
                return self._error_result(f"Account not found: {account_uuid}")

            # 更新状态
            updated_account = self._crud.update_status(account_uuid, status)

            GLOG.INFO(f"Account status updated: {account_uuid} -> {status}")

            return {
                "success": True,
                "message": f"Account status updated to {status}",
                "data": {
                    "account_uuid": updated_account.uuid,
                    "status": updated_account.status
                }
            }

        except Exception as e:
            GLOG.ERROR(f"Failed to update account status: {e}")
            return self._error_result(f"Failed to update account status: {str(e)}")

    @time_logger
    @retry(max_try=2)
    def get_account_balance(self, account_uuid: str) -> Dict[str, Any]:
        """
        获取账户余额信息

        Args:
            account_uuid: 账号UUID

        Returns:
            Dict: {
                "success": bool,
                "message": str,
                "data": {
                    "total_equity": str,
                    "available_balance": str,
                    "frozen_balance": str,
                    "currency_balances": list
                } or None
            }
        """
        try:
            # 获取账号
            account = self._crud.get_live_account_by_uuid(account_uuid, include_credentials=True)
            if not account:
                return self._error_result(f"Account not found: {account_uuid}")

            # 检查账号状态
            if not account.is_enabled():
                return self._error_result(f"Account is not enabled: {account.status}")

            # 解密凭证
            credentials = self._crud.get_decrypted_credentials(account_uuid)
            if not credentials:
                return self._error_result("Failed to decrypt credentials")

            # 根据交易所获取余额
            if account.is_okx():
                return self._get_okx_balance(account, credentials)
            elif account.is_binance():
                return self._get_binance_balance(account, credentials)
            else:
                return self._error_result(f"Unsupported exchange: {account.exchange}")

        except Exception as e:
            GLOG.ERROR(f"Failed to get account balance: {e}")
            return self._error_result(f"Failed to get account balance: {str(e)}")

    def _get_okx_balance(
        self,
        account: MLiveAccount,
        credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """获取OKX账户余额，包含币种涨跌信息"""
        try:
            from okx.Account import AccountAPI as OKXAccount
            from okx.PublicData import PublicAPI

            # 配置API
            domain = self.OKX_DOMAIN
            flag = "1" if account.is_testnet() else "0"

            api_key = credentials["api_key"]
            api_secret = credentials["api_secret"]
            passphrase = credentials.get("passphrase", "")

            # 创建API实例
            account_api = OKXAccount(
                api_key=api_key,
                api_secret_key=api_secret,
                passphrase=passphrase,
                domain=domain,
                flag=flag,
                debug=False
            )

            # 创建公共API实例（获取涨跌数据）
            public_api = PublicAPI(domain=domain, flag=flag, debug=False)

            # 获取余额
            result = account_api.get_account_balance()

            if result and result.get("code") == "0":
                data = result.get("data", [{}])[0] if result.get("data") else {}
                details = data.get("details", [])

                # OKX API字段映射
                total_equity = data.get("totalEq") or "0"

                # 计算可用余额（使用USD价值，不是直接加币种数量）
                available_sum_usd = 0.0
                frozen_sum_usd = 0.0

                # 解析币种余额，同时获取涨跌数据
                currency_balances = []
                spot_positions = []  # 现货持仓（币种余额）

                for detail in details:
                    ccy = detail.get("ccy", "")
                    avail_bal = float(detail.get("availBal", "0") or "0")
                    frozen_bal = float(detail.get("frozenBal", "0") or "0")
                    # OKX API 使用 cashBal 或 eq 字段
                    cash_bal = float(detail.get("cashBal", "0") or "0")
                    eq = float(detail.get("eq", "0") or "0")
                    bal = eq if eq > 0 else cash_bal  # 使用 eq 或 cashBal

                    # 获取 USD 价值（用于计算总余额）
                    eq_usd = float(detail.get("eqUsd", "0") or "0")

                    # 获取现货盈亏数据（自买入后的盈亏）
                    spot_upl = float(detail.get("spotUpl", "0") or "0")  # 未实现盈亏
                    spot_upl_ratio = float(detail.get("spotUplRatio", "0") or "0")  # 盈亏比例
                    open_avg_px = detail.get("openAvgPx", "")  # 平均开仓价

                    # 累加可用余额（仅 USDT 和 USDC 稳定币）
                    if ccy in ["USDT", "USDC"]:
                        available_sum_usd += avail_bal  # 直接加稳定币数量

                    # 只显示有余额的币种
                    if bal > 0:
                        currency_item = {
                            "currency": ccy,
                            "available": str(avail_bal),
                            "frozen": str(frozen_bal),
                            "balance": str(bal)
                        }
                        currency_balances.append(currency_item)

                        # 作为现货持仓显示（使用自买入后的盈亏）
                        if avail_bal > 0:
                            try:
                                # 获取当前价格
                                if ccy == "USDT":
                                    current_price = "1.0"
                                    avg_price = "1.0"
                                elif open_avg_px:
                                    # OKX 提供了平均开仓价，使用它
                                    avg_price = open_avg_px
                                    # 获取当前价格
                                    import requests
                                    ticker_url = f"{domain}/api/v5/market/ticker"
                                    response = requests.get(ticker_url, params={"instId": f"{ccy}-USDT"}, timeout=5)
                                    if response.status_code == 200:
                                        ticker_result = response.json()
                                        if ticker_result.get("code") == "0" and ticker_result.get("data"):
                                            current_price = ticker_result["data"][0].get("last", avg_price)
                                        else:
                                            current_price = avg_price
                                    else:
                                        current_price = avg_price
                                else:
                                    # 没有平均开仓价，获取当前价格
                                    import requests
                                    ticker_url = f"{domain}/api/v5/market/ticker"
                                    response = requests.get(ticker_url, params={"instId": f"{ccy}-USDT"}, timeout=5)
                                    if response.status_code == 200:
                                        ticker_result = response.json()
                                        if ticker_result.get("code") == "0" and ticker_result.get("data"):
                                            current_price = ticker_result["data"][0].get("last", "0")
                                            avg_price = current_price  # 没有历史数据，用当前价
                                        else:
                                            current_price = "0"
                                            avg_price = "0"
                                    else:
                                        current_price = "0"
                                        avg_price = "0"

                                # 使用 OKX 提供的盈亏数据（自买入后）
                                unrealized_pnl = str(spot_upl)
                                unrealized_pnl_pct = str(spot_upl_ratio * 100)  # 转换为百分比

                                spot_positions.append({
                                    "symbol": f"{ccy}-USDT",
                                    "side": "long",
                                    "size": str(avail_bal),
                                    "avg_price": avg_price,
                                    "current_price": current_price,
                                    "unrealized_pnl": unrealized_pnl,  # 自买入后的盈亏
                                    "unrealized_pnl_percentage": unrealized_pnl_pct,
                                    "margin": "0",
                                    "is_spot": True
                                })
                            except Exception as e:
                                # 如果获取数据失败，仍然显示为持仓
                                GLOG.DEBUG(f"Failed to get spot position data for {ccy}: {e}")
                                spot_positions.append({
                                    "symbol": f"{ccy}-USDT",
                                    "side": "long",
                                    "size": str(avail_bal),
                                    "avg_price": "0",
                                    "current_price": "0",
                                    "unrealized_pnl": "0",
                                    "unrealized_pnl_percentage": "0",
                                    "margin": "0",
                                    "is_spot": True
                                })

                # 使用 OKX 返回的可用余额，如果为空则用计算值
                avail_eq = data.get("availEq")
                if not avail_eq or avail_eq == "":
                    available = str(available_sum_usd)
                else:
                    available = avail_eq

                # 冻结余额（OKX 可能不提供此数据的 USD 价值）
                frozen = "0"

                return {
                    "success": True,
                    "message": "Balance retrieved successfully",
                    "data": {
                        "total_equity": total_equity,
                        "available_balance": available,
                        "frozen_balance": frozen,
                        "currency_balances": currency_balances,
                        "spot_positions": spot_positions  # 新增：现货持仓列表
                    }
                }
            else:
                error_msg = result.get("msg", "Unknown error") if result else "No response"
                return self._error_result(f"Failed to get balance: {error_msg}")

        except Exception as e:
            GLOG.ERROR(f"OKX balance query error: {e}")
            return self._error_result(f"OKX balance query error: {str(e)}")

    def _get_binance_balance(
        self,
        account: MLiveAccount,
        credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """获取Binance账户余额（待实现）"""
        # TODO: 实现Binance余额查询
        return self._error_result("Binance balance query not yet implemented")

    @time_logger
    @retry(max_try=2)
    def get_account_positions(self, account_uuid: str) -> Dict[str, Any]:
        """
        获取账户持仓信息

        Args:
            account_uuid: 账号UUID

        Returns:
            Dict: {
                "success": bool,
                "message": str,
                "data": {
                    "positions": list
                } or None
            }
        """
        try:
            # 获取账号
            account = self._crud.get_live_account_by_uuid(account_uuid, include_credentials=True)
            if not account:
                return self._error_result(f"Account not found: {account_uuid}")

            # 检查账号状态
            if not account.is_enabled():
                return self._error_result(f"Account is not enabled: {account.status}")

            # 解密凭证
            credentials = self._crud.get_decrypted_credentials(account_uuid)
            if not credentials:
                return self._error_result("Failed to decrypt credentials")

            # 根据交易所获取持仓
            if account.is_okx():
                return self._get_okx_positions(account, credentials)
            elif account.is_binance():
                return self._get_binance_positions(account, credentials)
            else:
                return self._error_result(f"Unsupported exchange: {account.exchange}")

        except Exception as e:
            GLOG.ERROR(f"Failed to get account positions: {e}")
            return self._error_result(f"Failed to get account positions: {str(e)}")

    def _get_okx_positions(
        self,
        account: MLiveAccount,
        credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """获取OKX账户持仓"""
        try:
            from okx.Account import AccountAPI as OKXAccount

            # 配置API
            domain = self.OKX_DOMAIN
            flag = "1" if account.is_testnet() else "0"

            api_key = credentials["api_key"]
            api_secret = credentials["api_secret"]
            passphrase = credentials.get("passphrase", "")

            # 创建API实例
            account_api = OKXAccount(
                api_key=api_key,
                api_secret_key=api_secret,
                passphrase=passphrase,
                domain=domain,
                flag=flag,
                debug=True
            )

            # 获取持仓
            # 注意：OKX的positions端点不支持instType="SPOT"
            # 现货交易没有"持仓"概念，只有余额
            # 这里获取所有衍生品持仓（期货、永续合约、期权等）
            result = account_api.get_positions()

            if result and result.get("code") == "0":
                positions_data = result.get("data", [])

                # 转换为统一格式
                positions = []
                for pos in positions_data:
                    # 只返回有持仓的
                    if float(pos.get("pos", "0")) != 0:
                        positions.append({
                            "symbol": pos.get("instId", ""),
                            "side": "long" if pos.get("posSide") == "long" else "short",
                            "size": pos.get("pos", "0"),
                            "avg_price": pos.get("avgPx", "0"),
                            "current_price": pos.get("markPx", "0"),
                            "unrealized_pnl": pos.get("upl", "0"),
                            "unrealized_pnl_percentage": pos.get("uplRatio", "0"),
                            "margin": pos.get("margin", "0")
                        })

                return {
                    "success": True,
                    "message": "Positions retrieved successfully",
                    "data": {
                        "positions": positions
                    }
                }
            else:
                error_msg = result.get("msg", "Unknown error") if result else "No response"
                return self._error_result(f"Failed to get positions: {error_msg}")

        except Exception as e:
            GLOG.ERROR(f"OKX positions query error: {e}")
            return self._error_result(f"OKX positions query error: {str(e)}")

    def _get_binance_positions(
        self,
        account: MLiveAccount,
        credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """获取Binance账户持仓（待实现）"""
        # TODO: 实现Binance持仓查询
        return self._error_result("Binance positions query not yet implemented")

    def get_user_accounts(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        exchange: Optional[str] = None,
        environment: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取用户的实盘账号列表

        Args:
            user_id: 用户ID
            page: 页码
            page_size: 每页数量
            exchange: 过滤交易所
            environment: 过滤环境
            status: 过滤状态

        Returns:
            Dict: {
                "success": bool,
                "data": {
                    "accounts": list,
                    "total": int,
                    "page": int,
                    "page_size": int,
                    "total_pages": int
                }
            }
        """
        try:
            result = self._crud.get_live_accounts_by_user(
                user_id=user_id,
                page=page,
                page_size=page_size,
                exchange=exchange,
                environment=environment,
                status=status
            )

            # 转换为字典列表（隐藏敏感信息）
            accounts_dict = [acc.to_dict() for acc in result["accounts"]]

            return {
                "success": True,
                "data": {
                    "accounts": accounts_dict,
                    "total": result["total"],
                    "page": result["page"],
                    "page_size": result["page_size"],
                    "total_pages": result["total_pages"]
                }
            }

        except Exception as e:
            GLOG.ERROR(f"Failed to get user accounts: {e}")
            return self._error_result(f"Failed to get user accounts: {str(e)}")

    def get_account_by_uuid(self, account_uuid: str) -> Dict[str, Any]:
        """
        获取账号详情（不包含敏感信息）

        Args:
            account_uuid: 账号UUID

        Returns:
            Dict: {
                "success": bool,
                "data": dict or None
            }
        """
        try:
            account = self._crud.get_live_account_by_uuid(account_uuid)
            if not account:
                return self._error_result(f"Account not found: {account_uuid}")

            return {
                "success": True,
                "data": account.to_dict()
            }

        except Exception as e:
            GLOG.ERROR(f"Failed to get account: {e}")
            return self._error_result(f"Failed to get account: {str(e)}")

    def update_account(
        self,
        account_uuid: str,
        name: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新实盘账号信息

        Args:
            account_uuid: 账号UUID
            name: 新名称
            api_key: 新API Key
            api_secret: 新API Secret
            passphrase: 新Passphrase
            description: 新描述

        Returns:
            Dict: {
                "success": bool,
                "message": str,
                "data": dict or None
            }
        """
        try:
            updated_account = self._crud.update_live_account(
                uuid=account_uuid,
                name=name,
                api_key=api_key,
                api_secret=api_secret,
                passphrase=passphrase,
                description=description,
                encrypt_new_credentials=True
            )

            if not updated_account:
                return self._error_result(f"Account not found: {account_uuid}")

            GLOG.INFO(f"Account updated: {account_uuid}")

            return {
                "success": True,
                "message": "Account updated successfully",
                "data": updated_account.to_dict()
            }

        except Exception as e:
            GLOG.ERROR(f"Failed to update account: {e}")
            return self._error_result(f"Failed to update account: {str(e)}")

    def delete_account(self, account_uuid: str) -> Dict[str, Any]:
        """
        删除实盘账号（软删除）

        Args:
            account_uuid: 账号UUID

        Returns:
            Dict: {
                "success": bool,
                "message": str
            }
        """
        try:
            success = self._crud.delete_live_account(account_uuid)

            if not success:
                return self._error_result(f"Account not found: {account_uuid}")

            GLOG.INFO(f"Account deleted: {account_uuid}")

            return {
                "success": True,
                "message": "Account deleted successfully"
            }

        except Exception as e:
            GLOG.ERROR(f"Failed to delete account: {e}")
            return self._error_result(f"Failed to delete account: {str(e)}")

    def _error_result(self, message: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            "success": False,
            "message": message,
            "data": None
        }
