"""
趋势追踪模型

衡量股票趋势的指标最重要的就是均线系统，因为它是应用最为广泛的趋势追踪指标，所以均线是不可或缺的，把它作为捕捉大盘主趋势的基石。
但是纯粹的均线由于噪音等原因，使得经常会出现误操作，需要进行更多的处理机制，
包括极点、过滤微小波动、高低点比较策略、高低点突破策略、长波的保护机制、长均线的保护机制等概念和技术细节。

均线简化
股票价格的波动会让人感觉价格变化飘忽不定，很难把握。
为了便于捕捉趋势，所以需要对价格走势曲线进行简化处理，这样可以借助于均线方法。
将a个（a为模型参数）连续的交易日的收盘价取一个均值，形成MA(a)，比如a为10，即10个交易日数据取一均值，
那么就可以得到股价的10日均线U，完成对价格曲线的第一步简化。

记录极点
极点就是局部的高点或者低点，在极点处股价出现了转折，所以它们是记录股价变化的关键点，包含了比较多的信息。
如果股价上涨至此，接下来又出现了下跌，那么就形成一个局部的高点；如果股价下跌至此，接下来又出现上涨，那么就形成一个低点。
这些叫做极点，往往是股价变化的关键信息点，将它们记录下来，以备进一步制定策略。

设置阀门，过滤微小波动
均线策略最大的优势跟踪趋势效果比较好，在形成趋势时能紧跟趋势，
但是最大的问题在于碰到盘整行情，均线就摇摆不定，容易频繁地发出交易信号，所以必须对其进行进一步处理。
可以结合记录的极点形成过滤微小波动的方法。
当股价形成一个极点M后，接下来股价波动在M点股价的上下B个（B为模型参数）指数点内，就认为股价和M点相比没有变化，
这样可以得到过滤了微小波动的均线趋势线W。
（很遗憾 这种微小的波动我认为也是信号，不是交易的信号而是某些指标的信号，回头趋势追踪模型会抛弃上面这些）
"""