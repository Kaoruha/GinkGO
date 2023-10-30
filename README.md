# README
Python Backtesting library for trading research
- Vectorized Backtesting
- Event Driven Backtesting


## Secure
``` yaml
database:
  clickhouse:
    database: ginkgo
    username: admin
    password: {password ==> base64encoder}
    host: localhost
    port: 8123
  mysql:
    database: ginkgo
    username: ginkgoadmin
    password: {password ==> base64encoder}
    host: localhost
    port: 3306
  mongodb:
    database: ginkgo
    username: ginkgoadm
    password: {password ==> base64encoder}
tushare:
  token: {tokenhere}
```

## Install

``` shell
python ./install.py
```

## Create Shortcuts
``` shell
sudo ./install.sh
```

## Unittest
```
ginkgo unittest run --all -y
```

## DataUpdate
```
# After install
python ./samples/cn_share_daily_update.py
```

## Run Basic Backtest
```
# After install
python ./samples/demo_backtest.py
```
