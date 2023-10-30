# Get the working directory

# Clean the configuration

rm -df ~/.ginkgo

# Stop the containers
docker stop -f ginkgo_ch ginkgo_ch_test ginkgo_ms ginkgo_ms_test ginkgo_redis

# TODO Remove the containers
docker rm -f ginkgo_ch ginkgo_ch_test ginkgo_ms ginkgo_ms_test ginkgo_redis


# Clean the log files and container files
# TODO
# Remove .log .db
