import threading
import signal
import psutil
import os

from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer, GinkgoConsumer
from ginkgo.data.drivers import create_redis_connection
from ginkgo.notifier.notifier_telegram import echo
from ginkgo.notifier.notifier_beep import beep as beepbeep
from ginkgo.notifier.notifier_telegram import (
    run_telebot as run_telegram_bot_api_server,
)
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import GLOG
from ginkgo.libs.ginkgo_thread import GinkgoThreadManager

gtm = GinkgoThreadManager()


class GinkgoNotifier(object):
    def __init__(self):
        self._producer = None
        try:
            self._producer = GinkgoProducer()
        except Exception as e:
            print(e)
        self.telebot_pname = gtm.get_thread_cache_name("telebot")
        pass

    @property
    def telebot_status(self) -> str:
        temp_redis = create_redis_connection()
        if temp_redis.exists(self.telebot_pname):
            cache = temp_redis.get(self.telebot_pname).decode("utf-8")
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
        self._producer.send("notify", {"type": "beep"})
        # beepbeep(2000, 1, 20, 30)

    def beep_coin(self) -> None:
        if GCONF.QUIET:
            return
        self._producer.send("notify", {"type": "beep"})
        # beepbeep(1920, 1, 30, 40)
        # beepbeep(2180, 1, 60, 230)


GNOTIFIER = GinkgoNotifier()
