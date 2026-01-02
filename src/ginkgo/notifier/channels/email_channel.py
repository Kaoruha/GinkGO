# Upstream: NotificationService (通知服务业务逻辑)、INotificationChannel (渠道接口)
# Downstream: SMTP 邮件服务器 (外部服务)
# Role: EmailChannel Email通知渠道实现通过SMTP协议发送邮件通知支持HTML格式和附件支持通知系统功能


"""
Email Notification Channel

通过 SMTP 发送邮件通知，支持 HTML 格式。
"""

import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List
from datetime import datetime

from ginkgo.notifier.channels.base_channel import INotificationChannel, ChannelResult
from ginkgo.libs import GLOG, GCONF


class EmailChannel(INotificationChannel):
    """
    Email 通知渠道

    通过 SMTP 协议发送邮件通知。
    支持：
    - 纯文本邮件
    - HTML 格式邮件
    - 附件
    - 自动重试机制
    """

    # 默认 SMTP 配置（可在 config.yaml 中覆盖）
    DEFAULT_SMTP_HOST = "smtp.gmail.com"
    DEFAULT_SMTP_PORT = 587
    DEFAULT_TIMEOUT = 10.0  # 秒 (FR-014a)

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_name: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 10.0
    ):
        """
        初始化 Email 渠道

        Args:
            smtp_host: SMTP 服务器地址（可选，默认从配置读取）
            smtp_port: SMTP 端口（可选，默认从配置读取）
            smtp_user: SMTP 用户名（可选，默认从配置读取）
            smtp_password: SMTP 密码（可选，默认从配置读取）
            from_name: 发件人名称（可选）
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            timeout: SMTP 超时时间（秒，默认 10s）
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_name = from_name or "Ginkgo Notification"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

        # 从配置加载默认值（如果未提供）
        self._load_config()

    @property
    def channel_name(self) -> str:
        """获取渠道名称"""
        return "email"

    def _load_config(self) -> None:
        """
        从配置加载 SMTP 凭证

        优先级：参数 > secure.yml > 默认值
        """
        # 如果参数已提供，不覆盖
        if self.smtp_host is not None:
            return

        # 从 secure.yml 读取配置
        self.smtp_host = GCONF.get("email.smtp_host", self.DEFAULT_SMTP_HOST)
        self.smtp_port = GCONF.get("email.smtp_port", self.DEFAULT_SMTP_PORT)
        self.smtp_user = GCONF.get("email.smtp_user", "")
        self.smtp_password = GCONF.get("email.smtp_password", "")

        # 从通知超时配置中读取 email 超时（FR-014a）
        timeout_config = GCONF.get("notifications.timeouts", {})
        if isinstance(timeout_config, dict):
            self.timeout = float(timeout_config.get("email", self.DEFAULT_TIMEOUT))

    def send(
        self,
        content: str,
        title: Optional[str] = None,
        to: Optional[str | List[str]] = None,
        html: bool = False,
        **kwargs
    ) -> ChannelResult:
        """
        发送邮件

        Args:
            content: 邮件内容
            title: 邮件主题（必需）
            to: 收件人邮箱地址或地址列表（必需）
            html: 是否使用 HTML 格式（默认 False）
            **kwargs: 其他参数（如 cc, bcc, attachments）

        Returns:
            ChannelResult: 发送结果
        """
        if not self.validate_config():
            return ChannelResult(
                success=False,
                error="Invalid email configuration (missing SMTP credentials)"
            )

        # 收件人验证
        if not to:
            return ChannelResult(
                success=False,
                error="No recipient specified"
            )

        # 统一收件人格式为列表
        recipients = [to] if isinstance(to, str) else to

        # 构建邮件消息
        message = self._build_message(
            content=content,
            subject=title or "Ginkgo Notification",
            recipients=recipients,
            html=html,
            **kwargs
        )

        # 发送邮件（带重试）
        return self._send_with_retry(message, recipients)

    def validate_config(self) -> bool:
        """
        验证 Email 配置

        Returns:
            bool: 配置是否有效
        """
        if not self.smtp_host:
            return False
        if not self.smtp_port:
            return False
        if not self.smtp_user:
            return False
        if not self.smtp_password:
            return False

        # 基本格式验证
        if self.smtp_port < 1 or self.smtp_port > 65535:
            return False

        return True

    def get_config_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要

        Returns:
            Dict: 配置摘要（隐藏敏感信息）
        """
        # 隐藏密码
        safe_password = "***" if self.smtp_password else None

        # 隐藏用户名部分信息
        safe_user = None
        if self.smtp_user:
            if "@" in self.smtp_user:
                parts = self.smtp_user.split("@")
                safe_user = f"{parts[0][0]}***@{parts[1]}"
            else:
                safe_user = f"{self.smtp_user[0]}***"

        return {
            "channel": self.channel_name,
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "smtp_user": safe_user,
            "from_name": self.from_name,
            "max_retries": self.max_retries,
            "timeout": self.timeout
        }

    def _build_message(
        self,
        content: str,
        subject: str,
        recipients: List[str],
        html: bool = False,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> MIMEMultipart:
        """
        构建邮件消息

        Args:
            content: 邮件内容
            subject: 邮件主题
            recipients: 收件人列表
            html: 是否 HTML 格式
            cc: 抄送列表（可选）
            bcc: 密送列表（可选）
            attachments: 附件列表（可选，格式：[{"filename": "file.txt", "content": b"..."}]）

        Returns:
            MIMEMultipart: 邮件消息对象
        """
        # 创建多部分消息
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.smtp_user}>"
        message["To"] = ", ".join(recipients)

        if cc:
            message["Cc"] = ", ".join(cc)

        # 添加邮件正文
        mime_type = "html" if html else "plain"
        mime_part = MIMEText(content, mime_type, "utf-8")
        message.attach(mime_part)

        # 添加附件
        if attachments:
            for attachment in attachments:
                filename = attachment.get("filename", "attachment")
                content = attachment.get("content", b"")
                mimetype = attachment.get("mimetype", "application/octet-stream")

                from email.mime.base import MIMEBase
                from email import encoders

                part = MIMEBase(*mimetype.split("/", 1))
                part.set_payload(content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {filename}"
                )
                message.attach(part)

        return message

    def _send_with_retry(
        self,
        message: MIMEMultipart,
        recipients: List[str]
    ) -> ChannelResult:
        """
        发送邮件（带重试）

        Args:
            message: 邮件消息对象
            recipients: 收件人列表

        Returns:
            ChannelResult: 发送结果
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                # 连接到 SMTP 服务器
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout) as server:
                    server.set_debuglevel(0)  # 关闭调试输出

                    # 启用 TLS（如果可用）
                    if server.has_extn("STARTTLS"):
                        server.starttls()

                    # 登录
                    server.login(self.smtp_user, self.smtp_password)

                    # 发送邮件
                    all_recipients = recipients.copy()
                    # 添加 CC 和 BCC 收件人
                    if message.get("Cc"):
                        cc_list = [addr.strip() for addr in message["Cc"].split(",")]
                        all_recipients.extend(cc_list)

                    server.send_message(message, to_addrs=all_recipients)

                    # 成功
                    return ChannelResult(
                        success=True,
                        message_id=f"{datetime.utcnow().isoformat()}_{len(recipients)}",
                        timestamp=datetime.utcnow().timestamp()
                    )

            except smtplib.SMTPAuthenticationError:
                last_error = "SMTP authentication failed"
                GLOG.ERROR(f"Email authentication error: {last_error}")
                break  # 认证错误不重试

            except smtplib.SMTPRecipientsRefused as e:
                last_error = f"Recipients refused: {e.recipients}"
                GLOG.ERROR(f"Email recipients error: {last_error}")
                break  # 收件人错误不重试

            except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError):
                last_error = "SMTP connection error"
                if attempt < self.max_retries - 1:
                    GLOG.WARN(f"Email connection error, retry {attempt + 1}/{self.max_retries}")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    break

            except smtplib.SMTPException as e:
                last_error = f"SMTP error: {str(e)}"
                if attempt < self.max_retries - 1:
                    GLOG.WARN(f"Email SMTP error, retry {attempt + 1}/{self.max_retries}")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    break

            except TimeoutError:
                last_error = f"SMTP timeout after {self.timeout}s"
                if attempt < self.max_retries - 1:
                    GLOG.WARN(f"Email timeout, retry {attempt + 1}/{self.max_retries}")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    break

            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                GLOG.ERROR(f"Email unexpected error: {last_error}")
                break

        # 所有重试都失败
        GLOG.ERROR(f"Email send failed after {self.max_retries} attempts: {last_error}")
        return ChannelResult(
            success=False,
            error=last_error,
            timestamp=datetime.utcnow().timestamp()
        )


# ============================================================================
# 便捷函数 - 无需实例化即可使用
# ============================================================================

def send_email(
    to: str | List[str],
    content: str,
    subject: str,
    html: bool = False,
    **kwargs
) -> ChannelResult:
    """
    发送邮件（便捷函数）

    无需手动创建 EmailChannel 实例，直接调用即可发送邮件。

    Args:
        to: 收件人邮箱地址或地址列表
        content: 邮件内容
        subject: 邮件主题
        html: 是否 HTML 格式
        **kwargs: 其他参数（如 cc, bcc, attachments）

    Returns:
        ChannelResult: 发送结果

    Examples:
        >>> from ginkgo.notifier.channels import send_email
        >>>
        >>> # 简单文本邮件
        >>> send_email(
        ...     to="user@example.com",
        ...     subject="Hello",
        ...     content="Hello World!"
        ... )
        >>>
        >>> # HTML 邮件
        >>> send_email(
        ...     to="user@example.com",
        ...     subject="Report",
        ...     content="<h1>Report</h1><p>Data here</p>",
        ...     html=True
        ... )
    """
    channel = EmailChannel()
    return channel.send(
        content=content,
        title=subject,
        to=to,
        html=html,
        **kwargs
    )


def send_email_html(
    to: str | List[str],
    subject: str,
    content: str,
    **kwargs
) -> ChannelResult:
    """发送 HTML 格式邮件"""
    return send_email(to, content, subject=subject, html=True, **kwargs)
