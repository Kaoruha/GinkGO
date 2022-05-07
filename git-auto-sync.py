import argparse
import os

codedev_url = "ssh://git@49.235.72.115:10222/Future/Ginkgo.git"
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
    print(com)
    os.system("git add .")
    os.system(f'git commit -m "{com}"')
    os.system("git push")
