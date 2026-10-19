"""Google claim/session and HTTP boundaries using explicit fake credentials."""
import copy
import http.client
import json
from pathlib import Path
import sys
import threading
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'broker-bridge'))
from google_auth import GoogleLogin
from bridge import make_handler,ThreadingHTTPServer
from test_trading import fixture,TOKEN,TRADE

CLIENT='123456789-fixture.apps.googleusercontent.com'
ORIGIN='https://fixture.site'
CREDENTIAL='fixture-google-credential-not-a-real-jwt'


class GoogleAuthTests(unittest.TestCase):
    def setUp(self):
        self.m,self.source,_=fixture();self.clock=time.time();self.claims={};self.calls=[]
        def verify(credential,audience):self.calls.append((credential,audience));return copy.deepcopy(self.claims)
        self.auth=GoogleLogin(self.source,client_id=CLIENT,emails='owner.fixture@gmail.com',verify=verify,now=lambda:self.clock)
    def challenge(self):
        c=self.auth.challenge(ORIGIN,'fixture-ip')
        self.claims={'iss':'https://accounts.google.com','aud':CLIENT,'sub':'fixture-owner-sub','email':'owner.fixture@gmail.com','email_verified':True,'name':'Fixture Owner','exp':self.clock+3600,'iat':self.clock,'nonce':c['nonce']}
        return c
    def login(self,c=None,**body):
        c=c or self.challenge();return self.auth.login({'challengeId':c['challengeId'],'credential':CREDENTIAL,**body},ORIGIN,'fixture-ip')
    def test_verified_session_is_terminal_bound_and_contains_no_bridge_or_trade_secret(self):
        result=self.login();self.assertEqual(result['user']['provider'],'google');self.assertEqual(self.calls[0][1],CLIENT);self.assertTrue(self.auth.session(result['token'],ORIGIN));self.assertNotIn(TOKEN,json.dumps(result));self.assertNotIn(TRADE,json.dumps(result));self.assertNotIn(result['token'],str(self.auth.sessions));self.assertNotIn(CREDENTIAL,str(self.auth.sessions));self.assertEqual(self.m.sent,[])
        self.m.login=987;self.assertIsNone(self.auth.session(result['token'],ORIGIN))
    def test_client_issuer_expiry_email_and_nonce_are_checked_server_side(self):
        for field,value in [('aud','other-client'),('iss','https://evil.fixture'),('exp',self.clock-1),('email_verified',False),('email','other.fixture@gmail.com'),('nonce','wrong-nonce'),('iat',self.clock+120)]:
            with self.subTest(field=field):
                c=self.challenge();self.claims[field]=value
                with self.assertRaises(ValueError):self.login(c)
    def test_challenge_is_single_use_origin_bound_and_expires(self):
        c=self.challenge();self.login(c)
        with self.assertRaises(ValueError):self.login(c)
        c=self.challenge()
        with self.assertRaises(ValueError):self.auth.login({'challengeId':c['challengeId'],'credential':CREDENTIAL},'https://other.fixture','fixture-ip')
        c=self.challenge();self.clock+=301
        with self.assertRaises(ValueError):self.login(c)
    def test_identity_is_not_granted_when_verifier_rejects_a_signature(self):
        c=self.challenge();self.auth.verify=lambda *_:(_ for _ in ()).throw(ValueError('fixture invalid signature'))
        with self.assertRaisesRegex(ValueError,'verification failed'):self.login(c)
        self.assertEqual(self.auth.sessions,{})
    def test_non_google_hosted_email_requires_explicit_stable_subject_allowlist(self):
        c=self.challenge();self.claims['email']='owner@external.fixture';self.auth.emails={'owner@external.fixture'}
        with self.assertRaises(ValueError):self.login(c)
        self.auth.subjects={'fixture-owner-sub'};c=self.challenge();self.claims['email']='owner@external.fixture';self.assertEqual(self.login(c)['user']['subject'],'fixture-owner-sub')
    def test_session_expires_is_origin_scoped_and_can_be_revoked(self):
        result=self.login();self.assertIsNone(self.auth.session(result['token'],'https://other.fixture'))
        result=self.login();self.auth.logout(result['token']);self.assertIsNone(self.auth.session(result['token'],ORIGIN))
        result=self.login();self.clock+=1801;self.assertIsNone(self.auth.session(result['token'],ORIGIN))
    def test_signin_is_disabled_until_explicit_client_and_allowlist_are_configured(self):
        auth=GoogleLogin(self.source,client_id='',emails='',subjects='',verify=lambda *_:{})
        self.assertFalse(auth.config()['enabled'])
        with self.assertRaises(ValueError):auth.challenge(ORIGIN,'fixture-ip')
        self.assertNotIn('owner.fixture',json.dumps(self.auth.config()))
    def test_multiple_devices_are_bounded_and_rate_limit_does_not_grow_unbounded(self):
        results=[self.login() for _ in range(5)]
        self.assertEqual(len(self.auth.sessions),4);self.assertIsNone(self.auth.session(results[0]['token'],ORIGIN));self.assertTrue(self.auth.session(results[-1]['token'],ORIGIN))
        for _ in range(10):self.auth.limit('other-fixture-ip')
        for _ in range(10):self.auth.limit('other-fixture-ip')
        with self.assertRaises(ValueError):self.auth.limit('other-fixture-ip')
    def test_http_google_session_reads_data_but_cannot_skip_trade_token_or_logout_checks(self):
        handler=make_handler(self.source,TOKEN,{ORIGIN},{'127.0.0.1'},enable_trading=True,trade_token=TRADE,google_login=self.auth)
        server=ThreadingHTTPServer(('127.0.0.1',0),handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def request(path,body=None,token=None,origin=ORIGIN,trade=None):
            headers={'Content-Type':'application/json'}
            if origin:headers['Origin']=origin
            if token:headers['Authorization']='Bearer '+token
            if trade:headers['X-Trade-Token']=trade
            c=http.client.HTTPConnection('127.0.0.1',server.server_port);c.request('POST' if body is not None else 'GET',path,json.dumps(body) if body is not None else None,headers);r=c.getresponse();result=r.status,json.loads(r.read());c.close();return result
        try:
            self.assertTrue(request('/v1/auth/config')[1]['enabled']);status,c=request('/v1/auth/challenge',{});self.assertEqual(status,200)
            self.claims={'iss':'https://accounts.google.com','aud':CLIENT,'sub':'fixture-owner-sub','email':'owner.fixture@gmail.com','email_verified':True,'exp':self.clock+3600,'iat':self.clock,'nonce':c['nonce']}
            status,result=request('/v1/auth/google',{'challengeId':c['challengeId'],'credential':CREDENTIAL});self.assertEqual(status,200);session=result['token']
            self.assertEqual(request('/v1/status',token=session)[0],200)
            self.assertEqual(request('/v1/trading/preview',{'accountKey':result['accountKey']},token=session)[0],403)
            self.assertEqual(request('/v1/auth/challenge',{},origin=None)[0],403)
            self.assertEqual(request('/v1/auth/challenge',{},origin='https://evil.fixture')[0],403)
            self.assertEqual(request('/v1/auth/logout',{},token=TOKEN)[0],401)
            self.assertEqual(request('/v1/auth/logout',{},token=session)[0],200)
            self.assertEqual(request('/v1/status',token=session)[0],401);self.assertEqual(request('/v1/status',token=TOKEN)[0],200);self.assertEqual(self.m.sent,[])
        finally:server.shutdown();server.server_close();thread.join();handler.ledger_store.close()


if __name__=='__main__':unittest.main()
