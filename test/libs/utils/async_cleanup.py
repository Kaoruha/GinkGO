"""
异步数据清理工具

提供通用的异步数据清理功能，支持pytest fixtures中的数据清理操作
"""

import time
from typing import Any, Dict, Optional, Union
from abc import ABC, abstractmethod


class AsyncCleanupMixin(ABC):
    """
    异步清理Mixin类

    为需要异步清理的CRUD类提供标准化的清理接口
    """

    @abstractmethod
    def remove(self, filters: Dict[str, Any]) -> Optional[int]:
        """
        删除数据方法

        Args:
            filters: 过滤条件

        Returns:
            Optional[int]: 删除的记录数（可能为None）
        """
        pass

    @abstractmethod
    def find(self, filters: Dict[str, Any]) -> list:
        """
        查询数据方法

        Args:
            filters: 过滤条件

        Returns:
            list: 查询结果列表
        """
        pass


def async_cleanup_with_wait(
    crud_obj: AsyncCleanupMixin,
    filters: Dict[str, Any],
    entity_name: str = "data",
    max_wait_time: float = 5.0,
    wait_interval: float = 0.5,
    verbose: bool = True
) -> bool:
    """
    异步清理数据并等待确认

    Args:
        crud_obj: 实现了AsyncCleanupMixin的CRUD对象
        filters: 清理过滤条件
        entity_name: 实体名称（用于日志）
        max_wait_time: 最大等待时间（秒）
        wait_interval: 检查间隔（秒）
        verbose: 是否输出详细日志

    Returns:
        bool: 清理是否成功
    """
    if verbose:
        print(f"\n🧹 Cleaning {entity_name}...")

    # 查询清理前的数据数量
    before_count = len(crud_obj.find(filters=filters))
    if verbose and before_count > 0:
        print(f"📊 Cleanup context: {before_count} {entity_name} records found")

    # 执行删除操作
    crud_obj.remove(filters=filters)

    # 等待并确认数据确实被删除
    waited_time = 0

    while waited_time < max_wait_time:
        # 检查是否还有数据
        remaining_data = crud_obj.find(filters=filters)
        remaining_count = len(remaining_data)

        if remaining_count == 0:
            if verbose:
                if before_count > 0:
                    print(f"✓ {entity_name} cleaned successfully: {before_count} → 0 records (waited {waited_time:.1f}s)")
                else:
                    print(f"✓ {entity_name} already clean: 0 records (waited {waited_time:.1f}s)")
            return True
        else:
            if verbose:
                print(f"⏳ Still have {remaining_count} {entity_name} records, waiting...")
            time.sleep(wait_interval)
            waited_time += wait_interval

    # 超时处理
    if verbose:
        print(f"⚠️ Cleanup timeout after {max_wait_time}s, forcing cleanup again...")

    # 强制再次清理
    crud_obj.remove(filters=filters)

    # 最后检查
    final_check = crud_obj.find(filters=filters)
    final_count = len(final_check)

    if final_count == 0:
        if verbose:
            print(f"✓ Forced cleanup completed: {before_count} → 0 records")
        return True
    else:
        if verbose:
            cleaned_count = before_count - final_count
            print(f"⚠️ Cleanup partially completed: {before_count} → {final_count} records ({cleaned_count} cleaned, {final_count} remaining)")
        return False


def create_async_cleanup_fixture(
    crud_class: type,
    filters: Dict[str, Any],
    entity_name: str,
    scope: str = "function"
):
    """
    创建异步清理fixture的工厂函数

    Args:
        crud_class: CRUD类
        filters: 清理过滤条件
        entity_name: 实体名称
        scope: fixture作用域

    Returns:
        pytest fixture函数
    """
    import pytest

    @pytest.fixture(scope=scope, autouse=True)
    def auto_cleanup_fixture():
        """自动清理fixture"""
        crud_obj = crud_class()

        # 测试前清理
        async_cleanup_with_wait(
            crud_obj=crud_obj,
            filters=filters,
            entity_name=entity_name
        )

        yield

        # 测试后清理
        async_cleanup_with_wait(
            crud_obj=crud_obj,
            filters=filters,
            entity_name=f"{entity_name} (post-test)"
        )

    # 设置fixture名称
    auto_cleanup_fixture.__name__ = f"auto_cleanup_{entity_name.lower().replace(' ', '_')}"

    return auto_cleanup_fixture


class AsyncCleanupManager:
    """
    异步清理管理器

    提供更灵活的清理操作管理
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.cleanup_operations = []

    def add_cleanup(
        self,
        crud_obj: AsyncCleanupMixin,
        filters: Dict[str, Any],
        entity_name: str,
        priority: int = 0
    ):
        """
        添加清理操作

        Args:
            crud_obj: CRUD对象
            filters: 过滤条件
            entity_name: 实体名称
            priority: 优先级（数字越小优先级越高）
        """
        self.cleanup_operations.append({
            'crud_obj': crud_obj,
            'filters': filters,
            'entity_name': entity_name,
            'priority': priority
        })

        # 按优先级排序
        self.cleanup_operations.sort(key=lambda x: x['priority'])

    def cleanup_all(self, max_wait_time: float = 5.0, wait_interval: float = 0.5) -> bool:
        """
        执行所有清理操作

        Args:
            max_wait_time: 最大等待时间
            wait_interval: 检查间隔

        Returns:
            bool: 所有清理是否都成功
        """
        if self.verbose:
            print(f"\n🧹 Starting cleanup of {len(self.cleanup_operations)} operations...")

        all_success = True
        total_before_count = 0
        total_cleaned_count = 0
        failed_operations = []

        for operation in self.cleanup_operations:
            # 查询清理前的数据数量
            before_count = len(operation['crud_obj'].find(filters=operation['filters']))
            total_before_count += before_count

            success = async_cleanup_with_wait(
                crud_obj=operation['crud_obj'],
                filters=operation['filters'],
                entity_name=operation['entity_name'],
                max_wait_time=max_wait_time,
                wait_interval=wait_interval,
                verbose=self.verbose
            )

            # 查询清理后的数据数量并计算清理量
            after_count = len(operation['crud_obj'].find(filters=operation['filters']))
            cleaned_count = before_count - after_count
            total_cleaned_count += cleaned_count

            if success:
                if self.verbose and cleaned_count > 0:
                    print(f"  ✓ {operation['entity_name']}: {cleaned_count} records cleaned")
            else:
                failed_operations.append(operation['entity_name'])
                all_success = all_success and success

        if self.verbose:
            if all_success:
                if total_before_count > 0:
                    print(f"✓ All cleanup operations completed successfully: {total_cleaned_count} total records cleaned")
                else:
                    print("✓ All cleanup operations completed: no records to clean")
            else:
                print(f"⚠️ Some cleanup operations failed: {', '.join(failed_operations)}")
                print(f"📊 Summary: {total_cleaned_count}/{total_before_count} records cleaned successfully")

        return all_success

    def clear(self):
        """清空清理操作列表"""
        self.cleanup_operations.clear()