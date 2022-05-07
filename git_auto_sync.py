import argparse
import os

codefever_url = "ssh://git@49.235.72.115:10222/Future/Ginkgo.git"
github_url = "git@github.com:Kaoruha/GinkGO.git"

if __name__ == "__main__":
    # args
    parser = argparse.ArgumentParser()
    parser.add_argument("-comment", "--comment", help="dev mode", action="store")
    parser.add_argument(
        "-debug",
        "--debug",
        help="set debug level",
        type=str,
        choices=["debug", "info", "warning", "critical"],
    )
    args = parser.parse_args()
    com = args.comment
    print(f"Your comment is {com}")

    os.system("git add .")
    os.system(f'git commit -m "{com}"')
    print("CodeFever push.")

    # 换回CodeFever源头
    print("Changing Origin to CodeFever")
    os.system("git remote rm origin")
    os.system(f"git remote add origin {codefever_url}")
    os.system('git push -u origin "main"')
    print("CodeFever push")

    # 换Github源头
    print("Changing Origin to Github")
    os.system("git remote rm origin")
    os.system(f"git remote add origin {github_url}")
    os.system('git push -u origin "master"')
    print("Github push")

    print("Changing Origin to CodeFever")
    os.system("git remote rm origin")
    os.system(f"git remote add origin {codefever_url}")
