# 使用手册

### 1、 开发环境部署

需要提前安装Python，建议3.6以上版本

#### 1、创建虚拟环境

#### 1.1、Python命令创建虚拟环境

```shell script
cd <project path>
python -m venv venv
```

#### 1.2、激活虚拟环境

#### 1.2.1、windows平台 powershell

```shell
venv\Scripts\Activate.ps1
```

#### 1.2.2、windows平台 cmd

```shell
venv\Scripts\Activate.bat
```

#### 1.2.3、MacOS下

```shell
source venv/bin/activate
```

### 2、安装依赖包

```shell
pip install -r environment.yml
```

### 3、更新依赖包

```shell
pip freeze > environment.yml
```

### 4、 生产环境部署

nginx+gunicorn

```shell script
# 通过gunicorn启动flask
gunicorn -w 4 -b 127.0.0.1:5000 -D --access-logfile ./static/logs/server_log BeuQuant:quant

# -w 线程数
# -b 绑定IP与端口
# -D 后台运行
# --access-logfile 设定日志文件地址
# BeuQuant:quant   主入口文件：flask对象
```

```shell script
# 停止gunicorn服务
gunicorn -w 4 -b 127.0.0.1:5000 -D --access-logfile ./static/logs/server_log quant:app

# 1 查询gunicorn的执行线程
ps aux | grep gunicorn

# 2 杀掉gunicorn线程
kill -9 <线程id>
```

全市场数据(日线/分钟线/tick)
财务数据
股票/期货/期权/港股/美股/(以及自定义数据源)
为多品种优化的数据结构QADataStruct
为大批量指标计算优化的QAIndicator [支持和通达信/同花顺指标无缝切换]
基于docker提供远程的投研环境
自动数据运维
回测

纯本地部署/开源
全市场(股票/期货/自定义市场[需要按规则配置])
多账户(不限制账户个数, 不限制组合个数)
多品种(QADataStruct原生为多品种场景进行了优化)
跨周期(基于动态的resample机制)
多周期(日线/周线/月线/1min/5min/15min/30min/60min/tick)
可视化(提供可视化界面)
自定义的风控分析/绩效分析
模拟

支持股票/期货的实时模拟(不限制账户)
支持定向推送/全市场推送
支持多周期实时推送/ 跨周期推送
模拟和回测一套代码
模拟和实盘一套代码
可视化界面
提供微信通知模版
实盘

支持股票(需要自行对接)
支持期货(支持CTP接口)
和模拟一套代码
不限制账户数量
基于策略实现条件单/风控单等
可视化界面
提供微信通知模版
终端