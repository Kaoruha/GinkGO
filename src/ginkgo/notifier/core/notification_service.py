# Upstream: CLI Commands (ginkgo notify 命令)、Kafka Worker (通知消费)
# Downstream: BaseService (继承提供服务基础能力)、NotificationTemplateCRUD (模板CRUD)、NotificationRecordCRUD (记录CRUD)、BaseNotificationChannel (通知渠道接口)
# Role: NotificationService通知业务服务提供通知发送/模板渲染/渠道选择/记录管理等业务逻辑支持通知系统功能

from __future__ import annotations  # 启用延迟注解评估，避免循环导入

"""
Notification Service

提供通知发送的核心业务逻辑，包括：
- 多渠道通知发送（Discord、Email、Kafka）
- 模板渲染和变量替换
- 通知记录管理
- 用户和用户组批量通知

注意：Webhook 相关方法已提取到 webhook_dispatcher.py
      全局通知函数已提取到 notify.py
      常量已提取到 notification_constants.py
"""

from typing import Dict, Any, List, Optional, Union, TYPE_CHECKING
from datetime import datetime
import uuid as uuid_lib

from ginkgo.libs import GLOG, retry
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.crud import NotificationTemplateCRUD, NotificationRecordCRUD, UserContactCRUD, UserGroupCRUD, UserGroupMappingCRUD
from ginkgo.data.models import MNotificationRecord
from ginkgo.notifier.channels.base_channel import BaseNotificationChannel, ChannelResult
from ginkgo.enums import NOTIFICATION_STATUS_TYPES, SOURCE_TYPES, CONTACT_TYPES
from ginkgo.interfaces.kafka_topics import KafkaTopics

# 从提取的模块导入常量和全局函数，保持向后兼容
from .notification_constants import *
from .notify import notify, notify_with_fields

# 导入 WebhookDispatcher
from .webhook_dispatcher import WebhookDispatcher

# 使用 TYPE_CHECKING 避免运行时循环导入
if TYPE_CHECKING:
    from ginkgo.notifier.core.template_engine import TemplateEngine
    from ginkgo.libs.utils.kafka_health_checker import KafkaHealthChecker


class NotificationService(BaseService):
    """
    通知服务

    提供通知发送的完整业务逻辑，包括：
    - 单个/批量用户通知发送
    - 模板渲染和变量替换
    - 多渠道支持（Discord、Email 等）
    - 通知记录持久化
    """

    def __init__(
        self,
        template_crud: NotificationTemplateCRUD,
        record_crud: NotificationRecordCRUD,
        template_engine: TemplateEngine,
        user_service: 'UserService',
        user_group_service: 'UserGroupService',
        contact_crud: Optional[UserContactCRUD] = None,
        group_crud: Optional[UserGroupCRUD] = None,
        group_mapping_crud: Optional[UserGroupMappingCRUD] = None,
        kafka_producer: Optional['GinkgoProducer'] = None,
        kafka_health_checker: Optional[KafkaHealthChecker] = None
    ):
        """
        初始化 NotificationService

        Args:
            template_crud: 通知模板 CRUD 实例
            record_crud: 通知记录 CRUD 实例
            template_engine: 模板引擎实例
            contact_crud: 用户联系方式 CRUD 实例（可选，用于基于用户的通知）
            group_crud: 用户组 CRUD 实例（可选，用于组通知）
            group_mapping_crud: 用户组映射 CRUD 实例（可选，用于获取组成员）
            user_service: 用户服务实例（必需，用于模糊搜索）
            user_group_service: 用户组服务实例（必需，用于模糊搜索）
            kafka_producer: Kafka 生产者（可选，用于异步通知）
            kafka_health_checker: Kafka 健康检查器（可选，用于降级逻辑）
        """
        super().__init__(crud_repo=record_crud)
        self.template_crud = template_crud
        self.record_crud = record_crud
        self.template_engine = template_engine
        self.contact_crud = contact_crud
        self.group_crud = group_crud
        self.group_mapping_crud = group_mapping_crud
        self.user_service = user_service
        self.user_group_service = user_group_service

        # Kafka 组件（可选，用于异步通知和降级逻辑）
        self._kafka_producer = kafka_producer
        self._kafka_health_checker = kafka_health_checker

        # 注册的通知渠道 {channel_name: channel_instance}
        self._channels: Dict[str, BaseNotificationChannel] = {}

        # 创建 Webhook 调度器实例
        self._webhook = WebhookDispatcher(self)

    def register_channel(self, channel: BaseNotificationChannel) -> None:
        """
        注册通知渠道

        Args:
            channel: 通知渠道实例
        """
        channel_name = channel.channel_name
        self._channels[channel_name] = channel
        GLOG.INFO(f"Registered notification channel: {channel_name}")

    def get_channel(self, channel_name: str) -> Optional[BaseNotificationChannel]:
        """
        获取通知渠道

        Args:
            channel_name: 渠道名称

        Returns:
            BaseNotificationChannel: 渠道实例，不存在返回 None
        """
        return self._channels.get(channel_name)

    @retry(max_try=3)
    def send(
        self,
        content: str,
        channels: Union[str, List[str]],
        user_uuid: Optional[str] = None,
        template_id: Optional[str] = None,
        content_type: str = "text",
        priority: int = 1,
        title: Optional[str] = None,
        **kwargs
    ) -> ServiceResult:
        """
        发送通知

        Args:
            content: 通知内容（已渲染或纯文本）
            channels: 渠道名称或列表（如 "discord" 或 ["discord", "email"]）
            user_uuid: 用户 UUID（可选）
            template_id: 使用的模板 ID（可选）
            content_type: 内容类型（text/markdown/html）
            priority: 优先级（0=低, 1=中, 2=高, 3=紧急）
            title: 通知标题（可选）
            **kwargs: 渠道特定的额外参数

        Returns:
            ServiceResult: 包含发送结果
        """
        try:
            # 标准化 channels 参数
            if isinstance(channels, str):
                channels = [channels]

            # 如果提供了template_id，先渲染模板
            final_content = content
            final_content_type = content_type
            final_title = title

            if template_id:
                template = self.template_crud.get_by_template_id(template_id)
                if template:
                    # 渲染模板（kwargs作为context传递）
                    rendered_content = self.template_engine.render(
                        template.content,
                        context=kwargs
                    )

                    content_type_enum = template.get_template_type_enum()
                    final_content_type = content_type_enum.name.lower()

                    # 对于嵌入式模板，解析JSON并创建embed对象
                    if final_content_type == "embedded":
                        try:
                            import json
                            embed_obj = json.loads(rendered_content)
                            # 将embed对象添加到kwargs
                            kwargs['embed'] = embed_obj
                            final_content = ""  # embed包含description，content设为空
                            final_title = embed_obj.get("title", title)
                        except json.JSONDecodeError as e:
                            GLOG.ERROR(f"Failed to parse embedded template JSON: {e}")
                            final_content = rendered_content
                    else:
                        # 文本/Markdown模板
                        final_content = rendered_content
                        final_title = template.subject or title

            # 生成唯一 message_id
            message_id = f"msg_{uuid_lib.uuid4().hex}"

            # 创建通知记录
            record = MNotificationRecord(
                message_id=message_id,
                content=final_content,
                content_type=final_content_type,
                channels=channels,
                status=NOTIFICATION_STATUS_TYPES.PENDING.value,
                priority=priority,
                user_uuid=user_uuid,
                template_id=template_id,
                source=SOURCE_TYPES.OTHER
            )

            # 保存记录
            record_uuid = self.record_crud.add(record)
            if record_uuid is None:
                return ServiceResult.error("Failed to create notification record")

            # 发送到各个渠道
            channel_results: Dict[str, Any] = {}
            success_count = 0
            first_error = None

            for channel_name in channels:
                # 处理 webhook 通道：需要动态创建 WebhookChannel 实例
                if channel_name == "webhook" and user_uuid:
                    channel = self._webhook._get_webhook_channel_for_user(user_uuid)
                    if channel is None:
                        error_msg = f"No webhook contact found for user {user_uuid}"
                        channel_results[channel_name] = {
                            "success": False,
                            "error": error_msg
                        }
                        first_error = first_error or error_msg
                        continue
                else:
                    channel = self.get_channel(channel_name)
                    if channel is None:
                        error_msg = f"Channel not found: {channel_name}"
                        channel_results[channel_name] = {
                            "success": False,
                            "error": error_msg
                        }
                        first_error = first_error or error_msg
                        continue

                try:
                    result = channel.send(
                        content=final_content,
                        title=final_title,
                        **kwargs
                    )

                    channel_results[channel_name] = result.to_dict()

                    if result.success:
                        success_count += 1
                    else:
                        first_error = first_error or result.error

                except Exception as e:
                    error_msg = f"Channel error: {str(e)}"
                    channel_results[channel_name] = {
                        "success": False,
                        "error": error_msg
                    }
                    first_error = first_error or error_msg

            # 更新记录状态
            record.set_channel_results_dict(channel_results)

            if success_count == len(channels):
                # 全部成功
                record.mark_as_sent()
                status = NOTIFICATION_STATUS_TYPES.SENT.value
            elif success_count == 0:
                # 全部失败
                record.mark_as_failed(first_error or "All channels failed")
                status = NOTIFICATION_STATUS_TYPES.FAILED.value
            else:
                # 部分成功
                record.status = NOTIFICATION_STATUS_TYPES.SENT.value  # 标记为已发送（部分成功）
                record.sent_at = datetime.now()
                status = NOTIFICATION_STATUS_TYPES.SENT.value

            # 更新记录
            self.record_crud.update_status(
                message_id=message_id,
                status=status,
                error_message=record.error_message
            )

            GLOG.INFO(f"Notification sent: {message_id}, channels={channels}, success={success_count}/{len(channels)}")

            return ServiceResult.success(
                data={
                    "message_id": message_id,
                    "record_uuid": record_uuid,
                    "channels": channels,
                    "success_count": success_count,
                    "total_channels": len(channels),
                    "channel_results": channel_results
                }
            )

        except Exception as e:
            GLOG.ERROR(f"Errorsending notification: {e}")
            return ServiceResult.error(
                f"Notification send failed: {str(e)}",
                message=str(e)
            )

    @retry(max_try=3)
    def send_to_users(
        self,
        user_uuids: List[str],
        content: str,
        channels: Union[str, List[str]],
        content_type: str = "text",
        priority: int = 1,
        **kwargs
    ) -> ServiceResult:
        """
        向多个用户发送通知

        Args:
            user_uuids: 用户 UUID 列表
            content: 通知内容
            channels: 渠道名称或列表
            content_type: 内容类型
            priority: 优先级
            **kwargs: 其他参数

        Returns:
            ServiceResult: 包含批量发送结果
        """
        try:
            results = []
            success_count = 0

            for user_uuid in user_uuids:
                result = self.send(
                    content=content,
                    channels=channels,
                    user_uuid=user_uuid,
                    content_type=content_type,
                    priority=priority,
                    **kwargs
                )

                results.append({
                    "user_uuid": user_uuid,
                    "success": result.is_success,
                    "data": result.data
                })

                if result.is_success:
                    success_count += 1

            GLOG.INFO(f"Batch notification sent: {success_count}/{len(user_uuids)} users")

            return ServiceResult.success(
                data={
                    "total_users": len(user_uuids),
                    "success_count": success_count,
                    "results": results
                }
            )

        except Exception as e:
            GLOG.ERROR(f"Errorsending batch notification: {e}")
            return ServiceResult.error(
                f"Batch notification failed: {str(e)}"
            )

    @retry(max_try=3)
    def send_template(
        self,
        template_id: str,
        context: Dict[str, Any],
        channels: Union[str, List[str]],
        user_uuid: Optional[str] = None,
        priority: int = 1,
        **kwargs
    ) -> ServiceResult:
        """
        使用模板发送通知

        Args:
            template_id: 模板 ID
            context: 模板变量上下文
            channels: 渠道名称或列表
            user_uuid: 用户 UUID（可选）
            priority: 优先级
            **kwargs: 其他参数（如 title）

        Returns:
            ServiceResult: 包含发送结果
        """
        try:
            # 渲染模板
            rendered_content = self.template_engine.render_from_template_id(
                template_id=template_id,
                context=context,
                strict=False  # 非严格模式，允许未定义变量
            )

            # 获取模板信息
            template = self.template_crud.get_by_template_id(template_id)
            if template is None:
                return ServiceResult.error(f"Template not found: {template_id}")

            content_type = template.get_template_type_enum().name.lower()

            # 提取 title（如果提供）
            title = kwargs.pop("title", None) or template.subject

            # 发送通知
            return self.send(
                content=rendered_content,
                channels=channels,
                user_uuid=user_uuid,
                template_id=template_id,
                content_type=content_type,
                priority=priority,
                title=title,
                **kwargs
            )

        except ValueError as e:
            # 模板渲染错误
            GLOG.ERROR(f"Template rendering error: {e}")
            return ServiceResult.error(
                f"Template error: {str(e)}",
                message=str(e)
            )
        except Exception as e:
            GLOG.ERROR(f"Errorsending template notification: {e}")
            return ServiceResult.error(
                f"Template notification failed: {str(e)}"
            )

    def _get_user_channels(self, user_uuid: str) -> List[str]:
        """
        获取用户的可用通知渠道

        Args:
            user_uuid: 用户 UUID

        Returns:
            List[str]: 可用渠道名称列表
        """
        if self.contact_crud is None:
            GLOG.WARN("UserContactCRUD not initialized, cannot get user channels")
            return []

        try:
            # 查询用户的所有活跃联系方式
            contacts = self.contact_crud.get_by_user(user_uuid, is_active=True)

            # 优先使用主联系方式
            primary_contacts = [c for c in contacts if c.is_primary]
            if primary_contacts:
                contacts = primary_contacts

            # 转换为渠道名称
            channels = []
            for contact in contacts:
                contact_type = CONTACT_TYPES.from_int(contact.contact_type)
                if contact_type == CONTACT_TYPES.EMAIL:
                    channels.append("email")
                elif contact_type == CONTACT_TYPES.WEBHOOK:
                    channels.append("webhook")

            return channels

        except Exception as e:
            GLOG.ERROR(f"Errorgetting user channels: {e}")
            return []

    def _resolve_user_uuid(self, user_input: str) -> Optional[str]:
        """
        解析用户输入，返回 UUID

        支持模糊搜索 - 在 uuid 和 name 字段中搜索匹配的用户

        Args:
            user_input: 用户 UUID 或 name（支持模糊匹配）

        Returns:
            Optional[str]: 用户 UUID，找不到返回 None
        """
        if self.contact_crud is None:
            return None

        try:
            result = self.user_service.fuzzy_search(user_input, limit=1)

            if not result.is_success:
                GLOG.ERROR(f"User search failed: {result.message}")
                return None

            if result.data.get("users"):
                return result.data["users"][0]["uuid"]

            return None

        except Exception as e:
            GLOG.ERROR(f"Errorresolving user UUID: {e}")
            return None

    def _resolve_group_uuids(self, group_input: str) -> List[str]:
        """
        解析组输入，返回用户 UUID 列表

        支持模糊搜索 - 在 uuid 和 name 字段中搜索匹配的组

        Args:
            group_input: 组 uuid 或 name（支持模糊匹配）

        Returns:
            List[str]: 组内用户 UUID 列表
        """
        if self.group_crud is None or self.group_mapping_crud is None:
            return []

        try:
            result = self.user_group_service.fuzzy_search(group_input, limit=1)

            if not result.is_success:
                GLOG.ERROR(f"Group search failed: {result.message}")
                return []

            if not result.data.get("groups"):
                return []

            group_uuid = result.data["groups"][0]["uuid"]

            # 获取组内所有用户
            return [m.user_uuid for m in mappings]

        except Exception as e:
            GLOG.ERROR(f"Errorresolving group: {e}")
            return []

    def _get_group_users(self, group_name: str) -> ServiceResult:
        """
        获取组内所有用户的 UUID 列表

        Args:
            group_name: 用户组名称

        Returns:
            ServiceResult: 包含 user_uuids 列表
        """
        if self.group_crud is None or self.group_mapping_crud is None:
            return ServiceResult.error("Group CRUDs not initialized")

        try:
            # 根据 name 获取 group_uuid
            if not group:
                return ServiceResult.error(f"Group not found: {group_name}")

            group_uuid = group[0].uuid

            # 获取组内所有用户
            user_uuids = [m.user_uuid for m in mappings]

            return ServiceResult.success(
                data={"group_name": group_name, "user_uuids": user_uuids}
            )

        except Exception as e:
            GLOG.ERROR(f"Errorgetting group users: {e}")
            return ServiceResult.error(f"Failed to get group users: {str(e)}")

    def _get_user_contact_address(self, user_uuid: str, channel: str) -> Optional[str]:
        """
        获取用户指定渠道的联系地址

        Args:
            user_uuid: 用户 UUID
            channel: 渠道名称 (discord/email)

        Returns:
            Optional[str]: 联系地址 (Webhook URL 或邮箱地址)
        """
        if self.contact_crud is None:
            return None

        try:
            contacts = self.contact_crud.get_by_user(user_uuid, is_active=True)

            # 确定要查找的联系方式类型
            target_type = None
            if channel in ("discord", "webhook"):
                target_type = CONTACT_TYPES.WEBHOOK
            elif channel == "email":
                target_type = CONTACT_TYPES.EMAIL
            else:
                return None

            # 优先使用主联系方式
            primary_contacts = [c for c in contacts if c.is_primary]
            if primary_contacts:
                contacts = primary_contacts

            # 查找匹配的联系方式
            for contact in contacts:
                if CONTACT_TYPES.from_int(contact.contact_type) == target_type:
                    return contact.address

            return None

        except Exception as e:
            GLOG.ERROR(f"Errorgetting user contact address: {e}")
            return None

    @retry(max_try=3)
    def send_to_user(
        self,
        user_uuid: str,
        content: str,
        title: Optional[str] = None,
        channels: Optional[Union[str, List[str]]] = None,
        content_type: str = "text",
        priority: int = 1,
        **kwargs
    ) -> ServiceResult:
        """
        根据用户联系方式发送通知

        自动查找用户的活跃联系方式，优先使用主联系方式。
        可选传入 channels 参数覆盖自动查找。

        Args:
            user_uuid: 用户 UUID
            content: 通知内容
            title: 通知标题（可选）
            channels: 渠道列表（可选，如果提供则覆盖自动查找）
            content_type: 内容类型
            priority: 优先级
            **kwargs: 其他参数

        Returns:
            ServiceResult: 包含发送结果
        """
        try:
            # 如果没有提供 channels，自动获取用户的可用渠道
            if channels is None:
                channels = self._get_user_channels(user_uuid)

            if not channels:
                return ServiceResult.error(
                    f"No active contact methods found for user {user_uuid}"
                )

            # 发送到所有可用渠道
            return self.send(
                content=content,
                channels=channels,
                user_uuid=user_uuid,
                content_type=content_type,
                priority=priority,
                title=title,
                **{k: v for k, v in kwargs.items() if k != 'channels'}
            )

        except Exception as e:
            GLOG.ERROR(f"Errorsending user notification: {e}")
            return ServiceResult.error(
                f"User notification failed: {str(e)}"
            )

    @retry(max_try=3)
    def send_template_to_user(
        self,
        user_uuid: str,
        template_id: str,
        context: Dict[str, Any],
        priority: int = 1,
        **kwargs
    ) -> ServiceResult:
        """
        使用模板向用户发送通知

        Args:
            user_uuid: 用户 UUID
            template_id: 模板 ID
            context: 模板变量上下文
            priority: 优先级
            **kwargs: 其他参数

        Returns:
            ServiceResult: 包含发送结果
        """
        try:
            # 渲染模板
            rendered_content = self.template_engine.render_from_template_id(
                template_id=template_id,
                context=context,
                strict=False
            )

            # 获取模板信息
            template = self.template_crud.get_by_template_id(template_id)
            if template is None:
                return ServiceResult.error(f"Template not found: {template_id}")

            content_type = template.get_template_type_enum().name.lower()
            title = kwargs.pop("title", None) or template.subject

            # 对于嵌入式模板，解析JSON作为完整的embed对象
            if content_type == "embedded":
                try:
                    import json
                    embed_obj = json.loads(rendered_content)

                    # 将整个embed对象作为embed参数传递
                    kwargs['embed'] = embed_obj

                    # 发送通知（content为空，因为embed包含description）
                    return self.send_to_user(
                        user_uuid=user_uuid,
                        content="",
                        title=title,
                        content_type=content_type,
                        priority=priority,
                        **kwargs
                    )
                except json.JSONDecodeError as e:
                    GLOG.ERROR(f"Failed to parse embedded template JSON: {e}")
                    return ServiceResult.error(f"Invalid embedded template format: {str(e)}")
            else:
                # 文本/Markdown模板直接使用渲染结果
                return self.send_to_user(
                    user_uuid=user_uuid,
                    content=rendered_content,
                    title=title,
                    content_type=content_type,
                    priority=priority,
                    **kwargs
                )

        except ValueError as e:
            GLOG.ERROR(f"Template rendering error: {e}")
            return ServiceResult.error(
                f"Template error: {str(e)}"
            )
        except Exception as e:
            GLOG.ERROR(f"Errorsending template to user: {e}")
            return ServiceResult.error(
                f"Template notification failed: {str(e)}"
            )

    @retry(max_try=3)
    def send_to_group(
        self,
        group_name: str,
        content: str,
        title: Optional[str] = None,
        content_type: str = "text",
        priority: int = 1,
        **kwargs
    ) -> ServiceResult:
        """
        向用户组发送通知

        Args:
            group_name: 用户组名称 (业务层面，如 "traders")
            content: 通知内容
            title: 通知标题（可选）
            content_type: 内容类型
            priority: 优先级
            **kwargs: 其他参数

        Returns:
            ServiceResult: 包含发送结果
        """
        try:
            if self.group_crud is None or self.group_mapping_crud is None:
                return ServiceResult.error(
                    "UserGroupCRUD and UserGroupMappingCRUD required for group notifications"
                )

            # 根据 name 获取 group_uuid
            if not group:
                return ServiceResult.error(f"Group not found: {group_name}")

            group_uuid = group[0].uuid

            # 获取组内所有用户
            if not mappings:
                return ServiceResult.error(f"No users found in group: {group_name}")

            user_uuids = [m.user_uuid for m in mappings]

            # 向所有用户发送通知
            results = []
            success_count = 0

            for user_uuid in user_uuids:
                result = self.send_to_user(
                    user_uuid=user_uuid,
                    content=content,
                    title=title,
                    content_type=content_type,
                    priority=priority,
                    **kwargs
                )

                results.append({
                    "user_uuid": user_uuid,
                    "success": result.is_success,
                    "message_id": result.data.get("message_id") if result.data else None
                })

                if result.is_success:
                    success_count += 1

            GLOG.INFO(f"Group notification sent: {success_count}/{len(user_uuids)} users in group '{group_name}'")

            return ServiceResult.success(
                data={
                    "group_name": group_name,
                    "total_users": len(user_uuids),
                    "success_count": success_count,
                    "results": results
                }
            )

        except Exception as e:
            GLOG.ERROR(f"Errorsending group notification: {e}")
            return ServiceResult.error(
                f"Group notification failed: {str(e)}"
            )

    @retry(max_try=3)
    def send_template_to_group(
        self,
        group_name: str,
        template_id: str,
        context: Dict[str, Any],
        priority: int = 1,
        **kwargs
    ) -> ServiceResult:
        """
        使用模板向用户组发送通知

        Args:
            group_name: 用户组名称
            template_id: 模板 ID
            context: 模板变量上下文
            priority: 优先级
            **kwargs: 其他参数

        Returns:
            ServiceResult: 包含发送结果
        """
        try:
            if self.group_crud is None or self.group_mapping_crud is None:
                return ServiceResult.error(
                    "UserGroupCRUD and UserGroupMappingCRUD required for group notifications"
                )

            # 根据 name 获取 group_uuid
            if not group:
                return ServiceResult.error(f"Group not found: {group_name}")

            group_uuid = group[0].uuid

            # 获取组内所有用户
            if not mappings:
                return ServiceResult.error(f"No users found in group: {group_name}")

            user_uuids = [m.user_uuid for m in mappings]

            # 向所有用户发送模板通知
            results = []
            success_count = 0

            for user_uuid in user_uuids:
                result = self.send_template_to_user(
                    user_uuid=user_uuid,
                    template_id=template_id,
                    context=context,
                    priority=priority,
                    **kwargs
                )

                results.append({
                    "user_uuid": user_uuid,
                    "success": result.is_success,
                    "message_id": result.data.get("message_id") if result.data else None
                })

                if result.is_success:
                    success_count += 1

            GLOG.INFO(f"Group template notification sent: {success_count}/{len(user_uuids)} users in group '{group_name}'")

            return ServiceResult.success(
                data={
                    "group_name": group_name,
                    "template_id": template_id,
                    "total_users": len(user_uuids),
                    "success_count": success_count,
                    "results": results
                }
            )

        except Exception as e:
            GLOG.ERROR(f"Errorsending group template notification: {e}")
            return ServiceResult.error(
                f"Group notification failed: {str(e)}"
            )

    # ==================== 查询方法 ====================

    def get_notification_history(
        self,
        user_uuid: str,
        limit: int = 100,
        status: Optional[int] = None
    ) -> ServiceResult:
        """
        获取用户的通知历史

        Args:
            user_uuid: 用户 UUID
            limit: 最大返回数量
            status: 状态过滤（可选）

        Returns:
            ServiceResult: 包含通知记录列表
        """
        try:
            records = self.record_crud.get_by_user(
                user_uuid=user_uuid,
                limit=limit,
                status=status
            )

            return ServiceResult.success(
                data={
                    "user_uuid": user_uuid,
                    "count": len(records),
                    "records": [r.model_dump() for r in records]
                }
            )

        except Exception as e:
            GLOG.ERROR(f"Errorgetting notification history: {e}")
            return ServiceResult.error(
                f"Failed to get history: {str(e)}"
            )

    def get_failed_notifications(self, limit: int = 50) -> ServiceResult:
        """
        获取失败的通知记录

        Args:
            limit: 最大返回数量

        Returns:
            ServiceResult: 包含失败记录列表
        """
        try:
            records = self.record_crud.get_recent_failed(limit=limit)

            return ServiceResult.success(
                data={
                    "count": len(records),
                    "records": [r.model_dump() for r in records]
                }
            )

        except Exception as e:
            GLOG.ERROR(f"Errorgetting failed notifications: {e}")
            return ServiceResult.error(
                f"Failed to get failed notifications: {str(e)}"
            )

    def get_records_by_user(
        self,
        user_uuid: str,
        limit: int = 100,
        status: Optional[int] = None
    ) -> ServiceResult:
        """
        查询用户的通知记录

        Args:
            user_uuid: 用户 UUID
            limit: 最大返回数量
            status: 可选的状态过滤

        Returns:
            ServiceResult with list of notification records
        """
        try:
            records = self.record_crud.get_by_user(
                user_uuid=user_uuid,
                limit=limit,
                status=status
            )

            return ServiceResult.success(
                data={
                    "records": records,
                    "count": len(records)
                },
                message=f"Found {len(records)} records for user {user_uuid}"
            )

        except Exception as e:
            GLOG.ERROR(f"Errorgetting records for user '{user_uuid}': {e}")
            return ServiceResult.error(
                f"Failed to get records: {str(e)}"
            )

    def get_records_by_template_id(
        self,
        template_id: str,
        limit: int = 100
    ) -> ServiceResult:
        """
        根据模板 ID 查询通知记录

        Args:
            template_id: 模板 ID
            limit: 最大返回数量

        Returns:
            ServiceResult with list of notification records
        """
        try:
            records = self.record_crud.get_by_template_id(
                template_id=template_id,
                limit=limit
            )

            return ServiceResult.success(
                data={
                    "records": records,
                    "count": len(records)
                },
                message=f"Found {len(records)} records for template {template_id}"
            )

        except Exception as e:
            GLOG.ERROR(f"Errorgetting records for template '{template_id}': {e}")
            return ServiceResult.error(
                f"Failed to get records: {str(e)}"
            )

    # ============================================================================
    # 委托方法 - 转发到 WebhookDispatcher（保持外部 API 兼容）
    # ============================================================================

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
        """委托到 WebhookDispatcher.send_webhook_direct"""
        return self._webhook.send_webhook_direct(
            webhook_url=webhook_url,
            content=content,
            title=title,
            color=color,
            fields=fields,
            footer=footer,
            author=author,
            url=url,
            **kwargs
        )

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
        """委托到 WebhookDispatcher.send_discord_webhook"""
        return self._webhook.send_discord_webhook(
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
        """委托到 WebhookDispatcher.send_trading_signal_webhook"""
        return self._webhook.send_trading_signal_webhook(
            webhook_url=webhook_url,
            direction=direction,
            code=code,
            price=price,
            volume=volume,
            strategy=strategy,
            reason=reason,
            footer=footer,
            **kwargs
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
        """委托到 WebhookDispatcher.send_system_notification_webhook"""
        return self._webhook.send_system_notification_webhook(
            webhook_url=webhook_url,
            message_type=message_type,
            content=content,
            details=details,
            footer=footer,
            **kwargs
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
        """委托到 WebhookDispatcher.send_trading_signal"""
        return self._webhook.send_trading_signal(
            user_uuid=user_uuid,
            group_name=group_name,
            group_uuid=group_uuid,
            direction=direction,
            code=code,
            price=price,
            volume=volume,
            strategy_name=strategy_name,
            priority=priority,
            **kwargs
        )

    # ============================================================================
    # Kafka 异步通知和降级逻辑 (FR-019a)
    # ============================================================================

    def send_async(
        self,
        content: str,
        channels: Union[str, List[str]],
        user_uuid: Optional[str] = None,
        template_id: Optional[str] = None,
        content_type: str = "text",
        priority: int = 1,
        title: Optional[str] = None,
        force_async: bool = False,
        **kwargs
    ) -> ServiceResult:
        """
        发送异步通知（优先使用 Kafka，降级时同步发送）

        根据 FR-019a：当 Kafka 不可用时自动降级为同步发送模式。

        Args:
            content: 通知内容
            channels: 渠道名称或列表
            user_uuid: 用户 UUID（可选）
            template_id: 使用的模板 ID（可选）
            content_type: 内容类型
            priority: 优先级
            title: 通知标题（可选）
            force_async: 是否强制异步模式（Kafka 不可用时返回错误而非降级）
            **kwargs: 其他参数

        Returns:
            ServiceResult: 包含发送结果
        """
        # 标准化 channels 参数
        if isinstance(channels, str):
            channels = [channels]

        # 检查 Kafka 组件是否已配置
        if self._kafka_producer is None or self._kafka_health_checker is None:
            if force_async:
                return ServiceResult.error(
                    "Kafka components not configured and force_async=True"
                )
            # Kafka 未配置，直接降级为同步发送
            GLOG.WARN("Kafka components not configured, degrading to sync mode")
            return self.send(
                content=content,
                channels=channels,
                user_uuid=user_uuid,
                template_id=template_id,
                content_type=content_type,
                priority=priority,
                title=title,
                **kwargs
            )

        # 检查 Kafka 是否可用
        should_degrade = self._kafka_health_checker.should_degrade()

        if should_degrade:
            # Kafka 不可用，记录降级事件并降级为同步发送
            health_summary = self._kafka_health_checker.get_health_summary()
            GLOG.WARN(f"Kafka unavailable, degrading to sync mode. Health status: {health_summary}")
            if force_async:
                return ServiceResult.error(
                    f"Kafka unavailable and force_async=True. Status: {health_summary}"
                )
            return self.send(
                content=content,
                channels=channels,
                user_uuid=user_uuid,
                template_id=template_id,
                content_type=content_type,
                priority=priority,
                title=title,
                **kwargs
            )

        # Kafka 可用，尝试异步发送
        try:
            # 构建消息
            message = self._build_kafka_message(
                content=content,
                channels=channels,
                user_uuid=user_uuid,
                template_id=template_id,
                content_type=content_type,
                priority=priority,
                title=title,
                **kwargs
            )

            # 发送到 Kafka（异步，不阻塞）
            success = self._kafka_producer.send_async(KafkaTopics.NOTIFICATIONS, message)
            if not success:
                raise Exception("Kafka send_async returned False")

            # 等待消息发送完成（避免程序退出时的超时错误）
            self._kafka_producer.flush(timeout=2.0)

            GLOG.DEBUG(f"Notification queued via Kafka for user {user_uuid}, channels: {channels}")

            return ServiceResult.success(
                data={
                    "mode": "async",
                    "message_id": f"kafka_{uuid_lib.uuid4().hex}",
                    "channels": channels,
                    "queued": True
                }
            )

        except Exception as e:
            GLOG.ERROR(f"Kafka async send error: {e}, degrading to sync mode")
            if force_async:
                return ServiceResult.error(f"Kafka send failed: {str(e)}")
            return self.send(
                content=content,
                channels=channels,
                user_uuid=user_uuid,
                template_id=template_id,
                content_type=content_type,
                priority=priority,
                title=title,
                **kwargs
            )

    def send_sync(
        self,
        content: str,
        channels: Union[str, List[str]],
        user_uuid: Optional[str] = None,
        template_id: Optional[str] = None,
        content_type: str = "text",
        priority: int = 1,
        title: Optional[str] = None,
        **kwargs
    ) -> ServiceResult:
        """
        同步发送通知（直接调用渠道，不经过 Kafka）

        此方法用于测试或需要立即确认发送结果的场景。
        与 send() 方法的区别：
        - send_sync: 强制同步模式，忽略 Kafka 配置
        - send: 根据 Kafka 配置自动选择异步或同步模式

        Args:
            content: 通知内容
            channels: 渠道名称或列表
            user_uuid: 用户 UUID（可选）
            template_id: 使用的模板 ID（可选）
            content_type: 内容类型
            priority: 优先级
            title: 通知标题（可选）
            **kwargs: 其他参数

        Returns:
            ServiceResult: 包含发送结果
        """
        # 标准化 channels 参数
        if isinstance(channels, str):
            channels = [channels]

        GLOG.DEBUG(f"Sending sync notification for user {user_uuid}, channels: {channels}")

        # 直接调用同步发送方法
        return self.send(
            content=content,
            channels=channels,
            user_uuid=user_uuid,
            template_id=template_id,
            content_type=content_type,
            priority=priority,
            title=title,
            **kwargs
        )

    def _build_kafka_message(
        self,
        content: str,
        channels: List[str],
        user_uuid: Optional[str] = None,
        template_id: Optional[str] = None,
        content_type: str = "text",
        priority: int = 1,
        title: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        构建 Kafka 消息格式（与 NotificationWorker 兼容）

        Args:
            content: 消息内容
            channels: 发送渠道列表
            user_uuid: 用户UUID（可选）
            template_id: 模板ID（可选）
            content_type: 内容类型
            priority: 优先级
            title: 消息标题（可选）
            **kwargs: 其他参数

        Returns:
            Dict: Kafka消息字典

        Worker 期望的消息格式（simple 类型）:
        {
            "message_type": "simple",
            "user_uuid": "user-123",
            "content": "通知内容",
            "title": "标题",
            "channels": ["webhook"],
            "priority": 1
        }
        """
        from datetime import datetime

        # 构建与 Worker 兼容的消息格式
        message = {
            "message_type": "simple",
            "user_uuid": user_uuid,
            "content": content,
            "title": title,
            "channels": channels if isinstance(channels, list) else [channels],
            "priority": priority,
        }

        # 添加可选字段
        if template_id:
            message["template_id"] = template_id

        # 添加其他参数
        if kwargs:
            message["kwargs"] = kwargs

        return message

    def check_kafka_health(self) -> Dict[str, Any]:
        """
        检查 Kafka 健康状态

        Returns:
            Dict: 健康检查结果，如果未配置 KafkaHealthChecker 则返回 None
        """
        if self._kafka_health_checker is None:
            return {
                "configured": False,
                "message": "KafkaHealthChecker not configured"
            }

        return self._kafka_health_checker.check_health()

    def get_kafka_status(self) -> Dict[str, Any]:
        """
        获取 Kafka 状态摘要

        Returns:
            Dict: Kafka 状态信息
        """
        if self._kafka_producer is None or self._kafka_health_checker is None:
            return {
                "enabled": False,
                "message": "Kafka components not configured"
            }

        health = self._kafka_health_checker.check_health()

        return {
            "enabled": True,
            "healthy": health.get("healthy", False),
            "should_degrade": self._kafka_health_checker.should_degrade(),
            "health_summary": self._kafka_health_checker.get_health_summary()
        }
