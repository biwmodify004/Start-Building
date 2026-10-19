"""Account-bound server risk policy, checked at preview and again at execution."""
import math
from database import number,total,now_ms
from journal import DAY
from trading import bound

class RiskEngine:
    def __init__(self,source,journal,executor,now=None):
        self.source,self.journal,self.store,self.executor=source,journal,journal.store,executor
        self.now=now or now_ms
    def _key(self,expected):return self.journal.dbkey(expected)
    def save(self,raw):
        expected=raw.get('accountKey');bound(self.source,expected)
        policy={}
        for name in ('maxRiskPct','dailyLossPct','maxDrawdownPct'):
            value=number(raw.get(name))
            if not 0<value<=100:raise ValueError('Risk limits must be greater than zero and at most 100 percent')
            policy[name]=value
        for name in ('costPerLot','slippagePoints'):
            value=number(raw.get(name))
            if not 0<=value<=1000000:raise ValueError('Invalid cost/slippage allowance')
            policy[name]=value
        reset=raw.get('resetMinuteUtc',0)
        if isinstance(reset,bool) or not isinstance(reset,int) or not 0<=reset<1440:raise ValueError('Reset must be a UTC minute from 0 to 1439')
        if not isinstance(raw.get('paused'),bool):raise ValueError('Choose whether new entries are paused')
        version=raw.get('version',0)
        if isinstance(version,bool) or not isinstance(version,int) or version<0:raise ValueError('Invalid risk policy version')
        policy.update(resetMinuteUtc=reset,paused=raw['paused'])
        self.journal.sync(expected,days=2)
        dbkey=self._key(expected)
        with self.store.transaction():
            saved=self.store.save_policy(dbkey,policy,version)
        return self.snapshot(expected)
    def snapshot(self,expected):
        status=self.journal.status(expected,False);account=status['account'];dbkey=self._key(expected);now=self.now()
        with self.store.transaction():
            policy=self.store.policy(dbkey)
            if not policy:return {'accountKey':expected,'configured':False,'blocked':True,'reasons':['Configure account risk limits before opening a new position'],'policy':None,'currency':account.get('currency',''),'updatedAt':now}
            sync=self.store.get_json('sync_state',dbkey) or {}
            offset=policy['resetMinuteUtc']*60000;day_start=((now-offset)//DAY)*DAY+offset
            today=self.store.sums(dbkey,day_start,now)
            balance=number(account.get('balance'));equity=number(account.get('equity'));credit=number(account.get('credit',0))
            fresh=bool(status.get('connected') and not sync.get('error') and sync.get('from',now+1)<=day_start and now-sync.get('syncedAt',0)<=90000 and sync.get('through',0)>=now-90000)
            if 'balance' in sync and (abs(balance-sync['balance'])>1e-6 or abs(credit-sync.get('credit',0))>1e-6):fresh=False
            state=self.store.get_json('risk_state',dbkey) or {'referenceAt':now,'peakEquity':equity,'flowTotal':0,'dayStart':day_start,'dailyHalt':False,'drawdownHalt':False}
            if state.get('dayStart')!=day_start:state.update(dayStart=day_start,dailyHalt=False)
            since_reference=self.store.sums(dbkey,state['referenceAt'],now)
            flows=since_reference['cashflow']
            reviewed=not today['review'] and not since_reference['review']
            if fresh and reviewed:
                peak=total([state['peakEquity'],flows,-state.get('flowTotal',0)])
                state.update(peakEquity=max(equity,peak),flowTotal=flows)
            peak=state['peakEquity']
            baseline=total([balance,-today['balanceDelta']])
            pnl=total([today['tradingNet'],equity,-balance,-credit])
            loss=max(0,-pnl);daily_limit=max(0,baseline)*policy['dailyLossPct']/100
            dd=max(0,peak-equity);dd_pct=dd/peak*100 if peak>0 else 100
            if fresh and reviewed and loss>=daily_limit:state['dailyHalt']=True
            if fresh and reviewed and dd_pct>=policy['maxDrawdownPct']:state['drawdownHalt']=True
            self.store.set_json('risk_state',dbkey,state)
            reasons=[]
            if not fresh:reasons.append('History/account snapshot is not synchronized; wait for Auto Journal')
            if not reviewed:reasons.append('Unclassified/canceled broker adjustments require statement reconciliation')
            if baseline<=0 or equity<=0 or peak<=0:reasons.append('A positive verified account balance/equity is required')
            if policy['paused']:reasons.append('New entries paused by your risk policy')
            if state['dailyHalt']:reasons.append('Daily Loss limit reached; new entries stay halted until the next configured day')
            if state['drawdownHalt']:reasons.append('Drawdown limit reached; review the account and explicitly reset the reference while flat')
            return {'accountKey':expected,'configured':True,'policy':policy,'currency':account.get('currency',''),'blocked':bool(reasons),'reasons':reasons,'equity':equity,'dayStart':day_start,'dayStartBalance':baseline,'dailyPnl':pnl,'dailyLoss':loss,'dailyLimit':daily_limit,'dailyRemaining':max(0,daily_limit-loss),'peakEquity':peak,'drawdown':dd,'drawdownPct':dd_pct,'drawdownRemaining':max(0,peak*policy['maxDrawdownPct']/100-dd),'referenceAt':state['referenceAt'],'dailyHalt':state['dailyHalt'],'drawdownHalt':state['drawdownHalt'],'updatedAt':now}
    def reset_reference(self,raw):
        expected=raw.get('accountKey');bound(self.source,expected)
        if raw.get('confirmed') is not True or not isinstance(raw.get('reason'),str) or not 3<=len(raw['reason'].strip())<=500:raise ValueError('Confirm the reference reset and record a reason')
        if self.executor.positions():raise ValueError('Close all positions before resetting the drawdown reference')
        self.journal.sync(expected,days=2);dbkey=self._key(expected);account=bound(self.source,expected)['account'];now=self.now()
        with self.store.transaction():
            state=self.store.get_json('risk_state',dbkey) or {}
            state.update(referenceAt=now,peakEquity=number(account['equity']),flowTotal=0,drawdownHalt=False)
            self.store.set_json('risk_state',dbkey,state);self.store.audit(dbkey,'risk-reference-reset',{'reason':raw['reason'].strip(),'equity':account['equity']})
        return self.snapshot(expected)
    def reducing(self,command,positions):
        if command['action']=='close':return True
        if command['action']!='modify':return False
        p=next((p for p in positions if str(p['ticket'])==command['position']),None)
        if not p:return False
        old,new=p.get('sl',0),command['sl']
        return not old or bool(new and (new>=old if p['side']=='buy' else new<=old))
    def estimate(self,command,policy,positions):
        side=command['side'];volume=command['volume'];entry=command['price'];sl=command['sl'];point=number(command['spec']['point'])
        if sl<=0:raise ValueError('Risk Engine requires a Stop Loss for every new or risk-increasing position')
        if command['action']=='modify':
            p=next(p for p in positions if p['ticket']==command['position']);entry=p['entry']
        else:
            entry+=(command['deviation']+policy['slippagePoints'])*point*(1 if side=='buy' else -1)
            if command.get('positionMode')=='netting':
                same=[p for p in positions if p['symbol']==command['symbol']]
                if same:
                    p=same[0]
                    if p['side']!=side:raise ValueError('Use Close/SLTP to reduce or manage an existing netting position before a new opposite-side entry')
                    combined=volume+p['volume'];entry=(entry*volume+p['entry']*p['volume'])/combined;volume=combined
        stop=sl-policy['slippagePoints']*point*(1 if side=='buy' else -1)
        if entry<=0 or stop<=0:raise ValueError('Invalid risk-adjusted price')
        if hasattr(self.source,'mt5'):
            with self.source.lock:
                result=self.source.mt5.order_calc_profit(self.source.mt5.ORDER_TYPE_BUY if side=='buy' else self.source.mt5.ORDER_TYPE_SELL,command['symbol'],volume,entry,stop)
            if result is None:raise ValueError('Broker could not calculate Stop Loss risk in account currency')
            risk=max(0,-number(result))
        else:
            spec=next(s for s in self.source.symbols() if s['ticker']==command['symbol']);tick=number(spec.get('tickSize'));value=number(spec.get('tickValue',0))
            if tick<=0 or value<=0:raise ValueError('MT4 tick value is unavailable; update the EA and wait for a fresh contract catalog')
            distance=(entry-stop) if side=='buy' else (stop-entry);risk=max(0,distance/tick*value*volume)
        return total([risk,policy['costPerLot']*volume])
    def check(self,command,expected):
        positions=self.executor.positions()
        if self.reducing(command,positions):return {'reducing':True,'estimatedLoss':0,'currency':bound(self.source,expected)['account'].get('currency','')}
        self.journal.sync(expected,days=2)
        snapshot=self.snapshot(expected)
        if snapshot['blocked']:raise ValueError('Risk Engine: '+'; '.join(snapshot['reasons']))
        policy=snapshot['policy'];loss=self.estimate(command,policy,positions);limit=snapshot['equity']*policy['maxRiskPct']/100
        if loss>limit+1e-8:raise ValueError(f'Risk Engine: estimated loss {loss:.2f} exceeds per-trade limit {limit:.2f} {snapshot["currency"]}')
        if loss>min(snapshot['dailyRemaining'],snapshot['drawdownRemaining'])+1e-8:raise ValueError('Risk Engine: Stop Loss risk exceeds the remaining Daily Loss / Drawdown budget')
        bound(self.source,expected)
        return {'reducing':False,'estimatedLoss':loss,'limit':limit,'currency':snapshot['currency'],'policyVersion':policy['version'],'dailyRemaining':snapshot['dailyRemaining'],'drawdownRemaining':snapshot['drawdownRemaining']}
