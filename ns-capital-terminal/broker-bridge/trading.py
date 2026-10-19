"""Manual, account-bound execution. Market data and MCP work without enabling this.
Previews do not place orders. Each preview can be committed once; uncertain sends
are never retried automatically. All tests use explicitly labeled fixtures.
"""
from collections import OrderedDict
from decimal import Decimal
import math
import re
import secrets
import threading
import time

IDENTIFIER = re.compile(r'^[a-zA-Z0-9_-]{16,80}$')
SYMBOL = re.compile(r'^[\w#.\-]{1,128}$', re.UNICODE)

def num(value, minimum=0):
    if isinstance(value, bool):
        raise ValueError('Invalid numeric value')
    value = float(value)
    if not math.isfinite(value) or value < minimum:
        raise ValueError('Invalid numeric value')
    return value

def key(status):
    account = status.get('account') or {}
    if not account.get('id') or not account.get('server'):
        raise ValueError('Update the bridge to expose account ID and server')
    return str(account['server']) + '|' + str(account['id'])

def bound(source, expected):
    status = source.status()
    if not status.get('connected') or not expected or key(status) != expected:
        raise ValueError('Trading account changed or disconnected. Reconnect it')
    return status

def on_grid(value, step):
    ratio = Decimal(str(value)) / Decimal(str(step))
    return abs(ratio - ratio.to_integral_value()) <= Decimal('0.000001')

def validate_spec(command, spec, quote, now):
    if not SYMBOL.fullmatch(str(command['symbol'])):
        raise ValueError('Invalid exact broker symbol')
    if now - num(quote['time']) > 10000 or num(quote['time']) > now + 5000:
        raise ValueError('No fresh broker tick. Wait for the market to update')
    bid, ask = num(quote['bid'], 1e-16), num(quote['ask'], 1e-16)
    if ask < bid:
        raise ValueError('Invalid broker spread')
    if command['action'] != 'modify':
        volume, step = num(command['volume'], 1e-16), num(spec['volumeStep'], 1e-16)
        if not num(spec['volumeMin'], 1e-16) <= volume <= num(spec['volumeMax'], 1e-16) or not on_grid(volume, step):
            raise ValueError('Volume must match broker minimum, maximum and step')
    distance = num(spec.get('stopsLevel', 0)) * num(spec['point'], 1e-16)
    if command['action'] != 'close':
        reference = bid if command['side'] == 'buy' else ask
        for field in ('sl', 'tp'):
            level = num(command[field])
            if not level:
                continue
            if not on_grid(level, num(spec['tickSize'], 1e-16)):
                raise ValueError(field.upper() + ' must align with the broker tick size')
            signed = (reference - level) if command['side'] == 'buy' else (level - reference)
            if field == 'tp':
                signed = -signed
            if signed <= 0 or signed + 1e-10 < distance:
                raise ValueError(field.upper() + ' is on the wrong side or too close to the broker price')
    return ask if command['side'] == 'buy' else bid

def command_input(raw, positions):
    if not isinstance(raw, dict) or raw.get('action') not in ('open', 'close', 'modify'):
        raise ValueError('Unsupported trading action')
    action = raw['action']
    command = {'action': action, 'symbol': str(raw.get('symbol', '')), 'side': raw.get('side'), 'volume': num(raw.get('volume', 0)), 'sl': num(raw.get('sl', 0)), 'tp': num(raw.get('tp', 0)), 'deviation': int(num(raw.get('deviation', 20))), 'position': '0'}
    if num(raw.get('deviation', 20)) != command['deviation'] or command['deviation'] > 100:
        raise ValueError('Deviation must be 0..100 broker points')
    if action != 'open':
        ticket = str(raw.get('position', ''))
        position = next((p for p in positions if str(p['ticket']) == ticket), None)
        if not position:
            raise ValueError('Position no longer exists in this account')
        if command['symbol'] and command['symbol'] != position['symbol']:
            raise ValueError('Position symbol does not match')
        command.update(symbol=position['symbol'], position=ticket, volume=position['volume'], side=position['side'] if action == 'modify' else 'sell' if position['side'] == 'buy' else 'buy')
        command['positionVersion'] = '|'.join(str(position.get(k, '')) for k in ('ticket', 'symbol', 'side', 'volume', 'sl', 'tp'))
    if command['side'] not in ('buy', 'sell'):
        raise ValueError('Choose buy or sell')
    return command

class MT5Execution:
    def __init__(self, source):
        self.source, self.mt5 = source, source.mt5

    def permissions(self):
        with self.source.lock:
            terminal, account = self.mt5.terminal_info(), self.mt5.account_info()
        return bool(terminal and account and terminal.trade_allowed and not getattr(terminal, 'tradeapi_disabled', True) and account.trade_allowed and account.trade_expert)

    def positions(self):
        with self.source.lock:
            rows = self.mt5.positions_get()
        if rows is None:
            raise RuntimeError('Cannot read positions from the terminal')
        return [{'ticket': str(p.ticket), 'symbol': p.symbol, 'side': 'buy' if p.type == 0 else 'sell', 'volume': float(p.volume), 'entry': float(p.price_open), 'price': float(p.price_current), 'sl': float(p.sl), 'tp': float(p.tp), 'profit': float(p.profit), 'swap': float(p.swap), 'time': int(p.time) * 1000} for p in rows]

    def prepare(self, raw, expected, now):
        status = bound(self.source, expected)
        if not self.permissions():
            raise ValueError('Trading is disabled in the terminal or account. Check Algo Trading and Python API permissions')
        command = command_input(raw, self.positions())
        with self.source.lock:
            self.source.select(command['symbol'])
            s = self.mt5.symbol_info(command['symbol'])
            if s is None:
                raise ValueError('Symbol is unavailable')
            spec = {'volumeMin': float(s.volume_min), 'volumeMax': float(s.volume_max), 'volumeStep': float(s.volume_step), 'tickSize': float(s.trade_tick_size or s.point), 'point': float(s.point), 'stopsLevel': int(s.trade_stops_level)}
            if command['action'] == 'open' and (s.trade_mode not in (1, 2, 4) or s.trade_mode == 1 and command['side'] != 'buy' or s.trade_mode == 2 and command['side'] != 'sell'):
                raise ValueError('The broker does not allow this side on this symbol')
            quote = self.source.quote(command['symbol'])
            command['price'] = validate_spec(command, spec, quote, now)
            if command['action'] == 'modify':
                request = {'action': self.mt5.TRADE_ACTION_SLTP, 'symbol': command['symbol'], 'position': int(command['position']), 'sl': command['sl'], 'tp': command['tp']}
            else:
                filling = self.mt5.ORDER_FILLING_IOC if s.filling_mode & 2 else self.mt5.ORDER_FILLING_FOK if s.filling_mode & 1 else self.mt5.ORDER_FILLING_RETURN if s.trade_exemode != 2 else None
                if filling is None:
                    raise ValueError('No supported fill policy for this broker symbol')
                request = {'action': self.mt5.TRADE_ACTION_DEAL, 'symbol': command['symbol'], 'volume': command['volume'], 'type': self.mt5.ORDER_TYPE_BUY if command['side'] == 'buy' else self.mt5.ORDER_TYPE_SELL, 'deviation': command['deviation'], 'magic': 260019, 'comment': 'NS Capital manual', 'type_time': self.mt5.ORDER_TIME_GTC, 'type_filling': filling}
                if s.trade_exemode != 2:
                    request['price'] = command['price']
                if command['action'] == 'close':
                    request['position'] = int(command['position'])
                else:
                    request.update(sl=command['sl'], tp=command['tp'])
            check = self.mt5.order_check(request)
            if check is None or check.retcode != 0:
                raise ValueError('Broker order check rejected: ' + str(getattr(check, 'comment', 'No response')))
        command.update(spec=spec, accountKey=expected, positionMode=status.get('account', {}).get('positionMode', 'unknown'))
        return command, request

    def execute(self, prepared, expected, request_id, now):
        with self.source.lock:
            fresh, request = self.prepare(prepared, expected, now)
            if fresh.get('positionVersion') != prepared.get('positionVersion'):
                raise ValueError('The position changed. Review a new request')
            tolerance = prepared['deviation'] * prepared['spec']['point']
            if prepared['action'] != 'modify' and abs(fresh['price'] - prepared['price']) > tolerance + 1e-10:
                raise ValueError('Price moved beyond the reviewed deviation. Review again')
            bound(self.source, expected)
            try:
                result = self.mt5.order_send(request)
            except Exception:
                return {'status':'unknown', 'message':'Execution transport failed. Check terminal positions/history before another action'}
        if result is None:
            return {'status': 'unknown', 'message': 'No execution response. Check terminal positions/history before taking another action'}
        try:
            retcode = int(result.retcode)
            status = 'filled' if retcode == 10009 else 'partial' if retcode == 10010 else 'accepted' if retcode == 10008 else 'unknown' if retcode in (10012, 10031) else 'rejected'
            return {'status': status, 'retcode': retcode, 'message': str(result.comment), 'order': str(result.order), 'deal': str(result.deal), 'volume': float(result.volume), 'price': float(result.price)}
        except Exception:
            return {'status':'unknown', 'message':'Invalid execution receipt. Check terminal positions/history before another action'}


class MT4Execution:
    def __init__(self, source):
        self.source = source

    def permissions(self):
        return self.source.trade_allowed

    def positions(self):
        with self.source.condition:
            if time.monotonic() - self.source.positions_at > 15:
                raise RuntimeError('Waiting for a fresh MT4 account snapshot. Update and attach the EA')
            return [dict(p) for p in self.source.positions_snapshot]

    def prepare(self, raw, expected, now):
        bound(self.source, expected)
        if not self.permissions():
            raise ValueError('EnableTrading and Allow live trading must be enabled in the MT4 EA')
        command = command_input(raw, self.positions())
        spec = next((s for s in self.source.symbols() if s['ticker'] == command['symbol']), None)
        if not spec:
            raise ValueError('Symbol not available in the MT4 catalog')
        command['price'] = validate_spec(command, spec, self.source.quote(command['symbol']), now)
        command.update(spec={k: spec[k] for k in ('volumeMin', 'volumeMax', 'volumeStep', 'point', 'tickSize')}, accountKey=expected, positionMode='hedging')
        return command, None

    def execute(self, prepared, expected, request_id, now):
        fresh, _ = self.prepare(prepared, expected, now)
        if fresh.get('positionVersion') != prepared.get('positionVersion'):
            raise ValueError('The position changed. Review again')
        if prepared['action'] != 'modify' and abs(fresh['price'] - prepared['price']) > prepared['deviation'] * prepared['spec']['point'] + 1e-10:
            raise ValueError('Price moved beyond the reviewed deviation. Review again')
        account = self.source.status()['account']
        if any('|' in str(account[k]) or '\n' in str(account[k]) for k in ('id', 'server')):
            raise ValueError('Unsupported account identifier')
        with self.source.condition:
            self.source.trade_queue[request_id] = {**prepared, 'requestId': request_id, 'expiresAt': now + 15000, 'accountId': account['id'], 'server': account['server']}
        return {'status': 'pending', 'message': 'Waiting for the MT4 EA. Do not resend this request'}

class TradingService:
    def __init__(self, source, enabled=False, now=None, journal=None):
        self.source, self.enabled = source, bool(enabled)
        self.now = now or (lambda: int(time.time() * 1000))
        self.executor = MT5Execution(source) if hasattr(source, 'mt5') else MT4Execution(source)
        self.lock, self.previews, self.receipts = threading.RLock(), OrderedDict(), OrderedDict()
        self.journal=journal;self.store=journal.store if journal else None
        if journal:
            from risk import RiskEngine
            self.risk=RiskEngine(source,journal,self.executor,now=self.now)
        else:self.risk=None

    def capability(self):
        try:
            allowed = bool(self.enabled and self.executor.permissions())
        except (AttributeError, RuntimeError):
            allowed = False
        return {'supported': True, 'enabled': self.enabled, 'allowed': allowed, 'actions': ['open', 'close', 'modify'], 'mode': 'manual', 'riskRequired':self.risk is not None}

    def state(self, expected):
        status = bound(self.source, expected)
        positions = self.executor.positions()
        bound(self.source, expected)
        return {'accountKey': expected, 'account': status['account'], 'broker': status['broker'], 'platform': status['platform'], 'trading': self.capability(), 'positions': positions, 'risk':self.risk.snapshot(expected) if self.risk else None, 'receipts':self.store.commands(self.journal.dbkey(expected)) if self.store else [], 'updatedAt': self.now()}

    def preview(self, raw):
        if not self.enabled:
            raise ValueError('Start the bridge with --enable-trading to enable manual orders')
        expected = raw.get('accountKey')
        with self.lock:
            command, _ = self.executor.prepare(raw, expected, self.now())
            if self.risk:command['risk']=self.risk.check(command,expected)
            bound(self.source, expected)
            preview_id = secrets.token_urlsafe(24)
            preview = {**command, 'previewId': preview_id, 'expiresAt': self.now() + 30000, 'usedBy': None}
            self.previews[preview_id] = preview
            # Never evict an unexpired preview/receipt to make room for a duplicate.
            for ident, old in list(self.previews.items()):
                if old['expiresAt'] < self.now() - 60000:
                    del self.previews[ident]
            if len(self.previews) > 1000:
                del self.previews[preview_id]
                raise ValueError('Too many pending requests')
            return {**command, 'previewId': preview_id, 'expiresAt': preview['expiresAt']}

    def execute(self, raw):
        request_id, preview_id, expected = raw.get('requestId'), raw.get('previewId'), raw.get('accountKey')
        if not isinstance(request_id, str) or not IDENTIFIER.fullmatch(request_id):
            raise ValueError('A valid unique requestId is required')
        with self.lock:
            if self.store:
                stored=self.store.command(self.journal.dbkey(expected),request_id)
                if stored:
                    if stored['previewId']!=preview_id or stored['accountKey']!=expected:raise ValueError('requestId is already bound to another request')
                    self.receipts[request_id]=stored
                    return self.receipt(request_id,expected)
            if request_id in self.receipts:
                receipt = self.receipts[request_id]
                if receipt['previewId'] != preview_id or receipt['accountKey'] != expected:
                    raise ValueError('requestId is already bound to another request')
                return self.receipt(request_id, expected)
            preview = self.previews.get(preview_id)
            if not self.enabled or not preview or preview['accountKey'] != expected or preview['expiresAt'] < self.now():
                raise ValueError('Preview expired or account changed. Review a new request')
            if preview['usedBy']:
                raise ValueError('This preview has already been submitted')
            bound(self.source, expected)
            if len(self.receipts) >= 10000:
                raise ValueError('Session request limit reached. Check all outstanding receipts before restarting the bridge')
            preview['usedBy'] = request_id
            self.receipts[request_id] = {'requestId': request_id, 'previewId': preview_id, 'accountKey': expected, 'status': 'pending', 'submittedAt': self.now(), 'message': 'Submitted; check receipt, do not send again'}
            if self.store:
                stored,claimed=self.store.claim(self.journal.dbkey(expected),self.receipts[request_id])
                if not claimed:
                    if stored['previewId']!=preview_id:raise ValueError('requestId is already bound to another preview')
                    self.receipts[request_id]=stored
                    return dict(stored)
            attempted=False
            try:
                if self.risk:
                    checked=self.risk.check(preview,expected)
                    if checked.get('policyVersion')!=preview.get('risk',{}).get('policyVersion'):raise ValueError('Risk policy changed. Review a new request')
                attempted=True
                result = self.executor.execute(preview, expected, request_id, self.now())
            except ValueError as error:
                result = {'status': 'rejected', 'message': str(error)}
            except Exception:
                result = {'status': 'unknown' if attempted else 'rejected', 'message': 'Execution outcome unavailable. Check the terminal before taking another action' if attempted else 'Risk/history check unavailable. No execution was attempted'}
            self.receipts[request_id].update(result)
            if self.store:self.store.save_command(self.journal.dbkey(expected),self.receipts[request_id])
            return dict(self.receipts[request_id])

    def receipt(self, request_id, expected):
        with self.lock:
            result = self.receipts.get(request_id)
            if result is None and self.store:result=self.store.command(self.journal.dbkey(expected),request_id)
            if not result or result['accountKey'] != expected:
                raise ValueError('Unknown request for this account')
            if isinstance(self.executor, MT4Execution) and result['status'] == 'pending':
                with self.source.condition:
                    update = self.source.trade_results.get(request_id)
                    if update:
                        result.update(update)
                    elif self.now() - result['submittedAt'] > 30000:
                        self.source.trade_queue.pop(request_id, None)
                        result.update(status='unknown', message='MT4 receipt unavailable. Check terminal positions/history before another action')
            if result['status']=='pending' and self.now()-result['submittedAt']>120000:result.update(status='unknown',message='No durable completion receipt. Inspect terminal history; never resend this request')
            if self.store:self.store.save_command(self.journal.dbkey(expected),result)
            return dict(result)
