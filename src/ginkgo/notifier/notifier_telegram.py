from src.ginkgo.libs.ginkgo_conf import GCONF
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telebot.util import quick_markup
import telebot


bot = telebot.TeleBot(GCONF.Telegram_Token)


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
    msg += "\n" + "/show display the detail"
    msg += "\n" + "/signals show recent 10 signals"
    bot.send_message(message.chat.id, msg)


@bot.message_handler(commands=["status"])
def status_handler(message):
    msg = bot.send_message(message.chat.id, "Show status")


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
    msg = "Backtest Records Callback"
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


def send_long_signal(signal_id: str):
    msg = "LONG SIGNAL"
    msg += "\n" + "ID: " + signal_id
    msg += "\n" + "FROM: " + "Signal via signal_id source"
    msg += "\n" + "CODE: " + "000001.SZ"
    msg += "\n" + "VOLE: " + "1000"
    msg += "\n" + "TIME: " + "2021-01-01 00:00:00"
    echo(msg)


def send_short_signal(code: str):
    msg = "SHORT SIGNAL"
    pass


def run_telebot():
    bot.infinity_polling()
