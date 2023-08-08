# README
A Python Backtest Library for trading strategies.
- Vectorized Backtesting
- Event Driven Backtesting


## Secure Example
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
python ./install 
```

## Unittest
```
python ./run_unittest.py --all
```


## Run Basic Backtest
