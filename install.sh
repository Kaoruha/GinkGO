# cmd = f"sudo echo '{env}/bin/python {wd}/main.py' > /usr/bin/ginkgo_cli"
SHELL_FOLDER=$(dirname $(readlink -f "$0"))
sudo rm /usr/bin/ginkgo 2>/dev/null
sudo echo $SHELL_FOLDER/venv/bin/python $SHELL_FOLDER/main.py \$@> /usr/bin/ginkgo
sudo chmod +x /usr/bin/ginkgo

echo "If you could see this under your command, it seems nothing wrong happend, you could type ginkgocli to use Ginkgo. Have Fun."
