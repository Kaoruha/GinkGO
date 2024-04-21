from src.ginkgo.libs.ginkgo_conf import GCONF
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telebot.util import quick_markup
from src.ginkgo.data.ginkgo_data import GDATA
from src.ginkgo.enums import FILE_TYPES
from src.ginkgo.backtest.plots.result_plot import ResultPlot
import telebot
import shutil
import yaml
import os
from src.ginkgo.artificial_intelligence.gemma_7b import Gemma7B

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
    msg += (
        "\n"
        + "/compare {backtest1} {backtest2} {index1} {index2} compare backtest result"
    )
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
        "Backtest": {"callback_data": "list_backtest_strategies"},
        "Live": {"callback_data": "list_live_strategies"},
    }
    bot.send_message(
        message.chat.id,
        "Choose the type of data you want to display:",
        reply_markup=quick_markup(button, row_width=4),
    )


def get_backtest_strategies():
    raw = GDATA.get_file_list_df(FILE_TYPES.BACKTEST.value)
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
        res = get_backtest_strategies()
        for i in res:
            bot.send_message(message.chat.id, i)
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


@bot.message_handler(commands=["compare"])
def compare_backtest(message):
    raw = GDATA.get_backtest_list_df().head(20)
    raw = raw.reindex(columns=["backtest_id", "profit", "start_at", "finish_at"])
    if len(message.text.split()) <= 2:
        bot.reply_to(
            message,
            "You could provide 2 backtest ids to confirm the detail.  For example: /res {uuid_1} {uuid_2}",
        )
        for i, r in raw.iterrows():
            bot.send_message(
                message.chat.id,
                f"[{i}]. {r['backtest_id']} \nWorth: {r['profit']} \nfrom {r['start_at']} to {r['finish_at']}",
            )
        return

    backtest_id1 = extract_arg(message.text)[0]
    backtest_id2 = extract_arg(message.text)[1]
    record1 = GDATA.get_backtest_record(backtest_id1)
    record2 = GDATA.get_backtest_record(backtest_id2)

    if len(message.text.split()) == 3:
        if record1 is None or record2 is None:
            bot.reply_to(message, "Ne such backtest record.")
            for i, r in raw.iterrows():
                bot.send_message(
                    message.chat.id,
                    f"[{i}]. {r['uuid']} \nWorth: {r['profit']} \nfrom {r['start_at']} to {r['finish_at']}",
                )
            return
        content1 = record1.content
        content2 = record2.content
        analyzers1 = yaml.safe_load(content1.decode("utf-8"))["analyzers"]
        analyzers1 = {i["id"]: i["parameters"][0] for i in analyzers1}
        analyzers2 = yaml.safe_load(content2.decode("utf-8"))["analyzers"]
        analyzers2 = {i["id"]: i["parameters"][0] for i in analyzers2}
        keys1 = list(analyzers1.keys())
        keys2 = list(analyzers2.keys())
        same_keys = list(set(keys1).intersection(set(keys2)))
        if len(same_keys) == 0:
            bot.send_message(message.chat.id, "No Related Analyzer.")
            return

        bot.send_message(
            message.chat.id,
            "You could type /res {back1} {back2} {analyzer} to get the detail.",
        )
        for i in same_keys:
            bot.send_message(message.chat.id, analyzers1[i])
            bot.send_message(message.chat.id, i)
        return

    if len(message.text.split()) >= 3:
        plot = ResultPlot("Backtest")
        fig_data1 = {}
        fig_data2 = {}
        for analyzer_id in extract_arg(message.text)[2:]:
            df = GDATA.get_analyzer_df_by_backtest(backtest_id1, analyzer_id)
            if df.shape[0] == 0:
                bot.reply_to(message, "No such analyzer record. Please check the id.")
                return
            pic_name = f"{backtest_id1}.{analyzer_id}.png"
            pic_path = os.path.join(GCONF.get_conf_dir(), pic_name)
            # Gen Pic
            content = record1.content
            analyzers = yaml.safe_load(content.decode("utf-8"))["analyzers"]
            analyzer_name = "TestName"
            for i in analyzers:
                if i["id"] == analyzer_id:
                    analyzer_name = i["parameters"][0]
                    break
            fig_data1[analyzer_name] = df

            df = GDATA.get_analyzer_df_by_backtest(backtest_id2, analyzer_id)
            if df.shape[0] == 0:
                bot.reply_to(message, "No such analyzer record. Please check the id.")
                return
            fig_data2[analyzer_name] = df
    plot.update_data(
        f"{backtest_id1} vs {backtest_id2}",
        [fig_data1, fig_data2],
        [backtest_id1, backtest_id2],
    )
    plot.save_plot(pic_path)
    photo = open(pic_path, "rb")
    try:
        shutil.os.remove(pic_path)
    except Exception as e:
        print(e)
        pass
    bot.send_photo(message.chat.id, photo)


@bot.message_handler(commands=["res"])
def res_backtest(message):
    raw = GDATA.get_backtest_list_df()
    raw = raw.reindex(columns=["backtest_id", "profit", "start_at", "finish_at"])
    if len(message.text.split()) == 1:
        bot.reply_to(
            message,
            "You could provide a backtest id to confirm the detail.  For example: /res {uuid}",
        )
        for i, r in raw.iterrows():
            bot.send_message(
                message.chat.id,
                f"[{i}]. {r['backtest_id']} \nWorth: {r['profit']} \nfrom {r['start_at']} to {r['finish_at']}",
            )
        return

    backtest_id = extract_arg(message.text)[0]
    record = GDATA.get_backtest_record(backtest_id)

    if len(message.text.split()) == 2:
        if record is None:
            bot.reply_to(message, "No such backtest record.")
            for i, r in raw.iterrows():
                bot.send_message(
                    message.chat.id,
                    f"[{i}]. {r['uuid']} \nWorth: {r['profit']} \nfrom {r['start_at']} to {r['finish_at']}",
                )
            return
        bot.send_message(
            message.chat.id, f"Backtest: {backtest_id}  \nWorth: {record.profit}"
        )
        content = record.content
        analyzers = yaml.safe_load(content.decode("utf-8"))["analyzers"]
        if len(analyzers) == 0:
            bot.send_message(message.chat.id, "No Analyzer.")
            return
        bot.send_message(
            message.chat.id,
            "You could type /res {backtest} {analyzer} to get the detail.",
        )
        for i in analyzers:
            bot.send_message(
                message.chat.id,
                i["parameters"][0],
            )
            bot.send_message(
                message.chat.id,
                i["id"],
            )

    if len(message.text.split()) >= 3:
        backtest_id = extract_arg(message.text)[0]
        plot = ResultPlot("Backtest")
        fig_data = {}
        for analyzer_id in extract_arg(message.text)[1:]:
            df = GDATA.get_analyzer_df_by_backtest(backtest_id, analyzer_id)
            if df.shape[0] == 0:
                bot.reply_to(message, "No such analyzer record. Please check the id.")
                return
            pic_name = f"{backtest_id}.{analyzer_id}.png"
            pic_path = os.path.join(GCONF.get_conf_dir(), pic_name)
            # Gen Pic
            content = record.content
            analyzers = yaml.safe_load(content.decode("utf-8"))["analyzers"]
            analyzer_name = "TestName"
            for i in analyzers:
                if i["id"] == analyzer_id:
                    analyzer_name = i["parameters"][0]
                    break
            fig_data[analyzer_name] = df
        plot.update_data(backtest_id, [fig_data], [backtest_id])
        plot.save_plot(pic_path)
        photo = open(pic_path, "rb")
        try:
            shutil.os.remove(pic_path)
        except Exception as e:
            print(e)
            pass
        bot.send_photo(message.chat.id, photo)


@bot.callback_query_handler(func=lambda call: True)
def refresh(call):
    if call.data == "list_backtest_strategies":
        bot.reply_to(call.message, "Here are the backtest strategies:")
        res = get_backtest_strategies()
        for i in res:
            try:
                bot.send_message(call.message.chat.id, i)
            except Exception as e:
                print(e)

        bot.answer_callback_query(call.id)
    elif call.data == "list_live_strategies":
        msg = get_live_strategies()
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
        try:
            bot.send_message(chat_id, message)
        except Exception as e:
            print(e)


def run_telebot():
    bot.infinity_polling()
