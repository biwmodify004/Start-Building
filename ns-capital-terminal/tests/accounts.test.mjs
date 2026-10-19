import test from 'node:test';
import assert from 'node:assert/strict';
import {TradingAccounts,accountKey,maskedAccount} from '../src/accounts.mjs';
import {BrokerMarketProvider} from '../src/broker.mjs';
const token='fixture-account-token-01234567890123456789';
const status={protocol:'ns-market-bridge/1',readOnly:true,connected:true,platform:'MT5',broker:'Fixture Broker',account:{id:'12345678',server:'Fixture-Server',currency:'USD',balance:10000,equity:10001,mode:'demo'}};
const storage=()=>{const map=new Map();return{getItem:k=>map.get(k)||null,setItem:(k,v)=>map.set(k,v),serialized:()=>[...map.values()].join('')};};
test('multiple verified account profiles persist without their session tokens or balances',()=>{
 const store=storage(),a=new TradingAccounts({storage:store}),first=a.add({label:'CFD account',url:'http://localhost:8787',kind:'cfd',status,token});
 const second=a.add({label:'Futures account',url:'http://localhost:8788',kind:'futures',status:{...status,account:{...status.account,id:'87654321'}},token:token+'2'});
 assert.equal(a.profiles.length,2);assert.notEqual(first.id,second.id);assert.equal(a.token(first.id),token);assert.ok(!store.serialized().includes(token));assert.ok(!store.serialized().includes('balance'));assert.equal(maskedAccount(status.account),'•••• 5678');
 const restored=new TradingAccounts({storage:store});assert.equal(restored.profiles.length,2);assert.equal(restored.token(first.id),'');assert.equal(restored.activeId,null);assert.equal(restored.get(second.id).kind,'futures');
 a.disconnect();assert.equal(a.activeId,null);a.remove(first.id);assert.equal(a.profiles.length,1);assert.equal(a.token(first.id),'');
});
test('unverified accounts and unsafe bridge URLs cannot be saved',()=>{const a=new TradingAccounts({storage:storage()});assert.throws(()=>a.add({url:'http://localhost:8787',status:{...status,connected:false},token}));assert.throws(()=>a.add({url:'http://localhost:8787',status:{...status,account:null},token}));assert.throws(()=>a.add({url:'http://remote.test',status,token}));assert.equal(a.profiles.length,0);});
test('connecting a saved profile to a different terminal identity is rejected and credentials cleared',async()=>{
 const provider=new BrokerMarketProvider({fetchImpl:async()=>({ok:true,json:async()=>status})});await assert.rejects(provider.connect({url:'http://localhost:8787',token,expectedAccount:'Different|987'}),/account has changed/);assert.equal(provider.connection,null);assert.equal(provider.token,'');assert.equal(accountKey(status.account),'Fixture-Server|12345678');
});
test('account drift during polling never delivers another account candles or quotes',async()=>{
 let changed=false;const calls=[],p=new BrokerMarketProvider({fetchImpl:async(raw)=>{const url=new URL(raw);calls.push(url.pathname);let body;if(url.pathname==='/v1/status')body={...status,account:{...status.account,id:changed?'999':status.account.id}};else if(url.pathname==='/v1/symbols')body={symbols:[{ticker:'ESZ6',currency:'USD',tickSize:.25,assetClass:'futures'}]};else throw new Error('Must stop before another account market data');return{ok:true,json:async()=>body};},schedule:()=>0,cancel(){}});
 await p.connect({url:'http://localhost:8787',token});changed=true;const delivered=[];const stop=p.subscribe('ESZ6','15',bar=>delivered.push(bar));await new Promise(r=>setImmediate(r));assert.equal(delivered.length,0);assert.equal(p.status('ESZ6','15').type,'error');assert.match(p.status('ESZ6','15').error,/account changed/);assert.ok(!calls.includes('/v1/bars'));stop();p.destroy();
});
