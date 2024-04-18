const HOST = 'http://localhost'
const PORT = '8000'

export const API_ENDPOINTS = {
  fetchBacktest: `${HOST}:${PORT}/api/v1/backtest`,
  fetchRecord: `${HOST}:${PORT}/api/v1/record`,
  fetchAnalyzer: `${HOST}:${PORT}/api/v1/analyzer`,
  fetchOrder: `${HOST}:${PORT}/api/v1/order`,
  fetchOrderFilled: `${HOST}:${PORT}/api/v1/order_filled`,
  fetchSignal: `${HOST}:${PORT}/api/v1/signal`,
  fetchStockInfo: `${HOST}:${PORT}/api/v1/stockinfo`,
  fetchDaybar: `${HOST}:${PORT}/api/v1/daybar`
}
