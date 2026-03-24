# Upstream: GLOG (日志记录), LogService (日志查询), GCONF (配置管理)
# Downstream: 钉钉Webhook, 企业微信Webhook, 邮件SMTP, Redis (告警去重)
# Role: 日志告警服务，监控日志错误模式并发送多渠道告警通知

import hashlib
import json
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

import requests

from ginkgo.libs import GLOG, GCONF
from ginkgo.data.services.base_service import BaseService


class AlertService(BaseService):
    """
    日志告警服务

    监控 ClickHouse 日志数据中的错误模式，当满足告警条件时
    通过多种渠道（钉钉、企业微信、邮件）发送告警通知。

    告警抑制机制：使用 Redis 存储告警发送记录，相同错误模式
    在 5 分钟内只发送一次告警，避免告警风暴。
    """

    # 告警抑制 TTL（秒）
    SUPPRESSION_TTL = 300  # 5 分钟

    # Redis Key 前缀
    SUPPRESSION_KEY_PREFIX = "alert:suppression:"

    def __init__(self, redis_client=None, db_engine=None):
        """
        初始化告警服务

        Args:
            redis_client: Redis 客户端（用于告警抑制）
            db_engine: ClickHouse 数据库引擎（用于查询日志）
        """
        super().__init__()
        self._redis = redis_client
        self._db_engine = db_engine

        # 告警规则存储（运行时内存）
        # 生产环境可持久化到数据库
        self._rules: Dict[str, Dict[str, Any]] = {}

        # 加载配置
        self._load_config()

    def _load_config(self):
        """从 GCONF 加载告警配置"""
        try:
            # 钉钉配置
            self._dingtalk_webhook = getattr(GCONF, 'LOGGING_ALERTS_DINGTALK_WEBHOOK', "")

            # 企业微信配置
            self._wechat_webhook = getattr(GCONF, 'LOGGING_ALERTS_WECHAT_WEBHOOK', "")

            # 邮件配置
            self._email_smtp_host = getattr(GCONF, 'LOGGING_ALERTS_EMAIL_SMTP_HOST', "")
            self._email_smtp_port = getattr(GCONF, 'LOGGING_ALERTS_EMAIL_SMTP_PORT', 587)
            self._email_username = getattr(GCONF, 'LOGGING_ALERTS_EMAIL_USERNAME', "")
            self._email_password = getattr(GCONF, 'LOGGING_ALERTS_EMAIL_PASSWORD', "")
            self._email_from = getattr(GCONF, 'LOGGING_ALERTS_EMAIL_FROM', "")
            self._email_to = getattr(GCONF, 'LOGGING_ALERTS_EMAIL_TO', [])

            # 默认告警渠道
            self._default_channels = getattr(GCONF, 'LOGGING_ALERTS_CHANNELS', ["dingtalk"])

        except Exception as e:
            GLOG.ERROR(f"加载告警配置失败: {e}")
            # 设置默认值
            self._dingtalk_webhook = ""
            self._wechat_webhook = ""
            self._email_smtp_host = ""
            self._email_smtp_port = 587
            self._email_username = ""
            self._email_password = ""
            self._email_from = ""
            self._email_to = []
            self._default_channels = []

    # ==================== 告警规则管理 ====================

    def add_alert_rule(
        self,
        name: str,
        pattern: str,
        threshold: int = 10,
        window_minutes: int = 5,
        channels: Optional[List[str]] = None,
        level: str = "ERROR"
    ) -> str:
        """
        添加告警规则

        Args:
            name: 规则名称
            pattern: 错误模式（关键词或正则表达式）
            threshold: 触发阈值（时间窗口内出现次数）
            window_minutes: 时间窗口（分钟）
            channels: 告警渠道列表 ["dingtalk", "wechat", "email"]
            level: 日志级别

        Returns:
            规则 ID
        """
        rule_id = f"rule_{int(time.time())}_{name}"

        rule = {
            "id": rule_id,
            "name": name,
            "pattern": pattern,
            "threshold": threshold,
            "window_minutes": window_minutes,
            "channels": channels or self._default_channels,
            "level": level,
            "created_at": datetime.now().isoformat()
        }

        self._rules[rule_id] = rule
        GLOG.INFO(f"添加告警规则: {name} (pattern={pattern}, threshold={threshold})")

        return rule_id

    def remove_alert_rule(self, rule_id: str) -> bool:
        """
        删除告警规则

        Args:
            rule_id: 规则 ID

        Returns:
            是否删除成功
        """
        if rule_id in self._rules:
            del self._rules[rule_id]
            GLOG.INFO(f"删除告警规则: {rule_id}")
            return True
        return False

    def get_alert_rules(self, rule_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取告警规则

        Args:
            rule_id: 规则 ID（可选，为空时返回所有规则）

        Returns:
            规则列表
        """
        if rule_id:
            return [self._rules.get(rule_id)] if rule_id in self._rules else []
        return list(self._rules.values())

    # ==================== 告警检查 ====================

    def check_error_patterns(self) -> List[Dict[str, Any]]:
        """
        检查错误模式是否触发告警

        查询 ClickHouse 统计各错误模式的出现频率，与规则阈值比较。

        Returns:
            触发的告警列表
        """
        triggered_alerts = []

        for rule_id, rule in self._rules.items():
            try:
                # 查询该错误模式在时间窗口内的出现次数
                count = self._count_error_pattern(
                    pattern=rule["pattern"],
                    window_minutes=rule["window_minutes"],
                    level=rule["level"]
                )

                # 判断是否超过阈值
                if count >= rule["threshold"]:
                    alert = {
                        "rule_id": rule_id,
                        "rule_name": rule["name"],
                        "pattern": rule["pattern"],
                        "count": count,
                        "threshold": rule["threshold"],
                        "level": rule["level"],
                        "timestamp": datetime.now().isoformat()
                    }
                    triggered_alerts.append(alert)

            except Exception as e:
                GLOG.ERROR(f"检查告警规则 {rule_id} 失败: {e}")

        return triggered_alerts

    def _count_error_pattern(self, pattern: str, window_minutes: int, level: str) -> int:
        """
        统计错误模式在时间窗口内的出现次数

        Args:
            pattern: 错误模式
            window_minutes: 时间窗口（分钟）
            level: 日志级别

        Returns:
            出现次数
        """
        if self._db_engine is None:
            GLOG.WARN("数据库引擎未配置，无法查询错误模式")
            return 0

        try:
            from ginkgo.services.logging import LogService
            log_service = LogService(engine=self._db_engine)

            # 使用 LogService 搜索日志
            time_end = datetime.now()
            time_start = time_end - timedelta(minutes=window_minutes)

            logs = log_service.search_logs(
                keyword=pattern,
                level=level,
                time_start=time_start,
                time_end=time_end,
                limit=10000
            )

            return len(logs)

        except Exception as e:
            GLOG.ERROR(f"查询错误模式失败: {e}")
            return 0

    # ==================== 告警发送 ====================

    def send_alert(
        self,
        message: str,
        rule_id: str,
        pattern: str,
        channels: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送告警通知

        Args:
            message: 告警消息
            rule_id: 规则 ID
            pattern: 错误模式
            channels: 告警渠道列表
            metadata: 附加元数据

        Returns:
            是否发送成功（至少一个渠道成功）
        """
        # 检查告警抑制
        if not self.should_send_alert(rule_id, pattern):
            GLOG.INFO(f"告警被抑制: rule={rule_id}, pattern={pattern}")
            return False

        # 构造告警内容
        alert_content = {
            "title": f"Ginkgo 日志告警: {rule_id}",
            "message": message,
            "pattern": pattern,
            "rule_id": rule_id,
            "timestamp": datetime.now().isoformat(),
            **(metadata or {})
        }

        channels = channels or self._default_channels
        success = False

        for channel in channels:
            try:
                if channel == "dingtalk":
                    if self._send_dingtalk_alert(alert_content):
                        success = True
                elif channel == "wechat":
                    if self._send_wechat_alert(alert_content):
                        success = True
                elif channel == "email":
                    if self._send_email_alert(alert_content):
                        success = True
                else:
                    GLOG.WARN(f"不支持的告警渠道: {channel}")

            except Exception as e:
                # 单个渠道失败不影响其他渠道
                GLOG.ERROR(f"发送 {channel} 告警失败: {e}")

        if success:
            # 记录告警已发送（抑制）
            self._mark_alert_sent(rule_id, pattern)

        return success

    def should_send_alert(self, rule_id: str, pattern: str) -> bool:
        """
        检查是否应该发送告警（抑制机制）

        Args:
            rule_id: 规则 ID
            pattern: 错误模式

        Returns:
            是否应该发送
        """
        if self._redis is None:
            # Redis 不可用时，不进行抑制（总是发送）
            return True

        try:
            key = self._get_suppression_key(rule_id, pattern)
            result = self._redis.get(key)
            return result is None
        except Exception as e:
            GLOG.ERROR(f"检查告警抑制失败: {e}")
            return True

    def _mark_alert_sent(self, rule_id: str, pattern: str):
        """标记告警已发送（设置抑制）"""
        if self._redis is None:
            return

        try:
            key = self._get_suppression_key(rule_id, pattern)
            self._redis.setex(key, self.SUPPRESSION_TTL, "1")
        except Exception as e:
            GLOG.ERROR(f"设置告警抑制失败: {e}")

    def _get_suppression_key(self, rule_id: str, pattern: str) -> str:
        """获取告警抑制 Redis Key"""
        # 对 pattern 进行 hash，避免特殊字符问题
        pattern_hash = hashlib.md5(pattern.encode()).hexdigest()[:8]
        return f"{self.SUPPRESSION_KEY_PREFIX}{rule_id}:{pattern_hash}"

    # ==================== 告警渠道实现 ====================

    def _send_dingtalk_alert(self, content: Dict[str, Any]) -> bool:
        """
        发送钉钉告警

        Args:
            content: 告警内容

        Returns:
            是否发送成功
        """
        if not self._dingtalk_webhook:
            GLOG.WARN("钉钉 Webhook 未配置")
            return False

        try:
            # 构造钉钉消息格式
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": content["title"],
                    "text": f"## {content['title']}\n\n"
                            f"**消息**: {content['message']}\n\n"
                            f"**错误模式**: `{content['pattern']}`\n\n"
                            f"**规则ID**: {content['rule_id']}\n\n"
                            f"**时间**: {content['timestamp']}"
                }
            }

            response = requests.post(
                self._dingtalk_webhook,
                json=message,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("errcode") == 0:
                    GLOG.INFO(f"钉钉告警发送成功: {content['title']}")
                    return True
                else:
                    GLOG.ERROR(f"钉钉告警返回错误: {result}")
            else:
                GLOG.ERROR(f"钉钉告警 HTTP 错误: {response.status_code}")

        except Exception as e:
            GLOG.ERROR(f"发送钉钉告警异常: {e}")

        return False

    def _send_wechat_alert(self, content: Dict[str, Any]) -> bool:
        """
        发送企业微信告警

        Args:
            content: 告警内容

        Returns:
            是否发送成功
        """
        if not self._wechat_webhook:
            GLOG.WARN("企业微信 Webhook 未配置")
            return False

        try:
            # 构造企业微信消息格式
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"## {content['title']}\n"
                               f"> 消息: {content['message']}\n"
                               f"> 错误模式: <font color=\"warning\">{content['pattern']}</font>\n"
                               f"> 规则ID: {content['rule_id']}\n"
                               f"> 时间: {content['timestamp']}"
                }
            }

            response = requests.post(
                self._wechat_webhook,
                json=message,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("errcode") == 0:
                    GLOG.INFO(f"企业微信告警发送成功: {content['title']}")
                    return True
                else:
                    GLOG.ERROR(f"企业微信告警返回错误: {result}")
            else:
                GLOG.ERROR(f"企业微信告警 HTTP 错误: {response.status_code}")

        except Exception as e:
            GLOG.ERROR(f"发送企业微信告警异常: {e}")

        return False

    def _send_email_alert(self, content: Dict[str, Any]) -> bool:
        """
        发送邮件告警

        Args:
            content: 告警内容

        Returns:
            是否发送成功
        """
        if not self._email_smtp_host or not self._email_to:
            GLOG.WARN("邮件 SMTP 未配置")
            return False

        try:
            # 构造邮件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = content["title"]
            msg["From"] = self._email_from
            msg["To"] = ", ".join(self._email_to)

            # 邮件正文（HTML）
            html_body = f"""
            <html>
              <body>
                <h2>{content['title']}</h2>
                <p><strong>消息:</strong> {content['message']}</p>
                <p><strong>错误模式:</strong> <code>{content['pattern']}</code></p>
                <p><strong>规则ID:</strong> {content['rule_id']}</p>
                <p><strong>时间:</strong> {content['timestamp']}</p>
              </body>
            </html>
            """

            msg.attach(MIMEText(html_body, "html", "utf-8"))

            # 发送邮件
            with smtplib.SMTP(self._email_smtp_host, self._email_smtp_port) as server:
                server.starttls()
                server.login(self._email_username, self._email_password)
                server.send_message(msg)

            GLOG.INFO(f"邮件告警发送成功: {content['title']}")
            return True

        except Exception as e:
            GLOG.ERROR(f"发送邮件告警异常: {e}")
            return False
