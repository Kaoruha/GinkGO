"""
动量反转模型

A股市场存在显著的动量及反转效应，
按照形成期为6个月持有期为9个月的动量策略以及形成期为2个月持有期为1个月的反转策略构建的投资组合表现最佳。
从不同的市场阶段看，动量策略在熊市阶段表现优异，而反转策略则在牛市阶段可以取得出色的业绩。

动量及反转效应：（？趋势以及均值回归）
动量效应是指在一定时期内，如果某股票或者某股票组合在前一段时期表现较好，
那么，下一段时期该股票或者股票投资组合仍将有良好表现。
而反转效应则是指在一定时期内表现较差的股票在接下来的一段时期内有回复均值的需要，所以表现会较好。

动量效应测试结果：
从超额收益来看，形成期为4－9个月，持有期为6－10个月的动量组合可以取得较高的超额收益；
从战胜基准的频率来看，形成期为6－8个月间，持有期为9－10个月的动量组合战胜基准的频率较高。
综合来看，形成期为6个月，持有期为9个月的动量组合在整个样本内表现最佳。

反转效应测试结果：
从超额收益来看，形成期为1或2个月，持有期为1个月的反转组合可以取得较高的超额收益；
从战胜基准的频率来看，短期组合，也即形成期和持有期都为1或2个月的反转组合战胜基准的频率较高。
综合前面两个因素，形成期为2个月，持有期为1个月的反转组合在整个样本内表现最佳。

动量策略表现：
买入前6个月累计收益率最高的一组股票，并持有9个月的动量策略构建的投资组合在考虑单边0.25%的交易成本以后，
在长达7年多的测试期中取得了226％的累计收益，远高于同期沪深300指数取得的117％的累计收益。
在整个测试阶段，动量策略战胜基准的频率为58.43％。
这一策略在熊市中表现尤为出色，相对于沪深300平均每个月可以取得1.2％左右的超额收益，信息比率为0.82，
熊市阶段战胜基准的频率在65％以上。

反转策略表现：
买入前2个月内累计收益率最低的一组股票，并持有1个月的反转策略构建的投资组合在考虑单边0.25%的交易成本以后，
在长达7年多的测试期中取得了261％的累计收益，远高于同期沪深300指数取得的117％的累计收益。
在整个测试阶段，动量策略战胜基准的频率为51.69％。这一策略在牛市中表现尤为出色，
相对于沪深300平均每个月可以取得接近1.5％的超额收益，信息比率为0.78，牛市阶段战胜基准的频率接近于57％。

结论：
A股市场存在显著的动量及反转效应。长期来看动量和反转策略相对于沪深300都可以取得超额收益，
但是动量反转策略在不同的市场阶段表现不同，
动量策略在熊市阶段表现优异，
而反转策略则在牛市阶段可以取得出色的表现。
因此在A股市场应用动量或者反转效应选择股票时，应根据市场环境在动量和反转策略间进行选择，牛市选择反转，熊市则选择动量。
（？问题来了，我怎么知道我再牛市还是在熊市）
"""