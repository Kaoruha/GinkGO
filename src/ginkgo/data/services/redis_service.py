"""
Redis缓存服务 - 扁平化架构实现

提供Redis缓存操作、数据同步进度跟踪、任务状态管理等功能
"""

from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
import json

from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.libs.utils.common import time_logger, retry


class RedisService(BaseService):
    """Redis缓存服务 - 直接继承BaseService"""

    def __init__(self, redis_crud=None, **deps):
        """
        初始化Redis服务

        Args:
            redis_crud: RedisCRUD实例，如果为None则自动创建
            **deps: 其他依赖
        """
        if redis_crud is None:
            from ginkgo.data.crud import RedisCRUD
            redis_crud = RedisCRUD()

        super().__init__(crud_repo=redis_crud, **deps)

        # 为了向后兼容，保留redis属性
        self.redis = redis_crud.redis

    # ==================== 标准接口实现 ====================

    def get(self, key: str = None, **filters) -> ServiceResult:
        """获取缓存值"""
        try:
            if key:
                value = self._crud_repo.get(key)
                return ServiceResult.success(
                    data={'value': value},
                    message=f"成功获取键{key}的值"
                )
            else:
                # 如果没有提供key，返回所有键的信息
                pattern = filters.get('pattern', '*')
                keys = self._crud_repo.keys(pattern)
                return ServiceResult.success(
                    data={'keys': keys, 'count': len(keys)},
                    message=f"找到{len(keys)}个匹配键"
                )
        except Exception as e:
            return ServiceResult.error(f"获取缓存失败: {str(e)}")

    def count(self, pattern: str = "*") -> ServiceResult:
        """统计键数量"""
        try:
            keys = self._crud_repo.keys(pattern)
            return ServiceResult.success(
                data={'count': len(keys)},
                message=f"模式{pattern}共有{len(keys)}个键"
            )
        except Exception as e:
            return ServiceResult.error(f"统计键数量失败: {str(e)}")

    def validate(self, key: str, value: Any = None) -> ServiceResult:
        """验证缓存数据"""
        try:
            if not key:
                return ServiceResult.error("键不能为空")

            if not isinstance(key, str):
                return ServiceResult.error("键必须是字符串")

            # 检查键长度
            if len(key) > 250:
                return ServiceResult.error("键长度不能超过250字符")

            return ServiceResult.success(message="缓存数据验证通过")
        except Exception as e:
            return ServiceResult.error(f"缓存数据验证失败: {str(e)}")

    def check_integrity(self, key: str) -> ServiceResult:
        """检查缓存完整性"""
        try:
            # 检查键是否存在
            if not self._crud_repo.exists(key):
                return ServiceResult.error(f"键{key}不存在")

            # 检查值是否可读
            value = self._crud_repo.get(key)

            # 检查TTL
            ttl = self._crud_repo.ttl(key)

            return ServiceResult.success(
                data={'key': key, 'ttl': ttl, 'value_valid': True, 'value_type': type(value).__name__},
                message=f"键{key}完整性检查通过"
            )
        except Exception as e:
            return ServiceResult.error(f"完整性检查失败: {str(e)}")

    @time_logger
    def set(self, key: str, value: Any, ttl: int = 3600) -> ServiceResult:
        """设置缓存值"""
        try:
            # 尝试JSON序列化
            try:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
            except (TypeError, ValueError):
                pass  # 保持原值

            # 设置缓存
            self._crud_repo.set(key, value, ex=ttl)

            return ServiceResult.success(
                data={'key': key, 'ttl': ttl},
                message=f"成功设置键{key}的缓存"
            )
        except Exception as e:
            return ServiceResult.error(f"设置缓存失败: {str(e)}")

    @time_logger
    def delete(self, key: str) -> ServiceResult:
        """删除缓存"""
        try:
            result = self._crud_repo.delete(key)
            return ServiceResult.success(
                data={'deleted': bool(result)},
                message=f"键{key}删除{'成功' if result else '失败'}"
            )
        except Exception as e:
            return ServiceResult.error(f"删除缓存失败: {str(e)}")

    def exists(self, key: str) -> ServiceResult:
        """检查键是否存在"""
        try:
            exists = bool(self._crud_repo.exists(key))
            return ServiceResult.success(
                data={'exists': exists},
                message=f"键{key}{'存在' if exists else '不存在'}"
            )
        except Exception as e:
            return ServiceResult.error(f"检查键存在性失败: {str(e)}")

    # ==================== 业务特定方法 ====================

    # ==================== 数据同步进度管理 ====================
    
    def save_sync_progress(self, code: str, date: datetime, data_type: str = "tick"):
        """
        保存数据同步进度
        
        Args:
            code: 股票代码
            date: 同步的日期
            data_type: 数据类型 (tick, bar, adjustfactor等)
        """
        try:
            cache_key = f"{data_type}_update_{code}"
            date_str = date.strftime("%Y-%m-%d")
            
            self._crud_repo.sadd(cache_key, date_str)
            self._crud_repo.expire(cache_key, 60 * 60 * 24 * 30)  # 30天TTL
            
            self._logger.DEBUG(f"Saved sync progress: {code} - {date_str}")
            return True
        except Exception as e:
            self._logger.ERROR(f"Failed to save sync progress: {e}")
            return False

    def get_sync_progress(self, code: str, data_type: str = "tick") -> Set[str]:
        """
        获取已同步的日期集合

        Args:
            code: 股票代码
            data_type: 数据类型

        Returns:
            已同步日期的字符串集合
        """
        try:
            cache_key = f"{data_type}_update_{code}"
            return self._crud_repo.smembers(cache_key)
        except Exception as e:
            self._logger.ERROR(f"Failed to get sync progress: {e}")
            return set()
    
    def check_date_synced(self, code: str, date: datetime, data_type: str = "tick") -> bool:
        """
        检查指定日期是否已同步
        
        Args:
            code: 股票代码
            date: 要检查的日期
            data_type: 数据类型
            
        Returns:
            True if already synced
        """
        synced_dates = self.get_sync_progress(code, data_type)
        date_str = date.strftime("%Y-%m-%d")
        return date_str in synced_dates
    
    def clear_sync_progress(self, code: str, data_type: str = "tick") -> bool:
        """
        清除指定股票的同步进度缓存
        
        Args:
            code: 股票代码
            data_type: 数据类型
            
        Returns:
            成功返回True
        """
        try:
            cache_key = f"{data_type}_update_{code}"
            deleted = self._crud_repo.delete(cache_key)
            self._logger.INFO(f"Cleared sync progress for {code} ({data_type}), deleted: {deleted}")
            return True
        except Exception as e:
            self._logger.ERROR(f"Failed to clear sync progress: {e}")
            return False

    def clear_all_sync_progress(self, data_type: str = None) -> int:
        """
        清除所有同步进度缓存
        
        Args:
            data_type: 数据类型，如果提供则只清除该类型的缓存，否则清除所有类型
            
        Returns:
            清除的缓存数量
        """
        try:
            if data_type:
                cache_pattern = f"{data_type}_update_*"
            else:
                cache_pattern = "*_update_*"
            
            deleted = self._crud_repo.delete_pattern(cache_pattern)
            self._logger.INFO(f"Cleared {deleted} sync progress cache entries with pattern '{cache_pattern}'")
            return deleted
        except Exception as e:
            self._logger.ERROR(f"Failed to clear all sync progress cache: {e}")
            return 0
    
    def get_progress_summary(self, code: str, start_date: datetime, end_date: datetime, 
                           data_type: str = "tick") -> Dict[str, Any]:
        """
        获取指定日期范围的同步进度摘要
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            data_type: 数据类型
            
        Returns:
            包含进度信息的字典
        """
        synced_dates = self.get_sync_progress(code, data_type)
        
        total_dates = 0
        synced_count = 0
        missing_dates = []
        
        current_date = start_date
        while current_date <= end_date:
            total_dates += 1
            date_str = current_date.strftime("%Y-%m-%d")
            
            if date_str in synced_dates:
                synced_count += 1
            else:
                missing_dates.append(current_date.date())
            
            current_date += timedelta(days=1)
        
        return {
            "code": code,
            "data_type": data_type,
            "total_dates": total_dates,
            "synced_count": synced_count,
            "missing_count": len(missing_dates),
            "missing_dates": missing_dates,
            "completion_rate": synced_count / total_dates if total_dates > 0 else 0,
            "first_missing_date": missing_dates[0] if missing_dates else None
        }

    # ==================== 任务状态管理 ====================
    
    def save_task_status(self, task_id: str, status: str, metadata: Dict[str, Any] = None):
        """
        保存任务状态
        
        Args:
            task_id: 任务ID
            status: 任务状态 (RUNNING, SUCCESS, FAILED, PENDING)
            metadata: 任务元数据
        """
        try:
            cache_key = f"task_status_{task_id}"
            task_data = {
                "task_id": task_id,
                "status": status,
                "updated_at": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            self._crud_repo.set(cache_key, task_data, 60 * 60 * 24 * 7)  # 7天TTL
            return True
        except Exception as e:
            self._logger.ERROR(f"Failed to save task status: {e}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        try:
            cache_key = f"task_status_{task_id}"
            return self._crud_repo.get(cache_key)
        except Exception as e:
            self._logger.ERROR(f"Failed to get task status: {e}")
            return None

    # ==================== 通用缓存操作 ====================
    
    def set_cache(self, key: str, value: Any, expire_seconds: int = 3600):
        """设置缓存"""
        try:
            return self._crud_repo.set(key, value, expire_seconds)
        except Exception as e:
            self._logger.ERROR(f"Failed to set cache: {e}")
            return False
    
    def get_cache(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            return self._crud_repo.get(key)
        except Exception as e:
            self._logger.ERROR(f"Failed to get cache: {e}")
            return None
    
    def delete_cache(self, key: str) -> bool:
        """删除缓存"""
        try:
            return self._crud_repo.delete(key)
        except Exception as e:
            self._logger.ERROR(f"Failed to delete cache: {e}")
            return False
    
    def exists(self, key: str) -> ServiceResult:
        """检查key是否存在"""
        try:
            key_exists = self._crud_repo.exists(key)
            return ServiceResult.success(
                data=key_exists,  # 直接封装bool值
                message=f"Key '{key}' exists: {key_exists}"
            )
        except Exception as e:
            self._logger.ERROR(f"Failed to check key existence: {e}")
            return ServiceResult.error(f"Failed to check key existence: {str(e)}")

    # ==================== 进程管理 ====================
    
    def register_main_process(self, pid: int) -> bool:
        """
        注册主控进程
        
        Args:
            pid: 进程ID
            
        Returns:
            注册是否成功
        """
        try:
            maincontrol_key = "ginkgo_maincontrol"
            success = self._crud_repo.set(maincontrol_key, str(pid))
            if success:
                self._logger.INFO(f"Registered main process: {pid}")
            return success
        except Exception as e:
            self._logger.ERROR(f"Failed to register main process: {e}")
            return False
    
    def unregister_main_process(self) -> bool:
        """
        注销主控进程
        
        Returns:
            注销是否成功
        """
        try:
            maincontrol_key = "ginkgo_maincontrol"
            success = self._crud_repo.delete(maincontrol_key)
            if success:
                self._logger.INFO("Unregistered main process")
            return success
        except Exception as e:
            self._logger.ERROR(f"Failed to unregister main process: {e}")
            return False
    
    def get_main_process_pid(self) -> Optional[int]:
        """
        获取主控进程PID
        
        Returns:
            主控进程PID，如果不存在返回None
        """
        try:
            maincontrol_key = "ginkgo_maincontrol"
            pid_str = self._crud_repo.get(maincontrol_key)
            return int(pid_str) if pid_str else None
        except Exception as e:
            self._logger.ERROR(f"Failed to get main process PID: {e}")
            return None
    
    def register_watchdog(self, pid: int) -> bool:
        """
        注册看门狗进程
        
        Args:
            pid: 看门狗进程ID
            
        Returns:
            注册是否成功
        """
        try:
            watchdog_key = "ginkgo_watchdog"
            success = self._crud_repo.set(watchdog_key, str(pid))
            if success:
                self._logger.INFO(f"Registered watchdog process: {pid}")
            return success
        except Exception as e:
            self._logger.ERROR(f"Failed to register watchdog: {e}")
            return False
    
    def unregister_watchdog(self) -> bool:
        """
        注销看门狗进程
        
        Returns:
            注销是否成功
        """
        try:
            watchdog_key = "ginkgo_watchdog"
            success = self._crud_repo.delete(watchdog_key)
            if success:
                self._logger.INFO("Unregistered watchdog process")
            return success
        except Exception as e:
            self._logger.ERROR(f"Failed to unregister watchdog: {e}")
            return False
    
    def get_watchdog_pid(self) -> Optional[int]:
        """
        获取看门狗进程PID
        
        Returns:
            看门狗进程PID，如果不存在返回None
        """
        try:
            watchdog_key = "ginkgo_watchdog"
            pid_str = self._crud_repo.get(watchdog_key)
            return int(pid_str) if pid_str else None
        except Exception as e:
            self._logger.ERROR(f"Failed to get watchdog PID: {e}")
            return None
    
    def add_worker_to_pool(self, pid: int, pool_type: str = "general") -> bool:
        """
        将工作进程添加到进程池
        
        Args:
            pid: 工作进程ID
            pool_type: 进程池类型 ('general' 或 'data_worker')
            
        Returns:
            添加是否成功
        """
        try:
            if pool_type == "data_worker":
                general_pool = "ginkgo_thread_pool"
                data_pool = "ginkgo_dataworker_pool"
                # 数据工作进程需要加入两个池
                success1 = self._crud_repo.sadd(general_pool, str(pid))
                success2 = self._crud_repo.sadd(data_pool, str(pid))
                success = success1 and success2
            else:
                pool_key = "ginkgo_thread_pool"
                success = self._crud_repo.sadd(pool_key, str(pid)) > 0
            
            if success:
                self._logger.DEBUG(f"Added worker {pid} to {pool_type} pool")
            return success
        except Exception as e:
            self._logger.ERROR(f"Failed to add worker to pool: {e}")
            return False
    
    def remove_worker_from_pool(self, pid: int, pool_type: str = "general") -> bool:
        """
        从进程池中移除工作进程
        
        Args:
            pid: 工作进程ID
            pool_type: 进程池类型 ('general' 或 'data_worker')
            
        Returns:
            移除是否成功
        """
        try:
            if pool_type == "data_worker":
                general_pool = "ginkgo_thread_pool"
                data_pool = "ginkgo_dataworker_pool"
                # 从两个池中移除
                success1 = self._crud_repo.srem(general_pool, str(pid))
                success2 = self._crud_repo.srem(data_pool, str(pid))
                success = success1 or success2  # 只要有一个成功就算成功
            else:
                pool_key = "ginkgo_thread_pool"
                success = self._crud_repo.srem(pool_key, str(pid)) > 0
            
            if success:
                self._logger.DEBUG(f"Removed worker {pid} from {pool_type} pool")
            return success
        except Exception as e:
            self._logger.ERROR(f"Failed to remove worker from pool: {e}")
            return False
    
    def get_worker_pool_size(self, pool_type: str = "general") -> int:
        """
        获取工作进程池大小
        
        Args:
            pool_type: 进程池类型 ('general' 或 'data_worker')
            
        Returns:
            进程池中的工作进程数量
        """
        try:
            if pool_type == "data_worker":
                pool_key = "ginkgo_dataworker_pool"
            else:
                pool_key = "ginkgo_thread_pool"
            
            return self._crud_repo.scard(pool_key)
        except Exception as e:
            self._logger.ERROR(f"Failed to get worker pool size: {e}")
            return 0
    
    def get_all_workers(self, pool_type: str = "general") -> Set[int]:
        """
        获取进程池中的所有工作进程PID
        
        Args:
            pool_type: 进程池类型 ('general' 或 'data_worker')
            
        Returns:
            工作进程PID集合
        """
        try:
            if pool_type == "data_worker":
                pool_key = "ginkgo_dataworker_pool"
            else:
                pool_key = "ginkgo_thread_pool"
            
            pid_strings = self._crud_repo.smembers(pool_key)
            return {int(pid_str) for pid_str in pid_strings if pid_str.isdigit()}
        except Exception as e:
            self._logger.ERROR(f"Failed to get all workers: {e}")
            return set()

    # ==================== 任务管理 ====================
    
    def set_task_status(self, task_key: str, status_data: Dict[str, Any], ttl: int = 3600) -> bool:
        """
        设置任务状态
        
        Args:
            task_key: 任务键名
            status_data: 任务状态数据
            ttl: 过期时间（秒）
            
        Returns:
            设置是否成功
        """
        try:
            import time
            
            # 添加时间戳
            status_data['updated_at'] = time.time()
            
            # 直接存储dict，让RedisCRUD自动处理JSON序列化
            success = self._crud_repo.set(task_key, status_data, ttl)
            if success:
                self._logger.DEBUG(f"Set task status: {task_key}")
            return success
        except Exception as e:
            self._logger.ERROR(f"Failed to set task status: {e}")
            return False
    
    def get_task_status_by_key(self, task_key: str) -> Optional[Dict[str, Any]]:
        """
        通过完整键名获取任务状态（高级接口）
        
        Args:
            task_key: 完整的任务键名
            
        Returns:
            任务状态数据，如果不存在返回None
        """
        try:
            # 直接获取dict，RedisCRUD自动处理JSON反序列化
            status_data = self._crud_repo.get(task_key)
            return status_data
        except Exception as e:
            self._logger.ERROR(f"Failed to get task status by key: {e}")
            return None
    
    def update_task_status(self, task_key: str, updates: Dict[str, Any]) -> bool:
        """
        更新任务状态（部分更新）
        
        Args:
            task_key: 任务键名
            updates: 要更新的字段
            
        Returns:
            更新是否成功
        """
        try:
            current_status = self.get_task_status_by_key(task_key)
            if current_status is None:
                # 如果任务不存在，创建新任务
                return self.set_task_status(task_key, updates)
            
            # 合并更新
            current_status.update(updates)
            return self.set_task_status(task_key, current_status)
        except Exception as e:
            self._logger.ERROR(f"Failed to update task status: {e}")
            return False
    
    def cleanup_dead_tasks(self, max_idle_time: int = 3600) -> int:
        """
        清理死掉的任务（超过最大空闲时间的任务）
        
        Args:
            max_idle_time: 最大空闲时间（秒）
            
        Returns:
            清理的任务数量
        """
        try:
            import time
            
            current_time = time.time()
            cleaned_count = 0
            
            # 获取所有任务键
            task_keys = self._crud_repo.keys("ginkgo_task_*")
            
            for task_key in task_keys:
                task_status = self.get_task_status_by_key(task_key)
                if task_status and 'updated_at' in task_status:
                    last_update = task_status['updated_at']
                    if current_time - last_update > max_idle_time:
                        # 任务超过最大空闲时间，删除
                        if self._crud_repo.delete(task_key):
                            cleaned_count += 1
                            self._logger.DEBUG(f"Cleaned dead task: {task_key}")
            
            if cleaned_count > 0:
                self._logger.INFO(f"Cleaned {cleaned_count} dead tasks")
            
            return cleaned_count
        except Exception as e:
            self._logger.ERROR(f"Failed to cleanup dead tasks: {e}")
            return 0
    
    def get_active_tasks(self, pattern: str = "ginkgo_task_*") -> Dict[str, Dict[str, Any]]:
        """
        获取所有活跃任务
        
        Args:
            pattern: 任务键匹配模式
            
        Returns:
            活跃任务字典 {task_key: task_status}
        """
        try:
            active_tasks = {}
            task_keys = self._crud_repo.keys(pattern)
            
            for task_key in task_keys:
                task_status = self.get_task_status_by_key(task_key)
                if task_status:
                    active_tasks[task_key] = task_status
            
            return active_tasks
        except Exception as e:
            self._logger.ERROR(f"Failed to get active tasks: {e}")
            return {}
    
    def set_process_heartbeat(self, pid: int, status: str = "alive", metadata: Dict[str, Any] = None) -> bool:
        """
        设置进程心跳
        
        Args:
            pid: 进程ID
            status: 进程状态
            metadata: 额外元数据
            
        Returns:
            设置是否成功
        """
        try:
            import time
            
            heartbeat_key = f"ginkgo_heartbeat_{pid}"
            heartbeat_data = {
                "pid": pid,
                "status": status,
                "timestamp": time.time(),
                "metadata": metadata or {}
            }
            
            # 心跳信息30秒过期
            return self.set_task_status(heartbeat_key, heartbeat_data, ttl=30)
        except Exception as e:
            self._logger.ERROR(f"Failed to set process heartbeat: {e}")
            return False
    
    def get_process_heartbeat(self, pid: int) -> Optional[Dict[str, Any]]:
        """
        获取进程心跳信息
        
        Args:
            pid: 进程ID
            
        Returns:
            心跳信息，如果不存在返回None
        """
        try:
            heartbeat_key = f"ginkgo_heartbeat_{pid}"
            return self.get_task_status_by_key(heartbeat_key)
        except Exception as e:
            self._logger.ERROR(f"Failed to get process heartbeat: {e}")
            return None

    # ==================== 系统监控 ====================
    
    def get_redis_info(self) -> Dict[str, Any]:
        """获取Redis服务器信息"""
        try:
            return self._crud_repo.info()
        except Exception as e:
            self._logger.ERROR(f"Failed to get Redis info: {e}")
            return {"connected": False, "error": str(e)}

    # ==================== 函数缓存管理 ====================
    
    def set_function_cache(self, func_name: str, cache_key: str, result: Any, 
                          expiration_seconds: int = 3600) -> bool:
        """
        设置函数缓存
        
        Args:
            func_name: 函数名称
            cache_key: 缓存键（包含参数信息）
            result: 缓存结果
            expiration_seconds: 过期时间（秒）
            
        Returns:
            设置是否成功
        """
        try:
            import json
            import time
            
            full_cache_key = f"ginkgo_func_cache_{func_name}_{cache_key}"
            cache_data = {
                "result": result,
                "timestamp": time.time(),
                "func_name": func_name
            }
            
            # 序列化并存储
            cache_json = json.dumps(cache_data, default=str)
            success = self._crud_repo.set(full_cache_key, cache_json, expiration_seconds)
            
            if success:
                self._logger.DEBUG(f"Set function cache: {func_name} -> {cache_key}")
            return success
        except Exception as e:
            self._logger.ERROR(f"Failed to set function cache: {e}")
            return False
    
    def get_function_cache(self, func_name: str, cache_key: str) -> Optional[Any]:
        """
        获取函数缓存
        
        Args:
            func_name: 函数名称
            cache_key: 缓存键（包含参数信息）
            
        Returns:
            缓存的结果，如果不存在或过期返回None
        """
        try:
            import json
            
            full_cache_key = f"ginkgo_func_cache_{func_name}_{cache_key}"
            cache_json = self._crud_repo.get(full_cache_key)
            
            if cache_json:
                cache_data = json.loads(cache_json)
                return cache_data.get("result")
            
            return None
        except Exception as e:
            self._logger.ERROR(f"Failed to get function cache: {e}")
            return None
    
    def clear_function_cache(self, func_name: str = None, pattern: str = None) -> int:
        """
        清除函数缓存
        
        Args:
            func_name: 特定函数名称，如果提供则只清除该函数的缓存
            pattern: 自定义匹配模式，如果提供则覆盖func_name
            
        Returns:
            清除的缓存数量
        """
        try:
            if pattern:
                cache_pattern = pattern
            elif func_name:
                cache_pattern = f"ginkgo_func_cache_{func_name}_*"
            else:
                cache_pattern = "ginkgo_func_cache_*"
            
            cache_keys = self._crud_repo.keys(cache_pattern)
            cleared_count = 0
            
            for cache_key in cache_keys:
                if self._crud_repo.delete(cache_key):
                    cleared_count += 1
            
            if cleared_count > 0:
                self._logger.INFO(f"Cleared {cleared_count} function cache entries")
            
            return cleared_count
        except Exception as e:
            self._logger.ERROR(f"Failed to clear function cache: {e}")
            return 0
    
    def get_function_cache_stats(self, func_name: str = None) -> Dict[str, Any]:
        """
        获取函数缓存统计信息
        
        Args:
            func_name: 特定函数名称，如果提供则只统计该函数的缓存
            
        Returns:
            缓存统计信息
        """
        try:
            import json
            import time
            
            if func_name:
                cache_pattern = f"ginkgo_func_cache_{func_name}_*"
            else:
                cache_pattern = "ginkgo_func_cache_*"
            
            cache_keys = self._crud_repo.keys(cache_pattern)
            
            stats = {
                "total_entries": len(cache_keys),
                "by_function": {},
                "total_size_estimate": 0,
                "oldest_entry": None,
                "newest_entry": None
            }
            
            current_time = time.time()
            
            for cache_key in cache_keys:
                try:
                    cache_json = self._crud_repo.get(cache_key)
                    if cache_json:
                        cache_data = json.loads(cache_json)
                        func_name_from_cache = cache_data.get("func_name", "unknown")
                        timestamp = cache_data.get("timestamp", current_time)
                        
                        # 按函数统计
                        if func_name_from_cache not in stats["by_function"]:
                            stats["by_function"][func_name_from_cache] = {
                                "count": 0,
                                "size_estimate": 0
                            }
                        
                        stats["by_function"][func_name_from_cache]["count"] += 1
                        entry_size = len(cache_json)
                        stats["by_function"][func_name_from_cache]["size_estimate"] += entry_size
                        stats["total_size_estimate"] += entry_size
                        
                        # 时间统计
                        if stats["oldest_entry"] is None or timestamp < stats["oldest_entry"]:
                            stats["oldest_entry"] = timestamp
                        if stats["newest_entry"] is None or timestamp > stats["newest_entry"]:
                            stats["newest_entry"] = timestamp
                            
                except Exception as cache_parse_error:
                    self._logger.WARN(f"Failed to parse cache entry {cache_key}: {cache_parse_error}")
                    continue
            
            return stats
        except Exception as e:
            self._logger.ERROR(f"Failed to get function cache stats: {e}")
            return {"total_entries": 0, "by_function": {}, "error": str(e)}
    
    def cleanup_expired_function_cache(self) -> int:
        """
        清理过期的函数缓存条目
        
        Note: Redis会自动清理过期的键，但这个方法可以用于手动检查
        
        Returns:
            检查的缓存条目数量
        """
        try:
            cache_pattern = "ginkgo_func_cache_*"
            cache_keys = self._crud_repo.keys(cache_pattern)
            
            checked_count = 0
            for cache_key in cache_keys:
                # 尝试获取TTL，如果返回-2则表示键已过期或不存在
                ttl = self._crud_repo.ttl(cache_key)
                if ttl == -2:  # Key doesn't exist (expired)
                    checked_count += 1
                    
            self._logger.DEBUG(f"Checked {len(cache_keys)} function cache entries, {checked_count} were expired")
            return checked_count
        except Exception as e:
            self._logger.ERROR(f"Failed to cleanup expired function cache: {e}")
            return 0
    
    def is_function_cache_enabled(self) -> bool:
        """
        检查函数缓存功能是否可用
        
        Returns:
            True if function caching is available
        """
        try:
            # 简单测试Redis连接和基本操作
            test_key = "ginkgo_func_cache_test"
            test_value = "test"
            
            success = self._crud_repo.set(test_key, test_value, 1)  # 1秒过期
            if success:
                retrieved = self._crud_repo.get(test_key)
                self._crud_repo.delete(test_key)  # 清理测试键
                return retrieved == test_value
            
            return False
        except Exception as e:
            self._logger.ERROR(f"Function cache availability check failed: {e}")
            return False

    # ==================== 线程池管理 ====================
    
    def scan_thread_pool(self, pool_name: str = "ginkgo_thread_pool", cursor: int = 0, count: int = 100) -> tuple:
        """
        扫描线程池成员
        
        Args:
            pool_name: 线程池名称
            cursor: 扫描游标
            count: 每次扫描数量
            
        Returns:
            tuple: (下一个游标, 成员列表)
        """
        try:
            return self._crud_repo.sscan(pool_name, cursor=cursor, count=count)
        except Exception as e:
            self._logger.ERROR(f"Failed to scan thread pool {pool_name}: {e}")
            return (0, [])
    
    def scan_worker_pool(self, pool_name: str = "ginkgo_dataworker_pool", cursor: int = 0, count: int = 100) -> tuple:
        """
        扫描工作进程池成员
        
        Args:
            pool_name: 工作进程池名称
            cursor: 扫描游标
            count: 每次扫描数量
            
        Returns:
            tuple: (下一个游标, 成员列表)
        """
        try:
            return self._crud_repo.sscan(pool_name, cursor=cursor, count=count)
        except Exception as e:
            self._logger.ERROR(f"Failed to scan worker pool {pool_name}: {e}")
            return (0, [])
    
    def add_to_thread_list(self, list_name: str, value: str) -> int:
        """
        向线程列表添加元素
        
        Args:
            list_name: 列表名称
            value: 要添加的值
            
        Returns:
            int: 添加后列表长度
        """
        try:
            return self._crud_repo.lpush(list_name, value)
        except Exception as e:
            self._logger.ERROR(f"Failed to add to thread list {list_name}: {e}")
            return 0
    
    def remove_from_thread_list(self, list_name: str, value: str, count: int = 0) -> int:
        """
        从线程列表移除元素
        
        Args:
            list_name: 列表名称
            value: 要移除的值
            count: 移除数量（0表示移除所有）
            
        Returns:
            int: 实际移除的元素数量
        """
        try:
            return self._crud_repo.lrem(list_name, count, value)
        except Exception as e:
            self._logger.ERROR(f"Failed to remove from thread list {list_name}: {e}")
            return 0
    
    def pop_from_thread_list(self, list_name: str) -> Optional[str]:
        """
        从线程列表弹出元素
        
        Args:
            list_name: 列表名称
            
        Returns:
            Optional[str]: 弹出的元素
        """
        try:
            return self._crud_repo.lpop(list_name)
        except Exception as e:
            self._logger.ERROR(f"Failed to pop from thread list {list_name}: {e}")
            return None
    
    def get_thread_list_length(self, list_name: str) -> int:
        """
        获取线程列表长度
        
        Args:
            list_name: 列表名称
            
        Returns:
            int: 列表长度
        """
        try:
            return self._crud_repo.llen(list_name)
        except Exception as e:
            self._logger.ERROR(f"Failed to get thread list length {list_name}: {e}")
            return 0
    
    def clean_worker_status_keys(self, worker_pids: List[str]) -> int:
        """
        清理工作进程状态键
        
        Args:
            worker_pids: 工作进程PID列表
            
        Returns:
            int: 清理的键数量
        """
        try:
            cleaned_count = 0
            for pid in worker_pids:
                status_key = f"ginkgo_worker_status_{pid}"
                if self._crud_repo.delete(status_key):
                    cleaned_count += 1
                    
            if cleaned_count > 0:
                self._logger.DEBUG(f"Cleaned {cleaned_count} worker status keys")
            return cleaned_count
        except Exception as e:
            self._logger.ERROR(f"Failed to clean worker status keys: {e}")
            return 0
    
    def add_to_thread_pool_set(self, pool_name: str, pid: str) -> bool:
        """
        向线程池Set添加PID
        
        Args:
            pool_name: 池名称
            pid: 进程ID
            
        Returns:
            bool: 是否成功添加
        """
        try:
            result = self._crud_repo.sadd(pool_name, str(pid))
            return result > 0
        except Exception as e:
            self._logger.ERROR(f"Failed to add to thread pool set {pool_name}: {e}")
            return False
    
    def remove_from_thread_pool_set(self, pool_name: str, pid: str) -> bool:
        """
        从线程池Set移除PID
        
        Args:
            pool_name: 池名称
            pid: 进程ID
            
        Returns:
            bool: 是否成功移除
        """
        try:
            result = self._crud_repo.srem(pool_name, str(pid))
            return result > 0
        except Exception as e:
            self._logger.ERROR(f"Failed to remove from thread pool set {pool_name}: {e}")
            return False
    
    def get_thread_from_cache(self, cache_key: str) -> Optional[str]:
        """
        从缓存获取线程信息
        
        Args:
            cache_key: 缓存键
            
        Returns:
            Optional[str]: 线程信息
        """
        try:
            return self._crud_repo.get(cache_key)
        except Exception as e:
            self._logger.ERROR(f"Failed to get thread from cache {cache_key}: {e}")
            return None
    
    def set_thread_cache(self, cache_key: str, value: str) -> bool:
        """
        设置线程缓存
        
        Args:
            cache_key: 缓存键
            value: 缓存值
            
        Returns:
            bool: 是否设置成功
        """
        try:
            return self._crud_repo.set(cache_key, value)
        except Exception as e:
            self._logger.ERROR(f"Failed to set thread cache {cache_key}: {e}")
            return False

    # ==================== Redis状态重置 ====================

    def clear_all_cache(self, pattern: str = "*", exclude_patterns: List[str] = None) -> ServiceResult:
        """
        清理所有缓存的键，用于重置Redis状态

        Args:
            pattern: 键匹配模式，默认为 "*" 清理所有键
            exclude_patterns: 要排除的键模式列表，保护重要数据

        Returns:
            ServiceResult: 包含清理统计信息

        Example:
            # 清理所有键
            result = redis_service.clear_all_cache()

            # 清理特定模式的键，排除重要数据
            result = redis_service.clear_all_cache(
                pattern="*",
                exclude_patterns=["*_config_*", "*_auth_*"]
            )
        """
        try:
            if exclude_patterns is None:
                exclude_patterns = []

            # 获取所有匹配的键
            all_keys = self._crud_repo.keys(pattern)

            # 过滤掉要排除的键
            import fnmatch
            excluded_keys = set()
            for exclude_pattern in exclude_patterns:
                for key in all_keys:
                    if fnmatch.fnmatch(key, exclude_pattern):
                        excluded_keys.add(key)

            keys_to_delete = [key for key in all_keys if key not in excluded_keys]

            deleted_count = 0
            failed_count = 0

            # 批量删除键
            for key in keys_to_delete:
                try:
                    if self._crud_repo.delete(key):
                        deleted_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    self._logger.WARN(f"Failed to delete key {key}: {e}")

            # 记录清理结果
            self._logger.INFO(f"Redis cache cleared: {deleted_count} deleted, {failed_count} failed, {len(excluded_keys)} excluded")

            return ServiceResult.success(
                data={
                    "total_keys_found": len(all_keys),
                    "keys_excluded": len(excluded_keys),
                    "keys_to_delete": len(keys_to_delete),
                    "deleted_count": deleted_count,
                    "failed_count": failed_count,
                    "exclude_patterns": exclude_patterns
                },
                message=f"Redis缓存清理完成: 删除{deleted_count}个键，排除{len(excluded_keys)}个键"
            )

        except Exception as e:
            self._logger.ERROR(f"Failed to clear Redis cache: {e}")
            return ServiceResult.error(f"清理Redis缓存失败: {str(e)}")

    def clear_ginkgo_cache_only(self) -> ServiceResult:
        """
        仅清理Ginkgo相关的缓存，保护其他应用数据

        Returns:
            ServiceResult: 包含清理统计信息
        """
        # Ginkgo相关的键模式
        ginkgo_patterns = [
            "ginkgo_*",          # 通用ginkgo前缀
            "*_update_*",        # 同步进度缓存
            "task_status_*",     # 任务状态缓存
            "ginkgo_func_cache_*",  # 函数缓存
            "ginkgo_heartbeat_*",   # 进程心跳
            "ginkgo_thread_pool",   # 线程池
            "ginkgo_dataworker_pool",  # 数据工作池
            "test_*",            # 测试键
        ]

        return self.clear_all_cache(
            pattern="ginkgo_*",
            exclude_patterns=[]
        )

    def get_cache_statistics(self) -> ServiceResult:
        """
        获取缓存统计信息，用于监控和诊断

        Returns:
            ServiceResult: 包含详细的缓存统计信息
        """
        try:
            # 获取所有键
            all_keys = self._crud_repo.keys("*")
            total_keys = len(all_keys)

            # 按前缀分组统计
            prefix_stats = {}
            ginkgo_keys = []

            for key in all_keys:
                # 统计Ginkgo相关键
                if key.startswith("ginkgo_") or key.startswith("task_status_") or key.startswith("test_"):
                    ginkgo_keys.append(key)

                # 按前缀分组
                prefix = key.split('_')[0] if '_' in key else 'no_prefix'
                if prefix not in prefix_stats:
                    prefix_stats[prefix] = {"count": 0, "size_estimate": 0}
                prefix_stats[prefix]["count"] += 1

            # 获取内存使用情况
            redis_info = self._crud_repo.info()
            memory_info = {
                "used_memory": redis_info.get("used_memory", 0),
                "used_memory_human": redis_info.get("used_memory_human", "0B"),
                "maxmemory": redis_info.get("maxmemory", 0),
            }

            return ServiceResult.success(
                data={
                    "total_keys": total_keys,
                    "ginkgo_keys_count": len(ginkgo_keys),
                    "ginkgo_keys": ginkgo_keys,
                    "other_keys_count": total_keys - len(ginkgo_keys),
                    "prefix_statistics": prefix_stats,
                    "memory_info": memory_info,
                    "redis_info": redis_info
                },
                message=f"缓存统计: 共{total_keys}个键，其中{len(ginkgo_keys)}个Ginkgo键"
            )

        except Exception as e:
            self._logger.ERROR(f"Failed to get cache statistics: {e}")
            return ServiceResult.error(f"获取缓存统计失败: {str(e)}")

    def vacuum_redis(self, aggressive: bool = False) -> ServiceResult:
        """
        Redis数据库清理和优化

        Args:
            aggressive: 是否进行激进清理（包括可能影响性能的键）

        Returns:
            ServiceResult: 包含清理结果
        """
        try:
            # 首先获取统计信息
            stats_result = self.get_cache_statistics()
            if not stats_result.success:
                return stats_result

            stats = stats_result.data

            # 清理Ginkgo相关键
            ginkgo_result = self.clear_ginkgo_cache_only()

            # 激进模式：清理过期的键和空键
            expired_cleaned = 0
            if aggressive:
                all_keys = self._crud_repo.keys("*")
                for key in all_keys:
                    try:
                        ttl = self._crud_repo.ttl(key)
                        # 检查已过期但未自动清理的键
                        if ttl == -2:  # 键已过期但存在
                            if self._crud_repo.delete(key):
                                expired_cleaned += 1
                    except Exception:
                        continue

            self._logger.INFO(f"Redis vacuum completed: Ginkgo cache cleared, {expired_cleaned} expired keys removed")

            return ServiceResult.success(
                data={
                    "original_stats": stats,
                    "ginkgo_cleanup": ginkgo_result.data,
                    "expired_keys_cleaned": expired_cleaned,
                    "aggressive_mode": aggressive
                },
                message=f"Redis清理完成: Ginkgo缓存已清理，额外清理{expired_cleaned}个过期键"
            )

        except Exception as e:
            self._logger.ERROR(f"Failed to vacuum Redis: {e}")
            return ServiceResult.error(f"Redis清理失败: {str(e)}")