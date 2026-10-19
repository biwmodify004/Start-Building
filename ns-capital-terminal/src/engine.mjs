export const DEFAULT_CONFIG = Object.freeze({kind:'trend', fast:21, slow:50, period:20, deviation:2, atrPeriod:14, stopATR:1.5, reward:2, risk:0.5, capital:10000, feeBps:2, slippageBps:1});

export function ema(values, period) {
  const out=Array(values.length).fill(null), k=2/(period+1);
  if(values.length<period)return out;
  let v=values.slice(0,period).reduce((a,b)=>a+b,0)/period;
  out[period-1]=v;
  for(let i=period;i<values.length;i++)out[i]=v=values[i]*k+v*(1-k);
  return out;
}

export function bands(values, period=20, deviation=2) {
  const out=Array(values.length).fill(null);
  for(let i=period-1;i<values.length;i++) {
    const window=values.slice(i-period+1,i+1), mid=window.reduce((a,b)=>a+b,0)/period;
    const sd=Math.sqrt(window.reduce((a,b)=>a+(b-mid)**2,0)/period);
    out[i]={mid,upper:mid+sd*deviation,lower:mid-sd*deviation};
  }
  return out;
}

export function atr(bars, period=14) {
  const tr=bars.map((b,i)=>i?Math.max(b.high-b.low,Math.abs(b.high-bars[i-1].close),Math.abs(b.low-bars[i-1].close)):b.high-b.low);
  const out=Array(bars.length).fill(null);
  if(tr.length<period)return out;
  let value=tr.slice(0,period).reduce((a,b)=>a+b,0)/period;
  out[period-1]=value;
  for(let i=period;i<tr.length;i++)out[i]=value=(value*(period-1)+tr[i])/period;
  return out;
}

export function validateConfig(input={}) {
  const c={...DEFAULT_CONFIG,...input};
  if(!['trend','mean','breakout'].includes(c.kind))throw new Error('Unknown strategy');
  for(const key of Object.keys(DEFAULT_CONFIG).filter(k=>k!=='kind')) {
    c[key]=Number(c[key]);
    if(!Number.isFinite(c[key]))throw new Error(`Invalid ${key}`);
  }
  for(const key of ['fast','slow','period','atrPeriod']) {
    if(!Number.isInteger(c[key])||c[key]<2||c[key]>500)throw new Error(`${key}: 2–500`);
  }
  if(c.fast>=c.slow)throw new Error('Fast EMA must be shorter than slow EMA');
  if(c.risk<=0||c.risk>10||c.capital<=0||c.reward<=0||c.reward>20||c.stopATR<=0||c.deviation<=0||c.feeBps<0||c.feeBps>1000||c.slippageBps<0||c.slippageBps>1000)throw new Error('Check risk, capital, stops and costs');
  return c;
}

export function signalSeries(bars, input) {
  const c=validateConfig(input), close=bars.map(b=>b.close), fast=ema(close,c.fast), slow=ema(close,c.slow), bb=bands(close,c.period,c.deviation), volatility=atr(bars,c.atrPeriod);
  const signals=bars.map((b,i)=>{
    if(i<Math.max(c.slow,c.period,c.atrPeriod)||!volatility[i])return 0;
    if(c.kind==='trend')return fast[i]>slow[i]&&fast[i-1]<=slow[i-1]?1:fast[i]<slow[i]&&fast[i-1]>=slow[i-1]?-1:0;
    if(c.kind==='mean')return close[i-1]<bb[i-1].lower&&close[i]>=bb[i].lower?1:close[i-1]>bb[i-1].upper&&close[i]<=bb[i].upper?-1:0;
    const prior=bars.slice(i-c.period,i);
    return close[i]>Math.max(...prior.map(x=>x.high))?1:close[i]<Math.min(...prior.map(x=>x.low))?-1:0;
  });
  return {signals,fast,slow,bb,atr:volatility};
}

export function resolveExit(position, bar) {
  const {side,stop,target}=position;
  if(side===1) {
    if(bar.open<=stop)return {price:bar.open,reason:'Gap stop'};
    if(bar.open>=target)return {price:target,reason:'Target'};
    if(bar.low<=stop)return {price:stop,reason:'Stop'};
    if(bar.high>=target)return {price:target,reason:'Target'};
  } else {
    if(bar.open>=stop)return {price:bar.open,reason:'Gap stop'};
    if(bar.open<=target)return {price:target,reason:'Target'};
    if(bar.high>=stop)return {price:stop,reason:'Stop'};
    if(bar.low<=target)return {price:target,reason:'Target'};
  }
  return null;
}

export function backtest(rawBars, input={}) {
  const c=validateConfig(input), bars=validateBars(rawBars), data=signalSeries(bars,c);
  if(bars.length<Math.max(c.slow,c.period,c.atrPeriod)+3)throw new Error('Not enough bars for these settings');
  let cash=c.capital,position=null,peak=c.capital,maxDrawdown=0,maxDrawdownPct=0;
  const trades=[],equity=[{time:bars[0].time,value:cash}];
  const fee=c.feeBps/10000,slip=c.slippageBps/10000;
  function closePosition(price,time,reason) {
    const exit=price*(1-position.side*slip),exitFee=Math.abs(exit*position.units)*fee;
    const gross=(exit-position.entry)*position.side*position.units;
    cash+=gross-exitFee;
    trades.push({...position,exit,exitTime:time,reason,pnl:gross-position.entryFee-exitFee,r:(gross-position.entryFee-exitFee)/position.riskCash});
    position=null;
  }
  for(let i=1;i<bars.length;i++) {
    const bar=bars[i];
    if(!position&&data.signals[i-1]&&cash>0) {
      const side=data.signals[i-1],distance=data.atr[i-1]*c.stopATR,entry=bar.open*(1+side*slip),riskCash=cash*c.risk/100;
      const units=riskCash/distance,entryFee=Math.abs(entry*units)*fee;
      position={side,entry,entryTime:bar.time,signalTime:bars[i-1].time,stop:entry-side*distance,target:entry+side*distance*c.reward,units,entryFee,riskCash};
      cash-=entryFee;
    }
    if(position) {
      const exit=resolveExit(position,bar);
      if(exit)closePosition(exit.price,bar.time,exit.reason);
      else if(i===bars.length-1)closePosition(bar.close,bar.time,'End of data');
    }
    const mark=position?cash+(bar.close-position.entry)*position.side*position.units-Math.abs(bar.close*position.units)*fee:cash;
    peak=Math.max(peak,mark);
    maxDrawdown=Math.max(maxDrawdown,peak-mark);
    maxDrawdownPct=Math.max(maxDrawdownPct,(peak-mark)/peak*100);
    equity.push({time:bar.time,value:mark});
  }
  const winners=trades.filter(t=>t.pnl>0),losses=trades.filter(t=>t.pnl<0),grossProfit=winners.reduce((s,t)=>s+t.pnl,0),grossLoss=-losses.reduce((s,t)=>s+t.pnl,0);
  return {config:c,trades,equity,net:cash-c.capital,netPct:(cash/c.capital-1)*100,winRate:trades.length?winners.length/trades.length*100:0,profitFactor:grossLoss?grossProfit/grossLoss:grossProfit?Infinity:null,maxDrawdown,maxDrawdownPct,expectancy:trades.length?(cash-c.capital)/trades.length:0,bars:bars.length,from:bars[0].time,to:bars.at(-1).time};
}

export function validateBars(rows) {
  if(!Array.isArray(rows)||rows.length<2)throw new Error('At least 2 OHLCV rows are required');
  if(rows.length>100000)throw new Error('Maximum 100,000 rows');
  const map=new Map();
  for(let i=0;i<rows.length;i++) {
    const row=rows[i],b={time:Number(row.time),open:Number(row.open),high:Number(row.high),low:Number(row.low),close:Number(row.close),volume:Number(row.volume??0)};
    if(Object.values(b).some(x=>!Number.isFinite(x))||b.time<0||b.open<=0||b.close<=0||b.low<=0||b.high<Math.max(b.open,b.close)||b.low>Math.min(b.open,b.close)||b.volume<0)throw new Error(`Invalid OHLCV row ${i+1}`);
    map.set(b.time,b);
  }
  const out=[...map.values()].sort((a,b)=>a.time-b.time);
  if(out.length<2)throw new Error('At least 2 distinct timestamps are required');
  return out;
}

function splitRow(line,delimiter) {
  const fields=[];let part='',quoted=false;
  for(let i=0;i<line.length;i++) {
    if(line[i]==='"') {if(quoted&&line[i+1]==='"'){part+='"';i++;}else quoted=!quoted;}
    else if(line[i]===delimiter&&!quoted){fields.push(part.trim());part='';}else part+=line[i];
  }
  if(quoted)throw new Error('Unclosed CSV quote');
  fields.push(part.trim());return fields;
}

export function parseCSV(text,offsetMinutes=0) {
  const lines=text.replace(/^\uFEFF/,'').trim().split(/\r?\n/).filter(x=>x.trim());
  if(lines.length<3)throw new Error('CSV needs a header and at least 2 rows');
  const delimiter=['\t',';',','].sort((a,b)=>lines[0].split(b).length-lines[0].split(a).length)[0];
  const header=splitRow(lines[0],delimiter).map(h=>h.toLowerCase().replace(/[<>\s_]/g,''));
  const find=(...names)=>header.findIndex(h=>names.includes(h));
  const columns={time:find('time','timestamp','datetime'),date:find('date'),open:find('open'),high:find('high'),low:find('low'),close:find('close'),volume:find('tickvol','tickvolume','volume','vol')};
  if(['open','high','low','close'].some(k=>columns[k]<0)||(columns.time<0&&columns.date<0))throw new Error('Required columns: time (or date + time), open, high, low, close');
  return validateBars(lines.slice(1).map((line,i)=>{
    const row=splitRow(line,delimiter);let raw=columns.date>=0?row[columns.date]+(columns.time>=0?' '+row[columns.time]:''):row[columns.time];
    let time;
    if(/^\d{10,13}$/.test(raw))time=Number(raw)*(raw.length===10?1000:1);
    else {
      raw=raw.replace(/^(\d{4})\.(\d{2})\.(\d{2})/,'$1-$2-$3').replace(' ','T');
      if(!/(Z|[+-]\d{2}:?\d{2})$/i.test(raw))time=Date.parse(raw+'Z')-offsetMinutes*60000;else time=Date.parse(raw);
    }
    if(!Number.isFinite(time))throw new Error(`Invalid date at CSV row ${i+2}`);
    return {time,open:row[columns.open],high:row[columns.high],low:row[columns.low],close:row[columns.close],volume:columns.volume>=0?row[columns.volume]:0};
  }));
}

export function timeframeMs(tf) {
  if(/^\d+$/.test(tf))return Number(tf)*60000;
  const m=String(tf).match(/^(\d+)?([mhdw])$/i);
  if(!m)throw new Error('Unsupported timeframe');
  return Number(m[1]||1)*({m:60000,h:3600000,d:86400000,w:604800000}[m[2].toLowerCase()]);
}

export function aggregateBars(bars,ms) {
  const result=[];let current=null;
  for(const b of bars) {
    const time=Math.floor(b.time/ms)*ms;
    if(!current||current.time!==time){current={...b,time};result.push(current);}else{current.high=Math.max(current.high,b.high);current.low=Math.min(current.low,b.low);current.close=b.close;current.volume+=(b.volume||0);}
  }
  return result;
}

export function positionSize(balance,riskPct,entry,stop,tickSize,tickValue,lotStep=0.01) {
  const args=[balance,riskPct,entry,stop,tickSize,tickValue,lotStep].map(Number);
  if(args.some(x=>!Number.isFinite(x)||x<=0)||entry===stop||riskPct>10)throw new Error('Enter valid balance, risk, prices and broker tick specifications');
  const risk=balance*riskPct/100,lossPerLot=Math.abs(entry-stop)/tickSize*tickValue;
  const lots=Math.floor((risk/lossPerLot+Number.EPSILON)/lotStep)*lotStep;
  return {lots:Number(lots.toFixed(8)),risk,actualRisk:lots*lossPerLot,lossPerLot};
}
