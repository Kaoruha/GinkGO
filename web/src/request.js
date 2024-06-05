const HOST = 'http://localhost'
const PORT = '8000'

export const API_ENDPOINTS = {
  fetchBacktest: `${HOST}:${PORT}/api/v1/backtest`,
  delBacktest: `${HOST}:${PORT}/api/v1/del_backtest`,
  fetchRecord: `${HOST}:${PORT}/api/v1/record`,
  fetchAnalyzer: `${HOST}:${PORT}/api/v1/analyzer`,
  fetchOrder: `${HOST}:${PORT}/api/v1/order`,
  fetchOrderFilled: `${HOST}:${PORT}/api/v1/order_filled`,
  fetchSignal: `${HOST}:${PORT}/api/v1/signal`,
  fetchStockInfo: `${HOST}:${PORT}/api/v1/stockinfo`,
  fetchDaybar: `${HOST}:${PORT}/api/v1/daybar`,
  fetchFileList: `${HOST}:${PORT}/api/v1/file_list`,
  fetchFile: `${HOST}:${PORT}/api/v1/file`,
  updateFile: `${HOST}:${PORT}/api/v1/update_file`,
  renameFile: `${HOST}:${PORT}/api/v1/rename_file`,
  delFile: `${HOST}:${PORT}/api/v1/del_file`,
  addLivePortfolio: `${HOST}:${PORT}/api/v1/add_liveportfolio`,
  fetchLivePortfolio: `${HOST}:${PORT}/api/v1/liveportfolio`,
  delLivePortfolio: `${HOST}:${PORT}/api/v1/del_liveportfolio`,
  fetchCodeList: `${HOST}:${PORT}/api/v1/code_list`,
  fetchTradeRecord: `${HOST}:${PORT}/api/v1/traderecord`,
  addTradeRecord: `${HOST}:${PORT}/api/v1/add_traderecord`,
  updateTradeRecord: `${HOST}:${PORT}/api/v1/update_traderecord`,
  delTradeRecord: `${HOST}:${PORT}/api/v1/del_traderecord`
}
