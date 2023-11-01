#!/bin/bash

echo "Uninstall will start after 10s."
int=9
while(( $int>0 ))
do
    echo -ne "Data will remove after $int s. You could stop this with Ctrl+c.\r"
    sleep 1
    let "int--"
done
echo "Start Uninstall..."


# Get the working directory
SCRIPT_PATH=$(dirname "$0")

# echo "Clean the configuration."
# Clean the configuration
# rm -rf ~/.ginkgo

echo "Clean Docker Containers."
# Stop the containers
docker stop clickhouse_master clickhouse_test mysql_master mysql_test redis_master

# TODO Remove the containers
docker rm -f clickhouse_master clickhouse_test mysql_master mysql_test redis_master


echo "Clean logs."
# Clean the log files and container files
sudo rm -rf  "$SCRIPT_PATH/.logs"

echo "Clean databases."
sudo rm -rf  "$SCRIPT_PATH/.db"

echo "Clean Virtual Enviroment"
sudo rm -rf  "$SCRIPT_PATH/venv"
mkdir  "$SCRIPT_PATH/.logs"
mkdir  "$SCRIPT_PATH/.db"

echo "Clean Softlink"
# Clean the soft-link
sudo rm /usr/bin/ginkgo 2>/dev/null
sudo rm /bin/ginkgo 2>/dev/null
