# Upstream: GinkgoNotifier (调用echo发送Telegram消息)、run_telebot (独立线程运行)
# Downstream: telebot库(TeleBot API)、DataContainer(通过container访问file_crud/analyzer_record_crud)、ResultPlot(回测结果绘图)、GCONF(Telegram_Token/Telegram_ChatIDs/TELEGRAM_PWD)、FILE_TYPES枚举
# Role: Telegram通知Bot使用telebot库实现机器人交互提供欢迎/帮助/消息/回显等方法


from ginkgo.libs import GLOG
from ginkgo.libs.core.config import GCONF
from ginkgo.data.containers import container
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telebot.util import quick_markup
from ginkgo.enums import FILE_TYPES
import telebot
import yaml
import os

# from ginkgo.artificial_intelligence.gemma_7b import Gemma7B

import psutil

# 延迟初始化 bot，避免模块导入时因未配置 token 而失败
# 使用占位符 token（格式：botid:hash），实际使用时会检查是否配置
_token = GCONF.Telegram_Token if GCONF.Telegram_Token else "123456:ABCDEF"
bot = telebot.TeleBot(_token)
is_running = False


def _check_bot_enabled():
    """检查 Telegram Bot 是否真正配置并可用"""
    return GCONF.Telegram_Token is not None and GCONF.Telegram_Token != "123456:ABCDEF"


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
    msg += "\n" + "/compare {backtest1} {backtest2} {index1} {index2} compare backtest result"
    msg += "\n" + "/show {uuid} display the detail"
    msg += "\n" + "/signals show recent 10 signals"
    bot.send_message(message.chat.id, msg)


is_thinking = False
ai_bot = None


# @bot.message_handler()
# def send_chat(message):
#     global is_thinking
#     global ai_bot
#     if ai_bot is None:
#         ai_bot = Gemma7B()
#     if not is_thinking:
#         is_thinking = True
#         try:
#             msg = ai_bot.think(message.text)
#             print("=====================")
#             print(msg)
#             print(type(msg))
#             print("=====================")
#             bot.reply_to(message, msg)
#             is_thinking = False
#         except Exception as e:
#             print(e)
#             is_thinking = False
#     else:
#         bot.reply_to(message, "I am tinking.")
#         return


@bot.message_handler(commands=["status"])
def status_handler(message):
    msg = f"CPU RATIO : {GCONF.CPURATIO*100}%"
    bot.send_message(message.chat.id, msg)
    # Get CPU usage as a percentage
    cpu_usage = psutil.cpu_percent()
    bot.send_message(message.chat.id, f"CPU Usage: {cpu_usage}%")

    # Get RAM usage
    memory_usage = psutil.virtual_memory().percent
    bot.send_message(message.chat.id, f"RAM Usage: {memory_usage}%")

    temperatures = psutil.sensors_temperatures()

    for i in temperatures.keys():
        bot.send_message(message.chat.id, f"Sensor: {i}")
        for entry in temperatures[i]:
            bot.send_message(
                message.chat.id,
                f"{entry.label} Temperature: {entry.current}°C",
            )


@bot.message_handler(commands=["list"])
def list_handler(message):
    button = {
        "Backtest": {"callback_data": "list_backtest_strategies"},
        "Live": {"callback_data": "list_live_strategies"},
    }
    bot.send_message(
        message.chat.id,
        "Choose the type of data you want to display:",
        reply_markup=quick_markup(button, row_width=4),
    )


def get_backtest_strategies():
    file_crud = container.cruds.file()
    raw = file_crud.get_page_filtered(type=FILE_TYPES.ENGINE.value)
    res = []
    count = 0
    for i, r in raw.iterrows():
        count += 1
        id = r["uuid"]
        content = r["content"]
        name = yaml.safe_load(content.decode("utf-8"))["name"]
        res.append(f"{count}. {name} {id}\n")
    return res


def get_live_strategies():
    msg = "Live Strategy Callback"
    return msg


@bot.message_handler(commands=["verify"])
def verify_handler(message):
    msg = bot.send_message(message.chat.id, "Please type your token")
    bot.register_next_step_handler(msg, verify_next)


@bot.message_handler(commands=["address"])
def address_handler(message):
    msg = bot.send_message(message.chat.id, "Please type your token")
    bot.register_next_step_handler(msg, get_address)


def get_address(message):
    if message.text == GCONF.TELEGRAM_PWD:
        ip = os.popen("curl myip.ipip.net").read()
        bot.reply_to(message, f"{ip}")


def verify_next(message):
    bot.reply_to(message, f"Token {message.text} not exists.", reply_markup=ReplyKeyboardRemove())


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
        res = get_backtest_strategies()
        for i in res:
            bot.send_message(message.chat.id, i)
        return

    # #6448: notifier → client 反向依赖已解除；Telegram 触发回测已禁用，请用 CLI 跑
    bot.reply_to(
        message,
        "Backtest via Telegram is disabled. Run via CLI: `ginkgo backtest run <uuid>`",
    )


def _get_backtest_service():
    return container.backtest_task_service()


def _is_success(result) -> bool:
    if result is None:
        return False
    if hasattr(result, "is_success"):
        return bool(result.is_success())
    return bool(getattr(result, "success", False))


def _error_text(result) -> str:
    if result is None:
        return "Unknown service error"
    return getattr(result, "error", "") or getattr(result, "message", "") or "Unknown service error"


def _value(record, *names, default="-"):
    for name in names:
        if isinstance(record, dict):
            value = record.get(name)
        else:
            value = getattr(record, name, None)
        if value not in (None, ""):
            return value
    return default


def _task_items(data):
    if isinstance(data, dict):
        items = data.get("data", data.get("items", []))
    else:
        items = data or []
    if hasattr(items, "to_dict"):
        items = items.to_dict("records")
    return list(items)


def _format_backtest_task(index: int, record) -> str:
    task_id = _value(record, "uuid", "task_id", "backtest_id")
    name = _value(record, "name", "engine_name", default="")
    status = _value(record, "status", default="-")
    pnl = _value(record, "total_pnl", "profit", default="-")
    start_at = _value(record, "start_at", "start_time", "create_at", default="-")
    finish_at = _value(record, "finish_at", "end_time", "update_at", default="-")
    label = f"{name} {task_id}".strip()
    return f"[{index}]. {label}\nStatus: {status}\nWorth: {pnl}\nfrom {start_at} to {finish_at}"


def _send_backtest_task_list(message, intro: str):
    service = _get_backtest_service()
    result = service.list()
    bot.reply_to(message, intro)
    if not _is_success(result):
        bot.send_message(message.chat.id, f"Failed to list backtests: {_error_text(result)}")
        return

    records = _task_items(result.data)[:20]
    if len(records) == 0:
        bot.send_message(message.chat.id, "No backtest tasks found.")
        return

    for i, record in enumerate(records, 1):
        bot.send_message(message.chat.id, _format_backtest_task(i, record))


def _format_comparison(data) -> str:
    metrics = data.get("metrics", {}) if isinstance(data, dict) else {}
    if not metrics:
        return "No comparison metrics found."

    lines = ["Backtest comparison:"]
    for metric_name, values in metrics.items():
        lines.append(f"{metric_name}:")
        if isinstance(values, dict):
            for task_id, value in values.items():
                lines.append(f"  {task_id}: {value}")
        else:
            lines.append(f"  {values}")
    return "\n".join(lines)


def _format_result_summary(data) -> str:
    if not isinstance(data, dict):
        return str(data)

    lines = [f"Backtest: {data.get('task_id', data.get('uuid', '-'))}"]
    for field in ("engine_id", "portfolio_count", "analyzer_count", "total_records"):
        if field in data:
            lines.append(f"{field}: {data[field]}")
    if data.get("portfolios"):
        lines.append(f"portfolios: {', '.join(map(str, data['portfolios']))}")
    if data.get("analyzers"):
        lines.append(f"analyzers: {', '.join(map(str, data['analyzers']))}")
    time_range = data.get("time_range")
    if isinstance(time_range, dict):
        lines.append(f"time_range: {time_range.get('start', '-')} to {time_range.get('end', '-')}")
    return "\n".join(lines)


@bot.message_handler(commands=["compare"])
def compare_backtest(message):
    args = extract_arg(message.text)
    if len(args) < 2:
        _send_backtest_task_list(
            message,
            "You could provide 2 backtest ids. For example: /compare {uuid_1} {uuid_2}",
        )
        return

    service = _get_backtest_service()
    result = service.compare(args[:2])
    if not _is_success(result):
        bot.reply_to(message, f"Failed to compare backtests: {_error_text(result)}")
        return

    bot.send_message(message.chat.id, _format_comparison(result.data or {}))
    if len(args) > 2:
        bot.send_message(
            message.chat.id,
            "Analyzer plot comparison is not available through Telegram. Use /res {uuid} for summary.",
        )


@bot.message_handler(commands=["res"])
def res_backtest(message):
    args = extract_arg(message.text)
    if len(args) == 0:
        _send_backtest_task_list(
            message,
            "You could provide a backtest id to confirm the detail. For example: /res {uuid}",
        )
        return
    if len(args) > 1:
        bot.reply_to(
            message,
            "Analyzer detail plots are not available through Telegram. Use /res {uuid} for summary.",
        )
        return

    backtest_id = args[0]
    service = _get_backtest_service()
    result = service.get_results(backtest_id)
    if not _is_success(result):
        bot.reply_to(message, f"Failed to get backtest result: {_error_text(result)}")
        return

    bot.send_message(message.chat.id, _format_result_summary(result.data))


@bot.callback_query_handler(func=lambda call: True)
def refresh(call):
    if call.data == "list_backtest_strategies":
        bot.reply_to(call.message, "Here are the backtest strategies:")
        res = get_backtest_strategies()
        for i in res:
            try:
                bot.send_message(call.message.chat.id, i)
            except Exception as e:
                GLOG.ERROR(e)

        bot.answer_callback_query(call.id)
    elif call.data == "list_live_strategies":
        msg = get_live_strategies()
        bot.send_message(call.message.chat.id, msg)
        bot.answer_callback_query(call.id)


@bot.message_handler(content_types=["audio", "document"])
def audio_handler(message):
    bot.reply_to(message, "Can not handle audio files.")


def echo(message: str) -> None:
    """
    Echo to Everyone in Telegram_ChatIDs.
    Args:
        message(str): message to be send.
    Returns:
        None
    """
    # 检查 bot 是否真正配置
    if not _check_bot_enabled():
        return

    ids = GCONF.Telegram_ChatIDs
    if len(ids) > 20:
        ids = ids[:20]
    for chat_id in ids:
        try:
            bot.send_message(chat_id, message)
        except Exception as e:
            GLOG.ERROR(e)


def run_telebot():
    # 检查 bot 是否真正配置
    if not _check_bot_enabled():
        GLOG.WARNING(f"Telegram Bot not configured, skipping bot startup")
        return
    bot.infinity_polling()
