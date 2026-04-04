# Upstream: NotificationService (依赖注入，提供 send_template_to_user 等方法)
# Downstream: WebhookChannel (Discord Webhook 发送通道)
# Role: WebhookDispatcher 负责所有 Webhook/Discord 直接发送逻辑，从 NotificationService 中提取

"""
Webhook 调度器

将 Webhook 相关的发送逻辑从 NotificationService 中分离，包括：
- 直接 Webhook 发送（无需用户 UUID）
- Discord Webhook 封装
- 交易信号 Webhook 发送
- 系统通知 Webhook 发送
- 基于模板的交易信号发送
"""

from typing import Dict, Any, List, Optional, TYPE_CHECKING

from ginkgo.libs import GLOG
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.enums import CONTACT_TYPES

from .notification_constants import (
    DISCORD_COLOR_VOID,
    DISCORD_COLOR_WHITE,
    TRADING_SIGNAL_COLORS,
    SYSTEM_LEVEL_COLORS,
)

# 使用 TYPE_CHECKING 避免运行时循环导入
if TYPE_CHECKING:
    from .notification_service import NotificationService


class WebhookDispatcher:
    """
    Webhook 调度器

    封装所有 Webhook/Discord 相关的发送逻辑，接收 NotificationService 实例作为依赖，
    因为部分方法（如 send_trading_signal）需要调用 NotificationService 的模板发送方法。
    """

    def __init__(self, notification_service: 'NotificationService'):
        """
        初始化 WebhookDispatcher

        Args:
            notification_service: NotificationService 实例，用于访问渠道注册和模板发送能力
        """
        self._service = notification_service

    def _get_webhook_channel_for_user(self, user_uuid: str) -> Optional['BaseNotificationChannel']:
        """
        为用户获取 webhook 通道（动态创建 WebhookChannel 实例）

        Args:
            user_uuid: 用户 UUID

        Returns:
            BaseNotificationChannel: WebhookChannel 实例，如果没有找到 webhook 联系方式则返回 None
        """
        try:
            from ginkgo.notifier.channels.webhook_channel import WebhookChannel

            # 获取用户的 webhook 联系方式
            contacts = self._service.contact_crud.get_by_user(user_uuid, is_active=True)

            # 查找 webhook 类型的联系方式
            webhook_contact = None
            for contact in contacts:
                contact_type = CONTACT_TYPES.from_int(contact.contact_type)
                if contact_type == CONTACT_TYPES.WEBHOOK:
                    webhook_contact = contact
                    break

            if not webhook_contact:
                return None

            # 创建 WebhookChannel 实例
            return WebhookChannel(webhook_url=webhook_contact.address)

        except Exception as e:
            GLOG.ERROR(f"Error creating webhook channel for user {user_uuid}: {e}")
            return None

    def send_webhook_direct(
        self,
        webhook_url: str,
        content: str,
        title: Optional[str] = None,
        color: Optional[int] = None,
        fields: Optional[List[Dict[str, Any]]] = None,
        footer: Optional[Dict[str, str]] = None,
        author: Optional[Dict[str, str]] = None,
        url: Optional[str] = None,
        **kwargs
    ) -> ServiceResult:
        """
        直接发送 Webhook 消息（底层方法）

        适用于需要直接向指定 Webhook URL 发送通知的场景，无需预先在系统中配置用户。

        Args:
            webhook_url: Webhook URL
            content: 消息内容
            title: 消息标题
            color: 嵌入消息颜色
            fields: 嵌入字段数组，格式：[{"name": "字段名", "value": "字段值", "inline": True}]
            footer: 页脚信息，格式：{"text": "页脚文本", "icon_url": "图标URL"}
            author: 作者信息，格式：{"name": "作者名", "url": "链接", "icon_url": "图标URL"}
            url: 标题链接（点击标题跳转的URL）
            **kwargs: 其他参数

        Returns:
            ServiceResult: 包含发送结果
        """
        try:
            from ginkgo.notifier.channels.webhook_channel import WebhookChannel

            # 创建 WebhookChannel 实例
            channel = WebhookChannel(webhook_url=webhook_url)

            # 发送消息
            result = channel.send(
                content=content,
                title=title,
                color=color,
                fields=fields,
                footer=footer,
                author=author,
                url=url,
                **kwargs
            )

            if result.success:
                return ServiceResult.success(
                    data={
                        "message_id": result.message_id,
                        "timestamp": result.timestamp,
                        "webhook_url": webhook_url
                    }
                )
            else:
                return ServiceResult.error(
                    f"Webhook send failed: {result.error}"
                )

        except Exception as e:
            GLOG.ERROR(f"Error sending direct webhook: {e}")
            return ServiceResult.error(
                f"Direct webhook failed: {str(e)}"
            )

    # ============================================================================
    # Discord Webhook 封装方法
    # ============================================================================

    def send_discord_webhook(
        self,
        webhook_url: str,
        content: str,
        title: Optional[str] = None,
        color: Optional[int] = None,
        fields: Optional[List[Dict[str, Any]]] = None,
        footer: Optional[Dict[str, str]] = None,
        author: Optional[Dict[str, str]] = None,
        url: Optional[str] = None,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None,
        **kwargs
    ) -> ServiceResult:
        """
        发送 Discord Webhook 消息（基础方法，支持所有Discord参数）

        Discord Webhook 完整功能封装，footer等参数支持完整的Discord原生格式。

        Args:
            webhook_url: Discord Webhook URL
            content: 消息内容（支持Markdown）
            title: 嵌入消息标题
            color: 嵌入消息颜色（十进制，如3066993=绿色）
            fields: 嵌入字段数组，格式：[{"name": "字段名", "value": "字段值", "inline": True}]
            footer: 页脚信息，完整格式：{"text": "页脚", "icon_url": "图标URL"}
            author: 作者信息，格式：{"name": "作者名", "url": "链接", "icon_url": "图标URL"}
            url: 标题链接（点击标题跳转）
            username: 覆盖Webhook默认用户名
            avatar_url: 覆盖Webhook默认头像URL
            **kwargs: 其他参数

        Returns:
            ServiceResult: 包含发送结果

        Examples:
            >>> service = container.notification_service()
            >>>
            >>> # 简单文本消息
            >>> service.send_discord_webhook(
            ...     webhook_url="https://...",
            ...     content="Hello World"
            ... )
            >>>
            >>> # 完整footer格式
            >>> service.send_discord_webhook(
            ...     webhook_url="https://...",
            ...     content="订单已成交",
            ...     title="交易通知",
            ...     footer={"text": "LiveBot", "icon_url": "https://..."}
            ... )
        """
        return self.send_webhook_direct(
            webhook_url=webhook_url,
            content=content,
            title=title,
            color=color,
            fields=fields,
            footer=footer,
            author=author,
            url=url,
            username=username,
            avatar_url=avatar_url,
            **kwargs
        )

    # ============================================================================
    # 交易信号封装方法
    # ============================================================================

    def send_trading_signal_webhook(
        self,
        webhook_url: str,
        direction: str,
        code: str,
        price: float,
        volume: int,
        strategy: Optional[str] = None,
        reason: Optional[str] = None,
        footer: Optional[str] = None,
        **kwargs
    ) -> ServiceResult:
        """
        发送交易信号到 Discord Webhook（基于 Webhook 直接发送）

        面向业务的交易信号发送方法，参数简洁直观。

        Args:
            webhook_url: Discord Webhook URL
            direction: 交易方向 (LONG/SHORT)
            code: 股票代码
            price: 价格
            volume: 数量
            strategy: 策略名称（可选）
            reason: 信号原因（可选）
            footer: 页脚文本，如 "LiveBot"（可选，内部自动转换为Discord格式）
            **kwargs: 其他参数

        Returns:
            ServiceResult: 包含发送结果

        Examples:
            >>> service = container.notification_service()
            >>>
            >>> # 简单信号
            >>> service.send_trading_signal_webhook(
            ...     webhook_url="https://...",
            ...     direction="LONG",
            ...     code="000001.SZ",
            ...     price=12.50,
            ...     volume=1000,
            ...     footer="LiveBot"
            ... )
            >>>
            >>> # 带策略和原因
            >>> service.send_trading_signal_webhook(
            ...     webhook_url="https://...",
            ...     direction="SHORT",
            ...     code="600000.SH",
            ...     price=15.80,
            ...     volume=500,
            ...     strategy="双均线策略",
            ...     reason="金叉死叉",
            ...     footer="TradeBot"
            ... )
        """
        try:
            # 根据交易方向设置颜色和标题
            direction_upper = direction.upper()
            color = TRADING_SIGNAL_COLORS.get(direction_upper, DISCORD_COLOR_VOID)

            # 中文方向文本和图标
            direction_text_map = {"LONG": "做多", "SHORT": "做空", "VOID": "平仓"}
            direction_text = direction_text_map.get(direction_upper, direction_upper)
            icon = "📈" if direction_upper == "LONG" else "📉" if direction_upper == "SHORT" else "📊"
            title = f"{icon} {direction_text}信号"

            # 构建字段
            fields = [
                {"name": "代码", "value": code, "inline": True},
                {"name": "价格", "value": str(price), "inline": True},
                {"name": "数量", "value": str(volume), "inline": True}
            ]

            # 添加策略字段
            if strategy:
                fields.append({"name": "策略", "value": strategy, "inline": True})

            # 添加原因字段
            if reason:
                fields.append({"name": "原因", "value": reason, "inline": False})

            # 转换footer为Discord格式
            footer_obj = {"text": footer} if footer else None

            # 发送消息
            return self.send_discord_webhook(
                webhook_url=webhook_url,
                content=f"交易信号触发: {direction_upper}",
                title=title,
                color=color,
                fields=fields,
                footer=footer_obj,
                **kwargs
            )

        except Exception as e:
            GLOG.ERROR(f"Error sending trading signal webhook: {e}")
            return ServiceResult.error(
                f"Trading signal webhook failed: {str(e)}"
            )

    def send_system_notification_webhook(
        self,
        webhook_url: str,
        message_type: str,
        content: str,
        details: Optional[Dict[str, str]] = None,
        footer: Optional[str] = None,
        **kwargs
    ) -> ServiceResult:
        """
        发送系统通知到 Discord Webhook（基于 Webhook 直接发送）

        面向业务的系统通知发送方法，参数简洁直观。

        Args:
            webhook_url: Discord Webhook URL
            message_type: 消息类型 (info/success/warning/error/update)
            content: 通知内容
            details: 详细信息字典，格式：{"字段名": "字段值"}
            footer: 页脚文本，如 "DataBot"（可选，内部自动转换为Discord格式）
            **kwargs: 其他参数

        Returns:
            ServiceResult: 包含发送结果

        Examples:
            >>> service = container.notification_service()
            >>>
            >>> # 数据更新通知
            >>> service.send_system_notification_webhook(
            ...     webhook_url="https://...",
            ...     message_type="update",
            ...     content="K线数据更新完成",
            ...     details={"代码": "000001.SZ", "日期": "2026-01-01", "记录数": "5000"},
            ...     footer="DataBot"
            ... )
            >>>
            >>> # 系统错误通知
            >>> service.send_system_notification_webhook(
            ...     webhook_url="https://...",
            ...     message_type="error",
            ...     content="数据库连接失败",
            ...     details={"错误": "Connection timeout", "重试次数": "3"},
            ...     footer="SystemMonitor"
            ... )
        """
        try:
            # 根据消息类型设置标题和颜色
            type_upper = message_type.upper()

            # 使用 SYSTEM_LEVEL_COLORS 映射获取颜色
            color = SYSTEM_LEVEL_COLORS.get(type_upper, DISCORD_COLOR_WHITE)

            # 设置标题
            title_map = {
                "INFO": "系统消息",
                "SUCCESS": "操作成功",
                "WARNING": "系统警告",
                "ERROR": "系统错误",
                "UPDATE": "数据更新",
                "ALERT": "系统告警",
            }
            title = title_map.get(type_upper, f"系统通知: {message_type}")

            # 构建字段
            fields = []
            if details:
                for key, value in details.items():
                    fields.append({"name": key, "value": str(value), "inline": True})

            # 转换footer为Discord格式
            footer_obj = {"text": footer} if footer else None

            # 发送消息
            return self.send_discord_webhook(
                webhook_url=webhook_url,
                content=content,
                title=title,
                color=color,
                fields=fields if fields else None,
                footer=footer_obj,
                **kwargs
            )

        except Exception as e:
            print(f"Error sending system notification webhook: {e}")
            return ServiceResult.error(
                f"System notification webhook failed: {str(e)}"
            )

    def send_trading_signal(
        self,
        user_uuid: Optional[str] = None,
        group_name: Optional[str] = None,
        group_uuid: Optional[str] = None,
        direction: str = "LONG",
        code: str = "",
        price: float = 0.0,
        volume: int = 0,
        strategy_name: Optional[str] = None,
        priority: int = 2,
        **kwargs
    ) -> ServiceResult:
        """
        发送交易信号（基于模板）

        使用 simple_signal 模板发送格式化的交易信号通知。
        优先级默认为2（HIGH），确保交易信号及时送达。

        Args:
            user_uuid: 用户 UUID（与 group_name/group_uuid 二选一）
            group_name: 用户组名称（与 user_uuid 二选一）
            group_uuid: 用户组 UUID（与 user_uuid 二选一）
            direction: 交易方向 (LONG/SHORT)
            code: 股票代码
            price: 价格
            volume: 数量
            strategy_name: 策略名称（可选）
            priority: 优先级（默认2=HIGH）
            **kwargs: 其他参数

        Returns:
            ServiceResult: 包含发送结果

        Examples:
            >>> service = container.notification_service()
            >>>
            >>> # 发送给用户
            >>> service.send_trading_signal(
            ...     user_uuid="xxx",
            ...     direction="LONG",
            ...     code="000001.SZ",
            ...     price=12.50,
            ...     volume=1000
            ... )
            >>>
            >>> # 发送给用户组
            >>> service.send_trading_signal(
            ...     group_name="traders",
            ...     direction="SHORT",
            ...     code="600000.SH",
            ...     price=15.80,
            ...     volume=500,
            ...     strategy_name="趋势策略"
            ... )
        """
        try:
            # 获取交易方向对应的颜色和文本
            direction_upper = direction.upper()
            color = TRADING_SIGNAL_COLORS.get(direction_upper, DISCORD_COLOR_VOID)

            # 中文方向文本
            direction_text_map = {"LONG": "做多", "SHORT": "做空", "VOID": "平仓"}
            direction_text = direction_text_map.get(direction_upper, direction_upper)

            # 构建标题
            title = f"{'📈' if direction_upper == 'LONG' else '📉' if direction_upper == 'SHORT' else '📊'} {direction_text}信号 - {code}"

            # 准备模板变量（匹配 simple_signal 模板需求）
            context = {
                "title": title,
                "content": f"**{direction_text}信号**\n\n{f'策略: {strategy_name}' if strategy_name else ''}",
                "color": color,
                "symbol": code,
                "price": str(price),
                "direction": direction_text,
                "footer_text": "Ginkgo 交易系统"
            }

            if strategy_name:
                context["strategy_name"] = strategy_name

            # 根据接收者类型发送
            if user_uuid:
                return self._service.send_template_to_user(
                    user_uuid=user_uuid,
                    template_id="simple_signal",
                    context=context,
                    priority=priority,
                    **kwargs
                )
            elif group_name:
                return self._service.send_template_to_group(
                    group_name=group_name,
                    template_id="simple_signal",
                    context=context,
                    priority=priority,
                    **kwargs
                )
            elif group_uuid:
                # 如果提供的是 group_uuid，需要先查找 group_name
                if self._service.group_crud is None:
                    return ServiceResult.error("Group CRUD not initialized")

                group = self._service.group_crud.get_by_uuid(group_uuid)
                if group is None:
                    return ServiceResult.error(f"Group not found: {group_uuid}")

                return self._service.send_template_to_group(
                    group_name=group.name,
                    template_id="simple_signal",
                    context=context,
                    priority=priority,
                    **kwargs
                )
            else:
                return ServiceResult.error(
                    "Either user_uuid or group_name/group_uuid is required"
                )

        except Exception as e:
            GLOG.ERROR(f"Error sending trading signal: {e}")
            return ServiceResult.error(
                f"Trading signal failed: {str(e)}"
            )
