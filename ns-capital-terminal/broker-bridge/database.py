"""Server-owned SQLite ledger. No credentials, no generated market records."""
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
import json
import math
import sqlite3
import threading
import time


def now_ms(): return int(time.time()*1000)
def dumps(value): return json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':'))
def total(values): return float(sum((Decimal(str(v)) for v in values),Decimal(0)))
def number(value):
    if isinstance(value,bool): raise ValueError('Invalid ledger number')
    value=float(value)
    if not math.isfinite(value): raise ValueError('Invalid ledger number')
    return value

class LedgerStore:
    def __init__(self,path):
        self.path=str(path) if str(path)==':memory:' else str(Path(path).expanduser().resolve())
        if self.path!=':memory:': Path(self.path).expanduser().resolve().parent.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock()
        self.conn=sqlite3.connect(self.path,timeout=20,check_same_thread=False,isolation_level=None)
        self.conn.row_factory=sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys=ON');self.conn.execute('PRAGMA busy_timeout=20000')
        if self.path!=':memory:': self.conn.execute('PRAGMA journal_mode=DELETE');self.conn.execute('PRAGMA synchronous=FULL')
        with self.lock:
            version=self.conn.execute('PRAGMA user_version').fetchone()[0]
            if version>2: raise RuntimeError('Database is newer than this Bridge; update the Bridge')
            self.conn.executescript('''
            BEGIN IMMEDIATE;
            CREATE TABLE IF NOT EXISTS accounts(account_key TEXT PRIMARY KEY,snapshot TEXT NOT NULL,updated_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS deals(account_key TEXT NOT NULL,ticket TEXT NOT NULL,position_id TEXT NOT NULL,order_id TEXT NOT NULL,time_ms INTEGER NOT NULL,kind TEXT NOT NULL,symbol TEXT NOT NULL,side TEXT NOT NULL,entry INTEGER NOT NULL,volume REAL NOT NULL,price REAL NOT NULL,profit REAL NOT NULL,commission REAL NOT NULL,swap REAL NOT NULL,fee REAL NOT NULL,net REAL NOT NULL,balance_delta REAL NOT NULL,cashflow REAL NOT NULL,review INTEGER NOT NULL,raw TEXT NOT NULL,PRIMARY KEY(account_key,ticket),FOREIGN KEY(account_key) REFERENCES accounts(account_key));
            CREATE INDEX IF NOT EXISTS deals_time ON deals(account_key,time_ms,ticket);
            CREATE INDEX IF NOT EXISTS deals_position ON deals(account_key,position_id,time_ms);
            CREATE TABLE IF NOT EXISTS sync_state(account_key TEXT PRIMARY KEY,state TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS notes(account_key TEXT NOT NULL,id TEXT NOT NULL,time_ms INTEGER NOT NULL,body TEXT NOT NULL,PRIMARY KEY(account_key,id));
            CREATE TABLE IF NOT EXISTS deal_overrides(account_key TEXT NOT NULL,ticket TEXT NOT NULL,kind TEXT NOT NULL,reason TEXT NOT NULL,PRIMARY KEY(account_key,ticket));
            CREATE TABLE IF NOT EXISTS risk_policy(account_key TEXT PRIMARY KEY,version INTEGER NOT NULL,body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS risk_state(account_key TEXT PRIMARY KEY,body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS commands(account_key TEXT NOT NULL,request_id TEXT NOT NULL,preview_id TEXT NOT NULL,submitted_at INTEGER NOT NULL,body TEXT NOT NULL,PRIMARY KEY(account_key,request_id));
            CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,account_key TEXT NOT NULL,time_ms INTEGER NOT NULL,kind TEXT NOT NULL,body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS journal_preferences(account_key TEXT PRIMARY KEY,body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS coaching(account_key TEXT PRIMARY KEY,body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS record_shares(id TEXT PRIMARY KEY,account_key TEXT NOT NULL,token_hash TEXT NOT NULL UNIQUE,created_at INTEGER NOT NULL,expires_at INTEGER NOT NULL,revoked INTEGER NOT NULL DEFAULT 0,body TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS leaderboard(account_key TEXT PRIMARY KEY,alias TEXT NOT NULL,updated_at INTEGER NOT NULL,body TEXT NOT NULL);
            PRAGMA user_version=2;
            COMMIT;
            ''')
    @contextmanager
    def transaction(self):
        with self.lock:
            self.conn.execute('BEGIN IMMEDIATE')
            try: yield self;self.conn.execute('COMMIT')
            except BaseException: self.conn.execute('ROLLBACK');raise
    def close(self):
        with self.lock:self.conn.close()
    def backup(self,target):
        target=Path(target).expanduser().resolve()
        if target.exists():raise ValueError('Backup destination already exists')
        target.parent.mkdir(parents=True,exist_ok=True)
        with self.lock, sqlite3.connect(str(target)) as destination:self.conn.backup(destination)
    def account(self,key,snapshot):
        with self.lock:self.conn.execute('INSERT INTO accounts VALUES(?,?,?) ON CONFLICT(account_key) DO UPDATE SET snapshot=excluded.snapshot,updated_at=excluded.updated_at',(key,dumps(snapshot),now_ms()))
    def get_json(self,table,key):
        if table not in ('sync_state','risk_state'):raise ValueError('Invalid table')
        with self.lock:
            row=self.conn.execute(f'SELECT {"state" if table=="sync_state" else "body"} FROM {table} WHERE account_key=?',(key,)).fetchone()
            return json.loads(row[0]) if row else None
    def set_json(self,table,key,value):
        if table not in ('sync_state','risk_state'):raise ValueError('Invalid table')
        with self.lock:self.conn.execute(f'INSERT INTO {table} VALUES(?,?) ON CONFLICT(account_key) DO UPDATE SET {"state" if table=="sync_state" else "body"}=excluded.{"state" if table=="sync_state" else "body"}',(key,dumps(value)))
    def policy(self,key):
        with self.lock:
            row=self.conn.execute('SELECT version,body FROM risk_policy WHERE account_key=?',(key,)).fetchone()
            return {'version':row[0],**json.loads(row[1])} if row else None
    def save_policy(self,key,policy,version):
        current=self.policy(key)
        if (current['version'] if current else 0)!=version:raise ValueError('Risk settings changed. Refresh before saving')
        updated=version+1
        self.conn.execute('INSERT INTO risk_policy VALUES(?,?,?) ON CONFLICT(account_key) DO UPDATE SET version=excluded.version,body=excluded.body',(key,updated,dumps(policy)))
        self.audit(key,'risk-policy',{'version':updated,**policy})
        return {'version':updated,**policy}
    def audit(self,key,kind,body):
        with self.lock:self.conn.execute('INSERT INTO audit(account_key,time_ms,kind,body) VALUES(?,?,?,?)',(key,now_ms(),kind,dumps(body)))
    def ingest(self,key,status,deals,start,end,at,mode='terminal'):
        with self.transaction():
            self.account(key,status)
            for d in deals:
                override=self.conn.execute('SELECT kind,reason FROM deal_overrides WHERE account_key=? AND ticket=?',(key,d['ticket'])).fetchone()
                if override:d={**d,'kind':override['kind'],'cashflow':d['net'] if override['kind']=='cash' else 0,'review':0,'classificationReason':override['reason']}
                values=[key]+[d[k] for k in ('ticket','positionId','orderId','time','kind','symbol','side','entry','volume','price','profit','commission','swap','fee','net','balanceDelta','cashflow','review')]+[dumps(d)]
                self.conn.execute('''INSERT INTO deals VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(account_key,ticket) DO UPDATE SET position_id=excluded.position_id,order_id=excluded.order_id,time_ms=excluded.time_ms,kind=excluded.kind,symbol=excluded.symbol,side=excluded.side,entry=excluded.entry,volume=excluded.volume,price=excluded.price,profit=excluded.profit,commission=excluded.commission,swap=excluded.swap,fee=excluded.fee,net=excluded.net,balance_delta=excluded.balance_delta,cashflow=excluded.cashflow,review=excluded.review,raw=excluded.raw''',values)
            previous=self.get_json('sync_state',key) or {}
            continuous=previous.get('through',0)>=start-1000
            self.set_json('sync_state',key,{'from':min(start,previous.get('from',start)) if continuous else start,'through':end,'syncedAt':at,'error':None,'mode':mode,'balance':status['account'].get('balance'),'credit':status['account'].get('credit',0)})
    def fail_sync(self,key,message):
        with self.lock:
            current=self.get_json('sync_state',key) or {}
            self.set_json('sync_state',key,{**current,'error':str(message)[:300]})
    def rows(self,key,start=0,end=2**63-1):
        with self.lock:
            rows=self.conn.execute('SELECT raw FROM deals WHERE account_key=? AND time_ms>=? AND time_ms<=? ORDER BY time_ms,ticket',(key,start,end)).fetchall()
            return [json.loads(r[0]) for r in rows]
    def sums(self,key,start=0,end=2**63-1):
        with self.lock:
            row=self.conn.execute('''SELECT COALESCE(SUM(CASE WHEN kind NOT IN ('cash','credit') THEN net ELSE 0 END),0) AS tradingNet,COALESCE(SUM(cashflow),0) AS cashflow,COALESCE(SUM(balance_delta),0) AS balanceDelta,COALESCE(SUM(review),0) AS review FROM deals WHERE account_key=? AND time_ms>=? AND time_ms<=?''',(key,start,end)).fetchone()
            return dict(row)
    def journal(self,key,start,end,page=0,limit=100):
        with self.lock:
            count=self.conn.execute('SELECT COUNT(*) FROM deals WHERE account_key=? AND time_ms>=? AND time_ms<=?',(key,start,end)).fetchone()[0]
            rows=self.conn.execute('SELECT raw FROM deals WHERE account_key=? AND time_ms>=? AND time_ms<=? ORDER BY time_ms DESC,ticket DESC LIMIT ? OFFSET ?',(key,start,end,limit,page*limit)).fetchall()
            sums=self.conn.execute('''SELECT COALESCE(SUM(CASE WHEN kind NOT IN ('cash','credit') AND review=0 THEN profit ELSE 0 END),0) AS profit,COALESCE(SUM(CASE WHEN review=0 THEN commission ELSE 0 END),0) AS commission,COALESCE(SUM(CASE WHEN review=0 THEN swap ELSE 0 END),0) AS swap,COALESCE(SUM(CASE WHEN review=0 THEN fee ELSE 0 END),0) AS fee,COALESCE(SUM(CASE WHEN kind NOT IN ('cash','credit') AND review=0 THEN net ELSE 0 END),0) AS net,COALESCE(SUM(CASE WHEN review<>0 THEN net ELSE 0 END),0) AS unclassifiedNet,COALESCE(SUM(review),0) AS unclassifiedCount,COALESCE(SUM(cashflow),0) AS cashflow,COALESCE(SUM(CASE WHEN kind='trade' THEN 1 ELSE 0 END),0) AS fills FROM deals WHERE account_key=? AND time_ms>=? AND time_ms<=?''',(key,start,end)).fetchone()
            notes=self.conn.execute('SELECT body FROM notes WHERE account_key=? ORDER BY time_ms DESC LIMIT 200',(key,)).fetchall()
            return {'deals':[json.loads(r[0]) for r in rows],'count':count,'page':page,'limit':limit,'summary':dict(sums),'notes':[json.loads(n[0]) for n in notes],'sync':self.get_json('sync_state',key)}
    def classify(self,key,ticket,kind,reason):
        with self.transaction():
            row=self.conn.execute('SELECT raw FROM deals WHERE account_key=? AND ticket=?',(key,ticket)).fetchone()
            if not row:raise ValueError('History ticket not found in this account')
            d=json.loads(row[0])
            permitted=d['type'] in ((6,) if d['platform']=='MT4' else (2,5,6,13,14)) or d['kind']=='adjustment'
            if not permitted:raise ValueError('Only ambiguous balance/correction entries can be classified')
            d.update(kind=kind,cashflow=d['net'] if kind=='cash' else 0,review=0,classificationReason=reason)
            self.conn.execute('INSERT INTO deal_overrides VALUES(?,?,?,?) ON CONFLICT(account_key,ticket) DO UPDATE SET kind=excluded.kind,reason=excluded.reason',(key,ticket,kind,reason))
            self.conn.execute('UPDATE deals SET kind=?,cashflow=?,review=0,raw=? WHERE account_key=? AND ticket=?',(kind,d['cashflow'],dumps(d),key,ticket))
            self.audit(key,'deal-classification',{'ticket':ticket,'kind':kind,'reason':reason})

    def save_note(self,key,note):
        with self.lock:self.conn.execute('INSERT INTO notes VALUES(?,?,?,?) ON CONFLICT(account_key,id) DO UPDATE SET body=excluded.body',(key,note['id'],note['time'],dumps(note)))
    def delete_note(self,key,ident):
        with self.lock:self.conn.execute('DELETE FROM notes WHERE account_key=? AND id=?',(key,ident))
    def command(self,key,ident):
        with self.lock:
            r=self.conn.execute('SELECT body FROM commands WHERE account_key=? AND request_id=?',(key,ident)).fetchone()
            return json.loads(r[0]) if r else None
    def claim(self,key,body):
        with self.transaction():
            old=self.command(key,body['requestId'])
            if old:return old,False
            self.conn.execute('INSERT INTO commands VALUES(?,?,?,?,?)',(key,body['requestId'],body['previewId'],body['submittedAt'],dumps(body)))
            return body,True
    def save_command(self,key,body):
        with self.lock:self.conn.execute('UPDATE commands SET body=? WHERE account_key=? AND request_id=?',(dumps(body),key,body['requestId']))
    def commands(self,key):
        with self.lock:return [json.loads(r[0]) for r in self.conn.execute('SELECT body FROM commands WHERE account_key=? ORDER BY submitted_at DESC LIMIT 20',(key,))]

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Create a consistent backup of the server ledger (no overwrite)')
    parser.add_argument('database');parser.add_argument('backup');args=parser.parse_args()
    if not Path(args.database).expanduser().is_file():raise SystemExit('The source database does not exist')
    db=LedgerStore(args.database)
    try:db.backup(args.backup);print('Backup created')
    finally:db.close()
