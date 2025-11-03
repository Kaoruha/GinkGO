"""
T5架构监控面板模块

提供可视化监控面板和告警管理功能
"""

import asyncio
import json
from datetime import datetime, timedelta
from ginkgo.trading.time.clock import now as clock_now
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import defaultdict, deque

from ginkgo.libs import GLOG
from .metrics import get_metrics_collector
from .health import get_health_checker
from .tracing import get_tracer


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Alert:
    """告警"""
    alert_id: str
    rule_name: str
    level: AlertLevel
    message: str
    details: Dict[str, Any]
    created_time: datetime = field(default_factory=datetime.now)
    updated_time: datetime = field(default_factory=datetime.now)
    status: AlertStatus = AlertStatus.ACTIVE
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'alert_id': self.alert_id,
            'rule_name': self.rule_name,
            'level': self.level.value,
            'message': self.message,
            'details': self.details,
            'created_time': self.created_time.isoformat(),
            'updated_time': self.updated_time.isoformat(),
            'status': self.status.value
        }


@dataclass
class AlertRule:
    """告警规则"""
    rule_name: str
    condition_func: Callable[[Dict[str, Any]], bool]
    level: AlertLevel
    message_template: str
    cooldown_seconds: int = 300  # 5分钟冷却期
    enabled: bool = True
    
    last_triggered: Optional[datetime] = None
    
    def can_trigger(self) -> bool:
        """检查是否可以触发告警"""
        if not self.enabled:
            return False
        
        if self.last_triggered is None:
            return True
        
        return (clock_now() - self.last_triggered).total_seconds() >= self.cooldown_seconds


class AlertManager:
    """告警管理器"""
    
    def __init__(self, max_alerts: int = 1000):
        self.max_alerts = max_alerts
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: Dict[str, Alert] = {}
        self._alert_history: deque = deque(maxlen=max_alerts)
        self._handlers: Dict[AlertLevel, List[Callable[[Alert], None]]] = defaultdict(list)
        
        self._running = False
        self._check_task: Optional[asyncio.Task] = None
        self._check_interval = 30  # 30秒检查一次
    
    def add_rule(self, rule: AlertRule) -> None:
        """添加告警规则"""
        self._rules[rule.rule_name] = rule
        GLOG.INFO(f"添加告警规则: {rule.rule_name}")
    
    def remove_rule(self, rule_name: str) -> bool:
        """移除告警规则"""
        if rule_name in self._rules:
            del self._rules[rule_name]
            GLOG.INFO(f"移除告警规则: {rule_name}")
            return True
        return False
    
    def add_handler(self, level: AlertLevel, handler: Callable[[Alert], None]) -> None:
        """添加告警处理器"""
        self._handlers[level].append(handler)
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return [alert for alert in self._alerts.values() if alert.status == AlertStatus.ACTIVE]
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """获取告警历史"""
        history = list(self._alert_history)
        return history[-limit:] if limit > 0 else history
    
    def resolve_alert(self, alert_id: str) -> bool:
        """解决告警"""
        if alert_id in self._alerts:
            alert = self._alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.updated_time = clock_now()
            GLOG.INFO(f"告警已解决: {alert.rule_name}")
            return True
        return False
    
    def suppress_alert(self, alert_id: str) -> bool:
        """抑制告警"""
        if alert_id in self._alerts:
            alert = self._alerts[alert_id]
            alert.status = AlertStatus.SUPPRESSED
            alert.updated_time = clock_now()
            GLOG.INFO(f"告警已抑制: {alert.rule_name}")
            return True
        return False
    
    async def check_rules(self) -> None:
        """检查告警规则"""
        # 收集当前系统状态
        metrics_collector = get_metrics_collector()
        health_checker = get_health_checker()
        tracer = get_tracer()
        
        current_metrics = metrics_collector.get_current_metrics()
        health_status = health_checker.get_last_health_check()
        active_traces = tracer.get_active_traces()
        
        system_state = {
            'metrics': current_metrics,
            'health': health_status.to_dict() if health_status else {},
            'active_traces': len(active_traces),
            'timestamp': clock_now()
        }
        
        # 检查每个规则
        for rule in self._rules.values():
            try:
                if rule.can_trigger() and rule.condition_func(system_state):
                    await self._trigger_alert(rule, system_state)
            except Exception as e:
                GLOG.ERROR(f"检查告警规则失败 {rule.rule_name}: {e}")
    
    async def _trigger_alert(self, rule: AlertRule, system_state: Dict[str, Any]) -> None:
        """触发告警"""
        from uuid import uuid4
        
        alert_id = uuid4().hex[:16]
        
        # 格式化消息
        try:
            message = rule.message_template.format(**system_state.get('metrics', {}))
        except:
            message = rule.message_template
        
        alert = Alert(
            alert_id=alert_id,
            rule_name=rule.rule_name,
            level=rule.level,
            message=message,
            details=system_state
        )
        
        self._alerts[alert_id] = alert
        self._alert_history.append(alert)
        rule.last_triggered = clock_now()
        
        GLOG.WARN(f"告警触发: {rule.rule_name} - {message}")
        
        # 通知处理器
        handlers = self._handlers.get(rule.level, [])
        for handler in handlers:
            try:
                handler(alert)
            except Exception as e:
                GLOG.ERROR(f"告警处理器错误: {e}")
    
    async def start_monitoring(self) -> None:
        """开始监控"""
        if self._running:
            return
        
        self._running = True
        self._check_task = asyncio.create_task(self._monitoring_loop())
        GLOG.INFO("告警监控已启动")
    
    async def stop_monitoring(self) -> None:
        """停止监控"""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        GLOG.INFO("告警监控已停止")
    
    async def _monitoring_loop(self) -> None:
        """监控循环"""
        while self._running:
            try:
                await self.check_rules()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                GLOG.ERROR(f"告警监控循环错误: {e}")
                await asyncio.sleep(5)


class MonitoringDashboard:
    """监控面板"""
    
    def __init__(self):
        self.metrics_collector = get_metrics_collector()
        self.health_checker = get_health_checker()
        self.tracer = get_tracer()
        self.alert_manager = AlertManager()
        
        # 设置默认告警规则
        self._setup_default_alert_rules()
        self._setup_default_alert_handlers()
    
    def _setup_default_alert_rules(self) -> None:
        """设置默认告警规则"""
        # CPU使用率告警
        cpu_rule = AlertRule(
            rule_name="high_cpu_usage",
            condition_func=lambda state: state.get('metrics', {}).get('performance', {}).get('cpu_usage_percent', 0) > 80,
            level=AlertLevel.WARNING,
            message_template="CPU使用率过高: {cpu_usage_percent:.1f}%",
            cooldown_seconds=300
        )
        self.alert_manager.add_rule(cpu_rule)
        
        # 内存使用率告警
        memory_rule = AlertRule(
            rule_name="high_memory_usage",
            condition_func=lambda state: state.get('metrics', {}).get('performance', {}).get('memory_usage_mb', 0) > 1000,
            level=AlertLevel.WARNING,
            message_template="内存使用量过高: {memory_usage_mb:.1f}MB",
            cooldown_seconds=300
        )
        self.alert_manager.add_rule(memory_rule)
        
        # 请求错误率告警
        error_rate_rule = AlertRule(
            rule_name="high_error_rate",
            condition_func=lambda state: state.get('metrics', {}).get('performance', {}).get('success_rate', 100) < 95,
            level=AlertLevel.ERROR,
            message_template="请求成功率过低: {success_rate:.1f}%",
            cooldown_seconds=180
        )
        self.alert_manager.add_rule(error_rate_rule)
        
        # 系统健康告警
        health_rule = AlertRule(
            rule_name="system_unhealthy",
            condition_func=lambda state: state.get('health', {}).get('overall_status') == 'unhealthy',
            level=AlertLevel.CRITICAL,
            message_template="系统状态不健康",
            cooldown_seconds=60
        )
        self.alert_manager.add_rule(health_rule)
    
    def _setup_default_alert_handlers(self) -> None:
        """设置默认告警处理器"""
        # 日志处理器
        def log_handler(alert: Alert) -> None:
            if alert.level == AlertLevel.CRITICAL:
                GLOG.ERROR(f"🚨 CRITICAL ALERT: {alert.message}")
            elif alert.level == AlertLevel.ERROR:
                GLOG.ERROR(f"❌ ERROR ALERT: {alert.message}")
            elif alert.level == AlertLevel.WARNING:
                GLOG.WARN(f"⚠️ WARNING ALERT: {alert.message}")
            else:
                GLOG.INFO(f"ℹ️ INFO ALERT: {alert.message}")
        
        # 为所有级别添加日志处理器
        for level in AlertLevel:
            self.alert_manager.add_handler(level, log_handler)
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """获取面板数据"""
        # 获取基础数据
        current_metrics = self.metrics_collector.get_current_metrics()
        health_status = await self.health_checker.check_all_health()
        active_alerts = self.alert_manager.get_active_alerts()
        recent_alerts = self.alert_manager.get_alert_history(20)
        
        # 获取追踪信息
        active_traces = self.tracer.get_active_traces()
        
        # 构建面板数据
        dashboard_data = {
            'timestamp': clock_now().isoformat(),
            'system_overview': {
                'uptime_seconds': current_metrics.get('uptime_seconds', 0),
                'overall_health': health_status.overall_status.value,
                'healthy_components': health_status.healthy_components,
                'total_components': health_status.total_components,
                'active_alerts_count': len(active_alerts),
                'active_traces_count': len(active_traces)
            },
            'performance_metrics': current_metrics.get('performance', {}),
            'system_metrics': current_metrics.get('system', {}),
            'trading_metrics': current_metrics.get('trading', {}),
            'health_status': health_status.to_dict(),
            'active_alerts': [alert.to_dict() for alert in active_alerts],
            'recent_alerts': [alert.to_dict() for alert in recent_alerts],
            'trace_summary': {
                'active_traces': len(active_traces),
                'recent_traces': active_traces[:10]  # 最近10个
            }
        }
        
        return dashboard_data
    
    def get_metrics_history(self, metric_name: str, time_window: timedelta = None) -> List[Dict[str, Any]]:
        """获取指标历史"""
        if time_window is None:
            time_window = timedelta(hours=1)
        
        history = self.metrics_collector.get_metrics_history(metric_name, limit=0)
        cutoff_time = clock_now() - time_window
        
        recent_history = [
            {
                'timestamp': point.timestamp.isoformat(),
                'value': point.value,
                'metric_type': point.metric_type.value
            }
            for point in history
            if point.timestamp >= cutoff_time
        ]
        
        return recent_history
    
    def export_dashboard_json(self, include_history: bool = False) -> str:
        """导出面板数据为JSON"""
        dashboard_data = asyncio.run(self.get_dashboard_data())
        
        if include_history:
            # 添加关键指标历史
            key_metrics = ['cpu_usage', 'memory_usage', 'request_rate', 'error_rate']
            dashboard_data['metrics_history'] = {}
            
            for metric in key_metrics:
                dashboard_data['metrics_history'][metric] = self.get_metrics_history(metric)
        
        return json.dumps(dashboard_data, indent=2, ensure_ascii=False)
    
    async def generate_report(self, time_period: timedelta = None) -> Dict[str, Any]:
        """生成监控报告"""
        if time_period is None:
            time_period = timedelta(hours=24)  # 默认24小时报告
        
        end_time = clock_now()
        start_time = end_time - time_period
        
        # 获取时间窗口内的数据
        metrics_summary = self.metrics_collector.get_metrics_summary(time_period)
        alert_history = [
            alert for alert in self.alert_manager.get_alert_history()
            if alert.created_time >= start_time
        ]
        
        # 统计告警
        alert_stats = defaultdict(int)
        for alert in alert_history:
            alert_stats[alert.level.value] += 1
        
        # 生成报告
        report = {
            'report_period': {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_hours': time_period.total_seconds() / 3600
            },
            'metrics_summary': metrics_summary,
            'alert_summary': {
                'total_alerts': len(alert_history),
                'by_level': dict(alert_stats),
                'recent_alerts': [alert.to_dict() for alert in alert_history[-10:]]
            },
            'system_summary': {
                'health_checks_performed': len(alert_history),  # 简化统计
                'average_response_time': metrics_summary.get('response_time', {}).get('avg', 0)
            }
        }
        
        return report
    
    async def start_monitoring(self) -> None:
        """开始全面监控"""
        await self.health_checker.start_monitoring()
        await self.alert_manager.start_monitoring()
        GLOG.INFO("监控面板已启动")
    
    async def stop_monitoring(self) -> None:
        """停止监控"""
        await self.health_checker.stop_monitoring()
        await self.alert_manager.stop_monitoring()
        GLOG.INFO("监控面板已停止")


# 全局监控面板实例
_global_dashboard = MonitoringDashboard()


def get_dashboard() -> MonitoringDashboard:
    """获取全局监控面板"""
    return _global_dashboard


async def start_monitoring() -> None:
    """便捷函数：启动监控"""
    await _global_dashboard.start_monitoring()


async def stop_monitoring() -> None:
    """便捷函数：停止监控"""  
    await _global_dashboard.stop_monitoring()


async def get_dashboard_data() -> Dict[str, Any]:
    """便捷函数：获取面板数据"""
    return await _global_dashboard.get_dashboard_data()
