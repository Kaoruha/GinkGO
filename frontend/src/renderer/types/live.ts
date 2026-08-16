/**
 * 实盘账户域视图模型(AccountInfo/AccountCard/PositionItem 共用)
 *
 * 后端金额/数量为字符串,展示层经 utils/format 的 formatFixed 定点化。
 */

export interface BalanceInfo {
  total_equity: string
  available_balance: string
  frozen_balance: string
  currency_balances: Array<{
    currency: string
    available: string
    frozen: string
    balance: string
  }>
}

export interface PositionInfo {
  symbol: string
  side: 'long' | 'short'
  size: string
  avg_price: string
  current_price: string
  unrealized_pnl: string
  unrealized_pnl_percentage: string
  margin: string
  is_spot?: boolean  // 标记为现货持仓（币种余额）
}

export interface AccountData {
  uuid: string
  name: string
  exchange: string
  environment: string
  status: string
  balance?: BalanceInfo
  positions?: PositionInfo[]
  last_update?: string
  error?: string
}
