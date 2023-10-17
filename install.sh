# cmd = f"sudo echo '{env}/bin/python {wd}/main.py' > /usr/bin/ginkgo_cli"
SHELL_FOLDER=$(dirname $(readlink -f "$0"))
echo $SHELL_FOLDER
sudo echo $SHELL_FOLDER/venv/bin/python $SHELL_FOLDER/main.py > /usr/bin/ginkgocli
sudo chmod +x /usr/bin/ginkgocli
