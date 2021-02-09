# ginkGO
#### 1、 开发环境部署
#### 建议慢慢更换成 Conda 进行虚拟环境与包的管理
```shell script
# 1、创建虚拟环境
# 1.1、Python命令创建虚拟环境
python3 -m venv venv

# 1.2、Anaconda 使用conda进行虚拟环境包的管理
# 1.2.1、更新Anaconda
conda update anaconda
conda update conda
# 1.2.2、添加清华源
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
conda config --set show_channel_urls yes
# 1.2.3、创建环境
conda create -n ginkgo-venv python=3.7 # 新建一个虚拟环境
conda env create -f environment.yml # 按照 environment.yml 配置一个新的虚拟环境

# 2.激活虚拟环境
# 2.1、MacOS下
source venv/bin/activate

# 2.2、Anaconda，此刻conda已经完成包的安装,虚拟环境切换
conda activate ginkgo-venv

# 2.3、Windows
# GinkGO
venv\Scripts\activate

# 3、更新pip(conda 不需要这一步)
python3 -m pip install --upgrade pip

# 4、安装依赖包(conda 不需要这一步)
# 4.1、按照Pipfile内的包信息安装
pip install -r environment.txt

# 4.2、如果速度慢可以换国内源  
pip install -r environment.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4.3、有新的包在安装完成后，需要更新environment
pip freeze > environment.txt
conda env export > environment.yml
```

#### 2、 生产环境部署
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

#### 3、 YellowPrint与BluePrint
> libs下的yellowPrint实现了blueprint的衍生类，用于细分url，通过 yp_user.register(bp) 来挂载到Blueprint

#### 4、 爬虫
> app/spider是基于Scrapy框架拓展的爬虫模块



<!-- 投研分析

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

提供mac/windows的可安装版本(QACommunity)
提供全平台可用的web界面
提供手机客户端(ios/andriod) [内测中] -->