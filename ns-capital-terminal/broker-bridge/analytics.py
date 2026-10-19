"""Trade-cycle statistics and opt-in reports from the server ledger only."""
from collections import defaultdict
from decimal import Decimal
from hashlib import sha256
import json
import re
import secrets
from database import dumps, number, total
from journal import DAY

EPS = Decimal('0.00000001')


def trade_cycles(rows):
    """MT5 flat-to-flat cycles; MT4 closed tickets (partials remain separate).

    Never infer an opening balance or a missing entry. Incomplete cycles stay
    outside win-rate statistics. INOUT costs are split by closed/opened volume.
    Standalone account charges are reported separately, not assigned by guess.
    """
    active = {}; closed = []; excluded = 0; openings = []; other_costs = []
    for d in sorted(rows, key=lambda r: (r['time'], int(r['ticket']))):
        if d.get('review') or d['kind'] in ('cash', 'credit'):
            continue
        if d['kind'] != 'trade':
            other_costs.append(d['net']); continue
        volume = Decimal(str(d['volume']))
        if volume <= 0 or d['side'] not in ('buy', 'sell'):
            excluded += 1; continue
        if d['platform'] == 'MT4':
            opened = d.get('openedAt')
            if opened:
                openings.append({'time': opened, 'symbol': d['symbol'], 'volume': float(volume), 'ticket': d['ticket'], 'order': d['orderId']})
            closed.append({'id': d['positionId']+':'+d['ticket'], 'positionId': d['positionId'], 'symbol': d['symbol'], 'side': d['side'], 'openedAt': opened, 'closedAt': d['time'], 'volume': float(volume), 'net': d['net'], 'commission': d['commission'], 'swap': d['swap'], 'fee': d['fee'], 'tickets': [d['ticket']], 'basis': 'closed-ticket'})
            continue
        position = d['positionId']; entry = d['entry']; sign = 1 if d['side'] == 'buy' else -1
        if position == '0':
            excluded += 1; continue
        c = active.get(position)
        if entry == 0:
            openings.append({'time': d['time'], 'symbol': d['symbol'], 'volume': float(volume), 'ticket': d['ticket'], 'order': d['orderId']})
            if c is not None and not c['valid']:
                excluded += 1; continue
            if c is None:
                c = {'id': position+':'+d['ticket'], 'positionId': position, 'symbol': d['symbol'], 'side': d['side'], 'openedAt': d['time'], 'sign': sign, 'remaining': Decimal(0), 'volume': Decimal(0), 'net': [], 'commission': [], 'swap': [], 'fee': [], 'tickets': [], 'valid': True}
                active[position] = c
            if c['sign'] != sign or c['symbol'] != d['symbol']:
                c['valid'] = False; excluded += 1
            c['remaining'] += volume; c['volume'] += volume
            for name in ('net', 'commission', 'swap', 'fee'): c[name].append(d[name])
            c['tickets'].append(d['ticket'])
            continue
        if entry not in (1, 2, 3) or c is None:
            excluded += 1
            # A missing opening or reversal cannot be reconstructed from profit.
            active[position] = {'valid': False, 'sign': -sign, 'remaining': Decimal('Infinity'), 'symbol': d['symbol']}
            continue
        if not c['valid']:
            excluded += 1; continue
        old = c['remaining']
        if c['sign'] == sign or c['symbol'] != d['symbol'] or (entry != 2 and volume > old+EPS) or (entry == 2 and volume <= old+EPS):
            c['valid'] = False; excluded += 1; continue
        close_volume = min(volume, old); ratio = float(close_volume/volume)
        costs = total([d['commission'], d['fee']])
        close_net = total([d['profit'], d['swap'], costs*ratio]) if entry == 2 else d['net']
        c['net'].append(close_net); c['commission'].append(d['commission']*ratio); c['fee'].append(d['fee']*ratio); c['swap'].append(d['swap']); c['tickets'].append(d['ticket'])
        c['remaining'] -= close_volume
        if c['remaining'] <= EPS:
            closed.append({k: v for k, v in c.items() if k not in ('sign', 'remaining', 'valid', 'net', 'commission', 'swap', 'fee', 'volume')} | {name: total(c[name]) for name in ('net', 'commission', 'swap', 'fee')} | {'volume': float(c['volume']), 'closedAt': d['time'], 'basis': 'flat-to-flat'})
            del active[position]
        if entry == 2:
            residual = volume-old
            openings.append({'time': d['time'], 'symbol': d['symbol'], 'volume': float(residual), 'ticket': d['ticket'], 'order': d['orderId']})
            active[position] = {'id': position+':'+d['ticket'], 'positionId': position, 'symbol': d['symbol'], 'side': d['side'], 'openedAt': d['time'], 'sign': sign, 'remaining': residual, 'volume': residual, 'net': [costs*(1-ratio)], 'commission': [d['commission']*(1-ratio)], 'swap': [0], 'fee': [d['fee']*(1-ratio)], 'tickets': [d['ticket']], 'valid': True}
    return closed, openings, excluded, sum(c['valid'] for c in active.values()), total(other_costs)


def behavior_flags(openings, cycles, settings, start, end):
    if not settings.get('enabled'): return []
    flags = []; counts = defaultdict(list); orders = {}
    for entry in sorted(openings, key=lambda e: (e['time'], int(e['ticket']))):
        order = entry['order'] if entry['order'] != '0' else entry['ticket']
        dedup = (entry['symbol'], order)
        if dedup not in orders: orders[dedup] = dict(entry)
        else: orders[dedup]['volume'] = total([orders[dedup]['volume'], entry['volume']])
    for entry in orders.values():
        if not start <= entry['time'] <= end: continue
        day = entry['time']//DAY; counts[day].append(entry)
        previous = [c for c in cycles if c['net'] < 0 and c['symbol'] == entry['symbol'] and 0 < entry['time']-c['closedAt'] <= settings['cooldownMinutes']*60000]
        if previous:
            loss = max(previous, key=lambda c: c['closedAt'])
            if entry['volume'] >= loss['volume']*settings['sizeIncreaseFactor']:
                flags.append({'kind': 'rapid-size-increase', 'time': entry['time'], 'symbol': entry['symbol'], 'ticket': entry['ticket'], 'previousTrade': loss['id'], 'minutesAfterLoss': round((entry['time']-loss['closedAt'])/60000, 1), 'sizeRatio': round(entry['volume']/loss['volume'], 2)})
    for day, entries in counts.items():
        if len(entries) > settings['maxEntriesDay']:
            flags.append({'kind': 'entry-limit', 'time': entries[-1]['time'], 'dayUtc': day, 'count': len(entries), 'limit': settings['maxEntriesDay']})
    return sorted(flags, key=lambda f: f['time'], reverse=True)[:100]


class JournalAnalytics:
    def __init__(self, journal): self.journal = journal; self.store = journal.store

    def preference(self, key):
        with self.store.lock:
            row = self.store.conn.execute('SELECT body FROM journal_preferences WHERE account_key=?', (key,)).fetchone()
            return json.loads(row[0]) if row else {'enabled': False}

    def save_preferences(self, raw):
        expected = raw.get('accountKey'); key = self.journal.dbkey(expected)
        if not isinstance(raw.get('enabled'), bool): raise ValueError('Choose whether to enable behavior observations')
        settings = {'enabled': raw['enabled']}
        for name, lo, hi in (('maxEntriesDay', 1, 1000), ('cooldownMinutes', 1, 1440), ('sizeIncreaseFactor', 1.01, 20)):
            value = number(raw.get(name))
            if not lo <= value <= hi or name != 'sizeIncreaseFactor' and value != int(value): raise ValueError('Invalid behavior threshold')
            settings[name] = value
        with self.store.transaction():
            self.store.conn.execute('INSERT INTO journal_preferences VALUES(?,?) ON CONFLICT(account_key) DO UPDATE SET body=excluded.body', (key, dumps(settings)))
            self.store.audit(key, 'behavior-settings', settings)
        return {'accountKey': expected, 'settings': settings}

    def snapshot(self, expected, days=90):
        if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 3650: raise ValueError('Invalid analytics range')
        status = self.journal.status(expected, False); key = self.journal.dbkey(expected); end = self.journal.now(); start = end-days*DAY
        with self.store.lock:
            rows = self.store.rows(key, end=end); sync = self.store.get_json('sync_state', key)
            notes = [json.loads(r[0]) for r in self.store.conn.execute('SELECT body FROM notes WHERE account_key=? ORDER BY time_ms', (key,))]
            saved = self.store.conn.execute('SELECT body FROM coaching WHERE account_key=?', (key,)).fetchone()
        cycles, openings, excluded, opened, _ = trade_cycles(rows)
        selected = [c for c in cycles if start <= c['closedAt'] <= end]
        wins = [c['net'] for c in selected if c['net'] > 1e-8]; losses = [c['net'] for c in selected if c['net'] < -1e-8]
        cumulative = 0.; peak = 0.; drawdown = 0.; days_net = defaultdict(list); unattached = []
        for d in rows:
            if start <= d['time'] <= end and not d['review'] and d['kind'] not in ('cash', 'credit'):
                days_net[d['time']//DAY].append(d['net'])
                if d['kind'] != 'trade': unattached.append(d['net'])
        curve = []
        for day in sorted(days_net):
            pnl = total(days_net[day]); cumulative = total([cumulative, pnl]); peak = max(peak, cumulative); drawdown = max(drawdown, peak-cumulative)
            curve.append({'time': day*DAY, 'net': pnl, 'cumulative': cumulative})
        groups = defaultdict(list); position_counts = defaultdict(int)
        for c in cycles: position_counts[c['positionId']] += 1
        for c in selected:
            linked = [n for n in notes if n.get('positionId') == c['positionId'] and (position_counts[c['positionId']] == 1 or c['openedAt'] <= n['time'] <= c['closedAt'])]
            setup = linked[-1]['setup'] if linked else 'Unassigned'
            c['setup'] = setup; groups[(c['symbol'], setup)].append(c)
        breakdown = [{'symbol': s, 'setup': p, 'trades': len(cs), 'net': total(c['net'] for c in cs), 'winRate': sum(c['net'] > 1e-8 for c in cs)/len(cs)*100} for (s, p), cs in groups.items()]
        settings = self.preference(key)
        result = {'accountKey': expected, 'currency': status['account']['currency'], 'platform': status['platform'], 'from': start, 'through': end, 'sync': sync, 'settings': settings, 'closedTrades': len(selected), 'wins': len(wins), 'losses': len(losses), 'breakeven': len(selected)-len(wins)-len(losses), 'winRate': len(wins)/len(selected)*100 if selected else None, 'profitFactor': total(wins)/abs(total(losses)) if losses else None, 'noLosses': bool(wins) and not losses, 'closedNet': total(c['net'] for c in selected), 'bookedNet': cumulative, 'unattributedCosts': total(unattached), 'maxBookedDrawdown': drawdown, 'openCycles': opened, 'excludedRecords': excluded, 'pendingClassification': sum(bool(d['review']) for d in rows if start <= d['time'] <= end), 'completeRange': bool(sync and not sync.get('error') and sync.get('from', end) <= start+60000 and sync.get('through', 0) >= end-90000), 'basis': 'MT4 closed tickets; partial closes count separately' if status['platform'] == 'MT4' else 'MT5 complete flat-to-flat cycles', 'curve': curve, 'breakdown': sorted(breakdown, key=lambda r: -r['trades'])[:100], 'recentTrades': sorted(selected, key=lambda c: -c['closedAt'])[:100], 'flags': behavior_flags(openings, cycles, settings, start, end), 'coaching': json.loads(saved[0]) if saved else None}
        self.journal.status(expected, False)
        return result

    def save_coaching(self, expected, report):
        key = self.journal.dbkey(expected)
        with self.store.lock:
            self.store.conn.execute('INSERT INTO coaching VALUES(?,?) ON CONFLICT(account_key) DO UPDATE SET body=excluded.body', (key, dumps(report)))

    def report_data(self, expected, days):
        self.journal.status(expected)
        data = self.snapshot(expected, days)
        if not data['closedTrades'] or data['pendingClassification'] or data['excludedRecords'] or not data['completeRange']:
            raise ValueError('A complete recent range with closed trades and no unclassified rows is required')
        fields = ('platform', 'currency', 'from', 'through', 'closedTrades', 'wins', 'losses', 'breakeven', 'winRate', 'profitFactor', 'noLosses', 'closedNet', 'bookedNet', 'unattributedCosts', 'maxBookedDrawdown', 'basis', 'curve')
        return {k: data[k] for k in fields} | {'source': 'NS Capital terminal bridge snapshot', 'independentlyVerified': False, 'live': False}

    def create_share(self, raw):
        expected = raw.get('accountKey'); key = self.journal.dbkey(expected)
        if raw.get('consent') is not True: raise ValueError('Confirm sharing aggregate statistics')
        days = raw.get('days', 30); ttl = raw.get('expiresDays', 7)
        if isinstance(ttl, bool) or not isinstance(ttl, int) or not 1 <= ttl <= 30: raise ValueError('Report expiry must be 1..30 days')
        body = self.report_data(expected, days); token = secrets.token_urlsafe(32); ident = secrets.token_hex(12); at = self.journal.now(); expires = at+ttl*DAY
        with self.store.transaction():
            self.store.conn.execute('INSERT INTO record_shares VALUES(?,?,?,?,?,0,?)', (ident, key, sha256(token.encode()).hexdigest(), at, expires, dumps(body)))
            self.store.audit(key, 'track-record-created', {'id': ident, 'expiresAt': expires})
        return {'accountKey': expected, 'id': ident, 'token': token, 'expiresAt': expires}

    def shares(self, expected):
        key = self.journal.dbkey(expected)
        with self.store.lock:
            rows = self.store.conn.execute('SELECT id,created_at,expires_at,revoked FROM record_shares WHERE account_key=? ORDER BY created_at DESC LIMIT 50', (key,)).fetchall()
        return {'accountKey': expected, 'shares': [{'id': r[0], 'createdAt': r[1], 'expiresAt': r[2], 'revoked': bool(r[3])} for r in rows]}

    def revoke_share(self, raw):
        key = self.journal.dbkey(raw.get('accountKey')); ident = raw.get('id')
        if not isinstance(ident, str) or not re.fullmatch(r'[a-f0-9]{24}', ident): raise ValueError('Invalid report ID')
        with self.store.transaction():
            self.store.conn.execute('UPDATE record_shares SET revoked=1 WHERE id=? AND account_key=?', (ident, key))
            self.store.audit(key, 'track-record-revoked', {'id': ident})
        return {'accountKey': raw['accountKey'], 'ok': True}

    def shared(self, token):
        if not re.fullmatch(r'[A-Za-z0-9_-]{43}', token): raise ValueError('Report is unavailable or expired')
        with self.store.lock:
            r = self.store.conn.execute('SELECT body,created_at,expires_at FROM record_shares WHERE token_hash=? AND revoked=0 AND expires_at>?', (sha256(token.encode()).hexdigest(), self.journal.now())).fetchone()
        if not r: raise ValueError('Report is unavailable or expired')
        return {'report': json.loads(r[0]), 'createdAt': r[1], 'expiresAt': r[2]}

    def publish_rank(self, raw):
        expected = raw.get('accountKey'); key = self.journal.dbkey(expected)
        if raw.get('consent') is False:
            with self.store.lock: self.store.conn.execute('DELETE FROM leaderboard WHERE account_key=?', (key,))
            return {'accountKey': expected, 'ok': True}
        alias = raw.get('alias')
        if raw.get('consent') is not True or not isinstance(alias, str) or not 2 <= len(alias.strip()) <= 40: raise ValueError('Choose an alias and explicitly opt in')
        body = self.report_data(expected, 30)
        if body['closedTrades'] < 20 or body['profitFactor'] is None: raise ValueError('Ranking requires at least 20 complete closed trades and a realized loss in the last 30 days')
        with self.store.transaction():
            self.store.conn.execute('INSERT INTO leaderboard VALUES(?,?,?,?) ON CONFLICT(account_key) DO UPDATE SET alias=excluded.alias,updated_at=excluded.updated_at,body=excluded.body', (key, alias.strip(), self.journal.now(), dumps(body)))
            self.store.audit(key, 'leaderboard-opt-in', {'alias': alias.strip()})
        return {'accountKey': expected, 'ok': True}

    def rankings(self, expected):
        key = self.journal.dbkey(expected); now = self.journal.now()
        with self.store.lock:
            rows = self.store.conn.execute('SELECT account_key,alias,updated_at,body FROM leaderboard WHERE updated_at>?', (now-DAY,)).fetchall()
        entries = []
        for r in rows:
            d = json.loads(r[3]); entries.append({'alias': r[1], 'updatedAt': r[2], 'mine': r[0] == key, **{f: d[f] for f in ('profitFactor', 'winRate', 'closedTrades', 'from', 'through')}})
        entries.sort(key=lambda r: (-r['profitFactor'], -r['closedTrades'], r['updatedAt']))
        return {'accountKey': expected, 'scope': 'This bridge only; explicit opt-in; snapshots expire after 24 hours', 'metric': '30-day profit factor, after linked deal costs', 'entries': entries[:100]}
