"""Ollama/OpenAI wire fixtures; no downloaded model or real trading account."""
import json
import os
from pathlib import Path
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'broker-bridge'))
from ai_advisor import AITradeAdvisor
from test_trading import fixture, key, NOW

class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.mode='ok'
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def reply(self,value):
                encoded=json.dumps(value).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(encoded)
            def do_GET(self):
                owner.calls.append((self.path,None,dict(self.headers)))
                if owner.mode=='redirect':
                    self.send_response(302);self.send_header('Location','/leak');self.end_headers();return
                self.reply({'data':'invalid'} if owner.mode=='invalid' else {'data':[{'id':'fixture:latest'}]})
            def do_POST(self):
                payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])));owner.calls.append((self.path,payload,dict(self.headers)))
                if owner.mode=='redirect':
                    self.send_response(307);self.send_header('Location','/leak');self.end_headers();return
                content='invalid fixture JSON' if owner.mode=='invalid' else '{"action":"pass","reason":"Fixture only"}'
                self.reply({'choices':[{'message':{'content':content}}]})
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}/v1'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
    def advisor(self,**kwargs):
        self.mt5,source,trading=fixture()
        source.bars=lambda *args:[{'time':NOW()-i*60000,'open':4500,'high':4502,'low':4498,'close':4501,'volume':12} for i in reversed(range(120))]
        return AITradeAdvisor(source,trading,base=self.base,provider='ollama',model='fixture:latest',api_key='fixture-model-secret',**kwargs)
    def test_provider_defaults_legacy_configuration_and_bad_urls(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(AITradeAdvisor(None,None,provider='ollama').base,'http://127.0.0.1:11434/v1')
            self.assertEqual(AITradeAdvisor(None,None,provider='lm-studio').base,'http://127.0.0.1:1234/v1')
            self.assertFalse(AITradeAdvisor(None,None).status()['configured'])
            with patch.dict(os.environ,{'NS_AI_BASE_URL':self.base,'NS_AI_MODEL':'legacy'}):
                self.assertTrue(AITradeAdvisor(None,None).status()['configured'])
        with self.assertRaises(ValueError):AITradeAdvisor(None,None,provider='unknown')
        for base in ['http://public.example/v1','https://user:secret@example.test/v1','https://example.test/v1?key=secret','https://example.test/v1#key']:
            with self.subTest(base=base),self.assertRaises(ValueError):AITradeAdvisor(None,None,base=base)
    def test_ollama_probe_and_json_completion_over_actual_loopback_http(self):
        a=self.advisor();status=a.check();self.assertTrue(status['reachable']);self.assertTrue(status['modelAvailable']);self.assertEqual(status['providerLabel'],'Ollama')
        self.assertFalse(a.status()['checked']);self.assertEqual(len(self.calls),1)
        result=a.propose({'accountKey':key(a.source.status()),'symbol':'XAUUSD.pro','prompt':'Analyze fixture'})
        self.assertEqual(result['proposal']['action'],'pass');self.assertFalse(result['autoExecution']);self.assertEqual(self.mt5.sent,[])
        path,payload,headers=self.calls[-1];self.assertEqual(path,'/v1/chat/completions');self.assertEqual(payload['response_format'],{'type':'json_object'});self.assertFalse(payload['stream']);self.assertNotIn('tools',payload)
        self.assertEqual(headers['Authorization'],'Bearer fixture-model-secret');self.assertNotIn('fixture-model-secret',json.dumps(result));self.assertNotIn('Fixture-Server',json.dumps(payload))
    def test_exact_missing_model_is_distinct_from_an_unreachable_server(self):
        a=self.advisor();a.model='not-installed';status=a.check();self.assertTrue(status['reachable']);self.assertFalse(status['modelAvailable']);self.assertIn('exact',status['error']);self.assertTrue(all(body is None for _,body,_ in self.calls))
        a.base='http://127.0.0.1:1/v1';status=a.check();self.assertFalse(status['reachable']);self.assertNotIn('fixture-model-secret',json.dumps(status))
    def test_invalid_model_list_and_invalid_generated_json_are_not_accepted(self):
        self.mode='invalid';a=self.advisor();self.assertFalse(a.check()['reachable'])
        with self.assertRaises(ValueError):a.propose({'accountKey':key(a.source.status()),'symbol':'XAUUSD.pro','prompt':'Analyze fixture'})
        self.assertEqual(self.mt5.sent,[])
    def test_redirects_are_never_followed_and_errors_do_not_expose_credentials(self):
        self.mode='redirect';a=self.advisor();self.assertFalse(a.check()['reachable'])
        with self.assertRaises(RuntimeError) as error:a.call_model({'messages':[]})
        self.assertNotIn('fixture-model-secret',str(error.exception));self.assertTrue(all(path!='/leak' for path,_,_ in self.calls))
    def test_unconfigured_probe_makes_no_network_request(self):
        a=self.advisor();a.model='';status=a.check();self.assertFalse(status['configured']);self.assertTrue(status['checked']);self.assertEqual(self.calls,[])

if __name__=='__main__':unittest.main()
