# NS Capital Terminal

NS Capital’s personal trading workspace: real market charts, multiple MetaTrader accounts, a persistent Auto Journal, backend risk checks and optional model-assisted coaching. The chart core is **Vela 0.8.4**; the surrounding application is independently implemented. LuxAlgo private services and premium indicator code are not included.

**[Open the GitHub Pages website](https://biwmodify004.github.io/Start-Building/)** · **[คู่มือภาษาไทยฉบับเต็ม](docs/USER-MANUAL-TH.md)** · **[Deployment](docs/DEPLOYMENT-TH.md)** · **[Changelog](CHANGELOG.md)**

## Product scope

| Area | Implemented behavior |
| --- | --- |
| Charts | Full active Binance Spot catalog, REST/stream recovery, native Vela indicators/drawings/replay and provider-labeled global reference charts |
| Broker accounts | Verified MT4/MT5 gateway profiles; one active account per request; actual broker symbols and contract metadata |
| Execution | Opt-in market orders, full closes and SL/TP changes; separate Trade token, short-lived previews, account guards and durable receipts |
| Auto Journal | SQLite on the Bridge computer/VPS; actual terminal history, commission/swap/fees, cash-flow review, notes and CSV |
| Analytics | Complete MT5 flat-to-flat cycles; explicitly labeled MT4 closed tickets; booked P&L curve, win rate, profit factor and setup statistics |
| Risk | Server-side per-trade SL estimate, daily-loss and observed equity-DD gates, latched halts and reduction/close paths |
| AI | Ollama, LM Studio or compatible API; validated trade drafts and journal coaching from backend-computed metrics; no AI execution |
| Sharing | Explicit opt-in, redacted, expiring/revocable report snapshots; a qualifying internal Bridge leaderboard |
| Website | Responsive terminal/journal, Google sign-in verified by the Bridge, PWA shell, light/dark theme and searchable 28-chapter Thai manual |

No generated prices or sample accounts appear as actual financial records. Test fixtures are isolated under `tests/`.

## Architecture

The published frontend is a static PWA. GitHub Pages serves the public frontend. Google Identity Services signs users in; the Bridge verifies Google signatures, audience/issuer/expiry, a single-use nonce and an owner allowlist before issuing an account-bound 30-minute session. Python Bridge, SQLite and the logged-in MT4/MT5 terminal run on the owner’s Windows machine/VPS; a user-configured HTTPS gateway enables other devices. Ollama/LM Studio/API access runs through the Bridge. The website does not provision a Windows VPS or run MetaTrader in the browser.

The SQLite account namespace is platform + server + login. Multiple account Bridge processes on one host may share one local database file, with separate ports/tokens and one execution Bridge per account. This is not a multi-tenant SaaS backend or a database shared across network filesystems/VPS instances.

Track-record reports disclose their terminal-Bridge origin and lack of independent broker verification. The report viewer is public; its opaque report capability is required to read an unexpired, unrevoked snapshot from the Bridge.

## Development

Requires Node 22.13+ and Python 3.11+. Production MT5 additionally needs Windows, its terminal and the MetaQuotes Python package. Tests use fixtures and the Python standard library.

```sh
npm ci
npm test
npm run test:python
npm run build:pages
npm start
```

Open `http://127.0.0.1:8080`. Build output is `dist/`, including the website, `manual.html`, downloadable Thai manual and complete Broker Bridge ZIP. Browser-local research works without a model. Google Login requires a Google Web Client ID, explicit owner allowlist and the optional requirements-google.txt package installed on the Windows Bridge. No Client Secret is used in the browser.

| Source | Purpose |
| --- | --- |
| `src/` | Terminal, journal dashboard, account UI, portal pages and PWA |
| `broker-bridge/` | Gateway, MT4 EA, actual ledger, risk, analytics, model connector and MCP |
| `scripts/` | Build, Thai-manual rendering and secret-free ZIP packaging |
| `tests/` | Market, UI, execution, account, journal, risk, sharing and AI fixtures |
| `docs/` | Thai user manual, deployment and market/research boundaries |
| `.github/` | CI, contribution template and sanitized issue form |

In `biwmodify004/Start-Building`, this app is under `ns-capital-terminal/`; the active CI workflow is at repository root. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## Setup and operational boundaries

Follow the [Thai manual](docs/USER-MANUAL-TH.md) for MT4/MT5 installation, token roles, HTTPS, multiple accounts, risk configuration, AI/MCP, backup/restore and troubleshooting. Updating to 1.9 requires all Bridge modules, the updated MT4 EA if used, a private publisher token for MT4, complete history and explicit per-account risk limits before new entries.

New orders are rechecked at preview and execution. Daily and DD halts persist in SQLite. Closing and tightening stops can remain available while new risk is blocked. This does not auto-liquidate existing positions, reserve aggregate portfolio exposure, control other terminal apps, or guarantee a maximum realized loss during gaps/slippage. See the manual’s exact formulas and limitations.

The six MCP tools read broker data/positions or request a draft; none executes an order. AI keys and broker credentials stay server-side. Bridge/Trade tokens stay in browser memory and are excluded from local storage/backups. Browser-local profiles/research do not synchronize between devices. Central journal/risk data live on the Bridge, not in GitHub or ChatGPT storage.

Backtests and Paper Trading use loaded chart history and asset units rather than full CFD/Futures contract, margin, funding or swap simulation. See [DATA-RESEARCH.md](docs/DATA-RESEARCH.md). Connecting a model provides inference, not a training/continuous-auto-trading pipeline.

## Validation

Tests cover actual SQLite persistence/backup, deduplication/costs, complete/partial/reversal cycle accounting, cash-flow handling, daily/DD latches, execution-time policy changes, durable receipts, MT4 batches/private publisher/delivery guards, redacted/revocable sharing, opt-in ranking, model-input minimization, account-switch races, and real Vela integration in JSDOM. Build output retains third-party notices and excludes runtime databases/secrets.

Fixture tests do not verify real browser rendering/touch, broker execution, MetaEditor compilation or model inference on the user’s server. No real trading account is connected in the development environment.

## License and attribution

[Vela](https://github.com/LuxAlgo/Vela) is Apache-2.0 with its NOTICE requirement. Visible [Vela attribution](https://velacharts.dev), `vendor/VELA-LICENSE.txt`, `vendor/VELA-NOTICE.txt` and dependency notices ship with each build. No LuxAlgo private source, premium indicator code, private API or account session is included. Third-party components retain their licenses.

## GitHub Pages deployment

Root `.github/workflows/ns-capital-pages.yml` tests, builds and deploys changes on `main`; the artifact is scoped to `/Start-Building/`. Enable Repository Settings → Pages → Source: GitHub Actions once. The workflow needs Pages and OIDC write permissions only in its deploy job. `deployment/github-pages.json` records the target. This replaces Sites as the primary deployment; the old private Sites publication is retained unchanged.

Google Login setup: [Thai user manual](docs/USER-MANUAL-TH.md#google-login). Backend environment: `NS_GOOGLE_CLIENT_ID`, `NS_GOOGLE_ALLOWED_EMAILS` (Google-hosted accounts) or `NS_GOOGLE_ALLOWED_SUBS`, and `NS_ALLOWED_ORIGINS=https://biwmodify004.github.io`. OAuth client creation and Windows configuration must be performed with the owner's actual settings; no placeholder credential is active.
