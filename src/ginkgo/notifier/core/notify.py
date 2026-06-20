# Upstream: Kafka Worker (通知消费)、LiveCore 各组件 (task_timer, scheduler, data_manager 等)
# Downstream: NotificationDeliveryService (通知发送)、NotificationRecipientService (接收人配置)
# Role: 简化的全局通知函数，提供 notify / notify_with_fields 便捷 API

"""
全局通知函数

提供简化的通知发送 API，自动获取 NotificationDeliveryService 单例并发送通知：
- notify: 发送系统通知（支持 INFO/WARN/ERROR/ALERT 等级）
- notify_with_fields: 发送带自定义字段的系统通知
"""

from typing import Dict, Any, List, Optional

from datetime import datetime

from ginkgo.libs import GLOG
from ginkgo.enums import CONTACT_TYPES
from ginkgo.interfaces.kafka_topics import KafkaTopics

# 从常量模块导入颜色方案
from .notification_constants import DISCORD_COLOR_WHITE, SYSTEM_LEVEL_COLORS

# 使用延迟导入避免循环依赖
_notification_service_instance = None


def _get_notification_service():
    """获取 NotificationDeliveryService 单例（通过 notifier 容器）"""
    global _notification_service_instance

    if _notification_service_instance is not None:
        return _notification_service_instance

    try:
        from ginkgo.notifier.containers import container

        _notification_service_instance = container.notification_service()
        return _notification_service_instance

    except Exception as e:
        GLOG.ERROR(f"Failed to initialize NotificationDeliveryService: {e}")
        return None


def _get_recipient_user_uuids() -> List[str]:
    """解析所有活跃通知接收人为去重的 user UUID 列表"""
    try:
        from ginkgo.data.containers import container as data_container

        service = data_container.notification_recipient_service()
        result = service.get_all_recipient_user_uuids()
        return result.data if result.success else []
    except Exception as e:
        GLOG.ERROR(f"Failed to resolve recipient user uuids: {e}")
        return []


def notify(
    content: str,
    level: str = "INFO",
    details: Optional[Dict[str, Any]] = None,
    module: str = "System",
    async_mode: bool = True
) -> bool:
    """
    发送系统通知（简化版，内部调用）

    根据等级自动选择颜色和模板，自动发送到系统通知接收人。
    支持同步和异步模式。

    Args:
        content: 通知内容
        level: 等级 (INFO/WARN/ERROR/ALERT)，默认 INFO
        details: 详细信息字典
        module: 模块名称，默认 "System"
        async_mode: 异步模式（通过Kafka Worker），默认 True

    Returns:
        bool: 是否发送成功

    Examples:
        >>> # 异步发送（默认，不阻塞）
        >>> notify("任务完成")
        True
        >>>
        >>> # 同步发送（阻塞，等待结果）
        >>> notify("系统警告", level="WARN", async_mode=False)
        True
        >>>
        >>> # 错误通知
        >>> notify("连接失败", level="ERROR", details={"重试": "3次"})
        True
    """
    try:
        service = _get_notification_service()
        if service is None:
            GLOG.ERROR("NotificationDeliveryService not available")
            return False

        # 构建通知内容（不使用模板，直接发送）
        # 清理内容中的换行符，避免 Markdown 渲染问题
        clean_content = content.replace('\n', ' ').replace('\r', '')

        # 构建字段列表
        fields = []
        if details:
            for key, value in details.items():
                fields.append({
                    "name": str(key),
                    "value": str(value),
                    "inline": True
                })

        # 添加模块和时间字段
        fields.append({"name": "模块", "value": module, "inline": True})
        fields.append({"name": "时间", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "inline": True})

        # 通过 service facade 解析接收人
        user_uuids = _get_recipient_user_uuids()

        if not user_uuids:
            GLOG.WARN("No notification recipients found, notification not sent")
            return False

        # 构建标题
        level_upper = level.upper()
        title_map = {
            "INFO": "ℹ️ 系统消息",
            "SUCCESS": "✅ 操作成功",
            "WARNING": "⚠️ 系统警告",
            "ERROR": "❌ 系统错误",
            "ALERT": "🚨 系统告警",
        }
        title = title_map.get(level_upper, f"系统通知: {level}")

        # 获取颜色
        color = SYSTEM_LEVEL_COLORS.get(level_upper, DISCORD_COLOR_WHITE)

        success_count = 0

        # 根据async_mode选择发送方式
        if async_mode:
            # 异步模式：向每个用户异步发送（不阻塞）
            for user_uuid in user_uuids:
                result = service.send_async(
                    content=clean_content,
                    channels=["webhook"],
                    user_uuid=user_uuid,
                    priority=2 if level_upper in ("ERROR", "ALERT") else 1,
                    title=title,
                    color=color,
                    fields=fields if fields else None,
                    footer={"text": f"{module} • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
                )
                if result.is_success():
                    success_count += 1

            GLOG.INFO(f"Notification queued for {success_count}/{len(user_uuids)} users: {clean_content}")
            return success_count > 0
        else:
            # 同步模式：直接发送（阻塞，等待结果）
            for user_uuid in user_uuids:
                result = service.send_to_user(
                    user_uuid=user_uuid,
                    content=clean_content,
                    title=title,
                    channels=["webhook"],
                    priority=2 if level_upper in ("ERROR", "ALERT") else 1
                )

                # 如果发送成功，发送带格式的 Discord 消息
                if result.is_success():
                    success_count += 1

            # 额外发送格式化的 Discord webhook 消息
            for user_uuid in user_uuids:
                try:
                    _contacts_result = service.user_service.get_active_contacts(user_uuid, is_active=True)
                    contacts = _contacts_result.data if _contacts_result.success else []
                    for contact in contacts:
                        contact_type = CONTACT_TYPES.from_int(contact.contact_type)
                        if contact_type == CONTACT_TYPES.WEBHOOK and contact.is_primary:
                            service.send_discord_webhook(
                                webhook_url=contact.address,
                                content=clean_content,
                                title=title,
                                color=color,
                                fields=fields if fields else None,
                                footer={"text": f"{module} • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
                            )
                            break
                except Exception as e:
                    GLOG.ERROR(f"Failed to send notification to user: {e}")

            GLOG.INFO(f"Notification sent to {success_count}/{len(user_uuids)} users: {clean_content}")
            return success_count > 0

    except Exception as e:
        GLOG.ERROR(f"Failed to send notification: {e}")
        return False


def notify_with_fields(
    content: str,
    fields: List[Dict[str, Any]],
    title: Optional[str] = None,
    level: str = "INFO",
    module: str = "System",
    async_mode: bool = True,  # 默认异步模式
) -> bool:
    """
    发送系统通知（支持自定义字段）

    支持异步（Kafka）和同步（直接Discord webhook）两种模式。
    使用系统通知接收人配置。

    Args:
        content: 通知内容（支持Markdown）
        fields: Discord字段数组，格式：[{"name": "字段名", "value": "字段值", "inline": False}]
        title: 消息标题（可选）
        level: 等级 (INFO/WARN/ERROR/ALERT)，用于自动选择颜色，默认 INFO
        module: 模块名称，默认 "System"（仅用于日志）
        async_mode: 异步模式（需要Kafka），默认 True

    Returns:
        bool: 是否发送成功

    Examples:
        >>> # 发送带多个字段的通知
        >>> notify_with_fields(
        ...     content="TaskTimer启动成功",
        ...     title="TaskTimer",
        ...     fields=[
        ...         {"name": "节点ID", "value": "task_timer_1", "inline": True},
        ...         {"name": "任务数量", "value": "3", "inline": True},
        ...     ]
        ... )
        True
    """
    try:
        service = _get_notification_service()
        if service is None:
            GLOG.ERROR(f"[{module}] NotificationDeliveryService not available")
            return False

        # 通过 service facade 解析接收人
        user_uuids = _get_recipient_user_uuids()

        if not user_uuids:
            GLOG.WARN(f"[{module}] No notification recipients found")
            return False

        # 异步模式：通过 Kafka 发送
        if async_mode:
            try:
                # 构建自定义字段消息
                message = {
                    "message_type": "custom_fields",
                    "user_uuids": user_uuids,  # 发送给这些用户
                    "content": content,
                    "title": title,
                    "level": level,
                    "fields": fields,
                    "module": module,
                }

                # 发送到 Kafka
                if service._kafka_producer:
                    success = service._kafka_producer.send_async(KafkaTopics.NOTIFICATIONS, message)
                    if success:
                        service._kafka_producer.flush(timeout=2.0)
                        GLOG.INFO(f"[{module}] Notification queued for {len(user_uuids)} users (async)")
                        return True
                    else:
                        GLOG.WARN(f"[{module}] Kafka send_async failed, falling back to sync mode")
                else:
                    GLOG.WARN(f"[{module}] Kafka producer not available, falling back to sync mode")

            except Exception as e:
                GLOG.WARN(f"[{module}] Async send failed: {e}, falling back to sync mode")

        # 同步模式：直接发送到 Discord webhook
        color = SYSTEM_LEVEL_COLORS.get(level.upper(), DISCORD_COLOR_WHITE)

        success_count = 0
        for user_uuid in user_uuids:
            # 获取用户的webhook联系方式
            _contacts_result = service.user_service.get_active_contacts(user_uuid, is_active=True)
            contacts = _contacts_result.data if _contacts_result.success else []
            if contacts:
                for contact in contacts:
                    contact_type_enum = contact.get_contact_type_enum()
                    if contact_type_enum and contact_type_enum.name == "WEBHOOK" and contact.is_active:
                        # 直接发送到 Discord webhook
                        result = service.send_discord_webhook(
                            webhook_url=contact.address,
                            content=content,
                            title=title,
                            color=color,
                            fields=fields,
                            footer={"text": f"{module} • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
                        )
                        if result.is_success():
                            success_count += 1
                        break  # 每个用户只发送一次

        if success_count > 0:
            GLOG.INFO(f"[{module}] Notification sent to {success_count}/{len(user_uuids)} users (sync mode)")
            return True
        else:
            GLOG.WARN(f"[{module}] No notifications sent")
            return False

    except Exception as e:
        GLOG.ERROR(f"[{module}] Failed to send notification with fields: {e}")
        return False


def notify_trading_signal(signal, order, async_mode: bool = True) -> bool:
    """
    发送交易信号通知（#6150 半手动实盘核心链路）

    实盘产生信号→订单时调用，让用户收到 code/direction/volume/reason，
    手动执行后回报（POST /api/v1/signals/{id}/report）。

    镜像 notify()：收件人从配置表（notification_recipient）解析，
    支持同步直发与异步 Kafka→worker 两种模式。

    Note:
        通知发送实现由后续测试驱动（S1b 异步路径 / S2 渠道配置）。
        当前为 seam 占位，确保 _process_signal 已接线。

    Args:
        signal: Signal 对象（含 code/direction/reason）
        order: 产出的 Order 对象（含 volume/limit_price）
        async_mode: 异步模式（通过 Kafka Worker），默认 True

    Returns:
        bool: 是否发送成功
    """
    try:
        service = _get_notification_service()
        if service is None:
            GLOG.ERROR("NotificationDeliveryService not available for trading signal")
            return False

        user_uuids = _get_recipient_user_uuids()
        if not user_uuids:
            GLOG.WARN("No notification recipients found, trading signal not sent")
            return False

        # 从 signal/order 抽取交易字段
        code = str(getattr(signal, "code", ""))
        direction_raw = getattr(signal, "direction", "")
        direction_key = getattr(direction_raw, "name", str(direction_raw))
        direction_text = {"LONG": "做多", "SHORT": "做空", "VOID": "平仓"}.get(
            direction_key, direction_key
        )
        volume = getattr(order, "volume", 0)
        reason = getattr(signal, "reason", "") or ""

        content = f"{direction_text}信号 {code} 数量 {volume}"
        if reason and reason != "no reason":
            content += f"\n原因: {reason}"
        title = f"交易信号 {code}"

        if async_mode:
            # 异步路径：Kafka→worker 订阅→渠道发送（镜像 notify()）
            success_count = 0
            for user_uuid in user_uuids:
                result = service.send_async(
                    content=content,
                    channels=["email"],
                    user_uuid=user_uuid,
                    priority=2,
                    title=title,
                )
                if result.is_success():
                    success_count += 1

            GLOG.INFO(
                f"Trading signal queued for {success_count}/{len(user_uuids)} users (async): {code}"
            )
            return success_count > 0

        # 同步路径：逐个收件人直发
        success_count = 0
        for user_uuid in user_uuids:
            result = service.send_to_user(
                user_uuid=user_uuid,
                content=content,
                title=title,
                channels=["email"],
                priority=2,
            )
            if result.is_success():
                success_count += 1

        GLOG.INFO(f"Trading signal sent to {success_count}/{len(user_uuids)} users: {code}")
        return success_count > 0

    except Exception as e:
        GLOG.ERROR(f"Failed to send trading signal notification: {e}")
        return False
