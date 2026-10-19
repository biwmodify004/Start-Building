import {validateBars,timeframeMs} from './engine.mjs';

export const BRIDGE_PROTOCOL='ns-market-bridge/1';
export function pauseBrokerSnapshot(raw,imports={}){
 if(!raw)return{raw,resume:false};
 try{const doc=JSON.parse(raw);let resume=false,changed=false;
  if(Array.isArray(doc?.charts))for(const chart of doc.charts)if(chart&&typeof chart==='object'){
   const prefix=String(chart.symbol).split(':')[0].toLowerCase(),broker=chart.provider==='broker'||prefix==='broker'||prefix.startsWith('broker_'),synthetic=chart.provider==='sample'||prefix==='sample';
   if(broker||synthetic){const ticker=String(chart.symbol).split(':').at(-1),csv=synthetic&&imports[ticker];chart.symbol=csv?'csv:'+ticker:'binance:BTCUSDT';chart.provider=csv?'csv':'binance';if(!csv)chart.timeframe='15';chart.drawings={version:1,drawings:[]};resume||=broker;changed=true;}
  }
  return{raw:changed?JSON.stringify(doc):raw,resume};
 }catch{return{raw,resume:false};}
}
export function bridgeURL(value){
 const url=new URL(String(value).trim());
 if(url.username||url.password||url.search||url.hash)throw new Error('Use a bridge URL without credentials, query or fragment');
 const loopback=['localhost','127.0.0.1','[::1]'].includes(url.hostname);
 if(url.protocol!=='https:'&&!(url.protocol==='http:'&&loopback))throw new Error('Use HTTPS for a VPS, or HTTP on localhost only');
 return url.href.replace(/\/$/,'');
}
export function brokerSymbol(value){const symbol=String(value);if(!/^[\p{L}\p{N}#_.-]{1,128}$/u.test(symbol))throw new Error('Invalid broker symbol');return symbol;}
export function brokerFrame(tf){if(/^(?:\d+)?M$/.test(String(tf)))throw new Error('Monthly broker charts are not supported');const ms=timeframeMs(tf),map=new Map([[60000,'1'],[300000,'5'],[900000,'15'],[1800000,'30'],[3600000,'60'],[14400000,'240'],[86400000,'D'],[604800000,'W']]);if(!map.has(ms))throw new Error('Broker timeframe is not supported');return map.get(ms);}
export class BrokerMarketProvider{
 constructor({fetchImpl=globalThis.fetch?.bind(globalThis),onBars=()=>{},onStatus=()=>{},pollMs=2000,now=()=>Date.now(),schedule=setTimeout,cancel=clearTimeout}={}){Object.assign(this,{fetchImpl,onBars,onStatus,pollMs,now,schedule,cancel});this.url='';this.token='';this.catalog=[];this.statuses=new Map();this.sessions=new Set();this.connection=null;this.generation=0;}
 info(){return{name:'broker',displayName:'Personal broker bridge · MT4 / MT5',capabilities:{enumerate:true,stream:true,symbolInfo:true},supportedTimeframes:['1','5','15','30','60','240','D','W']};}
 key(symbol,tf){return brokerSymbol(symbol)+'|'+(/^(?:\d+)?M$/.test(String(tf))?'month:'+tf:timeframeMs(tf));}
 market(symbol){return this.catalog.find(m=>m.ticker===symbol);}
 status(symbol,tf){return this.statuses.get(this.key(symbol,tf))||{type:'idle',updatedAt:0,tickAt:0};}
 report(symbol,tf,next){const status={...this.status(symbol,tf),symbol,timeframe:tf,...next};this.statuses.set(this.key(symbol,tf),status);this.onStatus(status);return status;}
 async request(path,params={},signal){
  if(!this.url||!this.token)throw new Error('Connect your broker bridge first');
  if(this.accountIdentity&&['/v1/bars','/v1/quote'].includes(path))params={...params,accountKey:this.accountIdentity};const url=new URL(this.url+path);for(const [k,v]of Object.entries(params))if(v!=null)url.searchParams.set(k,String(v));
  const response=await this.fetchImpl(url.href,{headers:{Authorization:'Bearer '+this.token},credentials:'omit',cache:'no-store',redirect:'error',signal:signal?AbortSignal.any([signal,AbortSignal.timeout(20000)]):AbortSignal.timeout(20000)});
  let data;try{data=await response.json();}catch{throw new Error('Bridge returned an invalid response');}
  if(!response.ok)throw new Error(data.error||'Broker bridge HTTP '+response.status);return data;
 }
 async connect({url,token,expectedAccount}){
  this.disconnect();const endpoint=bridgeURL(url),credential=String(token).trim();if(credential.length<32||!/^[!-~]+$/.test(credential))throw new Error('Bridge token must contain at least 32 printable ASCII characters');this.url=endpoint;this.token=credential;
  const generation=this.generation;
  try{const status=await this.request('/v1/status');if(generation!==this.generation)throw new Error('Connection cancelled');if(status.protocol!==BRIDGE_PROTOCOL||status.readOnly!==true)throw new Error('This endpoint is not an NS read-only market bridge');if(!status.connected)throw new Error(status.error||'Terminal is not connected. Log in to MT4 / MT5 first');if(expectedAccount&&this.connectionKey(status)!==expectedAccount)throw new Error('The terminal account has changed. Add it as a new account');this.connection=status;this.accountIdentity=this.connectionKey(status);await this.listSymbols();if(!this.catalog.length)throw new Error('No broker symbols are available. Open Market Watch / check the terminal');return status;}catch(error){if(generation===this.generation)this.disconnect();throw error;}
 }
 connectionKey(status){return status?.account?.id&&status?.account?.server?String(status.account.server)+'|'+String(status.account.id):null;}
 async listSymbols(){
  const generation=this.generation,data=await this.request('/v1/symbols');if(generation!==this.generation)throw new Error('Connection cancelled');
  if(!Array.isArray(data.symbols))throw new Error('Broker symbol catalog is invalid');
  const seen=new Map();for(const m of data.symbols){try{const ticker=brokerSymbol(m.ticker),tickSize=Number(m.tickSize);if(!(tickSize>0)||typeof m.currency!=='string'||!m.currency)continue;seen.set(ticker,{...m,ticker,tickSize,description:String(m.description||ticker),type:['forex','commodity','index','crypto','stock','futures'].includes(m.type)?m.type:'custom',currency:String(m.currency)});}catch{}}
  this.catalog=[...seen.values()].sort((a,b)=>a.ticker.localeCompare(b.ticker));return this.catalog;
 }
 async getSymbolInfo(symbol){symbol=brokerSymbol(symbol);let market=this.market(symbol);if(!market){await this.listSymbols();market=this.market(symbol);}if(!market)throw new Error('Symbol is not available in this broker terminal: '+symbol);return{ticker:symbol,description:market.description,type:market.type,timezone:'Etc/UTC',currency:market.currency,mintick:market.tickSize};}
 async fetchBars(symbol,tf,range={},signal){
  const data=await this.request('/v1/bars',{symbol:brokerSymbol(symbol),timeframe:brokerFrame(tf),limit:Math.min(10000,Math.max(2,range.limit||720)),from:range.from,to:range.to},signal);
  if(data.symbol!==symbol||data.timeframe!==brokerFrame(tf))throw new Error('Bridge returned bars for a different market');
  if(!Array.isArray(data.bars))throw new Error('Broker candles are invalid');return validateBars(data.bars);
 }
 async getBars(symbol,tf,range={}){const generation=this.generation;try{const bars=await this.fetchBars(symbol,tf,range);if(generation!==this.generation)throw new Error('Connection changed');this.onBars('broker',symbol,tf,bars);if(this.status(symbol,tf).type!=='live')this.report(symbol,tf,{type:'history',error:null});return bars;}catch(error){if(generation===this.generation)this.report(symbol,tf,{type:'error',error:error.message});throw error;}}
 subscribe(symbol,tf,onBar){
  symbol=brokerSymbol(symbol);brokerFrame(tf);const generation=this.generation;let stopped=false,timer=null,controller=null,lastBarTime=-Infinity;
  const session={key:this.key(symbol,tf),stop:()=>{if(stopped)return;stopped=true;this.cancel(timer);controller?.abort();this.sessions.delete(session);}};this.sessions.add(session);
  const poll=async()=>{if(stopped)return;controller=new AbortController();try{
   const connection=await this.request('/v1/status',{},controller.signal);if(!connection.connected||this.connectionKey(connection)!==this.accountIdentity)throw new Error('Trading account changed or disconnected. Reconnect the account');const bars=await this.fetchBars(symbol,tf,{limit:3},controller.signal),quote=await this.request('/v1/quote',{symbol},controller.signal);if(stopped||generation!==this.generation)return;
   const tickAt=Number(quote.time),bid=Number(quote.bid),ask=Number(quote.ask),age=this.now()-tickAt;
   if(quote.symbol!==symbol||!Number.isFinite(tickAt)||!(bid>0)||!(ask>=bid)||age< -5000)throw new Error('Invalid broker quote');
   if(!bars.length)throw new Error('No broker candles received');
   for(const bar of bars){if(bar.time<lastBarTime||bar.time>this.now()+5000)continue;lastBarTime=bar.time;onBar(bar);}
   this.onBars('broker',symbol,tf,bars);this.report(symbol,tf,{type:age<=30000?'live':'stale',updatedAt:this.now(),tickAt,bid,ask,transport:'HTTP / 2s',error:null});
  }catch(error){if(!stopped&&generation===this.generation)this.report(symbol,tf,{type:'error',error:error.message});}finally{if(!stopped&&generation===this.generation)timer=this.schedule(poll,this.pollMs);}};
  this.report(symbol,tf,{type:'connecting',error:null});poll();return session.stop;
 }
 stop(symbol,tf){const key=this.key(symbol,tf);for(const session of [...this.sessions])if(session.key===key)session.stop();}
 disconnect(){this.generation++;for(const session of [...this.sessions])session.stop();this.statuses.clear();this.connection=null;this.accountIdentity=null;this.catalog=[];this.token='';this.url='';}
 destroy(){this.disconnect();}
}
