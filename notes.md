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


mongo
use quant
db.createUser({user:"ginkgo",pwd:"caonima123",roles:[{role:"readWrite",db:"quant"}]})



Designing an event-driven stock backtest system in Python can be broken down into the following high-level steps:

Define the data structures that you will use to represent financial instruments, such as stocks, and financial data, such as prices and volumes.
Define the events that your system will generate and process. These could include market data events, such as tick data, as well as order and execution events.
Implement a data feed module that can read financial data from external sources and generate market data events for your system to process.
Implement a strategy module that can receive market data events and generate order events based on some pre-defined rules.
Implement an execution module that can receive order events and generate execution events based on the current market conditions.
Implement a portfolio module that can receive execution events and update the current state of your portfolio.
Implement a performance module that can calculate key performance metrics for your backtest, such as return on investment and Sharpe ratio.
Here is a more detailed breakdown of each step:

Define the data structures
Define classes for financial instruments, such as stocks, and financial data, such as prices and volumes. These classes should have attributes that allow you to represent the relevant data, as well as methods that allow you to manipulate and interact with the data.
Define a class for your portfolio that contains information about the current state of your portfolio, including the number of shares you own, the current value of those shares, and any cash or margin balances.
Define the events
Define classes for the events that your system will generate and process. These could include market data events, such as tick data, as well as order and execution events.
Each event should contain all of the relevant information needed to trigger a particular action within your system. For example, a market data event might include the current price and volume for a particular stock, while an order event might include the stock symbol, the order type, and the quantity of shares to be bought or sold.
Implement a data feed module
Implement a data feed module that can read financial data from external sources and generate market data events for your system to process.
This module should be able to handle different types of financial data, such as tick data or historical price data, and should be able to parse the data into the appropriate event format.
You may also want to implement a data caching mechanism to improve performance, as reading data from external sources can be time-consuming.
Implement a strategy module
Implement a strategy module that can receive market data events and generate order events based on some pre-defined rules.
This module should be able to handle different types of trading strategies, such as trend-following or mean-reversion, and should be able to adjust its behavior based on market conditions.
You may also want to implement a strategy testing framework to help you evaluate the effectiveness of different trading strategies.
Implement an execution module
Implement an execution module that can receive order events and generate execution events based on the current market conditions.
This module should be able to handle different types of orders, such as market orders or limit orders, and should be able to execute orders in a timely and efficient manner.
You may also want to implement an order management system to help you keep track of your orders and their status.
Implement a portfolio module
Implement a portfolio module that can receive execution events and update the current state of your portfolio.
This module should be able to handle different types of transactions, such as buying or selling shares, and should be able to calculate the current value of your portfolio based on the current market prices.
