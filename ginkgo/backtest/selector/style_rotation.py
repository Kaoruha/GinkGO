"""
风格轮动模型

市场上的投资者是有偏好的，有时候会偏好价值股，有时候偏好成长股，有时候偏好大盘股，有时候偏好小盘股。
由于投资者的这种不同的交易行为，形成了市场风格。

在2009年是小盘股风格，小盘股持续跑赢沪深300指数；而在2011年，则是大盘股风格，大盘股跌幅远远小于沪深300指数。
如果能事先通过一种模型判断未来的风格，进行风格轮动操作，则可以获得超额收益。

晨星风格箱法
晨星风格箱法是一个3×3矩阵，从大盘和小盘、价值型和成长型来对基金风格进行划分，
介于大盘和小盘之间的为中盘，介于价值型和成长型之间的为混合型，共有9类风格。
规模指标:
市值。通过比较基金持有股票的市值中值来划分，市值中值小于10 亿美元为小盘；大于50亿美元为大盘；10亿~50亿美元为中盘。
估值指标:
平均市盈率、平均市净率。基金所持有股票的市盈率、市净率用基金投资于该股票的比例加权求平均，
然后把两个加权平均指标和标普500成份股的市盈率、市净率的相对比值相加。
对于标普500来说，这个比值和是2。
如果最后所得比值和小于1.75，则为“价值型”；
大于2.25为“成长型”；
介于1.75~2.25之间为“混合型"。


风格轮动的经济解释
宏观经济表现强劲时，小市值公司有一个较好的发展环境，易于成长壮大，甚至还会有高于经济增速的表现.
因此，小盘股表现突出的概率高于大盘股。
而当经济走弱时，由于信心的匮乏和未来市场的不确定性，投资者可能会倾向于选择大盘股，起到防御作用.
即使低通货膨胀、货币走强，也不足以冒险去选择小盘股。
研究发现，经济名义增长率是用来解释规模效应市场周期的有力变量。
当名义增长率提高时，小市值组合表现更优，因为小公司对宏观经济变动更为敏感，当工业生产率提高、通货膨胀率上升时，小公司成长更快。

"""