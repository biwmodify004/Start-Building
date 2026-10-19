import {aggregateBars,timeframeMs} from './engine.mjs';

export const BINANCE_REST='https://data-api.binance.vision/api/v3';
export const BINANCE_WS='wss://data-stream.binance.vision:443/ws';
export const BINANCE_PAIRS=[
 {ticker:'BTCUSDT',description:'Bitcoin / USDT'}, {ticker:'ETHUSDT',description:'Ethereum / USDT'},
 {ticker:'SOLUSDT',description:'Solana / USDT'}, {ticker:'BNBUSDT',description:'BNB / USDT'},
 {ticker:'XRPUSDT',description:'XRP / USDT'}, {ticker:'DOGEUSDT',description:'Dogecoin / USDT'},
 {ticker:'ADAUSDT',description:'Cardano / USDT'}
];
const INTERVALS=new Map([[1,'1m'],[3,'3m'],[5,'5m'],[15,'15m'],[30,'30m'],[60,'1h'],[120,'2h'],[240,'4h'],[360,'6h'],[480,'8h'],[720,'12h'],[1440,'1d'],[4320,'3d'],[10080,'1w']]);
export function binanceFrame(tf){if(/^(?:\d+)?M$/.test(String(tf)))throw new Error('Monthly charts are not supported by this Binance adapter. Choose 1D or a shorter interval.');const minutes=timeframeMs(tf)/60000;if(!Number.isInteger(minutes)||minutes<1)throw new Error('Binance Spot supports minute-based chart intervals');let base=minutes;if(!INTERVALS.has(base))base=[...INTERVALS.keys()].filter(m=>m<minutes&&minutes%m===0).at(-1);if(!base)throw new Error('Unsupported Binance interval');return {interval:INTERVALS.get(base),step:minutes*60000,baseStep:base*60000,ratio:minutes/base};}
export function binanceSymbol(value){const symbol=String(value).toUpperCase();if(!/^[A-Z0-9]{4,30}$/.test(symbol))throw new Error('Use a Binance Spot symbol, such as BTCUSDT');return symbol;}
export function decodeKline(row){const b={time:Number(row[0]),open:Number(row[1]),high:Number(row[2]),low:Number(row[3]),close:Number(row[4]),volume:Number(row[5])};if(Object.values(b).some(v=>!Number.isFinite(v))||b.time<0||b.open<=0||b.close<=0||b.low<=0||b.high<Math.max(b.open,b.close)||b.low>Math.min(b.open,b.close)||b.volume<0)throw new Error('Invalid Binance candle');return b;}
const sorted=bars=>[...new Map(bars.map(b=>[b.time,b])).values()].sort((a,b)=>a.time-b.time);

// Public market data only: no account keys, order routes, or third-party proxies.
export class BinanceMarketProvider {
 constructor({onBars=()=>{},onStatus=()=>{},fetchImpl=globalThis.fetch?.bind(globalThis),WebSocketImpl=globalThis.WebSocket,now=()=>Date.now(),schedule=setTimeout,cancel=clearTimeout,pollMs=5000,stallMs=15000}={}){
  Object.assign(this,{onBars,onStatus,fetchImpl,WebSocketImpl,now,schedule,cancel,pollMs,stallMs});this.statuses=new Map();this.sessions=new Set();this.metadata=new Map();
 }
 info(){return {name:'binance',displayName:'Binance Spot · public data',requiresApiKey:false,supportedTimeframes:['1','3','5','15','30','45','60','120','180','240','D','W'],capabilities:{enumerate:true,stream:true,symbolInfo:true}};}
 async listSymbols(){return BINANCE_PAIRS.map(pair=>({...pair,type:'crypto'}));}
 key(symbol,tf){return binanceSymbol(symbol)+'|'+(/^(?:\d+)?M$/.test(String(tf))?'month:'+tf:timeframeMs(tf));}
 status(symbol,tf){return this.statuses.get(this.key(symbol,tf))||{type:'idle',updatedAt:0};}
 report(symbol,tf,next){const value={...this.status(symbol,tf),...next,symbol,timeframe:tf};this.statuses.set(this.key(symbol,tf),value);this.onStatus(value);}
 async request(path,params={},signal){const url=new URL(BINANCE_REST+'/'+path);for(const [key,value]of Object.entries(params))if(value!=null)url.searchParams.set(key,String(value));const timeout=AbortSignal.timeout(12000);const combined=signal?AbortSignal.any([signal,timeout]):timeout;let response;try{response=await this.fetchImpl(url.toString(),{signal:combined,credentials:'omit'});}catch(error){if(signal?.aborted)throw error;throw new Error(error.name==='TimeoutError'?'Binance request timed out':'Cannot reach Binance public data. Check your connection or network restrictions.');}const body=await response.json();if(!response.ok||body?.code<0){const error=new Error('Binance: '+(body?.msg||'HTTP '+response.status));error.status=response.status;throw error;}return body;}
 async fetchBars(symbol,tf,range={},signal){symbol=binanceSymbol(symbol);const frame=binanceFrame(tf),limit=Math.max(1,Math.min(Math.trunc(range.limit||720),10000)),wanted=Math.min(limit*frame.ratio+frame.ratio-1,20000);const rows=[];let cursor=range.from!=null?Number(range.from):null,end=range.to!=null?Number(range.to):undefined;
  while(rows.length<wanted){const size=Math.min(1000,wanted-rows.length),params={symbol,interval:frame.interval,limit:size,...(cursor!=null?{startTime:cursor}:{}),...(end!=null?{endTime:end}:{})};const page=await this.request('klines',params,signal);if(!Array.isArray(page))throw new Error('Unexpected Binance candle response');if(!page.length)break;const decoded=page.map(decodeKline);rows.push(...decoded);if(page.length<size)break;if(cursor!=null){const next=decoded.at(-1).time+frame.baseStep;if(next<=cursor)break;cursor=next;if(end!=null&&cursor>end)break;}else{const next=decoded[0].time-1;if(end!=null&&next>=end)break;end=next;}}
  const bars=sorted(rows),result=frame.ratio===1?bars:aggregateBars(bars,frame.step);return result.filter(b=>(range.from==null||b.time>=range.from)&&(range.to==null||b.time<=range.to)).slice(-limit);
 }
 async getBars(symbol,tf,range={}){symbol=binanceSymbol(symbol);const before=this.status(symbol,tf);if(!before.updatedAt)this.report(symbol,tf,{type:'loading',error:null});try{const bars=await this.fetchBars(symbol,tf,range);if(bars.length){this.onBars('binance',symbol,tf,bars);if(!['live','polling','reconnecting'].includes(this.status(symbol,tf).type))this.report(symbol,tf,{type:'history',updatedAt:this.now(),error:null});}return bars;}catch(error){this.report(symbol,tf,{type:'error',error:error.message});throw error;}}
 async getSymbolInfo(ticker){ticker=binanceSymbol(ticker);if(!this.metadata.has(ticker))this.metadata.set(ticker,this.request('exchangeInfo',{symbol:ticker}).then(data=>{const s=data.symbols?.[0];if(!s)return undefined;const tick=Number(s.filters?.find(f=>f.filterType==='PRICE_FILTER')?.tickSize);return {ticker,type:'crypto',description:s.baseAsset+' / '+s.quoteAsset,basecurrency:s.baseAsset,currency:s.quoteAsset,timezone:'Etc/UTC',session:'24x7',...(tick>0?{mintick:tick,pricescale:Math.round(1/tick)}:{})};}).catch(()=>({ticker,type:'crypto',currency:ticker.endsWith('USDT')?'USDT':undefined,timezone:'Etc/UTC',session:'24x7'})));return this.metadata.get(ticker);}
 subscribe(symbol,tf,onBar){symbol=binanceSymbol(symbol);const frame=binanceFrame(tf),key=this.key(symbol,tf);let stopped=false,socket=null,watchdog=null,retry=null,pollTimer=null,pollAbort=null,polling=false,pollBusy=false,attempt=0,lastEvent=0,lastBarTime=-Infinity;
  const report=next=>this.report(symbol,tf,next);
  const emit=bar=>{if(stopped||bar.time<lastBarTime)return;lastBarTime=bar.time;this.onBars('binance',symbol,tf,[bar]);onBar(bar);};
  const clear=id=>{if(id!=null)this.cancel(id);};
  const stopPolling=()=>{polling=false;clear(pollTimer);pollTimer=null;pollAbort?.abort();pollAbort=null;};
  const poll=async()=>{if(stopped||!polling||pollBusy)return;pollBusy=true;const controller=new AbortController();pollAbort=controller;try{const bars=await this.fetchBars(symbol,tf,{limit:3},controller.signal);if(!stopped&&polling&&bars.length){for(const bar of bars)emit(bar);report({type:'polling',transport:'REST',updatedAt:this.now(),error:null,pollMs:this.pollMs});}}catch(error){if(!stopped&&polling&&!controller.signal.aborted)report({type:'error',transport:'REST',error:error.message});}finally{pollBusy=false;if(pollAbort===controller)pollAbort=null;if(!stopped&&polling)pollTimer=this.schedule(poll,this.pollMs);}};
  const startPolling=()=>{if(stopped||polling)return;polling=true;report({type:'reconnecting',transport:'REST',error:null});void poll();};
  const scheduleReconnect=()=>{if(stopped||retry!=null)return;const delay=Math.min(30000,1000*2**Math.min(attempt++,5));retry=this.schedule(()=>{retry=null;connect();},delay);};
  const disconnect=ws=>{if(socket!==ws)return;socket=null;clear(watchdog);watchdog=null;ws.onopen=ws.onmessage=ws.onerror=ws.onclose=null;try{ws.close();}catch{}if(!stopped){startPolling();scheduleReconnect();}};
  const armWatchdog=()=>{clear(watchdog);watchdog=this.schedule(()=>{watchdog=null;if(stopped)return;if(socket&&this.now()-lastEvent>=this.stallMs)disconnect(socket);else armWatchdog();},this.stallMs);};
  const connect=()=>{if(stopped)return;report({type:polling?'reconnecting':'connecting',transport:polling?'REST':'WebSocket',error:null});if(!this.WebSocketImpl||frame.ratio>1){startPolling();return;}let ws;try{ws=new this.WebSocketImpl(BINANCE_WS+'/'+symbol.toLowerCase()+'@kline_'+frame.interval);}catch{startPolling();scheduleReconnect();return;}socket=ws;lastEvent=this.now();armWatchdog();ws.onopen=()=>{if(stopped||socket!==ws)return;armWatchdog();};ws.onmessage=event=>{if(stopped||socket!==ws)return;try{const data=JSON.parse(event.data),k=data.k;if(data.e!=='kline'||data.s!==symbol||k?.i!==frame.interval)return;const raw=decodeKline([k.t,k.o,k.h,k.l,k.c,k.v]);const eventTime=Number(data.E);if(!Number.isFinite(eventTime)||this.now()-eventTime>this.stallMs)return;if(raw.time<lastBarTime)return;lastEvent=this.now();attempt=0;stopPolling();emit(raw);report({type:'live',transport:'WebSocket',updatedAt:this.now(),eventTime,error:null});armWatchdog();}catch{}};ws.onerror=()=>disconnect(ws);ws.onclose=()=>disconnect(ws);};
  const stop=()=>{if(stopped)return;stopped=true;clear(watchdog);clear(retry);stopPolling();if(socket){socket.onopen=socket.onmessage=socket.onerror=socket.onclose=null;try{socket.close();}catch{}socket=null;}this.sessions.delete(session);if(![...this.sessions].some(s=>s.key===key))report({type:'closed',transport:null});};
  const session={key,stop};this.sessions.add(session);connect();return stop;
 }
 stop(symbol,tf){const key=this.key(symbol,tf);for(const session of [...this.sessions])if(session.key===key)session.stop();}
 destroy(){for(const session of [...this.sessions])session.stop();}
}
