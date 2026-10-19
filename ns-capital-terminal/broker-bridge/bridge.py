"""NS Capital personal gateway. Manual trading requires --enable-trading and a separate trade token.

Python 3.11+. MT5 mode additionally requires the MetaQuotes Windows package.
MT4 mode receives quotes/candles from NS_Market_Bridge.mq4 via WebRequest.
"""
from __future__ import annotations
import argparse
from collections import OrderedDict
from datetime import datetime, timezone
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
import re
import secrets
import threading
import time
from urllib.parse import parse_qs, urlsplit
from trading import TradingService, key as trading_account_key
from ai_advisor import AITradeAdvisor
from mcp_server import VERSIONS as MCP_VERSIONS, handle as mcp_handle, call_tool as mcp_call_tool

PROTOCOL = "ns-market-bridge/1"
FRAMES = {"1": 1, "5": 5, "15": 15, "30": 30, "60": 60, "240": 240, "D": 1440, "W": 10080}
SYMBOL = re.compile(r"^[\w#.\-]{1,128}$", re.UNICODE)

def valid_symbol(value):
    if not isinstance(value, str) or not SYMBOL.fullmatch(value):
        raise ValueError("Invalid symbol")
    return value

def valid_frame(value):
    if value not in FRAMES:
        raise ValueError("Unsupported timeframe")
    return value

def finite(value, minimum=0):
    if isinstance(value, bool):
        raise ValueError("Invalid number")
    number = float(value)
    if not math.isfinite(number) or number < minimum:
        raise ValueError("Invalid number")
    return number

def clean_bars(rows):
    if not isinstance(rows, list) or len(rows) > 10000:
        raise ValueError("Invalid candle list")
    unique = {}
    for row in rows:
        b = {k: finite(row[k], 1e-16) for k in ("open", "high", "low", "close")}
        b.update(time=int(finite(row["time"])), volume=finite(row.get("volume", 0)))
        if b["high"] < max(b["open"], b["close"]) or b["low"] > min(b["open"], b["close"]):
            raise ValueError("Invalid candle range")
        if b["time"] > int(time.time() * 1000) + 5000:
            raise ValueError("Future candle: check broker UTC offset")
        unique[b["time"]] = b
    return [unique[t] for t in sorted(unique)]

def clean_quote(row):
    symbol = valid_symbol(row["symbol"])
    bid, ask, at = finite(row["bid"], 1e-16), finite(row["ask"], 1e-16), int(finite(row["time"]))
    if ask < bid or at > time.time() * 1000 + 5000:
        raise ValueError("Invalid quote: check broker UTC offset")
    return {"symbol": symbol, "bid": bid, "ask": ask, "time": at}

def classify(name, path=""):
    value = (name + " " + path).upper()
    if any(x in value for x in ("XAU", "XAG", "GOLD", "SILVER", "METAL", "COMMOD")):
        return "commodity"
    if any(x in value for x in ("INDEX", "INDICES", "US30", "US500", "USTEC", "NAS100", "GER40", "DE40", "JP225", "UK100")):
        return "index"
    if any(x in value for x in ("FOREX", "FX\\", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "GBPJPY")):
        return "forex"
    if any(x in value for x in ("CRYPTO", "BTC", "ETH")):
        return "crypto"
    return "custom"

class MT5Source:
    def __init__(self, terminal_path=None, module=None):
        if module is None:
            try:
                import MetaTrader5 as module
            except ImportError as error:
                raise RuntimeError("Install MetaTrader5 with Windows Python, then log in to the broker's desktop MT5") from error
        self.mt5, self.lock = module, threading.RLock()
        ok = module.initialize(terminal_path) if terminal_path else module.initialize()
        if not ok:
            raise RuntimeError("MT5 initialization failed. Open the correct logged-in terminal and set NS_MT5_PATH")

    def status(self):
        with self.lock:
            terminal, account = self.mt5.terminal_info(), self.mt5.account_info()
        details = None if account is None else {"id": str(getattr(account, "login", "")), "server": str(getattr(account, "server", "")), "currency": str(getattr(account, "currency", "")), "mode": "demo" if getattr(account, "trade_mode", None) == 0 else "real" if getattr(account, "trade_mode", None) == 2 else "contest" if getattr(account, "trade_mode", None) == 1 else "unknown", "balance": getattr(account, "balance", None), "equity": getattr(account, "equity", None), "freeMargin": getattr(account, "margin_free", None), "positionMode": "hedging" if getattr(account, "margin_mode", None) == 2 else "netting" if getattr(account, "margin_mode", None) in (0, 1) else "unknown"}
        return {"protocol": PROTOCOL, "readOnly": True, "platform": "MT5", "broker": getattr(account, "company", "MT5 broker"), "connected": bool(terminal and terminal.connected and account), "serverTimeBasis": "UTC", "accountCurrency": getattr(account, "currency", None), "account": details}

    def symbols(self):
        with self.lock:
            rows = self.mt5.symbols_get()
            if rows is None:
                raise RuntimeError("MT5 symbol catalog unavailable")
            result = []
            for s in rows:
                tick = s.trade_tick_size or s.point
                if not SYMBOL.fullmatch(s.name) or not s.currency_profit or not tick or s.trade_mode == 0:
                    continue
                result.append({"ticker": s.name, "description": s.description, "type": classify(s.name, s.path), "currency": s.currency_profit, "baseAsset": s.currency_base, "tickSize": tick, "tickValue": s.trade_tick_value, "lotStep": s.volume_step, "contractSize": s.trade_contract_size, "assetClass": "futures" if getattr(s, "trade_calc_mode", -1) in (1, 33, 34) else "cfd" if getattr(s, "trade_calc_mode", -1) in (0, 2, 3, 4, 5) else "other", "expiry": int(getattr(s, "expiration_time", 0)) * 1000, "exchange": str(getattr(s, "exchange", "")), "volumeMin": s.volume_min, "volumeMax": s.volume_max, "volumeStep": s.volume_step, "point": s.point, "stopsLevel": s.trade_stops_level})
            return result

    def select(self, symbol):
        if not self.mt5.symbol_select(symbol, True):
            raise ValueError("Symbol unavailable in this terminal: " + symbol)

    def quote(self, symbol):
        with self.lock:
            self.select(symbol)
            q = self.mt5.symbol_info_tick(symbol)
            if q is None:
                raise RuntimeError("Broker quote unavailable")
            return clean_quote({"symbol": symbol, "bid": q.bid, "ask": q.ask, "time": q.time_msc or q.time * 1000})

    def bars(self, symbol, frame, limit, start=None, end=None):
        with self.lock:
            self.select(symbol)
            tf = getattr(self.mt5, "TIMEFRAME_" + {"D": "D1", "W": "W1"}.get(frame, ("H" + str(int(frame) // 60)) if frame in ("60", "240") else "M" + frame))
            if end is not None:
                rows = self.mt5.copy_rates_from(symbol, tf, datetime.fromtimestamp(end / 1000, timezone.utc), limit)
            else:
                rows = self.mt5.copy_rates_from_pos(symbol, tf, 0, limit)
            if rows is None:
                raise RuntimeError("MT5 candles unavailable. Load history in the terminal")
            bars = clean_bars([{"time": int(r["time"]) * 1000, "open": float(r["open"]), "high": float(r["high"]), "low": float(r["low"]), "close": float(r["close"]), "volume": float(r["tick_volume"])} for r in rows])
        return [b for b in bars if (start is None or b["time"] >= start) and (end is None or b["time"] <= end)][-limit:]

class MT4Source:
    def __init__(self, wait_seconds=15):
        self.condition = threading.Condition()
        self.catalog, self.quotes = {}, {}
        self.series, self.pending = OrderedDict(), OrderedDict()
        self.broker, self.heartbeat, self.connected = "MT4 broker", 0, False
        self.account = None
        self.trade_allowed, self.positions_at = False, 0
        self.positions_snapshot = []
        self.trade_queue, self.trade_results = OrderedDict(), OrderedDict()
        self.wait_seconds = wait_seconds

    def status(self):
        with self.condition:
            return {"protocol": PROTOCOL, "readOnly": True, "platform": "MT4", "broker": self.broker, "account": self.account, "connected": self.connected and time.monotonic() - self.heartbeat < 45, "serverTimeBasis": "UTC (EA configured broker offset)", "error": None if self.heartbeat else "Attach NS_Market_Bridge EA and allow WebRequest"}

    def symbols(self):
        with self.condition:
            return list(self.catalog.values())

    def publish(self, payload):
        # Validate the complete payload before changing any shared state.
        catalog = None
        if "symbols" in payload:
            if not isinstance(payload["symbols"], list) or len(payload["symbols"]) > 20000:
                raise ValueError("Invalid symbol catalog")
            catalog = {}
            for m in payload["symbols"]:
                ticker = valid_symbol(m["ticker"])
                if not isinstance(m.get("currency"), str) or not m["currency"]:
                    continue
                catalog[ticker] = {"ticker": ticker, "description": str(m.get("description", ticker))[:500], "currency": m["currency"][:12], "tickSize": finite(m["tickSize"], 1e-16), "type": classify(ticker, str(m.get("path", ""))), "lotStep": finite(m.get("lotStep", .01), 1e-16), "assetClass": "cfd", "expiry": finite(m.get("expiry", 0), 0), "volumeMin": finite(m.get("volumeMin", .01), 1e-16), "volumeMax": finite(m.get("volumeMax", 100), 1e-16), "volumeStep": finite(m.get("lotStep", .01), 1e-16), "point": finite(m.get("point", m["tickSize"]), 1e-16), "stopsLevel": finite(m.get("stopsLevel", 0))}
        quotes = [clean_quote(q) for q in payload.get("quotes", [])]
        series = []
        for entry in payload.get("series", []):
            key = (valid_symbol(entry["symbol"]), valid_frame(entry["timeframe"]))
            series.append((key, clean_bars(entry["bars"])))
        positions = None
        if "positions" in payload:
            if not isinstance(payload["positions"], list) or len(payload["positions"]) > 20000:
                raise ValueError("Invalid MT4 position list")
            positions = []
            for p in payload["positions"]:
                ticket, side = str(p["ticket"]), p["side"]
                if not ticket.isdigit() or side not in ("buy", "sell"):
                    raise ValueError("Invalid MT4 position")
                profit, swap = float(p["profit"]), float(p.get("swap", 0))
                if not math.isfinite(profit) or not math.isfinite(swap):
                    raise ValueError("Invalid MT4 profit")
                positions.append({"ticket":ticket, "symbol":valid_symbol(p["symbol"]), "side":side, "volume":finite(p["volume"],1e-16), "entry":finite(p["entry"],1e-16), "price":finite(p["price"],1e-16), "sl":finite(p.get("sl",0)), "tp":finite(p.get("tp",0)), "profit":profit, "swap":swap, "time":int(finite(p["time"]))})
        account = payload.get("account")
        if account is not None:
            if not isinstance(account, dict) or not str(account.get("id", "")) or not str(account.get("server", "")):
                raise ValueError("Invalid trading account identity")
            account = {"id": str(account["id"])[:80], "server": str(account["server"])[:160], "currency": str(account.get("currency", ""))[:12], "mode": "demo" if account.get("mode") == "demo" else "real", **{key: finite(account[key]) for key in ("balance", "equity", "freeMargin") if key in account}}
        with self.condition:
            if account is not None:
                if self.account and (account["id"], account["server"]) != (self.account["id"], self.account["server"]):
                    self.catalog.clear(); self.quotes.clear(); self.series.clear(); self.pending.clear(); self.trade_queue.clear(); self.positions_snapshot=[]; self.positions_at=0
                self.account = account
            if catalog is not None:
                self.catalog = catalog
            for q in quotes:
                old = self.quotes.get(q["symbol"])
                if not old or q["time"] >= old["time"]:
                    self.quotes[q["symbol"]] = q
            for key, bars in series:
                merged = {b["time"]: b for b in self.series.get(key, (0, []))[1]}
                merged.update({b["time"]: b for b in bars})
                self.series[key] = (time.monotonic(), [merged[t] for t in sorted(merged)[-10000:]])
                self.series.move_to_end(key)
                while len(self.series) > 128:
                    self.series.popitem(last=False)
            if positions is not None:
                self.positions_snapshot, self.positions_at = positions, time.monotonic()
            self.trade_allowed = payload.get("tradeAllowed") is True
            self.broker = str(payload.get("broker", self.broker))[:160]
            self.connected = payload.get("connected") is True
            self.heartbeat = time.monotonic()
            self.condition.notify_all()

    def next_trade(self):
        with self.condition:
            while self.trade_queue:
                ident, command = self.trade_queue.popitem(last=False)
                if command["expiresAt"] < time.time() * 1000:
                    self.trade_results[ident] = {"status":"rejected", "message":"MT4 command expired before pickup"}
                    continue
                # One delivery only; the EA re-posts receipts, never re-runs a command.
                return "|".join(str(command[k]) for k in ("requestId", "action", "symbol", "side", "volume", "sl", "tp", "deviation", "position", "accountId", "server", "expiresAt", "price"))
            return ""

    def publish_trade_result(self, payload):
        ident = payload.get("requestId", "")
        if not isinstance(ident,str) or not re.fullmatch(r"[a-zA-Z0-9_-]{16,80}",ident) or payload.get("status") not in ("filled","rejected","unknown"):
            raise ValueError("Invalid MT4 receipt")
        with self.condition:
            self.trade_results.setdefault(ident, {"status":payload["status"], "message":str(payload.get("message", ""))[:300], "order":str(payload.get("order", "")), "retcode":int(finite(payload.get("retcode",0)))})
            if len(self.trade_results) > 10000:
                self.trade_results.popitem(last=False)
            self.condition.notify_all()

    def next_request(self):
        with self.condition:
            if not self.pending:
                return ""
            key, request = self.pending.popitem(last=False)
            symbol, frame, end = key
            return f"{symbol}|{frame}|{request['limit']}|{end or 0}"

    def quote(self, symbol):
        with self.condition:
            if symbol not in self.quotes:
                raise RuntimeError("Waiting for MT4 quote. Request chart candles first")
            return dict(self.quotes[symbol])

    def bars(self, symbol, frame, limit, start=None, end=None):
        key, request_key = (symbol, frame), (symbol, frame, end)
        deadline = time.monotonic() + self.wait_seconds
        with self.condition:
            if symbol not in self.catalog:
                raise ValueError("Symbol unavailable in MT4: " + symbol)
            original_at = self.series.get(key, (0, []))[0]
            need_refresh = time.monotonic() - original_at > 1.5
            def filtered():
                return [b for b in self.series.get(key, (0, []))[1] if (start is None or b["time"] >= start) and (end is None or b["time"] <= end)][-limit:]
            if need_refresh or len(filtered()) < limit:
                existing = self.pending.get(request_key, {"limit": 0})
                self.pending[request_key] = {"limit": max(limit, existing["limit"])}
                while time.monotonic() < deadline:
                    if self.series.get(key, (0, []))[0] > original_at:
                        break
                    self.condition.wait(max(0, deadline - time.monotonic()))
                self.pending.pop(request_key, None)
                if self.series.get(key, (0, []))[0] <= original_at:
                    raise RuntimeError("MT4 EA did not respond. Check Experts log, WebRequest and UTC offset")
            return filtered()

def make_handler(source, token, allowed_origins, allowed_hosts, enable_trading=False, trade_token=None):
    if enable_trading and (not trade_token or len(trade_token) < 32 or trade_token == token):
        raise ValueError("Trading needs a separate 32+ character trade token")
    trading = TradingService(source, enabled=enable_trading)
    advisor = AITradeAdvisor(source, trading)
    def status_response():
        return {**source.status(), "readOnly":not enable_trading, "trading":trading.capability(), "ai":advisor.status()}
    def mcp_request(path, params):
        if path == "/v1/trading/state":
            return trading.state(trading_account_key(source.status()))
        if path == "/v1/ai/propose":
            return advisor.propose({**params, "accountKey":trading_account_key(source.status())})
        if path == "/v1/status":
            return status_response()
        if path == "/v1/symbols":
            return {"symbols": source.symbols()}
        if not source.status()["connected"]:
            raise RuntimeError("Broker terminal is disconnected")
        symbol = valid_symbol(params["symbol"])
        if path == "/v1/quote":
            return source.quote(symbol)
        frame = valid_frame(params["timeframe"])
        return {"symbol": symbol, "timeframe": frame, "bars": source.bars(symbol, frame, params["limit"])}
    def mcp_caller(name, args):
        return mcp_call_tool(name, args, request=mcp_request)
    class Handler(BaseHTTPRequestHandler):
        server_version = "NSMarketBridge/1"
        def setup(self):
            super().setup()
            self.connection.settimeout(25)
        def log_message(self, *args):
            pass  # Tokens, query strings and financial records are never logged.
        def origin_ok(self):
            origin = self.headers.get("Origin")
            return not origin or origin in allowed_origins
        def host_ok(self):
            return urlsplit("http://" + self.headers.get("Host", "")).hostname in allowed_hosts
        def reply(self, status, data, plain=False):
            body = b"" if status == 202 and data is None else data.encode("utf-8") if plain else json.dumps(data, allow_nan=False, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            origin = self.headers.get("Origin")
            if origin and origin in allowed_origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Type", "text/plain; charset=utf-8" if plain else "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def authorized(self, trade=False):
            if not self.host_ok() or not self.origin_ok():
                self.reply(403, {"error": "Host or Origin is not allowed"}); return False
            provided = self.headers.get("Authorization", "")
            if not hmac.compare_digest(provided.encode("utf-8"), ("Bearer " + token).encode("utf-8")):
                self.reply(401, {"error": "Invalid bridge token"}); return False
            if trade and (not enable_trading or not hmac.compare_digest(self.headers.get("X-Trade-Token", "").encode("utf-8"), (trade_token or "").encode("utf-8"))):
                self.reply(403, {"error":"Manual trading is disabled or the separate Trade token is invalid"}); return False
            return True
        def do_OPTIONS(self):
            if not self.host_ok() or not self.origin_ok():
                return self.reply(403, {"error": "Origin is not allowed"})
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", ""))
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Authorization, X-Trade-Token, Content-Type, Accept, MCP-Protocol-Version, MCP-Session-Id")
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.end_headers()
        def do_GET(self):
            if not self.authorized():
                return
            try:
                url = urlsplit(self.path)
                query = {k: v[-1] for k, v in parse_qs(url.query).items()}
                if url.path == "/mcp":
                    return self.reply(405, {"error": "MCP uses POST JSON responses; no SSE stream is offered"})
                if url.path == "/v1/status":
                    return self.reply(200, status_response())
                if url.path == "/v1/ai/status":
                    return self.reply(200, advisor.status())
                if url.path == "/v1/trading/state":
                    return self.reply(200, trading.state(query.get("accountKey")))
                if url.path == "/v1/trading/receipt":
                    return self.reply(200, trading.receipt(query.get("requestId"), query.get("accountKey")))
                if url.path == "/v1/mt4/trade-request" and isinstance(source, MT4Source):
                    if self.authorized(trade=True):
                        return self.reply(200, source.next_trade(), plain=True)
                    return
                if url.path == "/v1/symbols":
                    return self.reply(200, {"symbols": source.symbols()})
                if url.path == "/v1/mt4/request" and isinstance(source, MT4Source):
                    return self.reply(200, source.next_request(), plain=True)
                if url.path not in ("/v1/quote", "/v1/bars"):
                    return self.reply(404, {"error": "Unknown data route"})
                if not source.status()["connected"]:
                    return self.reply(503, {"error": "Broker terminal is disconnected"})
                expected = query.get("accountKey")
                def same_account():
                    account = source.status().get("account") or {}
                    return str(account.get("server", "")) + "|" + str(account.get("id", "")) == expected
                if expected and not same_account():
                    return self.reply(409, {"error": "Trading account changed. Reconnect the account"})
                symbol = valid_symbol(query.get("symbol"))
                if url.path == "/v1/quote":
                    quote = source.quote(symbol)
                    if expected and not same_account():
                        return self.reply(409, {"error": "Trading account changed during request"})
                    return self.reply(200, quote)
                frame = valid_frame(query.get("timeframe", "15"))
                limit = int(query.get("limit", "720"))
                if not 1 <= limit <= 10000:
                    raise ValueError("limit must be 1..10000")
                start = int(finite(query["from"])) if "from" in query else None
                end = int(finite(query["to"])) if "to" in query else None
                if start is not None and end is not None and start > end:
                    raise ValueError("Invalid time range")
                bars = source.bars(symbol, frame, limit, start, end)
                if expected and not same_account():
                    return self.reply(409, {"error": "Trading account changed during request"})
                return self.reply(200, {"symbol": symbol, "timeframe": frame, "bars": bars})
            except (ValueError, KeyError, TypeError) as error:
                self.reply(400, {"error": str(error)})
            except Exception:
                self.reply(503, {"error": "Market data unavailable. Check the logged-in terminal and EA / history"})
        def do_POST(self):
            if not self.authorized():
                return
            if urlsplit(self.path).path == "/mcp":
                return self.post_mcp()
            if urlsplit(self.path).path == "/v1/ai/propose":
                return self.post_ai()
            if urlsplit(self.path).path in ("/v1/trading/preview", "/v1/trading/execute", "/v1/mt4/trade-result"):
                return self.post_trade()
            if urlsplit(self.path).path != "/v1/mt4/publish" or not isinstance(source, MT4Source):
                return self.reply(404, {"error": "No such route"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 8 * 1024 * 1024:
                    return self.reply(413, {"error": "Invalid request size"})
                if not self.headers.get("Content-Type", "").startswith("application/json"):
                    return self.reply(415, {"error": "JSON required"})
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise ValueError("JSON object required")
                source.publish(payload)
                self.reply(200, {"ok": True})
            except (ValueError, KeyError, TypeError, AttributeError) as error:
                self.reply(400, {"error": str(error)})
        def post_ai(self):
            try:
                size=int(self.headers.get("Content-Length","0"))
                if not 0<size<=16384 or not self.headers.get("Content-Type","").startswith("application/json"):
                    return self.reply(400,{"error":"A small JSON object is required"})
                payload=json.loads(self.rfile.read(size))
                if not isinstance(payload,dict):
                    raise ValueError("JSON object required")
                return self.reply(200,advisor.propose(payload))
            except (ValueError,KeyError,TypeError) as error:
                return self.reply(400,{"error":str(error)})
            except Exception:
                return self.reply(503,{"error":"AI draft unavailable. Check the model and broker data"})

        def post_trade(self):
            if not self.authorized(trade=True):
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 16384 or not self.headers.get("Content-Type", "").startswith("application/json"):
                    return self.reply(400, {"error":"A small JSON object is required"})
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise ValueError("JSON object required")
                path = urlsplit(self.path).path
                if path == "/v1/trading/preview":
                    return self.reply(200, trading.preview(payload))
                if path == "/v1/trading/execute":
                    return self.reply(200, trading.execute(payload))
                if not isinstance(source, MT4Source):
                    return self.reply(404, {"error":"MT4 receipt route unavailable"})
                source.publish_trade_result(payload)
                return self.reply(200, {"ok":True})
            except (ValueError, KeyError, TypeError) as error:
                return self.reply(400, {"error":str(error)})
            except Exception:
                return self.reply(503, {"error":"Trading response unavailable. Check the terminal; do not resend automatically"})

        def post_mcp(self):
            version = self.headers.get("MCP-Protocol-Version")
            if version and version not in MCP_VERSIONS:
                return self.reply(400, {"error": "Unsupported MCP protocol version"})
            if not self.headers.get("Content-Type", "").startswith("application/json"):
                return self.reply(415, {"error": "JSON required"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 262144:
                    return self.reply(413, {"error": "Invalid MCP request size"})
                message = json.loads(self.rfile.read(size))
            except (ValueError, TypeError):
                return self.reply(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Invalid JSON"}})
            response = mcp_handle(message, caller=mcp_caller)
            return self.reply(202 if response is None else 200, response)
        def do_DELETE(self):
            if self.authorized():
                self.reply(405, {"error": "Stateless MCP has no server session to delete"})
    return Handler

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["mt4", "mt5"], default=os.getenv("NS_BRIDGE_MODE", "mt5"))
    parser.add_argument("--port", type=int, default=int(os.getenv("NS_BRIDGE_PORT", "8787")))
    parser.add_argument("--enable-trading", action="store_true", help="Enable manual account-bound order routes; requires a separate trade token")
    args = parser.parse_args()
    token = os.getenv("NS_BRIDGE_TOKEN", "")
    if not token:
        token = secrets.token_urlsafe(32)
        print("Temporary bridge token (copy to website / MCP; changes at restart): " + token, flush=True)
    if len(token) < 32 or any(ord(c) < 33 or ord(c) > 126 for c in token):
        raise SystemExit("NS_BRIDGE_TOKEN must be at least 32 printable ASCII characters")
    trade_token = os.getenv("NS_TRADE_TOKEN", "")
    if args.enable_trading:
        if not trade_token:
            trade_token = secrets.token_urlsafe(32)
            print("Separate Trade token (only for manual execution): " + trade_token, flush=True)
        if len(trade_token) < 32 or trade_token == token or any(ord(c) < 33 or ord(c) > 126 for c in trade_token):
            raise SystemExit("NS_TRADE_TOKEN must be separate from the bridge token and contain 32+ printable ASCII characters")
    origins = set(filter(None, (x.strip() for x in os.getenv("NS_ALLOWED_ORIGINS", "https://ns-capital-terminal.biw-modify004.chatgpt.site,http://127.0.0.1:8080,http://localhost:8080").split(","))))
    hosts = set(filter(None, os.getenv("NS_ALLOWED_HOSTS", "localhost,127.0.0.1,::1").split(",")))
    source = MT5Source(os.getenv("NS_MT5_PATH")) if args.mode == "mt5" else MT4Source()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(source, token, origins, hosts, enable_trading=args.enable_trading, trade_token=trade_token))
    print(f"NS {args.mode.upper()} gateway ({'manual trading enabled' if args.enable_trading else 'market data only'}): http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
