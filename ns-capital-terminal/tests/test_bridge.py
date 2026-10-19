"""Real HTTP / MCP protocol checks with a clearly identified fixture source.
Does not connect to a broker or claim to compile the MT4 EA.
"""
from pathlib import Path
import http.client
import json
import os
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "broker-bridge"))
from bridge import MT4Source, MT5Source, PROTOCOL, ThreadingHTTPServer, make_handler

TOKEN = "fixture-read-only-token-01234567890123456789"
NOW = lambda: int(time.time() * 1000)
def bars():
    at = NOW() // 900000 * 900000
    return [{"time": at - (2-i)*900000, "open": 4500, "high": 4502, "low": 4498, "close": 4501, "volume": 12} for i in range(3)]

class Fixture:
    def __init__(self):
        self.connected = True
    def status(self):
        return {"protocol": PROTOCOL, "readOnly": True, "connected": self.connected, "broker": "FIXTURE ONLY", "platform": "MT5"}
    def symbols(self):
        return [{"ticker": "XAUUSD.pro", "description": "Fixture Gold", "currency": "USD", "tickSize": .01}]
    def bars(self, symbol, frame, limit, start=None, end=None):
        return [b for b in bars() if (start is None or b["time"] >= start) and (end is None or b["time"] <= end)][-limit:]
    def quote(self, symbol):
        return {"symbol": symbol, "bid": 4501, "ask": 4501.2, "time": NOW()}

class BridgeHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Fixture()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.source, TOKEN, {"https://terminal.test"}, {"127.0.0.1", "localhost"}))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_address[1]
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()
    def request(self, method, path, token=TOKEN, origin=None, body=None, extra=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        headers = {"Authorization": "Bearer " + token}
        if origin:
            headers["Origin"] = origin
        if extra:
            headers.update(extra)
        conn.request(method, path, body, headers)
        response = conn.getresponse()
        result = (response.status, dict(response.getheaders()), response.read())
        conn.close()
        return result
    def test_auth_origin_host_and_preflight(self):
        self.assertEqual(self.request("GET", "/v1/status", token="wrong")[0], 401)
        self.assertEqual(self.request("GET", "/v1/status", origin="https://untrusted.test")[0], 403)
        self.assertEqual(self.request("GET", "/v1/status", extra={"Host": "untrusted.test"})[0], 403)
        code, headers, _ = self.request("OPTIONS", "/v1/status", origin="https://terminal.test")
        self.assertEqual(code, 204)
        self.assertEqual(headers["Access-Control-Allow-Origin"], "https://terminal.test")
        self.assertEqual(headers["Access-Control-Allow-Private-Network"], "true")
        self.assertNotIn("Access-Control-Allow-Credentials", headers)
    def test_market_routes_use_exact_symbol_timestamp_and_limit(self):
        code, headers, body = self.request("GET", "/v1/status", origin="https://terminal.test")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["broker"], "FIXTURE ONLY")
        self.assertEqual(headers["Cache-Control"], "no-store")
        code, _, body = self.request("GET", "/v1/bars?"+urlencode({"symbol":"XAUUSD.pro", "timeframe":"15", "limit":2}))
        data = json.loads(body)
        self.assertEqual(code, 200)
        self.assertEqual(data["symbol"], "XAUUSD.pro")
        self.assertEqual(len(data["bars"]), 2)
        self.assertGreater(data["bars"][0]["time"], 1_000_000_000_000)
        self.assertEqual(self.request("GET", "/v1/quote?symbol=XAUUSD.pro")[0], 200)
    def test_invalid_ranges_and_trading_routes_are_rejected(self):
        for query in ("symbol=EURUSD&limit=10001", "symbol=EURUSD&timeframe=M", "symbol=../EURUSD", "symbol=EURUSD&from=200&to=100"):
            self.assertEqual(self.request("GET", "/v1/bars?" + query)[0], 400)
        self.assertEqual(self.request("POST", "/v1/orders")[0], 404)
        self.source.connected = False
        try:
            self.assertEqual(self.request("GET", "/v1/bars?symbol=XAUUSD.pro")[0], 503)
        finally:
            self.source.connected = True
    def test_mcp_stdio_initialization_and_read_only_tool_calls_over_real_http(self):
        env = {**os.environ, "NS_BRIDGE_URL": f"http://127.0.0.1:{self.port}", "NS_BRIDGE_TOKEN": TOKEN}
        messages = [
            {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"fixture-test","version":"1"}}},
            {"jsonrpc":"2.0","method":"notifications/initialized"},
            {"jsonrpc":"2.0","id":2,"method":"tools/list"},
            {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_connection_status","arguments":{}}},
            {"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"get_candles","arguments":{"symbol":"XAUUSD.pro","timeframe":"15","limit":2}}},
            {"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"get_quote","arguments":{"symbol":"XAUUSD.pro"}}},
            {"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"list_symbols","arguments":{}}},
            {"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"place_order","arguments":{}}},
            {"jsonrpc":"2.0","id":8,"method":"tools/call","params":{"name":"get_candles","arguments":{"symbol":"XAUUSD.pro","limit":True}}},
        ]
        result = subprocess.run([sys.executable,str(ROOT/"broker-bridge/mcp_server.py")],input="\n".join(json.dumps(m) for m in messages)+"\n",text=True,capture_output=True,env=env,timeout=10,check=True)
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(responses),8)
        self.assertEqual(result.stderr,"")
        self.assertEqual(responses[0]["result"]["protocolVersion"],"2025-11-25")
        tools = responses[1]["result"]["tools"]
        self.assertEqual(len(tools),4)
        self.assertTrue(all(t["annotations"]["readOnlyHint"] for t in tools))
        self.assertEqual(responses[2]["result"]["structuredContent"]["broker"],"FIXTURE ONLY")
        self.assertEqual(len(responses[3]["result"]["structuredContent"]["bars"]),2)
        self.assertGreater(responses[4]["result"]["structuredContent"]["time"],NOW()-5000)
        self.assertEqual(responses[5]["result"]["structuredContent"]["symbols"][0]["ticker"],"XAUUSD.pro")
        self.assertTrue(responses[6]["result"]["isError"])
        self.assertTrue(responses[7]["result"]["isError"])
        self.assertNotIn(TOKEN,result.stdout)
    def test_streamable_http_mcp_json_transport_auth_notifications_and_tools(self):
        headers={"Content-Type":"application/json", "Accept":"application/json, text/event-stream", "MCP-Protocol-Version":"2025-11-25"}
        def post(message, **kwargs):
            return self.request("POST","/mcp",body=json.dumps(message),extra=headers,**kwargs)
        initialize={"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25"}}
        self.assertEqual(post(initialize,token="wrong")[0],401)
        self.assertEqual(post(initialize,origin="https://untrusted.test")[0],403)
        code,_,body=post(initialize,origin="https://terminal.test")
        self.assertEqual(code,200)
        self.assertEqual(json.loads(body)["result"]["protocolVersion"],"2025-11-25")
        self.assertEqual(post({"jsonrpc":"2.0","method":"notifications/initialized"})[::2],(202,b""))
        code,_,body=post({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_quote","arguments":{"symbol":"XAUUSD.pro"}}})
        self.assertEqual(code,200)
        self.assertEqual(json.loads(body)["result"]["structuredContent"]["symbol"],"XAUUSD.pro")
        self.assertEqual(self.request("GET","/mcp")[0],405)
        bad={**headers,"MCP-Protocol-Version":"unknown"}
        self.assertEqual(self.request("POST","/mcp",body=json.dumps(initialize),extra=bad)[0],400)

class MT4Tests(unittest.TestCase):
    def test_requests_actual_symbol_frame_and_converts_no_timestamps_implicitly(self):
        source = MT4Source(wait_seconds=1)
        source.publish({"broker":"Fixture MT4", "connected":True, "symbols":[{"ticker":"GOLD.a", "currency":"USD", "tickSize":.01}]})
        result=[]
        thread=threading.Thread(target=lambda:result.extend(source.bars('GOLD.a','15',3)))
        thread.start()
        deadline=time.monotonic()+.5
        command=''
        while not command and time.monotonic()<deadline:
            command=source.next_request()
            if not command: time.sleep(.005)
        self.assertEqual(command,'GOLD.a|15|3|0')
        source.publish({"broker":"Fixture MT4", "connected":True, "quotes":[{"symbol":"GOLD.a","bid":4501,"ask":4501.2,"time":NOW()}],"series":[{"symbol":"GOLD.a","timeframe":"15","bars":bars()}]})
        thread.join(1)
        self.assertEqual(len(result),3)
        self.assertEqual(result[-1]['time'],bars()[-1]['time'])
        self.assertTrue(source.status()['connected'])
        original=source.quote('GOLD.a')['time']
        source.publish({'quotes':[{'symbol':'GOLD.a','bid':4500,'ask':4500.2,'time':original-1000}]})
        self.assertEqual(source.quote('GOLD.a')['time'],original)
    def test_invalid_future_data_does_not_mutate_catalog_or_quotes(self):
        source=MT4Source(wait_seconds=.01)
        with self.assertRaises(ValueError):
            source.publish({'symbols':[{'ticker':'EURUSD','currency':'USD','tickSize':.00001}], 'quotes':[{'symbol':'EURUSD','bid':1.1,'ask':1.2,'time':NOW()+60000}]})
        self.assertEqual(source.symbols(),[])
        self.assertEqual(source.quotes,{})

class MT5Tests(unittest.TestCase):
    def test_mt5_uses_logged_in_terminal_exact_symbol_and_utc_rates(self):
        selected=[]
        record={'time':int(bars()[-1]['time']/1000),'open':4500,'high':4502,'low':4498,'close':4501,'tick_volume':12}
        module=SimpleNamespace(initialize=lambda *args:True,terminal_info=lambda:SimpleNamespace(connected=True),account_info=lambda:SimpleNamespace(company='Fixture MT5',currency='USD'),symbol_select=lambda s,v:selected.append((s,v)) or True,TIMEFRAME_M15=15,copy_rates_from_pos=lambda s,tf,pos,n:[record],symbol_info_tick=lambda s:SimpleNamespace(bid=4501,ask=4501.2,time_msc=NOW(),time=int(time.time())))
        source=MT5Source(module=module)
        self.assertTrue(source.status()['readOnly'])
        self.assertEqual(source.status()['broker'],'Fixture MT5')
        result=source.bars('XAUUSD.pro','15',1)
        self.assertEqual(result[0]['time'],record['time']*1000)
        self.assertEqual(selected[-1],('XAUUSD.pro',True))
        self.assertEqual(source.quote('XAUUSD.pro')['symbol'],'XAUUSD.pro')
        self.assertFalse(hasattr(module,'order_send'))

if __name__=='__main__':
    unittest.main()
