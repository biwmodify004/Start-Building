# NS Capital Terminal

Personal charting and strategy research workspace for NS Capital. The app uses the licensed, open-source **Vela 0.8.4** chart core and independently implemented research, backtesting, paper trading and journaling features. This is an initial functional implementation, not a copy of LuxAlgo's private platform backend or Quant AI.

## Run locally

Requires Node.js 22 or later.

```sh
npm ci
npm test
npm run build
npm start
```

Open `http://127.0.0.1:8080`. Any static host can serve `dist/`. No API keys are needed for the default mode. All application and chart scripts are bundled locally; no chart CDN is needed.

## Included

- Vela chart workspace: candlesticks and other registered styles, multiple chart layouts, drawing tools, native indicators, chart settings, timezone selection, screenshots, and bar replay.
- Initial red/orange/yellow EMAs: 21, 50, 200. Bollinger Bands and other native studies are available from Indicators.
- NS Research: honest local keyword parser for EMA crossover, Bollinger re-entry and prior-range breakout, with editable JSON rules.
- Backtesting: next-open execution after a closed-bar signal, Wilder ATR stops, fixed reward multiple, equity-based risk sizing, per-side commission and adverse slippage, gap-aware stops and conservative stop-first ambiguous bars.
- Real computed equity, net P&L, win rate, profit factor, bar-close maximum drawdown, trade table, chart marks and CSV trade export.
- Clearly labeled deterministic synthetic samples, public Binance Spot crypto feed with connection state and recovery, and CSV imports including MT5 tab-separated exports with explicit broker UTC offset.
- Watchlist, browser-local price alerts, simulated market orders and exits, journal with BTR/DCE tags, JSON backup/restore, light/dark themes, Thai/English host UI and Thai/New York clocks with DST handled by IANA timezones.
- Broker tick-based risk calculator; values are editable examples and must match the user's broker contract.

## Data and calculation boundaries

The initial XAUUSD and other sample data are **synthetic** and end on 16 October 2026. They are neither historical market observations nor current quotes. Samples do not implement exchange trading calendars. Select Binance for external crypto data; availability depends on network, provider and region. Forex, gold and index live feeds need a separate licensed provider integration. Import CSV to research your own prices.

CSV imports require a header and positive OHLC prices. Supported delimiters: comma, semicolon, tab. Columns: `time`/`timestamp` or `date` + `time`, `open`, `high`, `low`, `close`, optional `volume`/`tickvol`. Epoch seconds, epoch milliseconds, ISO dates and MT5 dates are supported. Unzoned date strings use the import dialog's UTC offset. Duplicates keep the last row, then sort ascending. Finer timeframes cannot be reconstructed from coarse CSV bars. Limits: 25 MiB per import, 100,000 CSV rows; chart history capture retains at most 10,000 bars per chart identity.

Backtests use loaded chart history, or the revealed prefix during Replay. Current forming Binance bars are excluded. The available history is not an entire exchange archive. Size is in asset units, and capital/P&L use the symbol's quote currency. Backtests model no margin, leverage, funding, swap, spread other than the chosen slippage, volume constraints or liquidation. There can be at most one strategy position. A surviving position is closed at the final bar. Drawdown is sampled at bar closes, so intrabar drawdown can be larger. Limited sample results are not evidence of an investment edge.

Paper orders use asset units, not CFD lots. Accounts are separate by quote currency: USD, USDT, JPY. Fills use visible chart prices with configurable commission but no paper slippage or margin modeling. Stop/target exits require this page to receive new bars on the same symbol/timeframe and Replay mode. Alerts run only while the page is open; no background service or broker orders are installed.

User notes, positions, alerts, imported bars and chart layouts remain in this browser's localStorage. They do not sync between devices or users. Use Backup to export a JSON archive. Clearing browser storage removes local records. No user records or API credentials are committed to GitHub.

## Binance Spot live prices

Choose **Binance · Crypto** above the chart, then choose BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, DOGEUSDT or ADAUSDT from the pair selector. The native symbol picker also lists these pairs. A direct link can select the source: `/?source=binance&symbol=BTCUSDT`.

This adapter uses Binance's official, public market-data-only hosts:

- Historical candles: `https://data-api.binance.vision/api/v3/klines`
- Current candle updates: `wss://data-stream.binance.vision:443/ws/btcusdt@kline_15m`
- Documentation: https://developers.binance.com/en/docs/products/spot/faqs/market_data_only

No Binance account, API key, trading permission, backend or third-party proxy is required for this public feed. This is **Spot**, not futures, Forex or gold. External network and regional availability can still affect connectivity.

`BINANCE · LIVE` appears only after a fresh valid WebSocket candle for the selected pair and interval. Socket opening alone is not counted as a live price. The status line shows the receive time in Thailand time. A silent socket is closed after 15 seconds; REST updates are requested every 5 seconds while reconnecting, with no overlapping polling requests. REST fallback is labeled `BINANCE · REST`. Invalid, stale, wrong-symbol and out-of-order stream messages are ignored. When the selected live quote is unavailable or stale, paper Buy/Sell buttons are disabled. Existing data are not silently replaced with synthetic sample prices.

Use **Reconnect** to refresh chart history and resubscribe while retaining workspace content. Non-native aggregated intervals use REST so they do not render an incomplete streamed aggregate. Monthly chart intervals are outside the supported live interval list.

REST history and a real WebSocket candle were received successfully from this execution environment. Unit and simulated-DOM tests additionally cover reconnect, pair switching, stale stream detection, polling fallback and unsubscribe cleanup. This does not verify the user's browser/network or real browser rendering.

## Optional real AI through a local compatible server

The published static app uses **local rules only**. Quant AI, paid LuxAlgo indicators and LuxAlgo's proprietary services are not included.

An optional local server adapter is supplied for an OpenAI-compatible provider such as a locally running LM Studio server. Configure environment variables in your shell (do not commit keys):

```sh
AI_BASE_URL=http://127.0.0.1:1234/v1 AI_MODEL=your-loaded-model npm start
```

Then open `http://127.0.0.1:8080/?ai=1`. For a provider requiring authentication, set `AI_API_KEY` in the server environment. The browser sends only the typed strategy message and current numeric configuration to the local adapter. The adapter calls the configured provider, validates its structured proposal, and returns it for review. It does not execute arbitrary generated code. Backtests still require an explicit Run action. Secrets are server-only, never stored in browser storage or the build. By default the local server binds to `127.0.0.1`.

This adapter requires an available model endpoint; it is not deployed by the static Sites build. Its real inference behavior has not been verified without a configured model.

## Verification

`npm test` checks indicator warmups, no-future-data signals, next-bar entries, P&L reconciliation, round-trip costs, ambiguous SL/TP and gap fills, CSV timezone conversion, data validation, risk rounding, deterministic samples and the real Vela integration in a simulated DOM. DOM integration tests do not verify actual browser rendering, touch gestures, WebGL, a real browser network path or AI inference. The build bundles the real Vela workspace and all transitive browser dependencies with pinned versions.

## License and attribution

Vela: https://github.com/LuxAlgo/Vela · https://velacharts.dev

Vela is distributed under Apache-2.0 with its NOTICE attribution requirement. The app retains visible attribution and ships `vendor/VELA-LICENSE.txt`, `vendor/VELA-NOTICE.txt` and dependency notices in each build. No LuxAlgo private source code, private API, premium indicator code or account session is included. App source is supplied for the user's project; third-party components retain their own licenses.
