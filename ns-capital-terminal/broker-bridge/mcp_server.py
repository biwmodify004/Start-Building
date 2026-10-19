"""Read-only MCP stdio adapter for NS Market Bridge. Python 3.11+, no dependencies.

Uses newline-delimited JSON-RPC per the MCP stdio transport specification.
Start bridge.py separately; configure NS_BRIDGE_URL and NS_BRIDGE_TOKEN here.
stdout is reserved for protocol messages. No trading tools are exposed.
"""
import json
import os
import sys
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
FRAMES = ["1", "5", "15", "30", "60", "240", "D", "W"]
ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True}
TOOLS = [
    {"name": "get_connection_status", "description": "Read actual connected broker / MT4 or MT5 status. Never assumes Axi is connected.", "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "list_symbols", "description": "List the exact available broker symbols, suffixes, tick sizes and quote currencies.", "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "get_quote", "description": "Read broker bid, ask and original UTC tick timestamp in milliseconds. Check timestamp freshness.", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string", "minLength": 1, "maxLength": 128}}, "required": ["symbol"], "additionalProperties": False}},
    {"name": "get_candles", "description": "Read OHLCV broker candles in UTC milliseconds. The final candle can still be forming. 60=H1, 240=H4, D=D1, W=W1.", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string", "minLength": 1, "maxLength": 128}, "timeframe": {"type": "string", "enum": FRAMES, "default": "15"}, "limit": {"type": "integer", "minimum": 1, "maximum": 10000, "default": 720}}, "required": ["symbol"], "additionalProperties": False}}
]

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Bridge redirects are not allowed")

def query_bridge(path, params):
    base = os.getenv("NS_BRIDGE_URL", "http://127.0.0.1:8787").rstrip("/")
    url = urlsplit(base)
    if url.username or url.password or url.query or url.fragment or (url.scheme != "https" and not (url.scheme == "http" and url.hostname in ("localhost", "127.0.0.1", "::1"))):
        raise ValueError("Use a credential-free HTTPS bridge URL or localhost HTTP URL")
    token = os.getenv("NS_BRIDGE_TOKEN", "")
    if len(token) < 32:
        raise ValueError("Set the same NS_BRIDGE_TOKEN as bridge.py (at least 32 characters)")
    request = Request(base + path + ("?" + urlencode(params) if params else ""), headers={"Authorization": "Bearer " + token})
    try:
        with build_opener(NoRedirect).open(request, timeout=22) as response:
            return json.load(response)
    except HTTPError as error:
        raise RuntimeError("Bridge HTTP " + str(error.code) + ". Check connection and token") from None

def call_tool(name, args, request=query_bridge):
    spec = next((t for t in TOOLS if t["name"] == name), None)
    if not spec or not isinstance(args, dict) or set(args) - set(spec["inputSchema"]["properties"]):
        raise ValueError("Unknown tool or invalid arguments")
    for required in spec["inputSchema"].get("required", []):
        if not isinstance(args.get(required), str) or not 1 <= len(args[required]) <= 128:
            raise ValueError("A valid exact broker symbol is required")
    if name == "get_connection_status":
        return request("/v1/status", {})
    if name == "list_symbols":
        return request("/v1/symbols", {})
    if name == "get_quote":
        return request("/v1/quote", {"symbol": args["symbol"]})
    frame, limit = args.get("timeframe", "15"), args.get("limit", 720)
    if frame not in FRAMES or type(limit) is not int or not 1 <= limit <= 10000:
        raise ValueError("Invalid timeframe or candle limit")
    return request("/v1/bars", {"symbol": args["symbol"], "timeframe": frame, "limit": limit})

def handle(message, caller=call_tool):
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid request"}}
    if "id" not in message:
        return None
    request_id, method, params = message["id"], message.get("method"), message.get("params", {})
    if not isinstance(params, dict):
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": "Parameters must be an object"}}
    response = {"jsonrpc": "2.0", "id": request_id}
    if method == "initialize":
        version = params.get("protocolVersion")
        response["result"] = {"protocolVersion": version if version in VERSIONS else VERSIONS[0], "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "ns-capital-market-bridge", "version": "1.0.0"}, "instructions": "Read-only broker market data. Check get_connection_status and quote.time. The last candle may be forming. No order placement is available."}
    elif method == "ping":
        response["result"] = {}
    elif method == "tools/list":
        response["result"] = {"tools": [{**t, "annotations": ANNOTATIONS} for t in TOOLS]}
    elif method == "tools/call":
        try:
            result = caller(params.get("name"), params.get("arguments", {}))
            response["result"] = {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, allow_nan=False)}], "structuredContent": result, "isError": False}
        except Exception as error:
            response["result"] = {"content": [{"type": "text", "text": str(error)}], "isError": True}
    else:
        response["error"] = {"code": -32601, "message": "Method not found"}
    return response

def main():
    for line in sys.stdin:
        try:
            if len(line) > 262144:
                raise ValueError("Request too large")
            response = handle(json.loads(line))
        except Exception:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Invalid JSON-RPC message"}}
        if response is not None:
            print(json.dumps(response, ensure_ascii=True, allow_nan=False, separators=(",", ":")), flush=True)

if __name__ == "__main__":
    main()
