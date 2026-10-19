import {aggregateBars,timeframeMs,validateBars} from './engine.mjs';

// CSV is explicitly offline and only contains data imported by the user.
// There is no generated quote or fallback market.
export class CSVProvider {
 constructor(onBars,imports={}){this.onBars=onBars;this.imports=imports;this.aggregates=new Map();}
 info(){return{name:'csv',displayName:'Imported CSV · Offline',capabilities:{enumerate:true,stream:false,symbolInfo:true}};}
 async listSymbols(){return Object.keys(this.imports).map(ticker=>({ticker,description:'Imported CSV · Offline',type:'custom'}));}
 async getSymbolInfo(ticker){if(!this.imports[ticker])throw new Error('Import a CSV for this symbol first');return{ticker,timezone:'Etc/UTC',currency:ticker.endsWith('JPY')?'JPY':ticker.endsWith('USDT')?'USDT':'USD',type:'custom',mintick:.00001};}
 async getBars(ticker,tf,range={}){
  const record=this.imports[ticker];if(!record)throw new Error('No imported data for this symbol');
  const key=ticker+'|'+tf;let all=this.aggregates.get(key);const step=timeframeMs(tf);
  if(step<record.step)throw new Error('CSV interval is coarser than selected timeframe');
  if(!all){all=aggregateBars(record.bars,step);this.aggregates.set(key,all);}
  const bars=all.filter(b=>(range.from==null||b.time>=range.from)&&(range.to==null||b.time<=range.to)).slice(-Math.min(range.limit||720,10000));this.onBars?.('csv',ticker,tf,bars);return bars;
 }
 addImport(ticker,bars){bars=validateBars(bars);const diffs=bars.slice(1).map((b,i)=>b.time-bars[i].time).sort((a,b)=>a-b);this.imports[ticker]={bars,step:diffs[Math.floor(diffs.length/2)]};this.aggregates.clear();return this.imports[ticker];}
}

export function removeSyntheticState(state){
 const convert=full=>typeof full==='string'&&full.startsWith('sample:')?(state.imports?.[full.slice(7)]?'csv:'+full.slice(7):null):full;
 state.watchlist=[...new Set((state.watchlist||[]).map(convert).filter(Boolean))];
 for(const key of ['positions','closed','alerts'])state[key]=(state[key]||[]).map(item=>({...item,full:convert(item.full)})).filter(item=>item.full);
 state.drawings=Object.fromEntries(Object.entries(state.drawings||{}).map(([key,value])=>[convert(key),value]).filter(([key])=>key));
 return state;
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
