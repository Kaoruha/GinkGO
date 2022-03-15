"""
多因子模型

采用一系列因子作为选股的标准，满足这些因子的加入篮子，不满足的剔除
针对多因子，最后采用打分或者回归法
打分就是根据因子的不同，赋予不同的权重，最后得到一个总的评价
回归法用过去的股票的收益率对多因子进行回归，得到一个回归方程
然后再把最新的因子值代入回归方程得到一个对未来股票收益的预判，以此为依据进行选股
应该对选股的因子定期进行有效性检验

多因子选股模型的建立过程主要分为
Step1、候选因子的选取

Step2、选股因子有效性的检验
    Step2.1、对于任意一个候选因子，在模型形成期的第一个月初开始计算市场中每只正常交易股票的该因子的大小
    Step2.2、按从小到大的顺序对样本股票进行排序，并平均分为n个组合，一直持有到月末
    Step2.3、在下月初再按同样的方法重新构建n个组合并持有到月末，每月如此，一直重复到模型形成期末

Step3、有效但冗余因子的剔除（？存疑、如何证明两个因子之间是完全相关的关系，可以互相代替？）
    Step3.1、先对不同因子下的n个组合进行打分，分值与该组合在整个模型形成期的收益相关，收益越大，分值越高
    Step3.2、按月计算个股的不同因子得分间的相关性矩阵
    Step3.3、在计算完每月因子得分相关性矩阵后，计算整个样本期内相关性矩阵的平均值
    Step3.4、设定一个得分相关性阀值 MinScoreCorr
    将得分相关性平均值矩阵中大于该阀值的元素所对应的因子只保留与其他因子相关性较小、有效性更强的因子
    而其它因子则作为冗余因子剔除
    
Step4、综合评分模型的建立和模型的评价
Step5、持续改进



"""