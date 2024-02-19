from src.ginkgo.libs.ginkgo_conf import GCONF
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telebot.util import quick_markup
from src.ginkgo.data.ginkgo_data import GDATA
from src.ginkgo.enums import FILE_TYPES
import telebot
import yaml
import os

import psutil

bot = telebot.TeleBot(GCONF.Telegram_Token)
is_running = False


def extract_arg(arg):
    return arg.split()[1:]


@bot.message_handler(commands=["start", "hello"])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "Welcome to Ginkgo, What can I do for you? You could type /help to get the commands",
    )


@bot.message_handler(commands=["help"])
def send_help(message):
    msg = "/status check ginkgo status"
    msg += "\n" + "/list show all live strategies"
    msg += "\n" + "/verify get authentification"
    msg += "\n" + "/run {uuid} run backtest by uuid"
    msg += "\n" + "/res {uuid} show backtest result by uuid(optional)"
    msg += "\n" + "/show {uuid} display the detail"
    msg += "\n" + "/signals show recent 10 signals"
    bot.send_message(message.chat.id, msg)


@bot.message_handler(commands=["status"])
def status_handler(message):
    msg = f"CPU RATIO: {GDATA.cpu_ratio}"
    bot.send_message(message.chat.id, msg)
    # Get CPU usage as a percentage
    cpu_usage = psutil.cpu_percent()
    bot.send_message(message.chat.id, f"CPU Usage: {cpu_usage}%")

    temperatures = psutil.sensors_temperatures()

    for i in temperatures.keys():
        bot.send_message(message.chat.id, f"Sensor: {i}")
        for entry in temperatures[i]:
            bot.send_message(
                message.chat.id,
                f"{entry.label} Temperature: {entry.current}°C",
            )

    # Get RAM usage
    memory_usage = psutil.virtual_memory().percent
    bot.send_message(message.chat.id, f"RAM Usage: {memory_usage}%")
    msg = f"REDIS WORKER: {GDATA.redis_worker_status}"
    bot.send_message(message.chat.id, msg)


@bot.message_handler(commands=["list"])
def list_handler(message):
    button = {
        "Backtest": {"callback_data": "list_backtest_records"},
        "Live": {"callback_data": "list_live_strategy"},
    }
    bot.send_message(
        message.chat.id,
        "Choose the type of data you want to display:",
        reply_markup=quick_markup(button, row_width=2),
    )


def list_backtest_records():
    raw = GDATA.get_file_list_df(FILE_TYPES.BACKTEST.value)
    msg = ""
    count = 0
    for i, r in raw.iterrows():
        count += 1
        id = r["uuid"]
        content = r["content"]
        name = yaml.safe_load(content.decode("utf-8"))["name"]
        msg += f"{count}. {name} {id}\n"
    return msg


def list_live_strategy():
    msg = "Live Strategy Callback"
    return msg


@bot.message_handler(commands=["verify"])
def verify_handler(message):
    msg = bot.send_message(message.chat.id, "Please type your token")
    bot.register_next_step_handler(msg, verify_next)


def verify_next(message):
    bot.reply_to(
        message, f"Token {message.text} not exists.", reply_markup=ReplyKeyboardRemove()
    )


@bot.message_handler(commands=["show"])
def show_handler(message):
    if len(message.text.split()) != 2:
        bot.reply_to(message, "Please type uuid. For example: /show {uuid}")
        return

    uuid = extract_arg(message.text)[0]
    msg = bot.reply_to(message, f"this is your uuid: {uuid}, fake search")


@bot.message_handler(commands=["signals"])
def status_handler(message):
    msg = bot.reply_to(message, "Show signals")


@bot.message_handler(commands=["run"])
def run_backtest(message):
    if len(message.text.split()) != 2:
        bot.reply_to(message, "Please type uuid. For example: /run {uuid}")
        return

    uuid = extract_arg(message.text)[0]
    from src.ginkgo.client.backtest_cli import run as run_backtest

    global is_running

    if not is_running:
        is_running = True
        run_backtest(uuid)
        is_running = False
    else:
        bot.reply_to(message, "Please wait for the previous backtest to finish.")
        return


@bot.message_handler(commands=["res"])
def res_backtest(message):
    if len(message.text.split()) != 2:
        bot.reply_to(message, "Could type uuid. For example: /res {uuid}")
        raw = GDATA.get_backtest_list_df().head(10)
        for i, r in raw.iterrows():
            bot.send_message(
                message.chat.id,
                f"{r['uuid']} Worth: {r['profit']} \nfrom {r['start_at']} to {r['finish_at']}",
            )
        return

    uuid = extract_arg(message.text)[0]


@bot.callback_query_handler(func=lambda call: True)
def refresh(call):
    if call.data == "list_backtest_records":
        msg = list_backtest_records()
        bot.send_message(call.message.chat.id, msg)
        bot.answer_callback_query(call.id)
    elif call.data == "list_live_strategy":
        msg = list_live_strategy()
        bot.send_message(call.message.chat.id, msg)
        bot.answer_callback_query(call.id)


@bot.message_handler(content_types=["audio", "document"])
def audio_handler(message):
    bot.reply_to(message, "Can not handle audio files.")


def echo(message: str):
    ids = GCONF.Telegram_ChatIDs
    if len(ids) > 20:
        ids = ids[:20]
    for chat_id in ids:
        bot.send_message(chat_id, message)


def run_telebot():
    bot.infinity_polling()
