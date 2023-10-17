import typer
import os
from typing_extensions import Annotated


app = typer.Typer()


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
def dataupdate(is_fast_on: Annotated[bool, typer.Option("--fast")] = False):
    if is_fast_on:
        print("Update in fast mode.")
    else:
        print("Update in normal mode.")


@app.command()
def status():
    os.system("docker ps -a | grep ginkgo")


@app.command()
def version():
    print(f"Ginkgo version: 2.1")


@app.command()
def interactive():
    print("Go into chat mode.")


if __name__ == "__main__":
    app()
