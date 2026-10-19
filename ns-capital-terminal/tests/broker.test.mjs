import test from 'node:test';
import assert from 'node:assert/strict';
import {BrokerMarketProvider,BRIDGE_PROTOCOL,bridgeURL,brokerFrame,brokerSymbol,pauseBrokerSnapshot} from '../src/broker.mjs';
import {GLOBAL_MARKETS,mountGlobalChart,widgetConfig} from '../src/global-markets.mjs';
import {JSDOM} from 'jsdom';

const token='fixture-token-only-01234567890123456789';
const markets=[{ticker:'XAUUSD.pro',description:'Gold / USD',type:'commodity',currency:'USD',tickSize:.01},{ticker:'EURUSD.a',description:'EUR / USD',type:'forex',currency:'USD',tickSize:.00001},{ticker:'#US30.cash',description:'US 30 CFD',type:'index',currency:'USD',tickSize:.1},{ticker:'USDJPY',description:'USD / JPY',type:'forex',currency:'JPY',tickSize:.001}];
const candles=now=>[0,1,2].map(i=>({time:Math.floor(now/900000)*900000-(2-i)*900000,open:4500,high:4502,low:4498,close:4501,volume:12}));
const flush=()=>new Promise(r=>setImmediate(r));
function fixture(options={}){
 let now=Date.UTC(2026,9,19,2),quoteAt=now,error=false;
 const calls=[],timers=new Set();
 const fetchImpl=async(raw,init)=>{const url=new URL(raw);calls.push({url,init});assert.equal(init.headers.Authorization,'Bearer '+token);assert.equal(init.credentials,'omit');assert.equal(init.redirect,'error');if(error)throw new Error('Fixture network unavailable');let body;
  if(url.pathname==='/v1/status')body={protocol:BRIDGE_PROTOCOL,connected:true,readOnly:true,broker:'Fixture Broker',platform:'MT5'};
  else if(url.pathname==='/v1/symbols')body={symbols:markets};
  else if(url.pathname==='/v1/bars')body={symbol:url.searchParams.get('symbol'),timeframe:url.searchParams.get('timeframe'),bars:candles(now)};
  else if(url.pathname==='/v1/quote')body={symbol:url.searchParams.get('symbol'),bid:4501,ask:4501.2,time:quoteAt};
  else throw new Error('Unexpected route');return {ok:true,status:200,json:async()=>body};
 };
 const provider=new BrokerMarketProvider({fetchImpl,now:()=>now,schedule:fn=>{timers.add(fn);return fn;},cancel:fn=>timers.delete(fn),...options});
 return {provider,calls,timers,setQuoteTime:value=>quoteAt=value,setError:value=>error=value,advance:value=>now+=value,now:()=>now,tick:async()=>{const fn=timers.values().next().value;assert.ok(fn);timers.delete(fn);await fn();}};
}

test('bridge URLs require explicit HTTPS or loopback HTTP; symbols keep actual suffixes',()=>{
 assert.equal(bridgeURL('http://127.0.0.1:8787/'),'http://127.0.0.1:8787');assert.equal(bridgeURL('https://bridge.example/personal/'),'https://bridge.example/personal');
 for(const url of ['http://192.168.1.1','https://user:pass@bridge.example','https://bridge.example/?token=secret','file:///tmp/test'])assert.throws(()=>bridgeURL(url));
 assert.equal(brokerSymbol('#US30.cash'),'#US30.cash');assert.equal(brokerFrame('1D'),'D');assert.equal(brokerFrame('4h'),'240');assert.throws(()=>brokerFrame('M'));assert.throws(()=>brokerFrame('45'));assert.throws(()=>brokerSymbol('../EUR/USD'));
});
test('restoring charts never reconnects a broker without its session credential',()=>{
 const doc={version:1,layout:'2h',charts:[{id:'one',symbol:'broker:XAUUSD.pro',provider:'broker',timeframe:'60',drawings:{version:1,drawings:[{id:'saved'}]}},{id:'two',symbol:'binance:ETHBTC',timeframe:'15'}]};
 const raw=JSON.stringify(doc),result=pauseBrokerSnapshot(raw),restored=JSON.parse(result.raw);
 assert.equal(result.resume,true);assert.equal(restored.charts[0].symbol,'sample:XAUUSD');assert.equal(restored.charts[0].provider,'sample');assert.equal(restored.charts[1].symbol,'binance:ETHBTC');assert.equal(doc.charts[0].drawings.drawings.length,1);assert.equal(pauseBrokerSnapshot('invalid').raw,'invalid');assert.equal(pauseBrokerSnapshot(JSON.stringify({version:1,charts:[{symbol:'sample:XAUUSD'}]})).resume,false);
});
test('broker catalog and tick/currency metadata come only from the connected terminal',async()=>{
 const f=fixture();const connection=await f.provider.connect({url:'http://127.0.0.1:8787',token});assert.equal(connection.broker,'Fixture Broker');assert.equal(f.provider.catalog.length,4);
 assert.deepEqual(await f.provider.getSymbolInfo('USDJPY'),{ticker:'USDJPY',description:'USD / JPY',type:'forex',timezone:'Etc/UTC',currency:'JPY',mintick:.001});assert.equal((await f.provider.getSymbolInfo('#US30.cash')).mintick,.1);
 await assert.rejects(()=>f.provider.getSymbolInfo('US30'),/not available/);
 const bars=await f.provider.getBars('XAUUSD.pro','15',{limit:720,to:f.now(),from:f.now()-900000});assert.equal(bars.length,3);const last=f.calls.at(-1).url;assert.equal(last.searchParams.get('symbol'),'XAUUSD.pro');assert.equal(last.searchParams.get('limit'),'720');assert.equal(f.provider.status('XAUUSD.pro','15').type,'history');assert.equal(f.provider.status('XAUUSD.pro','15').tickAt,0);
 f.provider.disconnect();assert.equal(f.provider.token,'');assert.equal(f.provider.catalog.length,0);
});
test('broker LIVE requires a fresh original tick; stale, failures and recovery remain explicit',async()=>{
 const received=[],f=fixture();await f.provider.connect({url:'http://127.0.0.1:8787',token});const stop=f.provider.subscribe('XAUUSD.pro','15',bar=>received.push(bar));await flush();await flush();
 assert.equal(f.provider.status('XAUUSD.pro','15').type,'live');assert.equal(f.provider.status('XAUUSD.pro','15').tickAt,f.now());assert.equal(received.length,3);
 f.advance(31000);await f.tick();assert.equal(f.provider.status('XAUUSD.pro','15').type,'stale');assert.equal(f.provider.status('XAUUSD.pro','15').tickAt,f.now()-31000);
 f.setError(true);await f.tick();assert.equal(f.provider.status('XAUUSD.pro','15').type,'error');
 f.setError(false);f.setQuoteTime(f.now());await f.tick();assert.equal(f.provider.status('XAUUSD.pro','15').type,'live');
 stop();assert.equal(f.timers.size,0);assert.equal(f.provider.sessions.size,0);
});
test('a non-bridge / disconnected endpoint is rejected without synthetic fallback or retained token',async()=>{
 for(const status of [{protocol:'unknown',connected:true,readOnly:true},{protocol:BRIDGE_PROTOCOL,connected:false,readOnly:true}]){
  const p=new BrokerMarketProvider({fetchImpl:async()=>({ok:true,json:async()=>status})});await assert.rejects(()=>p.connect({url:'http://localhost:8787',token}));assert.equal(p.token,'');assert.equal(p.connection,null);
 }
 const f=fixture();await assert.rejects(()=>f.provider.connect({url:'http://localhost:8787',token:'too-short'}),/32/);assert.equal(f.provider.token,'');
});
test('global catalog has metals, all seven majors, GBPJPY and separately labeled CFD indices',()=>{
 assert.equal(GLOBAL_MARKETS.length,18);assert.deepEqual(GLOBAL_MARKETS.filter(m=>m.group==='metals').map(m=>m.symbol),['XAUUSD','XAGUSD']);assert.equal(GLOBAL_MARKETS.filter(m=>m.group==='majors').length,7);assert.equal(GLOBAL_MARKETS.filter(m=>m.group==='indices').length,8);
 const config=widgetConfig(GLOBAL_MARKETS[0],{interval:'1',locale:'th',theme:'light'});assert.equal(config.symbol,'OANDA:XAUUSD');assert.equal(config.allow_symbol_change,false);assert.equal(config.timezone,'Asia/Bangkok');assert.throws(()=>widgetConfig({tv:'MALICIOUS:VALUE'}));
});
test('official TradingView widget retains attribution and isolates external data from Vela',()=>{
 const dom=new JSDOM('<div id="chart"></div>'),container=dom.window.document.getElementById('chart');
 mountGlobalChart(container,GLOBAL_MARKETS[1]);assert.equal(container.querySelector('script').src,'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js');assert.equal(JSON.parse(container.querySelector('script').textContent).symbol,'OANDA:XAGUSD');assert.match(container.querySelector('a').textContent,/by TradingView/);mountGlobalChart(container,GLOBAL_MARKETS[10]);assert.equal(container.querySelectorAll('script').length,1);dom.window.close();
});
