from cmd import Cmd
from rich.console import Console
import signal
import sys
import time
import os
import requests
import json


# 定义全局变量来计数 Ctrl+C 按下次数
ctrl_c_count = 0
exit_threshold = 3  # 设置按下次数的阈值


# 自定义信号处理函数
def handle_ctrl_c(signum, frame):
    global ctrl_c_count
    ctrl_c_count += 1
    remaining = exit_threshold - ctrl_c_count

    if remaining > 0:
        console.print(f"\nYou need try more to exit or you could type `bye`")
    else:
        console.print("\nSee you soon.")
        # raise KeyboardInterrupt
        sys.exit(0)


# 设置自定义处理函数
signal.signal(signal.SIGINT, handle_ctrl_c)


console = Console()
ans = "Ginkgo > "

mem = ""


def print(string):
    """
    Override the global print function.
    Support Emoji and Style in rich.
    """
    sys.stdout.write(ans)
    for char in string:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.01)
    sys.stdout.write("\x1b[2K" * len(string))
    sys.stdout.write("\r")
    console.print(f"{ans}{string}")


def chunk_print(response):
    global mem
    # 逐块读取流式数据
    console.print(ans, end="")
    for chunk in response.iter_lines(decode_unicode=True):
        if chunk:
            try:
                data = json.loads(chunk)
                msg = data["response"]
                console.print(msg, end="")
                mem += msg
            except Exception as e:
                console.print(f"mem len: {len(mem)}")
                mem = ""
                console.print("something wrong with response, the session will restart.")
    sys.stdout.write("\n")
    sys.stdout.write("\n")


def ask_ollama(msg: str):
    global mem
    mem += msg
    url = "http://localhost:11434/api/generate"
    payload = {"model": "mistral:latest", "prompt": mem}
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers, stream=True)
    # 逐块读取流式数据
    chunk_print(response)


class MyPrompt(Cmd):
    prompt = "Master > "
    # ans = "Ginkgo > "
    intro = "  ______              __  __               __             __"
    intro += "\n /_  _________  __   / / / ____ __________/ ___  _____   / /"
    intro += "\n  / / / ___/ / / /  / /_/ / __ `/ ___/ __  / _ / ___/  / /"
    intro += "\n / / / /  / /_/ /  / __  / /_/ / /  / /_/ /  __/ /     /_/"
    intro += "\n/_/ /_/   \\__, /  /_/ /_/\\__,_/_/   \\__,_/\\___/_/     (_)"
    intro += "\n           _/ /"
    intro += "\n         /___/"
    intro += "\n"
    intro += "\n"
    intro += f"{ans}Welcome!"
    intro += f"\n{ans}You can type ? to list commands"

    def app_exit(self, msg):
        print(f"Bye. See you soon. :four_leaf_clover:")
        return True

    def default(self, msg):
        global ctrl_c_count
        ctrl_c_count = 0
        exit_list = ["bye", "Bye", "BYE", "BYe", ":q", ":q!", ":qa"]
        if msg in exit_list:
            return self.app_exit(msg)

        ask_ollama(msg)

    def emptyline(self):
        # TODO
        pass

    def do_clear(self, msg):
        os.system("clear")
        global mem
        mem = ""

    def do_add(self, msg):
        # TODO
        print(f"add {msg}")

    def do_code_check(self, file_name):
        def find_and_read_file(directory, filename):
            """
            遍历指定目录及其子目录，查找与文件名匹配的文件并读取其内容。

            :param directory: 要搜索的目录路径
            :param filename: 要匹配的文件名
            :return: 如果找到文件，返回文件内容；如果没有找到，返回提示信息
            """

            for root, dirs, files in os.walk(directory):
                # 遍历文件夹中的每个文件
                for file in files:
                    if file == filename:
                        # 找到匹配的文件，打开并读取内容
                        file_path = os.path.join(root, file)
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        return content
            return f"文件 {filename} 未找到"
            # 示例用法

        directory = "/home/kaoru/Applications/Ginkgo"  # 请替换为实际目录路径
        content = find_and_read_file(directory, file_name)
        console.print(content)
        ask_ollama(content)

    def do_log_analyze(self, id):
        # TODO
        print(f"analyze {id}")
        file_name = f"bt_{id}.log"
        path = "/home/kaoru/.ginkgo/logs"
        content = ""
        max_line = 20
        logs = []
        try:
            with open(f"{path}/{file_name}", "r") as file:
                for line in file:
                    if "]:" not in line:
                        continue
                    logs.append(line.split("]:")[1])

                for i in range(0, len(logs), max_line):
                    batch = logs[i : i + max_line]
                    console.print(batch)
                    global mem
                    mem = ""
                    mem += (
                        "请根据之后提供的log帮我分析回测流程中是否存在逻辑问题,如果有例如前后矛盾或者无中生有等问题\n"
                    )
                    for j in content:
                        mem += j
                    ask_ollama(mem)
                    time.sleep(5)
        except Exception as e:
            print(e)
        finally:
            pass

    def help_add(self):
        # TODO
        print("Add a new entry to the system.")

    def do_data_update(self, msg):
        if msg == "fast":
            pass
        else:
            pass

    def help_data_update(self):
        # TODO
        print("Update All Data.")

    def do_health_check(self, msg):
        # TODO
        print("call ginkgo status later")

    def help_health_check(self):
        # TODO
        print("Check the status of Ginkgo.")

    def do_unittest(self, msg):
        # TODO
        print("call ginkgo test later")

    def help_unittest(self):
        print("Usage: pytest run --[mode] (unittest deprecated)")
        print("  -db     Run database units.")
        print("  -data   Run data-source relative units.")
        print("  -base   Run framework basic units.")
        print("  -libs   Run framework base libs.")
        print("  -backtest   Run Backtest Untis.")

    def do_plt_daybar(self, msg):
        # TODO
        print("call ginkgo plt later")

    def help_plt_daybar(self):
        print("Plot Candle Chart.")
