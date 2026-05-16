# Upstream: Trading Strategies, Analysis Modules (consumers of notifications)
# Downstream: Data Layer Services (NotificationService, UserService, UserGroupService)
# Role: 通知模块依赖注入容器管理NotificationDeliveryService/TemplateEngine/Worker等通知系统组件的依赖注入提供通知系统功能支持

from __future__ import annotations  # 启用延迟注解评估，避免运行时类型错误


"""
Notifier Module Container

Provides unified access to notification system components using dependency-injector,
including NotificationDeliveryService, TemplateEngine, and Workers.

This container manages the notification system's business logic services,
keeping them separate from the data layer (CRUD operations).

Usage Examples:

    from ginkgo.notifier.containers import container

    # Access notification service
    notification_service = container.notification_service()

    # Access template engine
    template_engine = container.template_engine()

    # Access workers
    worker = container.workers.notification()

    # For dependency injection:
    from dependency_injector.wiring import inject, Provide

    @inject
    def your_function(notification_service = Provide[Container.notification_service]):
        # Use notification_service here
        pass
"""

from dependency_injector import containers, providers
from typing import TYPE_CHECKING

# Import from data layer (dependencies)
from ginkgo.data.utils import get_crud

# Import services from user layer (dependencies)
from ginkgo.user.services import UserService, UserGroupService

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ginkgo.notifier.core.notification_service import NotificationDeliveryService
    from ginkgo.notifier.core.template_engine import TemplateEngine
    from ginkgo.notifier.workers.notification_worker import NotificationWorker


# ============= LAZY IMPORT FUNCTIONS =============

def _create_template_engine(template_crud):
    """Factory function to create TemplateEngine with lazy import."""
    from ginkgo.notifier.core.template_engine import TemplateEngine
    return TemplateEngine(template_crud=template_crud)


def _create_data_notification_service():
    """Factory function to create data layer NotificationService."""
    from ginkgo.data.services.notification_service import NotificationService
    return NotificationService()


def _create_notification_service(
    data_notification_service, template_engine,
    user_service, user_group_service,
    kafka_producer, kafka_health_checker
):
    """Factory function to create NotificationDeliveryService with lazy import."""
    from ginkgo.notifier.core.notification_service import NotificationDeliveryService
    return NotificationDeliveryService(
        notification_service=data_notification_service,
        template_engine=template_engine,
        user_service=user_service,
        user_group_service=user_group_service,
        kafka_producer=kafka_producer,
        kafka_health_checker=kafka_health_checker
    )


def _create_kafka_producer():
    """Factory function to create GinkgoProducer with lazy import."""
    from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
    return GinkgoProducer()


def _create_kafka_health_checker():
    """Factory function to create KafkaHealthChecker with lazy import."""
    from ginkgo.libs.utils.kafka_health_checker import KafkaHealthChecker
    from ginkgo.data.crud import KafkaCRUD
    return KafkaHealthChecker(KafkaCRUD())


class Container(containers.DeclarativeContainer):
    """
    Notification System Container

    Manages notification system business logic services and components.
    Depends on data layer Services and user Services.
    """

    # ==================== CRUD DEPENDENCIES (Template Engine only) ====================

    # Notification template CRUD (for TemplateEngine)
    notification_template_crud = providers.Singleton(
        get_crud, "notification_template"
    )

    # ==================== USER CRUD DEPENDENCIES (for UserService/UserGroupService) ====================

    user_crud = providers.Singleton(get_crud, "user")
    user_contact_crud = providers.Singleton(get_crud, "user_contact")
    user_group_crud = providers.Singleton(get_crud, "user_group")
    user_group_mapping_crud = providers.Singleton(get_crud, "user_group_mapping")

    # ==================== SERVICE DEPENDENCIES ====================

    # User services (constructed from CRUDs)
    user_service = providers.Singleton(
        lambda crud, contact_crud: UserService(crud, contact_crud),
        crud=user_crud,
        contact_crud=user_contact_crud
    )

    user_group_service = providers.Singleton(
        lambda group_crud, mapping_crud: UserGroupService(group_crud, mapping_crud),
        group_crud=user_group_crud,
        mapping_crud=user_group_mapping_crud
    )

    # ==================== NOTIFICATION SERVICES ====================

    # Kafka Components for async notifications
    kafka_producer = providers.Singleton(_create_kafka_producer)
    kafka_health_checker = providers.Singleton(_create_kafka_health_checker)

    # Template Engine (still needs template CRUD directly)
    template_engine = providers.Singleton(
        _create_template_engine,
        template_crud=notification_template_crud
    )

    # Data layer NotificationService (template + record management)
    data_notification_service = providers.Singleton(_create_data_notification_service)

    # Notification Delivery Service (main service, uses data layer NotificationService)
    notification_service = providers.Singleton(
        _create_notification_service,
        data_notification_service=data_notification_service,
        template_engine=template_engine,
        user_service=user_service,
        user_group_service=user_group_service,
        kafka_producer=kafka_producer,
        kafka_health_checker=kafka_health_checker
    )

    # ==================== WORKERS ====================

    # Worker factory (creates worker instances with proper configuration)
    def _create_notification_worker(
        notification_service,
        group_id: str = "notification_worker_group",
        auto_offset_reset: str = "earliest",
        node_id: str = None
    ) -> NotificationWorker:
        """Factory function to create NotificationWorker."""
        from ginkgo.notifier.workers.notification_worker import NotificationWorker
        return NotificationWorker(
            notification_service=notification_service,
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            node_id=node_id
        )

    # Worker provider (Factory pattern - allows creating multiple workers)
    workers = providers.Factory(
        _create_notification_worker,
        notification_service=notification_service
    )


# Singleton instance of the container
container = Container()


# ==================== HELPER FUNCTIONS ====================

def get_notification_service() -> 'NotificationDeliveryService':
    """
    Convenience function to get the NotificationDeliveryService instance.

    Returns:
        NotificationDeliveryService: The singleton notification service instance
    """
    return container.notification_service()


def get_template_engine() -> 'TemplateEngine':
    """
    Convenience function to get the TemplateEngine instance.

    Returns:
        TemplateEngine: The singleton template engine instance
    """
    return container.template_engine()


def get_service_info() -> dict:
    """
    Get information about available notification services.

    Returns:
        dict: Service information including available services and components
    """
    return {
        "services": ["notification_service", "template_engine"],
        "workers": ["notification"],
        "data_services": ["data_notification_service"]
    }
