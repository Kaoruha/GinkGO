# Get the working directory
SCRIPT_PATH=$(dirname "$0")

# Clean the configuration
rm -rf ~/.ginkgo

# Stop the containers
docker stop clickhouse_master clickhouse_test mysql_master mysql_test redis_master

# TODO Remove the containers
docker rm -f clickhouse_master clickhouse_test mysql_master mysql_test redis_master


# Clean the log files and container files
sudo rm -rf  "$SCRIPT_PATH/.logs"
sudo rm -rf  "$SCRIPT_PATH/.db"
sudo rm -rf  "$SCRIPT_PATH/venv"
mkdir  "$SCRIPT_PATH/.logs"
mkdir  "$SCRIPT_PATH/.db"

# Clean the soft-link
sudo rm /usr/bin/ginkgo 2>/dev/null
sudo rm /bin/ginkgo 2>/dev/null
