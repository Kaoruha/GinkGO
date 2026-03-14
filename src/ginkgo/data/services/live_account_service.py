# Upstream: Web UI/API Endpoints (实盘账号管理接口)
# Downstream: LiveAccountCRUD (数据持久化)、python-okx (API验证)、EncryptionService (凭证加密)
# Role: LiveAccountService实盘账号业务服务提供账号创建/验证/状态管理等业务逻辑


from typing import Optional, Dict, Any, List
from datetime import datetime

from ginkgo.data.services.base_service import BaseService
from ginkgo.data.services.encryption_service import get_encryption_service
from ginkgo.data.crud.live_account_crud import LiveAccountCRUD
from ginkgo.data.models.model_live_account import MLiveAccount, AccountStatusType, ExchangeType
from ginkgo.libs import GLOG, time_logger, retry


class LiveAccountService(BaseService):
    """
    实盘账号业务服务

    提供实盘账号管理的业务逻辑：
    - 创建账号并验证API凭证
    - 验证API连接和权限
    - 更新账号状态
    - 获取账户余额信息
    """

    def __init__(self, live_account_crud: Optional[LiveAccountCRUD] = None):
        """
        初始化LiveAccountService

        Args:
            live_account_crud: LiveAccountCRUD实例（可选，用于依赖注入）
        """
        super().__init__()
        self._crud = live_account_crud or LiveAccountCRUD()
        self._encryption_service = get_encryption_service()

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

            # 创建账号
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

            # 自动验证API凭证
            validation_result = None
            if auto_validate:
                validation_result = self.validate_account(account.uuid)
                if not validation_result["success"]:
                    # 验证失败，记录警告但不删除账号
                    GLOG.WARN(f"Account created but validation failed: {validation_result['error']}")

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
                from okx import Account as OKXAccount
                from okx import PublicData as OKXPublicData
            except ImportError:
                return self._error_result("python-okx package not installed. Run: pip install python-okx")

            # 确定API端点
            if account.is_testnet():
                # OKX测试网配置
                domain = "https://www.okx.com"  # OKX使用相同域名，通过flag区分
                flag = "1"  # 测试网标记
            else:
                domain = "https://www.okx.com"
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
                secret_key=api_secret,
                passphrase=passphrase,
                domain=domain,
                flag=flag,
                debug=True
            )

            # 尝试获取余额来验证凭证
            result = account_api.get_balance()

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
        """获取OKX账户余额"""
        try:
            from okx import Account as OKXAccount

            # 配置API
            domain = "https://www.okx.com"
            flag = "1" if account.is_testnet() else "0"

            api_key = credentials["api_key"]
            api_secret = credentials["api_secret"]
            passphrase = credentials.get("passphrase", "")

            # 创建API实例
            account_api = OKXAccount(
                api_key=api_key,
                secret_key=api_secret,
                passphrase=passphrase,
                domain=domain,
                flag=flag,
                debug=True
            )

            # 获取余额
            result = account_api.get_balance()

            if result and result.get("code") == "0":
                data = result.get("data", [{}])[0] if result.get("data") else {}
                details = data.get("details", [])

                total_equity = data.get("totalEq", "0")
                available = data.get("availBal", "0")
                frozen = data.get("frozenBal", "0")

                # 解析币种余额
                currency_balances = []
                for detail in details:
                    currency_balances.append({
                        "currency": detail.get("ccy", ""),
                        "available": detail.get("availBal", "0"),
                        "frozen": detail.get("frozenBal", "0"),
                        "balance": detail.get("bal", "0")
                    })

                return {
                    "success": True,
                    "message": "Balance retrieved successfully",
                    "data": {
                        "total_equity": total_equity,
                        "available_balance": available,
                        "frozen_balance": frozen,
                        "currency_balances": currency_balances
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
