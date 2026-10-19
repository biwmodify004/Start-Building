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

Open `http://127.0.0.1:8080`. Any static host can serve `dist/`. No API keys are needed for the default mode. The Vela workspace and its dependencies are bundled locally. The optional Global markets viewer loads the official TradingView widget script and frame from TradingView.

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

The initial XAUUSD and other sample data are **synthetic** and end on 16 October 2026. They are neither historical market observations nor current quotes. Samples do not implement exchange trading calendars. Select Binance for external crypto data; availability depends on network, provider and region. Global markets displays provider-labeled TradingView reference charts for Forex, metals and CFD indices. To use broker candles inside Vela, connect the included personal MT4/MT5 gateway to an already logged-in terminal. Broker data are unavailable until that gateway is running and authenticated. Import CSV to research other licensed prices.

CSV imports require a header and positive OHLC prices. Supported delimiters: comma, semicolon, tab. Columns: `time`/`timestamp` or `date` + `time`, `open`, `high`, `low`, `close`, optional `volume`/`tickvol`. Epoch seconds, epoch milliseconds, ISO dates and MT5 dates are supported. Unzoned date strings use the import dialog's UTC offset. Duplicates keep the last row, then sort ascending. Finer timeframes cannot be reconstructed from coarse CSV bars. Limits: 25 MiB per import, 100,000 CSV rows; chart history capture retains at most 10,000 bars per chart identity.

Backtests use loaded chart history, or the revealed prefix during Replay. Current forming Binance and broker bars are excluded. The available history is not an entire exchange archive. Size is in asset units, and capital/P&L use the symbol's quote currency. Backtests model no margin, leverage, funding, swap, spread other than the chosen slippage, volume constraints or liquidation. There can be at most one strategy position. A surviving position is closed at the final bar. Drawdown is sampled at bar closes, so intrabar drawdown can be larger. Limited sample results are not evidence of an investment edge.

Paper orders use asset units, not CFD lots. Accounts are separate by the actual quote currency, including USD, USDT, BTC, ETH, THB and other catalog quotes. Fills use visible chart prices with configurable commission but no paper slippage or margin modeling. Stop/target exits require this page to receive new bars on the same symbol/timeframe and Replay mode. Alerts run only while the page is open; no background service or broker orders are installed.

User notes, positions, alerts, imported bars and chart layouts remain in this browser's localStorage. They do not sync between devices or users. Use Backup to export a JSON archive. Clearing browser storage removes local records. No user records or API credentials are committed to GitHub.

## Binance Spot live prices

Choose **Binance · Crypto** above the chart. The pair selector and Vela's native symbol picker load **all currently trading Spot pairs** from Binance `exchangeInfo`, including every quote currency returned by the exchange. No fixed seven-coin list is used.

Click **All markets / สินทรัพย์ทั้งหมด** to search by symbol, base or quote asset, filter by quote currency (USDT, USDC, BTC, THB and all others returned), page through the full list, open a chart or star a pair into Watchlist. The dialog renders 100 rows per page; pagination changes presentation only, never the available catalog. Catalog requests are shared and cached for 15 minutes within this session. Opening the browser after cache expiry or clicking **Refresh list** loads new exchange listings. A failed refresh retains the previous catalog with an explicit error and its original timestamp.

The catalog uses `permissions=SPOT`, `symbolStatus=TRADING` and `showPermissionSets=false`, and checks the returned Spot/status flags. Halted, delisted and non-Spot entries are not listed as active markets. Unicode asset names are supported and URL-encoded for streams. Base/quote identifiers and tick size come from Binance metadata. Paper/backtest results use the actual quote currency, so ETH/BTC results are labeled BTC rather than USD; chart prices preserve each pair's tick precision.

A direct link can select a source and pair: `/?source=binance&symbol=BTCUSDT`.

This adapter uses Binance's official, public market-data-only hosts:

- Historical candles: `https://data-api.binance.vision/api/v3/klines`
- Current candle updates: `wss://data-stream.binance.vision:443/ws/btcusdt@kline_15m`
- Documentation: https://developers.binance.com/en/docs/products/spot/faqs/market_data_only

No Binance account, API key, trading permission, backend or third-party proxy is required for this public feed. This is **Spot**, not futures, Forex or gold. External network and regional availability can still affect connectivity.

`BINANCE · LIVE` appears only after a fresh valid WebSocket candle for the selected pair and interval. Socket opening alone is not counted as a live price. The status line shows the receive time in Thailand time. A silent socket is closed after 15 seconds; REST updates are requested every 5 seconds while reconnecting, with no overlapping polling requests. REST fallback is labeled `BINANCE · REST`. Invalid, stale, wrong-symbol and out-of-order stream messages are ignored. When the selected Binance quote is unavailable or stale, paper Buy/Sell buttons are disabled. Broker-feed CFD paper trading is not enabled; its quotes/candles are available for charting and unit-based research backtests. Existing data are not silently replaced with synthetic sample prices.

Use **Reconnect** to refresh chart history and resubscribe while retaining workspace content. Non-native aggregated intervals use REST so they do not render an incomplete streamed aggregate. Monthly chart intervals are outside the supported live interval list.

REST history and a real WebSocket candle were received successfully from this execution environment. The Binance catalog and live adapter are covered by unit and simulated-DOM tests, additionally covering the full dynamic catalog, quote filtering, pagination, Unicode pairs, non-USDT quote units, small-price precision, reconnect, pair switching, stale stream detection, polling fallback and unsubscribe cleanup. This does not verify the user's browser/network or real browser rendering.

## Mobile and tablet layout (1.3.1)

The host uses a chart-first layout on phones (up to 767 CSS pixels) and tablets (768–1180 CSS pixels). A five-action bottom navigation opens Chart, Research, Global markets, Watchlist and More. The compact menu retains Performance, Strategy Lab, Journal, Broker/MCP, Import, Backup, theme, language and help controls. Desktop side panels retain their independent toggles.

Research and Watchlist become exclusive drawers with close buttons, backdrop dismissal, Escape/Tab focus handling and background controls suspended while a drawer is open. Phone startup and short landscape windows collapse results to preserve chart space; results remain available from their tabs or More → Performance. The compact chart focus button expands the workspace and remains available to exit. Rotating or resizing changes the host layout without re-creating Vela charts, data subscriptions or indicators.

Controls use larger touch targets; editable fields use 16px text on compact/touch layouts. Tables scroll inside their own containers, asset rows retain their pair/quote text, and broker forms stack on phones. Global charts, Broker/MCP, market search and other dialogs adapt to the available viewport height. Safe-area insets and the visual viewport accommodate notches, browser controls and the keyboard without disabling browser zoom. A keyboard resize preserves an active Journal/strategy input rather than collapsing its panel. Vela uses its supported automatic layout mode for native touch tools.

Validation includes DOM interaction checks for phone/tablet/desktop transitions, drawer focus and exclusivity, menu forwarding, keyboard/visual viewport changes, and a real-Vela integration check that preserves chart and indicator instances across viewport changes. Both stylesheets are syntax-checked with esbuild. **Actual mobile/tablet rendering and touch gestures have not been verified on physical devices or in a browser emulator.**

## Global markets and personal broker prices (1.3)

Choose **Global markets / ตลาดโลก** for the embedded TradingView viewer: XAUUSD, XAGUSD, all seven FX majors (EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD), GBPJPY and eight major index CFDs. A direct link `/?view=markets` opens the viewer. The selected data source is OANDA through TradingView, **not Axi**. Index symbols are CFD references, not exchange cash-index feeds. Data availability and delays are governed by the widget/provider; check the chart's own status. The widget retains TradingView attribution. It does not export or feed quotes/candles into Vela, backtests, alerts or paper trading.

Choose **Broker / MCP** to connect the included `broker-bridge/` kit. Build output includes a downloadable ZIP and Thai setup guide. The gateway reads MT5 via MetaQuotes' Windows Python integration, or MT4 via the supplied WebRequest EA. Axi, Pepperstone, IC Markets and other MetaTrader accounts use this same terminal path, subject to account/platform availability. This is a custom NS integration; no native Axi MCP, broker API key, private API or broker login is supplied.

- Run on the Windows computer / VPS with the broker terminal already logged in. MT5 needs `pip install MetaTrader5`. MT4 needs the supplied EA, the gateway URL in WebRequest settings, desired instruments in Market Watch, and the actual broker UTC offset. One EA services one gateway; MT4 history uses that fixed offset and needs care across DST transitions.
- The website requires a gateway URL and a separate random 32+ character Bearer token. It reads the actual broker company name, exact symbol/suffix catalog, quote currency and tick size. The gateway reads the logged-in terminal; the website does not change its broker account. No broker password is sent to the website.
- URLs must use HTTPS, except loopback HTTP. Gateway binds to loopback; VPS access needs the user's HTTPS reverse proxy/tunnel and explicit Host/Origin allowlists. Browser local-network restrictions can require HTTPS or running the app locally. There is no automatically opened public port.
- Gateway credentials stay in memory only and are excluded from localStorage, backups and source. After reload, saved broker charts wait for a fresh connection; the app starts with clearly labeled samples and opens connection settings. Broker history is cleared when changing gateway connections. Separate broker processes/ports/tokens are needed for multiple terminals; this UI uses one connected gateway at a time.
- Broker updates poll roughly every two seconds. `BROKER · LIVE` requires a valid candle response and an original tick timestamp no more than 30 seconds old. Receipt of an old tick never becomes LIVE merely because an HTTP request succeeded. Missing/stale data and errors remain explicit, without synthetic fallback.
- The final broker candle can be forming and is excluded from current-bar research backtests. Backtests still model asset units/quote-currency P&L, not full CFD contracts, margin, spread, swap or leverage. Broker CFD paper orders are disabled. The existing manual risk calculator retains illustrative settings; verify contract and account-currency values before using it.

The same gateway exposes four **read-only MCP tools**: `get_connection_status`, `list_symbols`, `get_quote`, `get_candles`. It supports both local stdio (`mcp_server.py`, newline-delimited JSON-RPC) and stateless Streamable HTTP JSON responses at `/mcp`, protected by the same Bearer token and Host/Origin checks. HTTP GET returns 405 because no SSE stream is offered. Example configs and the Thai guide explain clients supporting token-authenticated HTTP and VPS HTTPS. Connecting ChatGPT remote MCP additionally requires a reachable user-owned HTTPS endpoint, supported authentication (OAuth where required), and connection registration. Those user-side steps are not installed automatically. No trading, withdrawal or account-write tools/routes are implemented.

Verified: **33 JavaScript tests and 8 Python tests**, including real Vela in a simulated DOM, exact-suffix selection, non-USD currency metadata, dynamic quote freshness, disconnect/cleanup, missing credentials on restore, widget structure/attribution, actual local HTTP auth/CORS/Host checks, MT4 request/response fixtures, MT5 UTC fixtures and full stdio/HTTP MCP initialize/list/call exchanges. The downloadable ZIP passes a standard ZIP integrity check. Fixtures are explicitly labeled and are not real broker quotes. **No actual Axi account, MT4 compiler or real browser rendering was available for end-to-end verification.**

Setup: [broker-bridge/README-TH.md](broker-bridge/README-TH.md).

Primary references:
- Axi platforms: https://help.axi.com/en-US/axiv2--axicorp-prod/article/UXVsGgzY-what-trading-platforms-can-i-use-to-trade
- Axi MT5: https://www.axi.com/th/trading-platforms/metatrader-5
- MetaQuotes Python: https://www.mql5.com/en/docs/python_metatrader5
- MQL4 WebRequest: https://docs.mql4.com/common/webrequest
- TradingView widget data: https://www.tradingview.com/widget-docs/faq/data/
- MCP transports: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports

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
