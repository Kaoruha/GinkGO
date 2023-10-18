import typer
import os
from cmd import Cmd
from typing_extensions import Annotated
from rich.console import Console

from ginkgo.backtest.plots import CandlePlot


app = typer.Typer()


class MyPrompt(Cmd):
    prompt = "Master > "
    ans = "Ginkgo > "
    intro = f"  ______              __  __               __             __"
    intro += f"\n /_  _________  __   / / / ____ __________/ ___  _____   / /"
    intro += f"\n  / / / ___/ / / /  / /_/ / __ `/ ___/ __  / _ \/ ___/  / /"
    intro += f"\n / / / /  / /_/ /  / __  / /_/ / /  / /_/ /  __/ /     /_/"
    intro += f"\n/_/ /_/   \__, /  /_/ /_/\__,_/_/   \__,_/\___/_/     (_)"
    intro += f"\n"
    intro += f"\n"
    intro += f"{ans}Welcome!"
    intro += f"\n{ans}You can type ? to list commands"

    def app_exit(self, msg):
        print(f"{self.ans}Bye. See you soon.")
        return True

    def default(self, msg):
        exit_list = ["bye", "Bye", "BYE", "BYe", ":q"]
        if msg in exit_list:
            return self.app_exit(msg)

        # Put it into LLM
        print("Default: {}".format(msg))

    def emptyline(self):
        print(f"\n{ans}You can type ? to list commands")

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


@app.command()
def hah(
    name: Annotated[
        str, typer.Argument(help="The name of the user to greet")
    ] = "Wilson"
):
    """
    Glad to see you.
    """
    print(f"haha {name}")


@app.command()
def mail(
    name: str,
    email: Annotated[str, typer.Option(prompt=True, confirmation_prompt=True)],
):
    print(f"Hello {name}, your email is {email}")


@app.command()
def password(
    name: str,
    password: Annotated[
        str, typer.Option(prompt=True, confirmation_prompt=True, hide_input=True)
    ],
):
    print(f"Hello {name}. Doing something very secure with password.")
    print(f"...just kidding, here it is, very insecure: {password}")


@app.command()
def data_update(is_fast_on: Annotated[bool, typer.Option("--fast")] = False):
    from ginkgo.data.ginkgo_data import GDATA

    GDATA.create_all()
    GDATA.update_stock_info()
    GDATA.update_trade_calendar()
    GDATA.update_all_cn_adjustfactor_aysnc()
    GDATA.update_all_cn_daybar_aysnc()
    if is_fast_on:
        GDATA.update_all_cn_tick_aysnc(fast_mode=True)
    else:
        GDATA.update_all_cn_tick_aysnc(fast_mode=False)


@app.command()
def status():
    os.system("docker ps -a | grep ginkgo")


@app.command()
def version():
    print(f"Ginkgo version: 2.1")


@app.command()
def unittest():
    print("run testunit")


@app.command()
def interactive():
    os.system("clear")
    p = MyPrompt()
    p.cmdloop()


@app.command()
def plt_daybar(
    code: Annotated[str, typer.Argument(help="The code of Share")],
    date_start: Annotated[str, typer.Argument(help="The start of peroid.")],
    date_end: Annotated[str, typer.Argument(help="The end of period.")],
):
    """
    Plot Candle Chart.
    """
    from ginkgo.data.ginkgo_data import GDATA

    info = GDATA.get_stock_info(code)
    code_name = info.code_name
    industry = info.industry
    df = GDATA.get_daybar_df(code, date_start, date_end)
    plt = CandlePlot(f"[{industry}] {code} {code_name}")
    plt.figure_init()
    plt.update_data(df)
    plt.show()


@app.command()
def list(Target: Annotated[str, typer.Argument(help="Different kind of list stuff.")]):
    pass


@app.command()
def show(code: Annotated[str, typer.Argument(help="The code of Share")]):
    pass


if __name__ == "__main__":
    app()
