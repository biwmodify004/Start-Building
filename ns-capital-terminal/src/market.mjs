import {aggregateBars,timeframeMs,validateBars} from './engine.mjs';

export const MARKETS=[
 {ticker:'XAUUSD',description:'Gold / US Dollar',type:'commodity',base:2650,vol:0.00028,badge:'Au',color:'#e1bb69'},
 {ticker:'US30',description:'Dow Jones · sample index',type:'index',base:42300,vol:0.00018,badge:'30',color:'#7ca8f7'},
 {ticker:'EURUSD',description:'Euro / US Dollar',type:'forex',base:1.092,vol:0.00011,badge:'€',color:'#87a4f1'},
 {ticker:'GBPJPY',description:'British Pound / Japanese Yen',type:'forex',base:192.5,vol:0.00015,badge:'£',color:'#c29bf4'},
 {ticker:'BTCUSDT',description:'Bitcoin / Tether',type:'crypto',base:67000,vol:0.0004,badge:'₿',color:'#f5a85b'},
 {ticker:'ETHUSDT',description:'Ethereum / Tether',type:'crypto',base:2600,vol:0.00045,badge:'Ξ',color:'#97a0e6'},
 {ticker:'SOLUSDT',description:'Solana / Tether',type:'crypto',base:155,vol:0.0006,badge:'S',color:'#6ccfae'}
];
export const SAMPLE_END=Date.UTC(2026,9,16,21);
const baseCache=new Map();
function random(seed){return()=>{seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
export function sampleBars(ticker) {
  if(baseCache.has(ticker))return baseCache.get(ticker);
  const meta=MARKETS.find(m=>m.ticker===ticker);
  if(!meta)throw new Error('Unknown sample market');
  const rand=random([...ticker].reduce((s,c)=>s*31+c.charCodeAt(0),7)),bars=[],count=64800;
  let price=meta.base;
  for(let i=0;i<count;i++) {
    const open=price,drift=Math.sin(i/1700)*0.000012+Math.cos(i/230)*0.000012;
    price=Math.max(meta.base*0.1,open*(1+(rand()-.5)*meta.vol*2+drift));
    const spread=open*meta.vol*rand()*.8;
    bars.push({time:SAMPLE_END-(count-i)*60000,open,close:price,high:Math.max(open,price)+spread,low:Math.min(open,price)-spread,volume:Math.round(5+rand()*450)});
  }
  baseCache.set(ticker,bars);return bars;
}

export class SampleProvider {
  constructor(onBars,imports={}){this.onBars=onBars;this.imports=imports;this.aggregates=new Map();}
  info(){return{name:'sample',displayName:'NS sample / CSV',capabilities:{enumerate:true,stream:false,symbolInfo:true}};}
  async listSymbols(){return [...MARKETS.map(({ticker,description,type})=>({ticker,description:description+' · SAMPLE',type})),...Object.keys(this.imports).map(ticker=>({ticker,description:'Imported CSV · UTC',type:'custom'}))];}
  async getSymbolInfo(ticker){return {ticker,timezone:'Etc/UTC',currency:ticker.endsWith('JPY')?'JPY':ticker.endsWith('USDT')?'USDT':'USD',type:MARKETS.find(x=>x.ticker===ticker)?.type||'custom',mintick:ticker==='EURUSD'?.00001:.01};}
  async getBars(ticker,tf,range={}) {
    const key=ticker+'|'+tf;
    let all=this.aggregates.get(key);
    if(!all){const source=this.imports[ticker]?.bars||sampleBars(ticker);const baseStep=this.imports[ticker]?.step||60000;const step=timeframeMs(tf);if(step<baseStep)throw new Error('CSV interval is coarser than selected timeframe');all=aggregateBars(source,step);this.aggregates.set(key,all);}
    const limit=Math.min(range.limit||720,10000);
    let bars=all.filter(b=>(range.from==null||b.time>=range.from)&&(range.to==null||b.time<=range.to));
    bars=bars.slice(-limit);this.onBars?.('sample',ticker,tf,bars);return bars;
  }
  addImport(ticker,bars){bars=validateBars(bars);const diffs=bars.slice(1).map((b,i)=>b.time-bars[i].time).sort((a,b)=>a-b);this.imports[ticker]={bars,step:diffs[Math.floor(diffs.length/2)]};this.aggregates.clear();return this.imports[ticker];}
}

export function recipeFromText(text,current) {
  const q=text.toLowerCase(),config={...current};
  let recognized=false;
  if(/mean|reversion|กลับค่า|กลับสู่|bb|bollinger/.test(q)){config.kind='mean';recognized=true;}
  else if(/breakout|break out|ทะลุ|เบรก/.test(q)){config.kind='breakout';recognized=true;}
  else if(/trend|เทรนด์|แนวโน้ม|ema|เทรน/.test(q)){config.kind='trend';recognized=true;}
  const periods=q.match(/ema\s*(\d+)\s*(?:\/|,|และ|and|กับ)\s*(\d+)/);
  if(periods){config.fast=Number(periods[1]);config.slow=Number(periods[2]);recognized=true;}
  const risk=q.match(/(?:risk|เสี่ยง)\s*(\d+(?:\.\d+)?)\s*%/);if(risk){config.risk=Number(risk[1]);recognized=true;}
  const reward=q.match(/(?:rr|r:r|reward)\s*(?:1\s*[:/]\s*)?(\d+(?:\.\d+)?)/);if(reward){config.reward=Number(reward[1]);recognized=true;}
  return {config,recognized,indicator:/rsi/.test(q)?'rsi':/atr/.test(q)&&!/stop|sl/.test(q)?'atr':null};
}
