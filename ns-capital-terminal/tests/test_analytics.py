"""Real ledger computations, explicit fixture deals only; no broker orders."""
import http.client
import json
from pathlib import Path
import sys
import threading
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'broker-bridge'))
from database import LedgerStore, now_ms
from journal import JournalService, normalize_deal, DAY
from analytics import JournalAnalytics, trade_cycles, behavior_flags
from ai_advisor import AITradeAdvisor
from bridge import MT5Source, make_handler, ThreadingHTTPServer
from trading import key
from test_trading import FakeMT5, TOKEN


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.db=LedgerStore(':memory:');self.m=FakeMT5();self.source=MT5Source(module=self.m);self.now=now_ms();self.expected=key(self.source.status());self.journal=JournalService(self.source,self.db,now=lambda:self.now);self.analytics=JournalAnalytics(self.journal);self.dbkey=self.journal.dbkey(self.expected)
    def tearDown(self):self.db.close()
    def deal(self,ticket,minute,entry=0,side=0,volume=1,profit=0,commission=0,swap=0,fee=0,position=500,platform='MT5',**other):
        return normalize_deal({'ticket':ticket,'order':ticket,'position_id':position,'time_msc':self.now-DAY+minute*60000,'type':side,'entry':entry,'symbol':'GOLD.fixture','volume':volume,'price':4500,'profit':profit,'commission':commission,'swap':swap,'fee':fee,**other},platform)
    def ingest(self,rows):self.db.ingest(self.dbkey,self.source.status(),rows,self.now-90*DAY,self.now,self.now)
    def standard(self):return [self.deal(1,1,commission=-2),self.deal(2,2,entry=1,side=1,volume=.4,profit=40,commission=-.8),self.deal(3,3,entry=1,side=1,volume=.6,profit=-10,commission=-1.2,swap=-3,fee=-.5)]
    def test_partial_closes_count_once_and_include_entry_and_exit_costs(self):
        self.ingest(self.standard());s=self.analytics.snapshot(self.expected,30)
        self.assertEqual(s['closedTrades'],1);self.assertEqual(s['wins'],1);self.assertEqual(s['winRate'],100);self.assertAlmostEqual(s['closedNet'],22.5);self.assertAlmostEqual(s['bookedNet'],22.5)
        self.assertEqual(s['recentTrades'][0]['tickets'],['1','2','3']);self.assertTrue(s['completeRange']);self.assertEqual(s['openCycles'],0)
    def test_inout_splits_reversal_costs_without_losing_or_double_counting(self):
        rows=[self.deal(1,1,volume=1,commission=-1),self.deal(2,2,entry=2,side=1,volume=3,profit=50,commission=-3,swap=-2),self.deal(3,3,entry=1,side=0,volume=2,profit=-20,commission=-2)]
        cycles,_,excluded,opened,_=trade_cycles(rows)
        self.assertEqual((len(cycles),excluded,opened),(2,0,0));self.assertEqual(cycles[0]['volume'],1);self.assertEqual(cycles[1]['volume'],2)
        self.assertAlmostEqual(cycles[0]['net'],46);self.assertAlmostEqual(cycles[1]['net'],-24);self.assertAlmostEqual(sum(c['net'] for c in cycles),sum(r['net'] for r in rows))
    def test_missing_entries_and_unclosed_positions_do_not_inflate_win_rate(self):
        rows=[self.deal(10,1,entry=1,side=1,profit=100,position=700),self.deal(12,2,entry=0,position=700),self.deal(11,2,position=800)]+self.standard()
        self.ingest(rows);s=self.analytics.snapshot(self.expected)
        self.assertEqual(s['closedTrades'],1);self.assertEqual(s['openCycles'],1);self.assertGreater(s['excludedRecords'],0)
        with self.assertRaises(ValueError):self.analytics.create_share({'accountKey':self.expected,'consent':True})
    def test_cashflows_are_outside_curve_and_unlinked_charges_are_disclosed(self):
        rows=self.standard()+[self.deal(20,5,side=2,profit=1000),self.deal(21,6,side=7,commission=-5),self.deal(22,7,side=6,profit=42)]
        self.ingest(rows);s=self.analytics.snapshot(self.expected,30)
        self.assertAlmostEqual(s['bookedNet'],17.5);self.assertEqual(s['unattributedCosts'],-5);self.assertEqual(s['pendingClassification'],1);self.assertAlmostEqual(s['closedNet'],22.5)
    def test_mt4_closed_tickets_keep_open_time_and_partial_ticket_basis(self):
        row=self.deal(1,5,entry=1,platform='MT4',opened_at=self.now-DAY+60000,profit=10,commission=-1)
        closed,opens,excluded,opened,_=trade_cycles([row]);self.assertEqual(closed[0]['basis'],'closed-ticket');self.assertEqual(closed[0]['net'],9);self.assertEqual(opens[0]['time'],row['openedAt']);self.assertEqual((excluded,opened),(0,0))
    def test_behavior_rules_deduplicate_fills_and_require_same_symbol_size_and_time(self):
        settings={'enabled':True,'maxEntriesDay':1,'cooldownMinutes':30,'sizeIncreaseFactor':1.5}
        loss={'id':'loss-fixture','symbol':'GOLD.fixture','closedAt':self.now-20*60000,'volume':1,'net':-10}
        entries=[{'time':self.now-10*60000,'symbol':'GOLD.fixture','volume':2,'ticket':'1','order':'9'},{'time':self.now-10*60000,'symbol':'GOLD.fixture','volume':2,'ticket':'2','order':'9'},{'time':self.now-5*60000,'symbol':'OTHER.fixture','volume':2,'ticket':'3','order':'10'}]
        flags=behavior_flags(entries,[loss],settings,self.now-DAY,self.now)
        self.assertEqual(sum(f['kind']=='rapid-size-increase' for f in flags),1);self.assertEqual(next(f for f in flags if f['kind']=='entry-limit')['count'],2)
        self.assertEqual(behavior_flags(entries,[loss],{'enabled':False},self.now-DAY,self.now),[])
    def test_preferences_persist_per_account_and_invalid_thresholds_reject(self):
        raw={'accountKey':self.expected,'enabled':True,'maxEntriesDay':5,'cooldownMinutes':30,'sizeIncreaseFactor':1.5}
        self.analytics.save_preferences(raw);self.assertTrue(self.analytics.snapshot(self.expected)['settings']['enabled'])
        for field,value in [('maxEntriesDay',1.5),('cooldownMinutes',0),('sizeIncreaseFactor',float('nan')),('enabled','yes')]:
            with self.subTest(field=field),self.assertRaises((ValueError,TypeError)):self.analytics.save_preferences({**raw,field:value})
        self.m.login=987;other=key(self.source.status());self.assertEqual(self.analytics.snapshot(other)['settings'],{'enabled':False})
    def test_setup_can_be_assigned_after_a_unique_position_closes(self):
        self.ingest(self.standard());self.journal.save_note({'accountKey':self.expected,'id':'00000000-0000-4000-8000-000000000001','text':'review','positionId':'500','setup':'Breakout'})
        self.assertEqual(self.analytics.snapshot(self.expected)['breakdown'][0]['setup'],'Breakout')
    def test_readonly_report_requires_consent_redacts_and_stores_only_a_token_hash(self):
        self.ingest(self.standard());raw={'accountKey':self.expected,'days':30,'expiresDays':1}
        with self.assertRaises(ValueError):self.analytics.create_share(raw)
        share=self.analytics.create_share({**raw,'consent':True});public=self.analytics.shared(share['token']);encoded=json.dumps(public)
        for field in ('accountKey','account_key','ticket','positionId','comment','token','Fixture-Server'):self.assertNotIn(field,encoded)
        self.assertFalse(public['report']['independentlyVerified']);self.assertFalse(public['report']['live']);self.assertEqual(public['report']['closedTrades'],1)
        self.assertNotIn(share['token'],json.dumps(list(self.db.conn.execute('SELECT * FROM record_shares').fetchone())))
        self.assertNotIn('token',json.dumps(self.analytics.shares(self.expected)))
        self.now+=DAY+1
        with self.assertRaises(ValueError):self.analytics.shared(share['token'])
    def test_cross_account_revocation_cannot_revoke_another_report(self):
        self.ingest(self.standard());share=self.analytics.create_share({'accountKey':self.expected,'consent':True,'days':30})
        self.m.login=987;other=key(self.source.status());self.analytics.revoke_share({'accountKey':other,'id':share['id']});self.assertEqual(self.analytics.shared(share['token'])['report']['closedTrades'],1)
        self.m.login=12345678;self.analytics.revoke_share({'accountKey':self.expected,'id':share['id']})
        with self.assertRaises(ValueError):self.analytics.shared(share['token'])
    def test_rankings_only_show_qualified_opted_in_snapshots_and_expire(self):
        rows=[]
        for i in range(20):rows += [self.deal(100+i*2,1+i*3,position=1000+i),self.deal(101+i*2,2+i*3,entry=1,side=1,profit=10 if i%2 else -5,position=1000+i)]
        self.ingest(rows);self.assertEqual(self.analytics.rankings(self.expected)['entries'],[])
        self.analytics.publish_rank({'accountKey':self.expected,'alias':'Fixture alias','consent':True});entries=self.analytics.rankings(self.expected)['entries'];self.assertEqual(len(entries),1);self.assertEqual(entries[0]['profitFactor'],2);self.assertTrue(entries[0]['mine'])
        self.now+=DAY+1;self.assertEqual(self.analytics.rankings(self.expected)['entries'],[])
        self.analytics.publish_rank({'accountKey':self.expected,'consent':False})
    def test_ai_coaching_uses_server_metrics_redacts_inputs_and_never_trades(self):
        self.ingest(self.standard());self.journal.save_note({'accountKey':self.expected,'id':'00000000-0000-4000-8000-000000000002','text':'NEVER SEND MY PRIVATE NOTE','setup':'General'});calls=[]
        def completion(payload):calls.append(payload);return json.dumps({'summary':'Fixture evidence summary','strengths':['One measured observation'],'improvements':[],'nextPlan':['Review plan']})
        advisor=AITradeAdvisor(self.source,None,provider='ollama',model='fixture-model',completion=completion)
        result=advisor.coach({'accountKey':self.expected,'days':30,'closedTrades':9999},self.analytics)
        prompt=json.dumps(calls);self.assertNotIn('NEVER SEND',prompt);self.assertNotIn(self.expected,prompt);self.assertIn('"closedTrades": 1',calls[0]['messages'][1]['content']);self.assertFalse(result['coaching']['autoExecution']);self.assertEqual(self.m.sent,[]);self.assertEqual(self.analytics.snapshot(self.expected)['coaching']['model'],'fixture-model')
        advisor.completion=lambda _:json.dumps({'summary':'Bad shape','strengths':'wrong','improvements':[],'nextPlan':[]})
        with self.assertRaises(ValueError):advisor.coach({'accountKey':self.expected},self.analytics)
    def test_http_share_view_needs_only_report_capability_and_respects_origin(self):
        self.ingest(self.standard());share=self.analytics.create_share({'accountKey':self.expected,'consent':True,'days':30})
        handler=make_handler(self.source,TOKEN,{'https://fixture.site'},{'127.0.0.1'},store=self.db)
        server=ThreadingHTTPServer(('127.0.0.1',0),handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def request(path,body,origin='https://fixture.site'):
            connection=http.client.HTTPConnection('127.0.0.1',server.server_port);connection.request('POST',path,json.dumps(body),{'Content-Type':'application/json','Origin':origin});response=connection.getresponse();status=response.status;data=json.loads(response.read());connection.close();return status,data
        try:
            status,data=request('/v1/track-record/view',{'token':share['token']});self.assertEqual(status,200);self.assertIn('report',data)
            self.assertEqual(request('/v1/track-record/view',{'token':share['token']},'https://evil.fixture')[0],403)
            self.assertEqual(request('/v1/journal/share',{'accountKey':self.expected,'consent':True})[0],401)
            self.assertEqual(request('/v1/track-record/view',{'token':'wrong'})[0],404)
        finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
