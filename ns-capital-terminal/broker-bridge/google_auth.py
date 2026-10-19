"""Google identity verification and short-lived, terminal-bound read sessions.

Google credentials and bearer secrets are never persisted or logged. Trading
still requires the independent Trade token and all existing backend risk gates.
"""
from collections import OrderedDict
from hashlib import sha256
import hmac
import importlib.util
import os
import re
import secrets
import threading
import time


def verify_google_token(credential, audience):
    from google.oauth2 import id_token
    import requests
    from google.auth.transport.requests import Request
    class BoundedRequest(Request):
        def __call__(self, *args, **kwargs):
            kwargs['timeout'] = 8
            return super().__call__(*args, **kwargs)
    with requests.Session() as session:
        return id_token.verify_oauth2_token(credential, BoundedRequest(session=session), audience)


def dependency_ready():
    try:
        return bool(importlib.util.find_spec('google.oauth2.id_token') and importlib.util.find_spec('requests'))
    except (ImportError, ModuleNotFoundError):
        return False


class GoogleLogin:
    def __init__(self, source, client_id=None, emails=None, subjects=None, verify=None, now=None):
        self.source = source
        self.client_id = (client_id if client_id is not None else os.getenv('NS_GOOGLE_CLIENT_ID', '')).strip()
        self.emails = {v.strip().lower() for v in (emails if emails is not None else os.getenv('NS_GOOGLE_ALLOWED_EMAILS', '')).split(',') if v.strip()}
        self.subjects = {v.strip() for v in (subjects if subjects is not None else os.getenv('NS_GOOGLE_ALLOWED_SUBS', '')).split(',') if v.strip()}
        if self.client_id and not re.fullmatch(r'[A-Za-z0-9_-]+\.apps\.googleusercontent\.com', self.client_id):
            raise ValueError('NS_GOOGLE_CLIENT_ID must be a Google Web OAuth client ID')
        self.verify = verify or verify_google_token
        self.ready = verify is not None or dependency_ready()
        self.now = now or time.time
        self.lock = threading.RLock()
        self.challenges = OrderedDict(); self.sessions = OrderedDict(); self.rates = OrderedDict()

    def config(self):
        configured = bool(self.client_id and (self.emails or self.subjects))
        return {'provider': 'google', 'configured': configured, 'enabled': configured and self.ready, 'clientId': self.client_id if configured else '', 'sessionSeconds': 1800, 'error': '' if configured and self.ready else 'Set NS_GOOGLE_CLIENT_ID and an owner allowlist on the Bridge; install requirements-google.txt'}

    def account(self):
        status = self.source.status(); account = status.get('account') or {}
        if not status.get('connected') or not account.get('server') or not account.get('id'):
            raise ValueError('Connect the intended broker terminal before Google sign-in')
        return str(status['platform'])+'|'+str(account['server'])+'|'+str(account['id'])

    def limit(self, address):
        at = self.now()
        with self.lock:
            previous = [v for v in self.rates.get(address, []) if v > at-300]
            if len(previous) >= 20: raise ValueError('Too many sign-in attempts; wait five minutes')
            self.rates[address] = previous+[at]; self.rates.move_to_end(address)
            while len(self.rates) > 256: self.rates.popitem(last=False)

    def challenge(self, origin, address):
        self.limit(address)
        if not self.config()['enabled']: raise ValueError(self.config()['error'])
        account = self.account(); at = self.now(); ident = secrets.token_urlsafe(24); nonce = secrets.token_urlsafe(32)
        with self.lock:
            self.challenges[ident] = {'nonce': nonce, 'origin': origin, 'account': account, 'expires': at+300}
            while len(self.challenges) > 64: self.challenges.popitem(last=False)
        return {'challengeId': ident, 'nonce': nonce, 'expiresAt': int((at+300)*1000)}

    def login(self, raw, origin, address):
        self.limit(address)
        if not self.config()['enabled']: raise ValueError(self.config()['error'])
        ident = raw.get('challengeId'); credential = raw.get('credential')
        if not isinstance(ident, str) or not isinstance(credential, str) or not 20 <= len(credential) <= 16000:
            raise ValueError('Invalid Google sign-in response')
        with self.lock: challenge = self.challenges.pop(ident, None)
        account = self.account(); at = self.now()
        if not challenge or challenge['expires'] <= at or challenge['origin'] != origin or challenge['account'] != account:
            raise ValueError('Sign-in challenge expired or account changed; try again')
        try: claims = self.verify(credential, self.client_id)
        except Exception: raise ValueError('Google ID token verification failed') from None
        if not isinstance(claims, dict) or claims.get('iss') not in ('accounts.google.com', 'https://accounts.google.com') or claims.get('aud') != self.client_id or claims.get('azp', self.client_id) != self.client_id or claims.get('email_verified') is not True or not isinstance(claims.get('sub'), str):
            raise ValueError('Google identity claims are invalid')
        expiry = claims.get('exp'); issued = claims.get('iat', at)
        if isinstance(expiry, bool) or not isinstance(expiry, (int, float)) or not at < expiry <= at+86400 or not isinstance(issued, (int, float)) or issued > at+30 or not hmac.compare_digest(str(claims.get('nonce', '')), challenge['nonce']):
            raise ValueError('Google token expired or nonce did not match')
        subject = claims['sub']; email = str(claims.get('email', '')).lower()
        # For a non-Google-hosted email use a stable sub allowlist instead.
        hosted_email = email.endswith('@gmail.com') or bool(claims.get('hd'))
        if subject not in self.subjects and not (hosted_email and email in self.emails):
            raise ValueError('This Google account is not allowed to access this Bridge')
        if self.account() != account: raise ValueError('Broker account changed during Google sign-in')
        token = secrets.token_urlsafe(32); hashed = sha256(token.encode()).hexdigest(); expires = min(at+1800, expiry)
        user = {'provider': 'google', 'subject': subject, 'email': email[:254], 'name': str(claims.get('name') or email or 'Google user')[:120]}
        with self.lock:
            for key, value in list(self.sessions.items()):
                if value['expires'] <= at: self.sessions.pop(key, None)
            self.sessions[hashed] = {'account': account, 'origin': origin, 'expires': expires, 'user': user}
            same = [k for k,v in self.sessions.items() if v['user']['subject'] == subject]
            for older in same[:-4]: self.sessions.pop(older, None)
            while len(self.sessions) > 16: self.sessions.popitem(last=False)
        return {'token': token, 'expiresAt': int(expires*1000), 'user': user, 'accountKey': account.split('|', 1)[1]}

    def session(self, token, origin):
        if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token): return None
        hashed = sha256(token.encode()).hexdigest()
        with self.lock: item = self.sessions.get(hashed)
        if not item: return None
        try: account = self.account()
        except Exception: return None
        if item['expires'] <= self.now() or item['origin'] != origin or item['account'] != account:
            with self.lock: self.sessions.pop(hashed, None)
            return None
        return {'user': item['user'], 'expiresAt': int(item['expires']*1000)}

    def logout(self, token):
        with self.lock: self.sessions.pop(sha256(token.encode()).hexdigest(), None)
