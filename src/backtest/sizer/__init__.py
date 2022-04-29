"""
仓位控制模块
持仓限额：我们需要找到有效的方法，根据每个品种的波动性正确的酸楚相应的持仓限额。

某一交易日的真实波动范围
TR = max（当日最高价-昨日收盘价）-min（当日最低价-昨日收盘价）
ATR是多个交易日价格波动幅度的数学平均值

假设单个品种的风险因子为20个基点，即任意一个瓶中平均在一个交易日内的变动对投资组合整体对最大影响应该为0.2%
当投资组合总资金为100万美元时，20个基点对风险因子在理论上相当等于2000美元对价值变动
如果黄金出现了买入信号，而黄金对ATR为10美元，那么点价为100对纽约商品交易所一手黄金期货合约在理论上单日产生的正常盈亏幅度为1000美元
因此，在当前风险因子的投资组合内，我们只需要购买两首黄金期货合约即可。

合约数量 = 0.002 * 资产价值 /（ATR100 * 该合约的点价）
分子是设定的风险因子*该投资组合的总资金，分母是该品种的正常日均波动幅度

其他控制仓位的方法还包括根据对价格波动对预期调节持仓限额，进而形成一个普适的风险基准

尾随止损（移动止损）Tairling Stop 为简单起见，止损点为距开仓以来最好价格相当于三个真是波动幅度均值的位置。
"""