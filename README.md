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
### Create a new virtual environment.
### Follow the instructions to install.

``` shell
python3 -m virtualenv venv;source venv/bin/activate

python ./install.py
```


``` shell
ginkgo --help
```

## Interactive Mode
``` shell
ginkgo interactive
```

## Unittest
``` shell
ginkgo unittest run --a
```

## Data

### Update
``` shell
ginkgo data update stockinfo
ginkgo data update calendar
ginkgo data update adjust --code 000001.SZ
ginkgo data update day --code 000001.SZ
ginkgo data update tick --code 000001.SZ
```

### List,Show
``` shell
ginkgo data list stockinfo --page 50
ginkgo data show stockinfo --code 000001.SZ
```

### Plot
``` shell
ginkgo data plot day --code 00001.SZ --start 20200101 --end 20210101
```

# File System

``` plaintest
# Construction
├── api
├── docs
├── samples
├── src
│   └── ginkgo
│       ├── artificial_intelligence
│       ├── backtest
│       │   ├── analyzers
│       │   ├── engines
│       │   ├── events
│       │   ├── feeders
│       │   ├── indices
│       │   ├── matchmakings
│       │   ├── plots
│       │   ├── portfolios
│       │   ├── risk_managements
│       │   ├── selectors
│       │   ├── sizers
│       │   └── strategies
│       ├── client
│       ├── config
│       ├── data
│       │   ├── drivers
│       │   ├── models
│       │   └── sources
│       ├── libs
│       └── notifier
├── test
│   ├── backtest
│   ├── data
│   ├── db
│   └── libs
└── web
    ├── public
    └── src
        ├── assets
        ├── components
        │   ├── dropdown
        │   └── icons
        ├── layouts
        ├── router
        ├── stores
        └── views

```
