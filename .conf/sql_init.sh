#!/bin/bash

set -e

host="localhost"
user="admin"
password="helloadmin"
shift 3
cmd="@"

until mysql -h "host" -u "user" --password="password" -e "show databases"; do
  >&2 echo "MySQL is unavailable - sleeping"
  sleep 1
done

>&2 echo "MySQL is up - executing command"
mysql -h "host" -u "user" --password="password" -e "CREATE DATABASE IF NOT EXISTS ginkgo;"

execcmd
