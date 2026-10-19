"""Persistent journal/risk tests. Explicit fixture accounts; no real trades."""
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace as NS
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'broker-bridge'))
from database import LedgerStore,now_ms
from journal import JournalService,normalize_deal,DAY
from trading import TradingService,key
from bridge import MT4Source,MT5Source,make_handler,ThreadingHTTPServer
from test_trading import FakeMT5,raw,execute,TOKEN,TRADE


def deal(ticket,at,profit=0,commission=0,swap=0,fee=0,typ=0,position=500,entry=0):
    return NS(ticket=ticket,order=ticket,position_id=position,time_msc=at,time=at//1000,type=typ,entry=entry,symbol='XAUUSD.pro' if typ in (0,1) else '',volume=.1 if typ in (0,1) else 0,price=4500,profit=profit,commission=commission,swap=swap,fee=fee,comment='EXPLICIT FIXTURE')

class LedgerRiskTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=str(Path(self.tmp.name)/'fixture.sqlite3');self.db=LedgerStore(self.path)
        self.m=FakeMT5();self.m.equity=10000;self.source=MT5Source(module=self.m);self.clock=now_ms();self.journal=JournalService(self.source,self.db,now=lambda:self.clock)
        self.trading=TradingService(self.source,enabled=True,journal=self.journal,now=lambda:self.clock);self.risk=self.trading.risk;self.expected=key(self.source.status());self.dbkey=self.journal.dbkey(self.expected)
    def tearDown(self):self.db.close();self.tmp.cleanup()
    def policy(self,**changes):
        current=self.db.policy(self.dbkey)
        return self.risk.save({'accountKey':self.expected,'version':current['version'] if current else 0,'maxRiskPct':2,'dailyLossPct':5,'maxDrawdownPct':10,'costPerLot':1,'slippagePoints':2,'resetMinuteUtc':0,'paused':False,**changes})
    def sync(self):return self.journal.sync(self.expected,days=90)
    def test_real_deal_fields_net_costs_deduplication_and_cashflow_separation(self):
        self.m.history=[deal(1,self.clock-10000,commission=-1),deal(2,self.clock-5000,profit=30,commission=-1,swap=-2,fee=-.5,typ=1,entry=1),deal(3,self.clock-2000,profit=500,typ=2)]
        self.sync();self.sync();view=self.journal.view(self.expected)
        self.assertEqual(view['count'],3);self.assertAlmostEqual(view['summary']['net'],25.5);self.assertEqual(view['summary']['cashflow'],500);self.assertEqual(view['summary']['commission'],-2);self.assertEqual(view['summary']['swap'],-2)
        self.m.history[1].fee=-1;self.sync();self.assertAlmostEqual(self.journal.view(self.expected)['summary']['net'],25)
    def test_same_tickets_are_isolated_by_account_and_persist_on_restart(self):
        self.m.history=[deal(1,self.clock-1000,profit=10)];self.sync();old_key=self.expected
        self.m.login=987;self.expected=key(self.source.status());self.m.history=[deal(1,self.clock-1000,profit=-20)];self.sync();self.assertEqual(self.journal.view(self.expected)['summary']['net'],-20)
        with self.assertRaises(ValueError):self.journal.view(old_key)
        self.db.close();self.db=LedgerStore(self.path);self.assertEqual(len(self.db.rows('MT5|'+old_key)),1);self.assertEqual(self.db.rows('MT5|'+old_key)[0]['net'],10)
    def test_history_failure_does_not_erase_data_and_blocks_new_entries(self):
        self.sync();self.policy();self.m.history_deals_get=lambda *args:None
        with self.assertRaises(RuntimeError):self.trading.preview(raw(self.source))
        self.assertTrue(self.risk.snapshot(self.expected)['blocked']);self.assertEqual(self.m.sent,[])
    def test_account_drift_during_sync_never_commits_other_account_rows(self):
        def drift(*args):self.m.login=999;return [deal(123,self.clock-1000,profit=99)]
        self.m.history_deals_get=drift
        with self.assertRaises(ValueError):self.sync()
        self.assertEqual(self.db.rows(self.dbkey),[])
    def test_unconfigured_limits_missing_stop_and_oversized_risk_are_rejected(self):
        self.sync()
        with self.assertRaises(ValueError):self.trading.preview(raw(self.source))
        self.policy(maxRiskPct=.1)
        with self.assertRaises(ValueError):self.trading.preview(raw(self.source))
        self.policy(maxRiskPct=2)
        with self.assertRaises(ValueError):self.trading.preview(raw(self.source,sl=0))
        p=self.trading.preview(raw(self.source));self.assertGreater(p['risk']['estimatedLoss'],112);self.assertLess(p['risk']['estimatedLoss'],200);self.assertEqual(self.m.sent,[])
    def test_policy_change_and_daily_breach_between_preview_and_execute_prevent_send(self):
        self.policy();p=self.trading.preview(raw(self.source));self.policy(maxRiskPct=3)
        self.assertEqual(execute(self.trading,p)['status'],'rejected');self.assertEqual(self.m.sent,[])
        p=self.trading.preview(raw(self.source));self.m.equity=9400
        r=execute(self.trading,p,'fixture-request-00000002');self.assertEqual(r['status'],'rejected');self.assertTrue(self.risk.snapshot(self.expected)['dailyHalt']);self.assertEqual(self.m.sent,[])
    def test_daily_loss_includes_booked_fees_swap_and_current_floating(self):
        self.m.history=[deal(1,self.clock-1000,profit=-100,commission=-10,swap=-5,fee=-1,entry=1)];self.m.balance=9884;self.m.equity=9784
        state=self.policy(dailyLossPct=2)
        self.assertAlmostEqual(state['dayStartBalance'],10000);self.assertAlmostEqual(state['dailyPnl'],-216);self.assertTrue(state['dailyHalt'])
    def test_deposits_do_not_hide_losses_or_create_a_false_daily_profit(self):
        self.m.history=[deal(1,self.clock-1000,profit=1000,typ=2)];self.m.balance=11000;self.m.equity=10800
        state=self.policy(dailyLossPct=1)
        self.assertEqual(state['dayStartBalance'],10000);self.assertEqual(state['dailyPnl'],-200);self.assertTrue(state['dailyHalt'])
    def test_withdrawals_and_credit_changes_are_neutral_to_daily_pnl_and_equity_drawdown(self):
        self.policy();self.clock+=1000
        self.m.history=[deal(21,self.clock-100,profit=-500,typ=2)];self.m.balance=9500;self.m.equity=9500;self.sync()
        state=self.risk.snapshot(self.expected);self.assertEqual(state['drawdown'],0);self.assertEqual(state['dailyPnl'],0);self.assertEqual(state['peakEquity'],9500)
        self.clock+=1000;self.m.history.append(deal(22,self.clock-100,profit=100,typ=3));self.m.credit=100;self.m.equity=9600;self.sync()
        state=self.risk.snapshot(self.expected);self.assertEqual(state['drawdown'],0);self.assertEqual(state['dailyPnl'],0);self.assertEqual(state['dayStartBalance'],10000)

    def test_trailing_drawdown_survives_restart_and_cash_deposits_adjust_peak(self):
        self.policy(dailyLossPct=99);self.m.equity=10500;self.sync();self.risk.snapshot(self.expected)
        self.m.history=[deal(3,self.clock-100,profit=1000,typ=2)];self.m.balance=11000;self.m.equity=11500;self.sync();state=self.risk.snapshot(self.expected)
        self.assertEqual(state['peakEquity'],11500);self.assertEqual(state['drawdown'],0)
        self.m.equity=10000;self.sync();self.assertTrue(self.risk.snapshot(self.expected)['drawdownHalt'])
        second=LedgerStore(self.path)
        try:self.assertTrue(second.get_json('risk_state',self.dbkey)['drawdownHalt'])
        finally:second.close()
        self.m.equity=11500;self.sync();self.assertTrue(self.risk.snapshot(self.expected)['drawdownHalt'])
    def test_daily_halt_resets_only_at_the_configured_day_boundary(self):
        self.clock=now_ms()-2*DAY;self.m.equity=9400;self.policy(dailyLossPct=5,maxDrawdownPct=99)
        self.assertTrue(self.risk.snapshot(self.expected)['dailyHalt']);self.m.equity=10000;self.sync();self.assertTrue(self.risk.snapshot(self.expected)['dailyHalt'])
        self.clock+=DAY;self.sync();self.assertFalse(self.risk.snapshot(self.expected)['dailyHalt'])
    def test_pause_blocks_entries_but_closing_and_tightening_stops_still_work(self):
        self.policy(paused=True);self.m.positions=[NS(ticket=77,symbol='XAUUSD.pro',type=0,volume=.1,price_open=4500,price_current=4501,sl=4490,tp=4520,profit=10,swap=-1,time=self.clock//1000)]
        with self.assertRaises(ValueError):self.trading.preview(raw(self.source))
        close=self.trading.preview(raw(self.source,action='close',position='77',sl=0,tp=0));self.assertTrue(close['risk']['reducing'])
        tighter=self.trading.preview(raw(self.source,action='modify',position='77',sl=4495,tp=4520));self.assertTrue(tighter['risk']['reducing'])
        with self.assertRaises(ValueError):self.trading.preview(raw(self.source,action='modify',position='77',sl=4480,tp=4520))
    def test_netting_addition_uses_combined_position_risk(self):
        self.policy(maxRiskPct=2);self.m.account_info_original=self.m.account_info
        self.m.account_info=lambda:NS(**{**vars(self.m.account_info_original()),'margin_mode':0})
        self.m.positions=[NS(ticket=77,symbol='XAUUSD.pro',type=0,volume=1,price_open=4500,price_current=4501,sl=4490,tp=4520,profit=100,swap=0,time=self.clock//1000)]
        with self.assertRaises(ValueError):self.trading.preview(raw(self.source))
    def test_execution_receipt_survives_restart_and_never_resubmits(self):
        self.policy();p=self.trading.preview(raw(self.source));r=execute(self.trading,p);self.assertEqual(r['status'],'filled');self.assertEqual(len(self.m.sent),1)
        restarted=TradingService(self.source,enabled=True,journal=self.journal)
        self.assertEqual(execute(restarted,p),r);self.assertEqual(len(self.m.sent),1)
        with self.assertRaises(ValueError):restarted.execute({'accountKey':self.expected,'previewId':'wrong','requestId':r['requestId']})
    def test_background_bootstrap_backfills_the_configured_window_after_a_risk_only_sync(self):
        self.m.history=[deal(11,self.clock-40*DAY,profit=25)]
        self.journal.sync(self.expected,days=2)
        self.assertEqual(self.journal.view(self.expected)['count'],0)
        self.journal.sync(self.expected)
        self.assertEqual(self.journal.view(self.expected)['count'],1)
        self.m.history[0].profit=20
        self.clock+=DAY+1
        self.journal.sync(self.expected)
        self.assertEqual(self.journal.view(self.expected)['summary']['net'],20)

    def test_server_notes_and_backup_are_account_scoped(self):
        self.sync();note={'accountKey':self.expected,'id':'fixture-note-00000001','text':'BTR lesson','setup':'BTR','symbol':'XAUUSD.pro'};self.journal.save_note(note)
        self.assertEqual(self.journal.view(self.expected)['notes'][0]['text'],'BTR lesson')
        backup=Path(self.tmp.name)/'backup.sqlite3';self.db.backup(backup);copy=LedgerStore(backup)
        try:self.assertEqual(copy.journal(self.dbkey,0,self.clock)['notes'][0]['setup'],'BTR')
        finally:copy.close()
        with self.assertRaises(ValueError):self.db.backup(backup)
    def test_ambiguous_balance_cost_classification_survives_resync(self):
        self.m.history=[deal(8,self.clock-1000,profit=-25,typ=5)];self.sync();self.assertEqual(self.db.sums(self.dbkey)['review'],1)
        self.journal.classify({'accountKey':self.expected,'ticket':'8','kind':'cost','reason':'Reconciled fixture statement fee'})
        self.sync();row=self.journal.view(self.expected)['deals'][0];self.assertEqual(row['kind'],'cost');self.assertEqual(row['review'],0);self.assertEqual(row['net'],-25)
    def test_risk_settings_compare_versions_and_reset_requires_flat_account(self):
        self.policy()
        with self.assertRaises(ValueError):self.risk.save({'accountKey':self.expected,'version':0,'maxRiskPct':2,'dailyLossPct':5,'maxDrawdownPct':10,'costPerLot':0,'slippagePoints':0,'resetMinuteUtc':0,'paused':False})
        self.m.positions=[NS(ticket=1,symbol='XAUUSD.pro',type=0,volume=.1,price_open=4500,price_current=4501,sl=4490,tp=4520,profit=0,swap=0,time=self.clock//1000)]
        with self.assertRaises(ValueError):self.risk.reset_reference({'accountKey':self.expected,'confirmed':True,'reason':'Reviewed fixture statement'})

class LedgerHTTPTests(unittest.TestCase):
    def setUp(self):
        self.m=FakeMT5();self.source=MT5Source(module=self.m);self.store=LedgerStore(':memory:');self.handler=make_handler(self.source,TOKEN,{'https://terminal.test'},{'127.0.0.1'},enable_trading=True,trade_token=TRADE,store=self.store)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),self.handler);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.expected=key(self.source.status())
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.store.close()
    def request(self,path,body=None,trade=''):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5);headers={'Authorization':'Bearer '+TOKEN,'X-Trade-Token':trade,'Origin':'https://terminal.test','Content-Type':'application/json'}
        c.request('GET' if body is None else 'POST',path,None if body is None else json.dumps(body),headers);r=c.getresponse();value=r.status,json.loads(r.read());c.close();return value
    def test_sync_journal_notes_auth_and_risk_policy_cannot_be_changed_with_read_token(self):
        code,result=self.request('/v1/journal/sync',{'accountKey':self.expected,'days':90});self.assertEqual(code,200);self.assertEqual(result['count'],0)
        self.assertEqual(self.request('/v1/risk/policy',{'accountKey':self.expected})[0],403)
        self.assertEqual(self.request('/v1/journal?accountKey=wrong')[0],400)
        code,_=self.request('/v1/journal/note',{'accountKey':self.expected,'id':'fixture-http-note-0001','text':'DCE fixture','setup':'DCE'});self.assertEqual(code,200)
        self.assertEqual(self.request('/v1/journal?accountKey='+self.expected)[1]['notes'][0]['text'],'DCE fixture')
    def test_unconfigured_backend_blocks_a_direct_order_even_if_browser_is_bypassed(self):
        self.assertEqual(self.request('/v1/trading/preview',raw(self.source),trade=TRADE)[0],400);self.assertEqual(self.m.sent,[])

class MT4LedgerTests(unittest.TestCase):
    def setUp(self):
        self.source=MT4Source();self.source.publish({'connected':True,'broker':'MT4 FIXTURE','account':{'id':'123','server':'Fixture-MT4','currency':'USD','balance':10000,'equity':10000,'credit':0},'positions':[],'tradeAllowed':True,'symbols':[{'ticker':'GOLD.a','currency':'USD','tickSize':.01,'tickValue':1,'point':.01,'volumeMin':.01,'volumeMax':10,'lotStep':.01}],'quotes':[{'symbol':'GOLD.a','bid':4501,'ask':4501.2,'time':now_ms()}]})
        self.db=LedgerStore(':memory:');self.journal=JournalService(self.source,self.db);self.expected=key(self.source.status());self.at=now_ms()
    def tearDown(self):self.db.close()
    def batch(self,rows,index=0,complete=True,run='fixture-run-00001'):
        return {'accountKey':self.expected,'runId':run,'batch':index,'from':self.at-90*DAY,'through':self.at,'snapshotBalance':10000,'snapshotCredit':0,'deals':rows,'complete':complete}
    def test_batches_commit_atomically_and_retries_never_duplicate_costs(self):
        row=vars(deal(123,self.at-1000,profit=20,commission=-2,swap=-1))
        self.journal.ingest_mt4(self.batch([row],complete=False));self.assertEqual(self.journal.view(self.expected)['count'],0)
        body=self.batch([],index=1);self.journal.ingest_mt4(body);self.journal.ingest_mt4(body)
        self.assertEqual(self.journal.view(self.expected)['count'],1);self.assertEqual(self.journal.view(self.expected)['summary']['net'],17)
    def test_mt4_balance_operations_require_statement_classification(self):
        self.journal.ingest_mt4(self.batch([vars(deal(6,self.at-1000,profit=1000,typ=6))]))
        pending=self.journal.view(self.expected);row=pending['deals'][0];self.assertEqual(row['review'],1);self.assertEqual(pending['summary']['net'],0);self.assertEqual(pending['summary']['unclassifiedNet'],1000)
        self.journal.classify({'accountKey':self.expected,'ticket':'6','kind':'cash','reason':'Verified fixture deposit'})
        self.assertEqual(self.journal.view(self.expected)['summary']['net'],0);self.assertEqual(self.journal.view(self.expected)['summary']['cashflow'],1000)
    def test_cross_account_and_out_of_sequence_history_is_rejected(self):
        with self.assertRaises(ValueError):self.journal.ingest_mt4(self.batch([],index=1))
        body=self.batch([]);body['accountKey']='Other|123'
        with self.assertRaises(ValueError):self.journal.ingest_mt4(body)
    def test_a_new_policy_halt_rechecks_an_mt4_command_before_delivery(self):
        self.journal.ingest_mt4(self.batch([]))
        trading=TradingService(self.source,enabled=True,journal=self.journal)
        policy={'accountKey':self.expected,'version':0,'maxRiskPct':2,'dailyLossPct':5,'maxDrawdownPct':10,'costPerLot':0,'slippagePoints':0,'resetMinuteUtc':0,'paused':False}
        trading.risk.save(policy)
        p=trading.preview(raw(self.source,symbol='GOLD.a'));r=execute(trading,p)
        self.assertEqual(r['status'],'pending')
        trading.risk.save({**policy,'version':1,'paused':True})
        self.assertEqual(self.source.next_trade(lambda c:trading.risk.check(c,self.expected)),'')
        self.assertEqual(trading.receipt(r['requestId'],self.expected)['status'],'rejected')

    def test_browser_read_token_cannot_publish_mt4_account_or_history_data(self):
        publish='fixture-publisher-token-01234567890123456789';handler=make_handler(self.source,TOKEN,{'https://terminal.test'},{'127.0.0.1'},store=self.db,publish_token=publish)
        server=ThreadingHTTPServer(('127.0.0.1',0),handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def request(path,body,publisher=''):
            c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3);c.request('POST',path,json.dumps(body),{'Authorization':'Bearer '+TOKEN,'X-Publish-Token':publisher,'Content-Type':'application/json'});r=c.getresponse();status=r.status;r.read();c.close();return status
        try:
            self.assertEqual(request('/v1/mt4/publish',{'account':{'id':'fake','server':'Fake'}}),403)
            self.assertEqual(request('/v1/mt4/history',self.batch([])),403)
            self.assertEqual(request('/v1/mt4/history',self.batch([]),publish),200)
            self.assertEqual(self.source.status()['account']['id'],'123')
        finally:server.shutdown();server.server_close();thread.join()
