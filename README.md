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

## Create Shortcuts
This command will create a soft link in /usr/bin
After running this command, you could just type `ginkgo --help` to use the lib no matter whether you have active your virtual environment.
It is not neccesary to run this, you could also active your environment and use `python main.py --help`
``` shell
sudo ./install.sh
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

├── api  (api server)
├── docs
├── samples
├── src (source code)
│   └── ginkgo
│       ├── artificial_intelligence (machine learning related)
│       ├── backtest (backtest and live engine)
│       │   ├── analyzers (Evaluating backtest)
│       │   ├── engines (main engine)
│       │   ├── events ()
│       │   ├── feeds (data feeder)
│       │   ├── indices (...)
│       │   ├── matchmakings
│       │   ├── plots (plot related)
│       │   ├── portfolios
│       │   ├── risk_managements (similar to strategy, but for risk manager)
│       │   ├── selectors (code picker)
│       │   ├── sizers (calculate position size)
│       │   └── strategies (calculate signals)
│       ├── client (cli command support)
│       ├── config (settings, include basic setting and db setting)
│       ├── data
│       │   ├── drivers (database driver)
│       │   ├── models (sqlalchemy model)
│       │   └── sources (data sources)
│       ├── libs (utils)
│       └── notifier (email, telegram, beep alert)
├── test (for unittest)
└── web (web code, vue project)
