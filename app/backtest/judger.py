"""
Does it outperform a benchmark?
Does it have a hight enough Sharpe ratio?
Does it have a small enough drawdown and short enough drawdown duration?
Does the backtest suffer from survivorship bias?
Does the strategy lose steam in recent years compared to its earlier years?

回报的量化：
1、平均复合增长率
2、滚动平均一年期回报率
3、平均月度回报率

部分评价指标：
1、策略收益：
$策略收益(P) = \frac{P_{End} - P_{Start}}{P_{Start}} * 100\%$

2、策略年化收益：
$策略年化收益 = (( 1 + P ) * 252 * n - 1) * 100\%$

P 为策略收益， n 为策略执行天数，美股252，A股250

3、胜率：

盈利次数在总交易次数种的占比

4、盈亏比：周期盈利亏损的比例

5、平均获利期望：周期内所有投资盈利单的平均获利比例

6、平均亏损期望：周期内所有投资亏损单的平均亏损比例

7、基准收益（Benchmark Returns）：
评价一个策略的好坏光看策略本身的收益是不够的，还需要根据市场的基准收益来进行权衡

8、Beta：代表了策略表现对大盘变化的敏感性，即策略与大盘的相关性。
即一个策略的Beta为1.5时，大盘涨1%，策略可能涨1.5%，反之亦然，如果一个策略的Beta为-1.5，说明大盘涨1%的时候，策略可能跌1.5%。
$Beta = \frac{Cov(D_p , D_m)}{Var(D_m)}$
$D_p$为策略每日收益，$D_m$为基准每日收益

9、Alpha：Alpha是**超额收益**，它与市场波动无关，也就是说不是靠系统性的上涨而获得收益
$Alpha = R_p - (R_f + \beta * (R_m - R_f))$
$R_p$是策略年化收益率，$R_m$是基准年花收益率，$R_f$是无风险利率（拿银行的利率或者余额宝的利率）

10、夏普比率（Sharpe）：策略在单位总风险下所能获得的超额收益
$SharpeRatio = \frac{R_p - R_f}{\sigma_{pd}}$
$\sigma$ 是策略收益波动率，即策略收益率的年化标准差

11、所提诺比率（Sortino）：描述的是策略在单位下行风险下所能获得的超额收益
$SortinoRatio = \frac{R_p - R_f}{\sigma_{pd}}$
$\sigma_{pd}$ 是策略下行波动率

12、信息比率（Information Ratio）：描述的是策略在单位超额风险下的超额收益。
$InformationRatio = \frac{R_p - R_f}{\sigma_t}$
$\sigma_t$ 是策略与基准每日收益插值的年化标准差

13、最大回撤（Max Drawdown）：描述的是策略最大的亏损情况，通常越小越好
$MaxDrawdown = \frac{P_x-P_y}{P_x}$
$P_x, P_y$是策略两日的累计收益

14、策略波动率（Algorithm Volatility）：用来测量策略的风险性，波动越大一般代表策略的风险越高
$Algorithm Volatility = \sqrt{\frac{250}{n - 1} * \sum_n^{i=1} (r_i - \overline{r})^ 2}$
$r_m, \overline{r}, n$分别表示每日的基准收益率，平均基准收益率以及策略的执行天数

*这里的250我觉得可能得根据A股美股变，回头确认下*

15、MAR比率：年均回报率除以最大的衰落幅度，衰落是根据月末数据计算的（月末衰落可能低估实际的衰落程度，可以换成最高点到最低点的跌幅）。
"""

