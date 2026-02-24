# Upstream: Trading Strategies, Analysis Modules (consumers of notifications)
# Downstream: Data Layer (CRUD operations for persistence)
# Role: 通知模块依赖注入容器管理NotificationService/TemplateEngine/Worker等通知系统组件的依赖注入提供通知系统功能支持

from __future__ import annotations  # 启用延迟注解评估，避免运行时类型错误


"""
Notifier Module Container

Provides unified access to notification system components using dependency-injector,
including NotificationService, TemplateEngine, and Workers.

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

# Import CRUDs from data layer (dependencies)
from ginkgo.data.utils import get_crud

# Import services from data layer (dependencies)
from ginkgo.user.services import UserService, UserGroupService

# Use TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from ginkgo.notifier.core.notification_service import NotificationService
    from ginkgo.notifier.core.template_engine import TemplateEngine
    from ginkgo.notifier.workers.notification_worker import NotificationWorker


# ============= LAZY IMPORT FUNCTIONS =============

def _create_template_engine(template_crud):
    """Factory function to create TemplateEngine with lazy import."""
    from ginkgo.notifier.core.template_engine import TemplateEngine
    return TemplateEngine(template_crud=template_crud)


def _create_notification_service(
    template_crud, record_crud, template_engine,
    contact_crud, group_crud, group_mapping_crud,
    user_service, user_group_service,
    kafka_producer, kafka_health_checker
):
    """Factory function to create NotificationService with lazy import."""
    from ginkgo.notifier.core.notification_service import NotificationService
    return NotificationService(
        template_crud=template_crud,
        record_crud=record_crud,
        template_engine=template_engine,
        contact_crud=contact_crud,
        group_crud=group_crud,
        group_mapping_crud=group_mapping_crud,
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
    return KafkaHealthChecker()


class Container(containers.DeclarativeContainer):
    """
    Notification System Container

    Manages notification system business logic services and components.
    Depends on CRUDs and user services from the data layer.
    """

    # ==================== CRUD DEPENDENCIES ====================

    # Notification CRUDs (from data layer)
    notification_template_crud = providers.Singleton(
        get_crud, "notification_template"
    )

    notification_record_crud = providers.Singleton(
        get_crud, "notification_record"
    )

    # User-related CRUDs (from data layer)
    user_contact_crud = providers.Singleton(
        get_crud, "user_contact"
    )

    user_group_crud = providers.Singleton(
        get_crud, "user_group"
    )

    user_group_mapping_crud = providers.Singleton(
        get_crud, "user_group_mapping"
    )

    # ==================== SERVICE DEPENDENCIES ====================

    # User services (from data layer - shared dependencies)
    # These are obtained from the data container
    def _get_user_service() -> UserService:
        """Get UserService from data container."""
        from ginkgo.data.containers import container as data_container
        return data_container.user_service()

    def _get_user_group_service() -> UserGroupService:
        """Get UserGroupService from data container."""
        from ginkgo.data.containers import container as data_container
        return data_container.user_group_service()

    user_service = providers.Singleton(_get_user_service)
    user_group_service = providers.Singleton(_get_user_group_service)

    # ==================== NOTIFICATION SERVICES ====================

    # Kafka Components for async notifications
    kafka_producer = providers.Singleton(_create_kafka_producer)
    kafka_health_checker = providers.Singleton(_create_kafka_health_checker)

    # Template Engine
    template_engine = providers.Singleton(
        _create_template_engine,
        template_crud=notification_template_crud
    )

    # Notification Service
    notification_service = providers.Singleton(
        _create_notification_service,
        template_crud=notification_template_crud,
        record_crud=notification_record_crud,
        template_engine=template_engine,
        contact_crud=user_contact_crud,
        group_crud=user_group_crud,
        group_mapping_crud=user_group_mapping_crud,
        user_service=user_service,
        user_group_service=user_group_service,
        kafka_producer=kafka_producer,
        kafka_health_checker=kafka_health_checker
    )

    # ==================== WORKERS ====================

    # Worker factory (creates worker instances with proper configuration)
    def _create_notification_worker(
        notification_service,
        record_crud,
        group_id: str = "notification_worker_group",
        auto_offset_reset: str = "earliest",
        node_id: str = None
    ) -> NotificationWorker:
        """Factory function to create NotificationWorker."""
        from ginkgo.notifier.workers.notification_worker import NotificationWorker
        return NotificationWorker(
            notification_service=notification_service,
            record_crud=record_crud,
            group_id=group_id,
            auto_offset_reset=auto_offset_reset,
            node_id=node_id
        )

    # Worker provider (Factory pattern - allows creating multiple workers)
    workers = providers.Factory(
        _create_notification_worker,
        notification_service=notification_service,
        record_crud=notification_record_crud
    )


# Singleton instance of the container
container = Container()


# ==================== HELPER FUNCTIONS ====================

def get_notification_service() -> NotificationService:
    """
    Convenience function to get the NotificationService instance.

    Returns:
        NotificationService: The singleton notification service instance
    """
    return container.notification_service()


def get_template_engine() -> TemplateEngine:
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
        "cruds": ["notification_template", "notification_record"]
    }
