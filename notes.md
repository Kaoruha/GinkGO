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




Define the data structure: Decide on the data structure to use for the financial data you will be backtesting. This could include stock prices, volumes, financial ratios, and other indicators.

Create an event-driven architecture: Use an event-driven architecture to handle the various events that will occur during the backtesting process. This approach allows you to separate the logic of the backtesting system from the data itself. You can use an event-driven library like asyncio or Twisted to help with this.

Define the events: Define the events that will be triggered during the backtesting process. These events could include things like price updates, order submissions, and trade executions.

Implement the event handlers: Write the code to handle each event. This might include updating the internal state of the backtesting system, submitting orders to the exchange, or executing trades.

Create a simulation environment: Create a simulation environment that mimics the behavior of a real exchange. This could include things like order books, price feeds, and market depth.

Define the trading strategies: Define the trading strategies that you want to test. This could include simple strategies like buy-and-hold, or more complex strategies that involve technical analysis, machine learning, or other techniques.

Backtest the strategies: Run the backtesting system on historical data to see how well the trading strategies perform. You can use various performance metrics like sharpe ratio, maximum drawdown, and cumulative returns to evaluate the performance of the strategies.

Optimize the strategies: Use the results of the backtest to optimize the trading strategies. This might involve tweaking parameters like stop loss levels, take profit levels, or trade sizes to improve performance.

Implement the strategies: Once you have optimized your trading strategies, you can implement them in a live trading environment.






Data Sources: You will need to decide on what data sources you want to use for your system. For bar data, you can use OHLC (open-high-low-close) data, while tick data will provide more granular details. News data can be used for event-driven trading strategies. You can use various APIs to fetch the data or directly subscribe to data feeds from different providers.

Data Storage: Once you have your data sources, you will need to design a system for storing this data. You can use a database or a cloud-based storage system such as AWS S3 to store and retrieve the data. A NoSQL database like MongoDB may be a good choice if you need to handle large amounts of unstructured data.

Data Processing: You will need to preprocess the data to extract features that are useful for your trading strategies. This may include computing technical indicators such as moving averages, RSI, Bollinger Bands, etc. You can also use machine learning algorithms to extract features automatically.

Portfolio Management: You will need to design a system for managing multiple portfolios. This may include risk management, position sizing, and rebalancing strategies. You can use tools like Pyfolio or Zipline to backtest and evaluate your strategies.

Execution: You will need to design an execution system to trade on the data you have processed. You can use APIs provided by brokers or implement your own execution algorithms.

Backtesting and Optimization: Once you have your system in place, you will need to backtest your strategies on historical data to evaluate their performance. You can use libraries like backtrader, Pyfolio, or Zipline to perform backtesting and optimization.

Monitoring and Alerts: Finally, you will need to set up a system for monitoring your trading strategies in real-time and sending alerts when certain events occur. This may include monitoring market data, portfolio performance, and risk levels.
