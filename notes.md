<!--
 * @Author: Kaoru
 * @Date: 2022-03-16 10:25:09
 * @LastEditTime: 2022-03-20 17:16:21
 * @LastEditors: Kaoru
 * @Description: Be stronger,be patient,be confident and never say die.
 * @FilePath: /Ginkgo/notes.md
 * What goes around comes around.
-->
Momentum 动力、趋势
MeanReversion 均值回归
MarketMaking 做市商
StatisticalArbitrage 统计套利
SENTMENT 情绪交易


高频交易 做不了
统计套利 可以做
算法交易 可以做




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


### Docker Mongo
docker run -d -v /Users/suny/data/mongo:/data/db -v /Users/suny/data/mongo/mongod.conf:/etc/mongod.conf --restart=always -p 27017:27017 --name=ginkgo_mongo mongo

docker run -d -v /Users/suny/data/mongo:/data/db --restart=always -p 27017:27017 --name=ginkgo_mongo mongo --config /etc/mongo/mongod.conf

docker run -d -v /Users/suny/Development/mongo:/data/db --restart=always -p 27017:27017 --ulimit nproc=65535 --name=ginkgo_mongo mongo

docker run -d -p 27017:27017 --ulimit nproc=65535 --name=ginkgo_mongo mongo
docker run -d -v F:\mongo:/data/db --restart=always -p 27017:27017 --ulimit nproc=65535 --name=ginkgo_mongo mongo

进入容器内部
mongo
use quant
db.createUser({user:"ginkgo",pwd:"caonima123",roles:[{role:"readWrite",db:"quant"}]})
