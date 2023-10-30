from cmd import Cmd
from rich.console import Console
import sys
import time
import os


console = Console()
ans = "Ginkgo > "


def print(string):
    """
    Override the global print function.
    Support Emoji and Style in rich.
    """
    sys.stdout.write(ans)
    for char in string:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.04)
    sys.stdout.write("\x1b[2K" * len(string))
    sys.stdout.write("\r")
    console.print(f"{ans}{string}")


class MyPrompt(Cmd):
    prompt = "Master > "
    # ans = "Ginkgo > "
    intro = f"  ______              __  __               __             __"
    intro += f"\n /_  _________  __   / / / ____ __________/ ___  _____   / /"
    intro += f"\n  / / / ___/ / / /  / /_/ / __ `/ ___/ __  / _ \/ ___/  / /"
    intro += f"\n / / / /  / /_/ /  / __  / /_/ / /  / /_/ /  __/ /     /_/"
    intro += f"\n/_/ /_/   \__, /  /_/ /_/\__,_/_/   \__,_/\___/_/     (_)"
    intro += f"\n           _/ /"
    intro += f"\n         /___/"
    intro += f"\n"
    intro += f"\n"
    intro += f"{ans}Welcome!"
    intro += f"\n{ans}You can type ? to list commands"

    def app_exit(self, msg):
        print(f"Bye. See you soon. :four_leaf_clover:")
        return True

    def default(self, msg):
        exit_list = ["bye", "Bye", "BYE", "BYe", ":q", ":q!", ":qa"]
        if msg in exit_list:
            return self.app_exit(msg)

        # TODO Put it into LLM
        print("Default: {}".format(msg))

    def emptyline(self):
        pass

    def do_clear(self, msg):
        os.system("clear")

    def do_add(self, msg):
        print(f"add {msg}")

    def help_add(self):
        print("Add a new entry to the system.")

    def do_data_update(self, msg):
        if msg == "fast":
            data_update(True)
        else:
            data_update(False)

    def help_data_update(self):
        print("Update All Data.")

    def do_health_check(self, msg):
        status()

    def help_health_check(self):
        print("Check the status of Ginkgo.")

    def do_unittest(self, msg):
        unittest()

    def help_unittest(self):
        print("Usage: unittest --[mode]")
        print("  -db     Run database units.")
        print("  -data   Run data-source relative units.")
        print("  -base   Run framework basic units.")
        print("  -libs   Run framework base libs.")
        print("  -backtest   Run Backtest Untis.")

    def do_plt_daybar(self, msg):
        from ginkgo.data.ginkgo_data import GDATA

        code = typer.prompt("What's the code?")
        info = GDATA.get_stock_info(code)
        date_start = typer.prompt("What's the start?")
        date_end = typer.prompt("What's the end?")
        code_name = info.code_name
        industry = info.industry
        df = GDATA.get_daybar_df(code, date_start, date_end)
        plt = CandlePlot(f"[{industry}] {code} {code_name}")
        plt.figure_init()
        plt.update_data(df)
        plt.show()

    def help_plt_daybar(self):
        print("Plot Candle Chart.")
