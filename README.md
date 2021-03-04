# Ginkgo Engine

整个项目是一个学习的过程，最后的成品只是一个工具，目标是为实现稳定盈利提供分析工具平台。投资有风险，请有自负盈亏的能力再进行实盘尝试。

## Software Requirements

- Operating System: Windows, Linux or Mac
- Database: Mongodb
- Web Server: Tornado

## Features

- 多源数据爬取，清洗后统一入库
- 回测引擎
- 策略评价模型
- TODO 前端页面
- TODO NLP新闻舆情分析
- TODO ML模块
- TODO 从策略编写到回测到模拟验证，最后实盘交易的全管线

## Setup

1. 下载项目
2. 安装环境
3. 安装MongoDB
4. 配置MongoDB

端口请保持27017

```shell
# 进入Mongo后，需要创建库与对应权限用户
use quant
db.createUser({user:"ginkgo",pwd:"caonima123",roles:[{role:"readWrite",db:"quant"}]})
```

如果是Mac，可能Linux也需要，需要取消最大文件限制数

```shell
ulimit -n 65535
# db路径与log路径得换成自己的
mongod --dbpath /Users/suny/Development/mongodb/db --logpath /Users/suny/Development/mongodb/log/mongodb.log
```

5. 运行测试脚本

test_engine.py