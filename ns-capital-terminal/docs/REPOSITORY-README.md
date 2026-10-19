# Start Building · NS Capital Terminal

Private trading workspace for NS Capital, with real market charts, MT4/MT5 account gateways, an Auto Journal, backend risk engine and optional AI coaching.

**[เปิดเว็บไซต์](https://ns-capital-terminal.biw-modify004.chatgpt.site)** · **[คู่มือภาษาไทย](ns-capital-terminal/docs/USER-MANUAL-TH.md)** · **[Project README](ns-capital-terminal/README.md)** · **[Deployment](ns-capital-terminal/docs/DEPLOYMENT-TH.md)**

| Path | Contents |
| --- | --- |
| `ns-capital-terminal/src/` | Responsive trading terminal, dashboard, PWA and login entry pages |
| `ns-capital-terminal/broker-bridge/` | Python ledger/risk/analytics, MT4 EA, MT5 integration, AI and MCP |
| `ns-capital-terminal/docs/` | Complete Thai user manual and operations |
| `ns-capital-terminal/tests/` | Fixture tests; no live broker execution |
| `.github/workflows/ns-capital-ci.yml` | JavaScript/Python tests and reproducible build |

```sh
cd ns-capital-terminal
npm ci
npm test
npm run test:python
npm run build
```

The published frontend and Windows Broker Bridge are separate runtime components. Site login uses ChatGPT/Sites access; execution requires a configured terminal, gateway, separate Trade token and backend risk limits. This repository contains no broker credentials or real account databases. See the project README for boundaries, attribution and verification limits.
