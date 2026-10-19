"""Manual trading/AI protocol tests. Fixture terminals only: no real orders."""
import http.client
import json
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace as NS
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'broker-bridge'))
from bridge import MT5Source,MT4Source,make_handler,ThreadingHTTPServer
from trading import TradingService,key
from ai_advisor import AITradeAdvisor

TOKEN='fixture-data-token-012345678901234567890'
TRADE='fixture-trade-token-01234567890123456789'
NOW=lambda:int(time.time()*1000)
class FakeMT5:
    TRADE_ACTION_DEAL=1;TRADE_ACTION_SLTP=6;ORDER_TYPE_BUY=0;ORDER_TYPE_SELL=1;ORDER_FILLING_IOC=1;ORDER_FILLING_FOK=0;ORDER_FILLING_RETURN=2;ORDER_TIME_GTC=0
    def __init__(self):
        self.login=12345678;self.allowed=True;self.price=4501.;self.tick_time=NOW();self.sent=[];self.retcode=10009;self.checkcode=0;self.none_result=False;self.positions=[];self.history=[];self.balance=10000;self.equity=9998;self.credit=0
    def initialize(self):return True
    def terminal_info(self):return NS(connected=True,trade_allowed=self.allowed,tradeapi_disabled=False)
    def account_info(self):return NS(login=self.login,company='FIXTURE ONLY',server='Fixture-Server',currency='USD',trade_mode=0,trade_allowed=True,trade_expert=True,margin_mode=2,balance=self.balance,equity=self.equity,credit=self.credit,margin_free=9000)
    def symbol_select(self,s,v):return s=='XAUUSD.pro'
    def symbol_info(self,s):return NS(name=s,description='Fixture Gold',currency_profit='USD',currency_base='XAU',path='CFD/Metals',trade_mode=4,trade_calc_mode=2,trade_tick_size=.01,point=.01,trade_tick_value=1,trade_contract_size=100,volume_min=.01,volume_max=10.,volume_step=.01,trade_stops_level=10,trade_exemode=2,filling_mode=3,exchange='',expiration_time=0)
    def symbols_get(self):return [self.symbol_info('XAUUSD.pro')]
    def symbol_info_tick(self,s):return NS(bid=self.price,ask=self.price+.2,time_msc=self.tick_time,time=self.tick_time//1000)
    def history_deals_get(self,start,end):
        return [d for d in self.history if start.timestamp()*1000<=d.time_msc<=end.timestamp()*1000]
    def order_calc_profit(self,side,symbol,volume,entry,exit):return (exit-entry)*100*volume*(1 if side==0 else -1)
    def positions_get(self):return self.positions
    def order_check(self,r):return NS(retcode=self.checkcode,comment='fixture order check')
    def order_send(self,r):
        self.sent.append(dict(r))
        return None if self.none_result else NS(retcode=self.retcode,comment='fixture only',order=987,deal=988,volume=r.get('volume',0),price=self.price)

def fixture(enabled=True):
    module=FakeMT5();source=MT5Source(module=module);service=TradingService(source,enabled=enabled);return module,source,service

def raw(source,**kwargs):return {'accountKey':key(source.status()),'action':'open','symbol':'XAUUSD.pro','side':'buy','volume':.1,'sl':4490,'tp':4520,'deviation':20,**kwargs}
def execute(service,preview,request='fixture-request-00000001'):return service.execute({'accountKey':preview['accountKey'],'previewId':preview['previewId'],'requestId':request})

class ExecutionTests(unittest.TestCase):
    def test_preview_checks_broker_without_sending_and_one_preview_executes_only_once(self):
        m,s,t=fixture();p=t.preview(raw(s));self.assertEqual(len(m.sent),0);r=execute(t,p);self.assertEqual(r['status'],'filled');self.assertEqual(execute(t,p),r);self.assertEqual(len(m.sent),1)
        with self.assertRaises(ValueError):execute(t,p,'fixture-request-00000002')
        self.assertNotIn('price',m.sent[0]) # MT5 market execution omits price as documented.
        self.assertEqual(m.sent[0]['type_filling'],1)
    def test_invalid_volume_tick_stops_and_stale_ticks_never_reach_order_send(self):
        m,s,t=fixture()
        for values in ({'volume':.015},{'volume':11},{'sl':4490.005},{'sl':4502},{'tp':4499},{'deviation':20.5},{'side':'invalid'}):
            with self.subTest(values=values),self.assertRaises(ValueError):t.preview(raw(s,**values))
        m.tick_time=NOW()-11000
        with self.assertRaises(ValueError):t.preview(raw(s))
        self.assertEqual(m.sent,[])
    def test_disabled_permissions_and_expired_or_wrong_account_previews_are_rejected(self):
        m,s,t=fixture(False)
        with self.assertRaises(ValueError):t.preview(raw(s))
        t.enabled=True;m.allowed=False
        with self.assertRaises(ValueError):t.preview(raw(s))
        m.allowed=True;p=t.preview(raw(s));t.now=lambda:p['expiresAt']+1
        with self.assertRaises(ValueError):execute(t,p)
        t.now=NOW;p=t.preview(raw(s));m.login=999
        with self.assertRaises(ValueError):execute(t,p)
        self.assertEqual(m.sent,[])
    def test_price_move_and_broker_rejection_are_not_retried(self):
        m,s,t=fixture();p=t.preview(raw(s));m.price+=1
        self.assertEqual(execute(t,p)['status'],'rejected');self.assertEqual(m.sent,[])
        m.checkcode=10019
        with self.assertRaises(ValueError):t.preview(raw(s))
    def test_unknown_partial_and_accepted_outcomes_are_not_misreported_as_filled(self):
        for code,expected in ((10010,'partial'),(10008,'accepted'),(10012,'unknown'),(10019,'rejected')):
            m,s,t=fixture();m.retcode=code;p=t.preview(raw(s));self.assertEqual(execute(t,p)['status'],expected);execute(t,p);self.assertEqual(len(m.sent),1)
        m,s,t=fixture();m.none_result=True;p=t.preview(raw(s));self.assertEqual(execute(t,p)['status'],'unknown');execute(t,p);self.assertEqual(len(m.sent),1)
    def test_close_and_sltp_use_exact_position_ticket_and_recheck_volume(self):
        m,s,t=fixture();position=NS(ticket=123,symbol='XAUUSD.pro',type=0,volume=.1,price_open=4500,price_current=4501,sl=4490,tp=4520,profit=-2,swap=-.1,time=NOW()//1000);m.positions=[position]
        self.assertEqual(t.state(key(s.status()))['positions'][0]['profit'],-2)
        p=t.preview(raw(s,action='close',position='123',sl=0,tp=0));self.assertEqual(execute(t,p)['status'],'filled');self.assertEqual(m.sent[0]['position'],123);self.assertEqual(m.sent[0]['type'],1)
        p=t.preview(raw(s,action='modify',position='123',sl=4485,tp=4530));execute(t,p,'fixture-request-00000002');self.assertEqual(m.sent[-1]['action'],6);self.assertNotIn('volume',m.sent[-1])
        p=t.preview(raw(s,action='close',position='123',sl=0,tp=0));position.volume=.2
        self.assertEqual(execute(t,p,'fixture-request-00000003')['status'],'rejected');self.assertEqual(len(m.sent),2)
    def test_parallel_duplicate_requests_have_only_one_execution(self):
        m,s,t=fixture();p=t.preview(raw(s));threads=[threading.Thread(target=lambda:execute(t,p)) for _ in range(8)]
        for th in threads:th.start()
        for th in threads:th.join()
        self.assertEqual(len(m.sent),1)
    def test_mt4_queue_delivers_once_and_reconciles_a_receipt_without_resubmission(self):
        s=MT4Source();s.publish({'connected':True,'broker':'MT4 FIXTURE','account':{'id':'123','server':'Fixture','currency':'USD'},'tradeAllowed':True,'positions':[],'symbols':[{'ticker':'GOLD.a','currency':'USD','tickSize':.01,'point':.01,'volumeMin':.01,'volumeMax':10,'lotStep':.01}], 'quotes':[{'symbol':'GOLD.a','bid':4501,'ask':4501.2,'time':NOW()}]})
        t=TradingService(s,enabled=True);p=t.preview(raw(s,symbol='GOLD.a'));r=execute(t,p);self.assertEqual(r['status'],'pending');command=s.next_trade();self.assertEqual(len(command.split('|')),13);self.assertEqual(s.next_trade(),'');s.publish_trade_result({'requestId':r['requestId'],'status':'filled','order':'456','retcode':0});self.assertEqual(t.receipt(r['requestId'],r['accountKey'])['status'],'filled');execute(t,p);self.assertEqual(s.next_trade(),'')

class TradingHTTPTests(unittest.TestCase):
    def setUp(self):
        self.module,self.source,_=fixture();handler=make_handler(self.source,TOKEN,{'https://terminal.test'},{'127.0.0.1'},enable_trading=True,trade_token=TRADE);self.store=handler.ledger_store
        handler.trading_service.risk.save({'accountKey':key(self.source.status()),'version':0,'maxRiskPct':5,'dailyLossPct':10,'maxDrawdownPct':20,'costPerLot':0,'slippagePoints':0,'resetMinuteUtc':0,'paused':False})
        self.server=ThreadingHTTPServer(('127.0.0.1',0),handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.store.close()
    def request(self,path,body=None,trade=TRADE,origin='https://terminal.test'):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_address[1],timeout=3);headers={'Authorization':'Bearer '+TOKEN,'X-Trade-Token':trade,'Content-Type':'application/json','Origin':origin};conn.request('POST' if body is not None else 'GET',path,json.dumps(body) if body is not None else None,headers);r=conn.getresponse();result=r.status,json.loads(r.read());conn.close();return result
    def test_separate_trade_token_origin_and_account_binding_are_required(self):
        self.assertEqual(self.request('/v1/trading/preview',raw(self.source),trade=TOKEN)[0],403)
        self.assertEqual(self.request('/v1/trading/preview',raw(self.source),origin='https://wrong.test')[0],403)
        self.assertEqual(self.request('/v1/trading/preview',raw(self.source,accountKey='Wrong|123'))[0],400)
        code,p=self.request('/v1/trading/preview',raw(self.source));self.assertEqual(code,200);self.assertEqual(self.module.sent,[])
        payload={'accountKey':p['accountKey'],'previewId':p['previewId'],'requestId':'fixture-request-http-0001'}
        self.assertEqual(self.request('/v1/trading/execute',payload)[1]['status'],'filled');self.request('/v1/trading/execute',payload);self.assertEqual(len(self.module.sent),1)
        self.assertFalse(self.request('/v1/status')[1]['readOnly'])
    def test_mcp_has_no_execution_tool_even_when_manual_execution_is_enabled(self):
        message={'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'execute_order','arguments':{}}};self.assertTrue(self.request('/mcp',message)[1]['result']['isError']);self.assertEqual(self.module.sent,[])

class AITests(unittest.TestCase):
    def advisor(self,result):
        m,s,t=fixture();s.bars=lambda *args:[{'time':NOW()-i*60000,'open':4500,'high':4502,'low':4498,'close':4501,'volume':12} for i in range(120)]
        a=AITradeAdvisor(s,t,base='http://127.0.0.1:1234/v1',model='fixture-model',api_key='fixture-secret-do-not-forward',completion=lambda payload:json.dumps(result));return m,s,t,a
    def test_ai_produces_only_validated_drafts_and_never_sends_an_order(self):
        m,s,t,a=self.advisor({'action':'open','symbol':'XAUUSD.pro','side':'buy','volume':.1,'sl':4490,'tp':4520,'reason':'Fixture hypothesis'});r=a.propose({'accountKey':key(s.status()),'symbol':'XAUUSD.pro','prompt':'Analyze the setup'});self.assertFalse(r['autoExecution']);self.assertEqual(r['proposal']['volume'],.1);self.assertEqual(m.sent,[]);self.assertNotIn('fixture-secret',json.dumps(r))
    def test_ai_can_pass_and_invalid_or_cross_symbol_drafts_are_rejected(self):
        m,s,t,a=self.advisor({'action':'pass','reason':'No setup'});self.assertEqual(a.propose({'accountKey':key(s.status()),'symbol':'XAUUSD.pro','prompt':'Analyze'})['proposal']['action'],'pass')
        for proposal in ({'action':'execute'},{'action':'open','symbol':'EURUSD','side':'buy','volume':.1},{'action':'open','symbol':'XAUUSD.pro','side':'buy','volume':999,'sl':0,'tp':0}):
            m,s,t,a=self.advisor(proposal)
            with self.assertRaises(ValueError):a.propose({'accountKey':key(s.status()),'symbol':'XAUUSD.pro','prompt':'Analyze'})
            self.assertEqual(m.sent,[])
    def test_ai_configuration_and_wrong_account_do_not_invoke_the_model(self):
        m,s,t,a=self.advisor({'action':'pass'});a.base=''
        with self.assertRaises(ValueError):a.propose({'accountKey':key(s.status()),'symbol':'XAUUSD.pro','prompt':'Analyze'})
        a.base='http://127.0.0.1:1234/v1'
        with self.assertRaises(ValueError):a.propose({'accountKey':'Wrong|99','symbol':'XAUUSD.pro','prompt':'Analyze'})
        self.assertEqual(m.sent,[])

if __name__=='__main__':unittest.main()
