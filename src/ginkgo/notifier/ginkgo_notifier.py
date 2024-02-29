from src.ginkgo.data.ginkgo_data import GDATA
from src.ginkgo.libs.ginkgo_logger import GLOG
from src.ginkgo.notifier.notifier_telegram import (
    run_telebot as run_telegram_bot_api_server,
)
from src.ginkgo.notifier.notifier_telegram import echo
from src.ginkgo.notifier.notifier_beep import beep as beepbeep
import threading
import signal
import psutil
import os


class GinkgoNotifier(object):
    def __init__(self):
        pass

    @property
    def telebot_status(self) -> str:
        temp_redis = GDATA.get_redis()
        cache_name = "telebot_pid"
        if temp_redis.exists(cache_name):
            cache = temp_redis.get(cache_name).decode("utf-8")
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
        temp_redis = GDATA.get_redis()
        cache_name = "telebot_pid"
        if temp_redis.exists(cache_name):
            cache = temp_redis.get(cache_name).decode("utf-8")
            try:
                proc = psutil.Process(int(cache))
                if proc.is_running():
                    os.kill(int(cache), signal.SIGKILL)
            except Exception as e:
                GLOG.DEBUG(e)

    def run_telebot(self) -> None:
        self.kill_telebot()
        # Start new woker

        cache_name = "telebot_pid"
        pid = os.getpid()
        temp_redis = GDATA.get_redis()
        temp_redis.set(cache_name, str(pid))
        t = threading.Thread(target=run_telegram_bot_api_server)
        t.start()
        t.join()

    def echo_to_telegram(self, message: str):
        echo(message)

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

    def beep(self, freq=2000.7, repeat=1, delay=20, length=30):
        beepbeep(freq, repeat, delay, length)


GNOTIFIER = GinkgoNotifier()
