"""
事务监控装饰器

提供 Saga 事务的自动监控和记录功能。
"""
from functools import wraps
from typing import Callable, Optional
from datetime import datetime

from core.logging import logger
from models.transaction import TransactionRecord


class TransactionMonitor:
    """事务监控器

    记录 Saga 事务的执行状态和结果。
    """

    def __init__(self, storage_backend: Optional[Callable] = None):
        """初始化监控器

        Args:
            storage_backend: 事务记录存储函数，接收 TransactionRecord 参数
        """
        self.storage_backend = storage_backend or self._default_storage

    def _default_storage(self, record: TransactionRecord):
        """默认存储实现（仅日志记录）

        可以扩展为存储到数据库或 Redis。
        """
        logger.info(
            f"Transaction {record.transaction_id}: "
            f"status={record.status}, "
            f"steps={len(record.steps)}, "
            f"error={record.error}"
        )

    def record_transaction(self, saga) -> TransactionRecord:
        """记录事务

        Args:
            saga: SagaTransaction 实例

        Returns:
            TransactionRecord: 事务记录
        """
        record = saga.to_record()
        self.storage_backend(record)
        return record

    def monitor(self, entity_type: str = "unknown"):
        """事务监控装饰器

        Args:
            entity_type: 实体类型标识

        Example:
            monitor = TransactionMonitor()

            @monitor.monitor("portfolio")
            async def create_portfolio(data):
                # ... 创建逻辑
                pass
        """

        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                transaction_id = f"{entity_type}:{datetime.now().isoformat()}"

                try:
                    result = await func(*args, **kwargs)

                    # 记录成功事务
                    record = TransactionRecord(
                        transaction_id=transaction_id,
                        entity_type=entity_type,
                        entity_id=getattr(result, 'uuid', None) if hasattr(result, 'uuid') else None,
                        status="completed",
                        steps=[],
                        error=None,
                        created_at=datetime.now(),
                        completed_at=datetime.now()
                    )
                    self.storage_backend(record)

                    return result

                except Exception as e:
                    # 记录失败事务
                    record = TransactionRecord(
                        transaction_id=transaction_id,
                        entity_type=entity_type,
                        entity_id=None,
                        status="failed",
                        steps=[],
                        error=str(e),
                        created_at=datetime.now(),
                        completed_at=datetime.now()
                    )
                    self.storage_backend(record)

                    raise

            return wrapper
        return decorator


# 全局监控实例
transaction_monitor = TransactionMonitor()
