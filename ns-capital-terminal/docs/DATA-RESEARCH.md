# Market data and research boundaries

## Data and calculation boundaries

The app starts with **Binance BTC/USDT** and only loads externally supplied prices. Synthetic generators and sample instruments have been removed. Existing sample favorites, paper prices, alerts and drawings are migrated out of browser storage; real user CSV imports are preserved under an explicit `csv:` provider. Saved sample chart layouts reopen on Binance, and saved broker layouts wait for a new authenticated connection. An unavailable feed produces a waiting/error state, never generated candles.

Binance availability depends on network, provider and region. Global markets displays provider-labeled TradingView reference charts for Forex, metals and CFD indices. Broker candles inside Vela require the included personal MT4/MT5 gateway and an already logged-in terminal. CSV data are explicitly offline user imports.

CSV imports require a header and positive OHLC prices. Supported delimiters: comma, semicolon, tab. Columns: `time`/`timestamp` or `date` + `time`, `open`, `high`, `low`, `close`, optional `volume`/`tickvol`. Epoch seconds, epoch milliseconds, ISO dates and MT5 dates are supported. Unzoned date strings use the import dialog's UTC offset. Duplicates keep the last row, then sort ascending. Finer timeframes cannot be reconstructed from coarse CSV bars. Limits: 25 MiB per import, 100,000 CSV rows; chart history capture retains at most 10,000 bars per chart identity.

Backtests use loaded chart history, or the revealed prefix during Replay. Current forming Binance and broker bars are excluded. The available history is not an entire exchange archive. Size is in asset units, and capital/P&L use the symbol's quote currency. Backtests model no margin, leverage, funding, swap, spread other than the chosen slippage, volume constraints or liquidation. There can be at most one strategy position. A surviving position is closed at the final bar. Drawdown is sampled at bar closes, so intrabar drawdown can be larger. A short loaded history is not evidence of an investment edge.

Paper orders use asset units, not CFD lots. Accounts are separate by the actual quote currency, including USD, USDT, BTC, ETH, THB and other catalog quotes. Fills use visible chart prices with configurable commission but no paper slippage or margin modeling. Stop/target exits require this page to receive new bars on the same symbol/timeframe and Replay mode. Alerts run only while the page is open; no background service or broker orders are installed.

User notes, positions, alerts, imported bars and chart layouts remain in this browser's localStorage. They do not sync between devices or users. Use Backup to export a JSON archive. Clearing browser storage removes local records. No user records or API credentials are committed to GitHub.

