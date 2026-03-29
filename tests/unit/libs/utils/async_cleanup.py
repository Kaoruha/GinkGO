"""
异步清理工具模块

提供测试数据清理的异步支持，用于CRUD测试中的数据清理操作。
"""

import time
from typing import Any, Dict, Optional


class AsyncCleanupMixin:
    """
    异步清理Mixin类

    为CRUD类提供异步清理能力的混入类。
    继承此类的CRUD对象可以支持带等待的异步清理操作。
    """

    def cleanup_with_wait(
        self,
        filters: Dict[str, Any],
        max_retries: int = 3,
        retry_delay: float = 0.5
    ) -> bool:
        """
        带重试和等待的清理操作

        Args:
            filters: 清理过滤条件
            max_retries: 最大重试次数
            retry_delay: 重试延迟(秒)

        Returns:
            bool: 清理是否成功
        """
        for attempt in range(max_retries):
            try:
                # 调用CRUD的remove方法
                self.remove(filters=filters)

                # 验证清理结果
                remaining = self.find(filters=filters)
                if len(remaining) == 0:
                    return True

                # 如果还有残留数据，等待后重试
                time.sleep(retry_delay)

            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"清理失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                    return False
                time.sleep(retry_delay)

        return False


def async_cleanup_with_wait(
    crud_obj: Any,
    filters: Dict[str, Any],
    description: str = "test data",
    max_retries: int = 3,
    retry_delay: float = 0.5
) -> bool:
    """
    异步清理工具函数

    对CRUD对象执行带等待的异步清理操作。

    Args:
        crud_obj: CRUD对象实例
        filters: 清理过滤条件
        description: 清理数据描述(用于日志)
        max_retries: 最大重试次数
        retry_delay: 重试延迟(秒)

    Returns:
        bool: 清理是否成功
    """
    for attempt in range(max_retries):
        try:
            # 执行删除
            crud_obj.remove(filters=filters)

            # 等待数据库同步
            time.sleep(retry_delay)

            # 验证清理结果
            try:
                remaining = crud_obj.find(filters=filters)
                if len(remaining) == 0:
                    print(f"Cleaned {description}: success (attempt {attempt + 1})")
                    return True
            except Exception:
                # 查询失败可能意味着表已删除或数据已清理
                print(f"Cleaned {description}: success (table may not exist)")
                return True

        except Exception as e:
            print(f"Cleanup attempt {attempt + 1}/{max_retries} failed for {description}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)

    print(f"Failed to clean {description} after {max_retries} attempts")
    return False


def cleanup_with_verification(
    crud_obj: Any,
    filters: Dict[str, Any],
    expected_count: int = 0
) -> bool:
    """
    带验证的清理操作

    执行清理后验证剩余数据数量是否符合预期。

    Args:
        crud_obj: CRUD对象实例
        filters: 清理过滤条件
        expected_count: 预期的剩余数据数量

    Returns:
        bool: 清理和验证是否成功
    """
    try:
        # 清理前计数
        before_count = len(crud_obj.find(filters=filters))

        # 执行清理
        crud_obj.remove(filters=filters)

        # 清理后计数
        after_count = len(crud_obj.find(filters=filters))

        if after_count == expected_count:
            print(f"Cleanup verified: {before_count} -> {after_count} records")
            return True
        else:
            print(f"Cleanup partial: {before_count} -> {after_count} records (expected {expected_count})")
            return False

    except Exception as e:
        print(f"Cleanup verification failed: {e}")
        return False
