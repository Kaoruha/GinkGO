import threading
import signal
import psutil
import os

from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer, GinkgoConsumer
from ginkgo.interfaces.notification_interface import INotificationService
from ginkgo.notifier.notifier_telegram import echo
from ginkgo.notifier.notifier_beep import beep as beepbeep
from ginkgo.notifier.notifier_telegram import (
    run_telebot as run_telegram_bot_api_server,
)
from ginkgo.libs.core.config import GCONF
from ginkgo.libs import GLOG
from ginkgo.libs.core.threading import GinkgoThreadManager

gtm = GinkgoThreadManager()


class GinkgoNotifier(INotificationService):
    def __init__(self):
        self._producer = None
        self._kafka_service = None
        self._redis_service = None
        try:
            # 保持向后兼容性，同时集成KafkaService
            self._producer = GinkgoProducer()
            # 集成KafkaService用于高级功能
            from ginkgo.data.containers import container
            self._kafka_service = container.kafka_service()
            self._redis_service = container.redis_service()
        except Exception as e:
            print(e)
        self.telebot_pname = gtm.get_thread_cache_name("telebot")
        pass

    @property
    def telebot_status(self) -> str:
        if self._redis_service and self._redis_service.exists(self.telebot_pname):
            cache = self._redis_service.get_cache(self.telebot_pname)
            if cache:
                try:
                    proc = psutil.Process(int(cache))
                    if proc.is_running():
                        return "RUNNING"
                    elif proc.is_sleeping():
                        return "SLEEPING"
                    else:
                        return "DEAD"
                except Exception as e:
                    return "DEAD"
        return "NOT EXIST"

    def kill_telebot(self) -> None:
        GLOG.DEBUG("Try kill TeleBot worker.")
        gtm.kill_thread("telebot")

    def run_telebot(self) -> None:
        self.kill_telebot()
        gtm.add_thread("telebot", run_telegram_bot_api_server)

    def echo_to_telegram(self, message: str):
        t = threading.Thread(target=echo, args=(message,))
        t.start()

    def send_long_signal(self, signal_id: str):
        msg = "LONG SIGNAL"
        msg += "\n" + "ID: " + signal_id
        msg += "\n" + "FROM: " + "Signal via signal_id source"
        msg += "\n" + "CODE: " + "000001.SZ"
        msg += "\n" + "VOLE: " + "1000"
        msg += "\n" + "TIME: " + "2021-01-01 00:00:00"
        self.echoto_telegram(msg)

    def send_short_signal(self, code: str):
        msg = "SHORT SIGNAL"
        self.echoto_telegram(msg)

    def beep(self) -> None:
        if GCONF.QUIET:
            return
        
        # 优先使用KafkaService，fallback到原来的producer
        if self._kafka_service:
            success = self._kafka_service.publish_message("notify", {"type": "beep"})
            if success:
                return
            GLOG.WARN("KafkaService failed, falling back to direct producer")
        
        # Fallback到原来的实现
        if self._producer:
            self._producer.send("notify", {"type": "beep"})
        # beepbeep(2000, 1, 20, 30)

    def beep_coin(self) -> None:
        if GCONF.QUIET:
            return
        
        # 优先使用KafkaService，fallback到原来的producer
        if self._kafka_service:
            success = self._kafka_service.publish_message("notify", {"type": "beep_coin"})
            if success:
                return
            GLOG.WARN("KafkaService failed, falling back to direct producer")
        
        # Fallback到原来的实现
        if self._producer:
            self._producer.send("notify", {"type": "beep"})
        # beepbeep(1920, 1, 30, 40)
        # beepbeep(2180, 1, 60, 230)
    
    def get_notification_stats(self) -> dict:
        """获取通知统计信息（利用KafkaService的统计功能）"""
        if self._kafka_service:
            try:
                stats = self._kafka_service.get_service_statistics()
                return {
                    "kafka_service_available": True,
                    "send_statistics": stats.get("send_statistics", {}),
                    "kafka_connection": stats.get("kafka_connection", {})
                }
            except Exception as e:
                GLOG.ERROR(f"Failed to get notification stats: {e}")
        
        return {
            "kafka_service_available": False,
            "producer_available": self._producer is not None
        }

    def send_message(self, message: str, target=None) -> None:
        """发送消息通知"""
        self.echo_to_telegram(message)

    def is_available(self) -> bool:
        """检查通知服务是否可用"""
        return (self._producer is not None) or (self._kafka_service is not None)


GNOTIFIER = GinkgoNotifier()
