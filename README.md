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
You could create virtual enviroment by virtualenv or conda.
### Follow the instructions to install.

``` shell
# virtualenv
python3 -m virtualenv venv;source venv/bin/activate

python ./install.py
```

```shell
# conda
conda create -n ginkgo python=3.12.8
conda activate ginkgo
python ./install.py
```

### Optimize config.
``` shell
vi ~/.ginkgo/config.yaml
```

``` shell
vi ~/.ginkgo/secure.yml
# You could set your db token and other auth here.
```

``` shell
ginkgo --help
```

if `ginkgo version` shows correct, you are good to go.

After Tushare token set. Data Update moduel should be prepared.

## Data
### Init
```
ginkgo data init
```
This command will create talbes and some default data.

### Update

``` shell
ginkgo data update stockinfo
```

```shell
ginkgo data update calendar
```

```shell
ginkgo data update adjust --code 000001.SZ
```

```shell
ginkgo data update day --code 000001.SZ
```

```shell
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
## Interactive Mode TODO
You could use language to use is tool. # TODO
``` shell
ginkgo interactive
```

## Unittest
Run unittest, after installation run this to to check every part of the library works fine.
``` shell
ginkgo configure --debug on
ginkgo unittest run --a
```

### Bakctest
```
ginkgo backtest ls
```
```
ginkgo backtest run {id}
```
