"""
统一错误处理系统 - 减少重复日志，提供结构化错误追踪
"""

import uuid
import traceback
from functools import wraps
from typing import Dict, Optional, Any, Callable, Type, List
from dataclasses import dataclass, field
from datetime import datetime
import threading

@dataclass
class ErrorInfo:
    """错误信息数据类"""
    error_id: str
    function_name: str
    error_type: str
    error_message: str
    timestamp: datetime
    stack_trace: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0

class GinkgoErrorHandler:
    """Ginkgo统一错误处理器"""
    
    def __init__(self):
        self.error_history: Dict[str, ErrorInfo] = {}
        self.error_patterns: Dict[str, int] = {}  # 错误模式计数
        self.lock = threading.RLock()
        
    def handle_error(
        self, 
        func_name: str, 
        error: Exception, 
        operation: str = "execution",
        context: Optional[Dict[str, Any]] = None,
        include_stack: bool = True
    ) -> str:
        """
        处理错误并返回错误ID
        
        Args:
            func_name: 函数名
            error: 异常对象
            operation: 操作类型
            context: 上下文信息
            include_stack: 是否包含堆栈信息
            
        Returns:
            str: 错误ID，用于追踪
        """
        error_id = uuid.uuid4().hex[:8]
        error_pattern = f"{func_name}:{type(error).__name__}"
        
        with self.lock:
            # 记录错误模式
            self.error_patterns[error_pattern] = self.error_patterns.get(error_pattern, 0) + 1
            
            # 创建错误信息
            error_info = ErrorInfo(
                error_id=error_id,
                function_name=func_name,
                error_type=type(error).__name__,
                error_message=str(error),
                timestamp=datetime.now(),
                context=context or {},
                stack_trace=traceback.format_exc() if include_stack else ""
            )
            
            self.error_history[error_id] = error_info
            
            # 清理过旧的错误记录（保留最近1000条）
            if len(self.error_history) > 1000:
                oldest_keys = sorted(
                    self.error_history.keys(),
                    key=lambda k: self.error_history[k].timestamp
                )[:100]
                for key in oldest_keys:
                    del self.error_history[key]
        
        # 智能日志记录
        self._log_error(error_info, error_pattern)
        
        return error_id
    
    def _log_error(self, error_info: ErrorInfo, error_pattern: str):
        """智能日志记录"""
        from ginkgo.libs import GLOG
        
        pattern_count = self.error_patterns.get(error_pattern, 1)
        
        # 根据错误频率决定日志级别
        if pattern_count == 1:
            # 首次出现，详细记录
            GLOG.ERROR(
                f"🔥 [{error_info.error_id}] {error_info.function_name} failed: "
                f"{error_info.error_type}: {error_info.error_message}"
            )
            if error_info.stack_trace and len(error_info.stack_trace) < 1000:
                GLOG.ERROR(f"Stack trace:\n{error_info.stack_trace}")
                
        elif pattern_count <= 5:
            # 少量重复，简化记录
            GLOG.ERROR(
                f"⚠️ [{error_info.error_id}] {error_info.function_name} failed "
                f"({pattern_count}th occurrence): {error_info.error_message}"
            )
        elif pattern_count == 10:
            # 达到阈值，警告
            GLOG.ERROR(
                f"🚨 [{error_info.error_id}] {error_info.function_name} has failed "
                f"{pattern_count} times with {error_info.error_type}. Consider investigation."
            )
        elif pattern_count % 50 == 0:
            # 每50次记录一次
            GLOG.ERROR(
                f"📊 [{error_info.error_id}] {error_info.function_name} failure count: {pattern_count}"
            )
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        with self.lock:
            total_errors = len(self.error_history)
            top_patterns = sorted(
                self.error_patterns.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            recent_errors = sorted(
                self.error_history.values(),
                key=lambda x: x.timestamp,
                reverse=True
            )[:10]
            
            return {
                "total_errors": total_errors,
                "unique_patterns": len(self.error_patterns),
                "top_error_patterns": top_patterns,
                "recent_errors": [
                    {
                        "id": e.error_id,
                        "function": e.function_name,
                        "error": f"{e.error_type}: {e.error_message}",
                        "time": e.timestamp.isoformat()
                    }
                    for e in recent_errors
                ]
            }
    
    def get_error_by_id(self, error_id: str) -> Optional[ErrorInfo]:
        """根据ID获取错误详情"""
        with self.lock:
            return self.error_history.get(error_id)

# 全局错误处理器
_error_handler = GinkgoErrorHandler()

def unified_error_handler(
    operation: str = "execution",
    include_stack: bool = True,
    reraise: bool = True,
    context_keys: Optional[List[str]] = None
):
    """
    统一错误处理装饰器
    
    Args:
        operation: 操作类型描述
        include_stack: 是否包含堆栈信息
        reraise: 是否重新抛出异常
        context_keys: 要从kwargs中提取的上下文键名
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 提取上下文信息
                context = {}
                if context_keys:
                    for key in context_keys:
                        if key in kwargs:
                            context[key] = str(kwargs[key])
                
                # 处理错误
                error_id = _error_handler.handle_error(
                    func_name=f"{func.__module__}.{func.__name__}" if hasattr(func, '__module__') else func.__name__,
                    error=e,
                    operation=operation,
                    context=context,
                    include_stack=include_stack
                )
                
                # 为异常添加错误ID
                if hasattr(e, 'error_id'):
                    e.error_id = error_id
                else:
                    # 创建新的异常类型，包含error_id
                    class TrackedError(type(e)):
                        def __init__(self, original_error, error_id):
                            super().__init__(str(original_error))
                            self.error_id = error_id
                            self.original_error = original_error
                    
                    tracked_error = TrackedError(e, error_id)
                    e = tracked_error
                
                if reraise:
                    raise e
                else:
                    return None
                    
        return wrapper
    return decorator

def get_error_handler() -> GinkgoErrorHandler:
    """获取全局错误处理器"""
    return _error_handler

def log_error_stats():
    """打印错误统计报告"""
    from rich.console import Console
    from rich.table import Table
    
    stats = _error_handler.get_error_stats()
    console = Console()
    
    console.print("\n[bold red]🔥 Error Statistics Report[/]")
    console.print("=" * 60)
    
    console.print(f"Total Errors: [red]{stats['total_errors']}[/]")
    console.print(f"Unique Patterns: [yellow]{stats['unique_patterns']}[/]")
    
    if stats['top_error_patterns']:
        console.print("\n[bold]Top Error Patterns:[/]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Pattern", style="cyan")
        table.add_column("Count", style="red", justify="right")
        
        for pattern, count in stats['top_error_patterns']:
            table.add_row(pattern, str(count))
        
        console.print(table)
    
    if stats['recent_errors']:
        console.print(f"\n[bold]Recent Errors (last {len(stats['recent_errors'])}):[/]")
        for error in stats['recent_errors']:
            console.print(
                f"[yellow]{error['id']}[/] | "
                f"[cyan]{error['function']}[/] | "
                f"[red]{error['error']}[/]"
            )