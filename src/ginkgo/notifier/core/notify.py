# Upstream: Kafka Worker (通知消费)、LiveCore 各组件 (task_timer, scheduler, data_manager 等)
# Downstream: NotificationService (通知发送)、NotificationRecipientCRUD (接收人配置)
# Role: 简化的全局通知函数，提供 notify / notify_with_fields 便捷 API

"""
全局通知函数

提供简化的通知发送 API，自动获取 NotificationService 单例并发送通知：
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
    """获取 NotificationService 单例（延迟初始化）"""
    global _notification_service_instance

    if _notification_service_instance is not None:
        return _notification_service_instance

    try:
        from ginkgo.data.containers import container
        from ginkgo.user.services.user_service import UserService
        from ginkgo.user.services.user_group_service import UserGroupService
        from ginkgo.notifier.core.template_engine import TemplateEngine
        from .notification_service import NotificationService

        template_crud = container.notification_template_crud()
        record_crud = container.notification_record_crud()
        template_engine = TemplateEngine(template_crud=template_crud)

        user_service = UserService(
            user_crud=container.user_crud(),
            user_contact_crud=container.user_contact_crud()
        )

        group_service = UserGroupService(
            user_group_crud=container.user_group_crud(),
            user_group_mapping_crud=container.user_group_mapping_crud()
        )

        _notification_service_instance = NotificationService(
            user_service=user_service,
            user_group_service=group_service,
            template_crud=template_crud,
            record_crud=record_crud,
            template_engine=template_engine,
            group_crud=container.user_group_crud(),
            group_mapping_crud=container.user_group_mapping_crud(),
            contact_crud=container.user_contact_crud()
        )

        return _notification_service_instance

    except Exception as e:
        GLOG.ERROR(f"Failed to initialize NotificationService: {e}")
        return None


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
            GLOG.ERROR("NotificationService not available")
            return False

        # 等级到模板ID的映射
        level_templates = {
            "INFO": "system_info",
            "WARN": "system_warn",
            "ERROR": "system_error",
            "ALERT": "system_alert"
        }

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

        # 获取所有系统通知接收人
        from ginkgo.data.containers import container
        from ginkgo.enums import RECIPIENT_TYPES

        recipient_crud = container.notification_recipient_crud()
        group_mapping_crud = container.user_group_mapping_crud()

        # 获取所有启用的通知接收人
        recipients = recipient_crud.find(filters={"is_del": False}, as_dataframe=False)

        if not recipients:
            GLOG.WARN("No notification recipients found, notification not sent")
            return False

        # 收集所有需要通知的用户UUID（去重）
        user_uuids_set = set()

        for recipient in recipients:
            recipient_type = recipient.get_recipient_type_enum()

            if recipient_type == RECIPIENT_TYPES.USER:
                # 单个用户类型
                if recipient.user_id:
                    user_uuids_set.add(recipient.user_id)

            elif recipient_type == RECIPIENT_TYPES.USER_GROUP:
                # 用户组类型 - 获取组内所有用户
                if recipient.user_group_id and group_mapping_crud:
                    mappings = group_mapping_crud.find_by_group(
                        recipient.user_group_id,
                        as_dataframe=False
                    )
                    for mapping in mappings:
                        user_uuids_set.add(mapping.user_uuid)

        user_uuids = list(user_uuids_set)

        if not user_uuids:
            GLOG.WARN("No users found from notification recipients")
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
                if result.is_success:
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
                if result.is_success:
                    success_count += 1

            # 额外发送格式化的 Discord webhook 消息
            for user_uuid in user_uuids:
                try:
                    contacts = service.contact_crud.get_by_user(user_uuid, is_active=True) if service.contact_crud else []
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
            GLOG.ERROR(f"[{module}] NotificationService not available")
            return False

        # 获取所有系统通知接收人
        from ginkgo.data.containers import container
        from ginkgo.enums import RECIPIENT_TYPES

        recipient_crud = container.notification_recipient_crud()
        group_mapping_crud = container.user_group_mapping_crud()

        # 获取所有启用的通知接收人
        recipients = recipient_crud.find(filters={"is_del": False}, as_dataframe=False)

        if not recipients:
            GLOG.WARN(f"[{module}] No notification recipients found")
            return False

        # 收集所有需要通知的用户UUID（去重）
        user_uuids_set = set()

        for recipient in recipients:
            recipient_type = recipient.get_recipient_type_enum()

            if recipient_type == RECIPIENT_TYPES.USER:
                # 单个用户类型
                if recipient.user_id:
                    user_uuids_set.add(recipient.user_id)

            elif recipient_type == RECIPIENT_TYPES.USER_GROUP:
                # 用户组类型 - 获取组内所有用户
                if recipient.user_group_id and group_mapping_crud:
                    mappings = group_mapping_crud.find_by_group(
                        recipient.user_group_id,
                        as_dataframe=False
                    )
                    for mapping in mappings:
                        user_uuids_set.add(mapping.user_uuid)

        user_uuids = list(user_uuids_set)

        if not user_uuids:
            GLOG.WARN(f"[{module}] No users found from notification recipients")
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
            if service.contact_crud:
                contacts = service.contact_crud.find_by_user_id(user_uuid, as_dataframe=False)
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
                        if result.is_success:
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
