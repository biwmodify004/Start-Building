"""Actual terminal-history ingestion, isolated by platform/server/login."""
from datetime import datetime,timezone
import math
import re
import threading
import time
from database import number,total,now_ms
from trading import key,bound,IDENTIFIER

DAY=86400000

def normalize_deal(row,platform):
    d=dict(row)
    ticket=str(d.get('ticket',''))
    if not ticket.isdigit() or len(ticket)>32:raise ValueError('Invalid broker deal ticket')
    typ=int(d.get('type',-1));entry=int(d.get('entry',1 if platform=='MT4' else 0))
    if platform=='MT4':
        kind='trade' if typ in (0,1) else 'adjustment' if typ==6 else 'credit' if typ==7 else 'adjustment'
    else:
        kind='trade' if typ in (0,1) else 'cash' if typ==2 else 'credit' if typ==3 else 'cost' if typ in (4,7,8,9,10,11,12,15,16,17) else 'adjustment'
    review=int(kind=='adjustment' or typ in (13,14))
    at=int(number(d.get('time_msc') or number(d.get('time',0))*1000))
    if at<0 or at>now_ms()+5000:raise ValueError('Invalid history time; check the broker UTC offset')
    profit,commission,swap,fee=[number(d.get(k,0)) for k in ('profit','commission','swap','fee')]
    net=total([profit,commission,swap,fee])
    symbol=str(d.get('symbol',''))[:128]
    opened=int(number(d.get('opened_at',0))) if platform=='MT4' else 0
    if opened<0 or opened>at:raise ValueError('Invalid order opening time')
    return {'ticket':ticket,'positionId':str(d.get('position_id',ticket if platform=='MT4' and kind=='trade' else '0')),'orderId':str(d.get('order',ticket if platform=='MT4' else '0')),'time':at,'openedAt':opened or None,'kind':kind,'symbol':symbol,'side':'buy' if typ==0 else 'sell' if typ==1 else '', 'entry':entry,'volume':number(d.get('volume',0)),'price':number(d.get('price',0)),'profit':profit,'commission':commission,'swap':swap,'fee':fee,'net':net,'balanceDelta':0 if kind=='credit' else net,'cashflow':net if kind in ('cash','credit') else 0,'review':review,'type':typ,'comment':str(d.get('comment',''))[:500],'platform':platform,'brokerFields':{k:d[k] for k in ('ticket','order','time','time_msc','opened_at','entry_price','type','entry','magic','position_id','reason','volume','price','commission','swap','profit','fee','symbol','comment','external_id') if k in d}}

class JournalService:
    def __init__(self,source,store,days=90,now=None):
        self.source,self.store,self.days=source,store,days
        self.now=now or now_ms
        self.lock=threading.RLock();self.staging={};self.last_full={}
    def status(self,expected,connected=True):
        status=self.source.status()
        if key(status)!=expected or connected and not status.get('connected'):raise ValueError('Account changed or terminal disconnected')
        return status
    def dbkey(self,expected):
        status=self.status(expected,False)
        return status['platform']+'|'+expected
    def sync(self,expected,days=None):
        with self.lock:
            status=self.status(expected);dbkey=self.dbkey(expected);at=self.now()
            if not hasattr(self.source,'mt5'):
                state=self.store.get_json('sync_state',dbkey)
                if not state or state.get('error') or at-state.get('syncedAt',0)>90000:raise RuntimeError('Waiting for a complete MT4 history publication. Update the EA, select All History, set HistoryReady and PublishToken')
                return state
            state=self.store.get_json('sync_state',dbkey) or {}
            start=at-int(days if days is not None else self.days)*DAY
            full=days is not None and days>=self.days or days is None and self.last_full.get(dbkey,0)<at-DAY
            if days is None and state.get('through') and not full and state.get('from',at)<=at-(self.days-1)*DAY:
                start=max(start,state['through']-2*DAY)
            try:
                deals=[];cursor=start
                with self.source.lock:
                    self.status(expected)
                    while cursor<=at:
                        end=min(at,cursor+7*DAY)
                        rows=self.source.mt5.history_deals_get(datetime.fromtimestamp(cursor/1000,timezone.utc),datetime.fromtimestamp(end/1000,timezone.utc))
                        if rows is None:raise RuntimeError('MT5 history read failed')
                        if len(rows)>100000 or len(deals)+len(rows)>500000:raise RuntimeError('History batch too large; use a shorter import range')
                        for row in rows:
                            raw=row._asdict() if hasattr(row,'_asdict') else vars(row)
                            deal=normalize_deal(raw,'MT5')
                            if start<=deal['time']<=at:deals.append(deal)
                        cursor=end+1
                    updated=self.status(expected)
                    if any(abs(number(updated['account'].get(k,0))-number(status['account'].get(k,0)))>1e-6 for k in ('balance','credit')):raise RuntimeError('Account balance changed during history sync; try again')
                    status=updated
                self.store.ingest(dbkey,status,deals,start,at,at,'MT5 deals')
                if full:self.last_full[dbkey]=at
                return self.store.get_json('sync_state',dbkey)
            except Exception:
                self.store.fail_sync(dbkey,'History sync failed; no new entries permitted until verified')
                raise
    def ingest_mt4(self,payload):
        with self.lock:
            expected=payload.get('accountKey');status=self.status(expected);dbkey=self.dbkey(expected)
            ident=payload.get('runId');index=payload.get('batch');rows=payload.get('deals');start=int(number(payload.get('from')));end=int(number(payload.get('through')))
            if not isinstance(ident,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}',ident) or not isinstance(index,int) or isinstance(index,bool) or not 0<=index<2000 or not isinstance(rows,list) or len(rows)>500 or start<0 or end<start or end>self.now()+5000 or self.now()-end>1800000:raise ValueError('Invalid MT4 history batch')
            normalized=[normalize_deal(r,'MT4') for r in rows]
            if any(not start<=d['time']<=end for d in normalized):raise ValueError('History row outside the declared range')
            active=self.staging.get(dbkey)
            if not active or active['id']!=ident:
                if index!=0:raise ValueError('Restart the MT4 history publication from batch zero')
                active={'id':ident,'next':0,'rows':{},'from':start,'through':end};self.staging[dbkey]=active
            if active['from']!=start or active['through']!=end:raise ValueError('History range changed during publication')
            if index<active['next']:return {'ok':True,'duplicate':True}
            if active.get('complete'):raise ValueError('Start a new history run after completion')
            if index!=active['next']:raise ValueError('History batch out of sequence')
            active['rows'].update({d['ticket']:d for d in normalized});active['next']+=1
            if len(active['rows'])>100000:del self.staging[dbkey];raise ValueError('MT4 history import is too large')
            if payload.get('complete') is True:
                self.status(expected)
                snapshot={**status,'account':{**status['account'],'balance':number(payload.get('snapshotBalance')),'credit':number(payload.get('snapshotCredit',0))}}
                self.store.ingest(dbkey,snapshot,list(active['rows'].values()),start,end,self.now(),'MT4 loaded Account History')
                # Retain the completed run's sequence so a lost ACK is idempotent.
                active['rows']={};active['complete']=True
                return {'ok':True,'complete':True}
            return {'ok':True,'complete':False}
    def view(self,expected,days=90,page=0):
        status=self.status(expected,False);dbkey=self.dbkey(expected);end=self.now();start=end-days*DAY
        return {'accountKey':expected,'platform':status['platform'],'account':status['account'],'updatedAt':end,**self.store.journal(dbkey,start,end,page)}
    def save_note(self,raw):
        expected=raw.get('accountKey');self.status(expected);dbkey=self.dbkey(expected)
        ident=raw.get('id');text=raw.get('text');setup=raw.get('setup','General');position=str(raw.get('positionId',''))
        if not isinstance(ident,str) or not IDENTIFIER.fullmatch(ident) or not isinstance(text,str) or not 1<=len(text.strip())<=2000 or setup not in ('BTR','DCE','Trend Following','Mean Reversion','Breakout','General'):raise ValueError('Invalid journal note')
        symbol=str(raw.get('symbol',''))[:128]
        if position and not any(d['positionId']==position for d in self.store.rows(dbkey)):raise ValueError('Position is not in this account journal')
        note={'id':ident,'time':self.now(),'text':text.strip(),'setup':setup,'symbol':symbol,'positionId':position}
        with self.store.transaction():self.store.save_note(dbkey,note);self.store.audit(dbkey,'journal-note',{'id':ident})
        return {'accountKey':expected,'note':note}
    def classify(self,raw):
        expected=raw.get('accountKey');self.status(expected);ticket=str(raw.get('ticket',''));kind=raw.get('kind');reason=raw.get('reason')
        if not ticket.isdigit() or kind not in ('cash','cost') or not isinstance(reason,str) or not 3<=len(reason.strip())<=500:raise ValueError('Select cash flow or trading cost and record a statement reconciliation reason')
        self.store.classify(self.dbkey(expected),ticket,kind,reason.strip())
        return {'accountKey':expected,'ok':True}
    def delete_note(self,raw):
        expected=raw.get('accountKey');self.status(expected);ident=raw.get('id')
        if not isinstance(ident,str) or not IDENTIFIER.fullmatch(ident):raise ValueError('Invalid note ID')
        self.store.delete_note(self.dbkey(expected),ident)
        return {'accountKey':expected,'ok':True}
