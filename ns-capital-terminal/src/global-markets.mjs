// Public chart widgets render their own licensed data. Prices are never scraped
// from the iframe or passed off as Axi quotes / Vela backtest inputs.
export const GLOBAL_MARKETS=[
 {symbol:'XAUUSD',name:'Gold · ทองคำ',group:'metals',tv:'OANDA:XAUUSD'},
 {symbol:'XAGUSD',name:'Silver · เงิน',group:'metals',tv:'OANDA:XAGUSD'},
 ...['EURUSD','GBPUSD','USDJPY','USDCHF','USDCAD','AUDUSD','NZDUSD'].map(symbol=>({symbol,name:symbol.slice(0,3)+' / '+symbol.slice(3),group:'majors',tv:'OANDA:'+symbol})),
 {symbol:'GBPJPY',name:'GBP / JPY',group:'crosses',tv:'OANDA:GBPJPY'},
 ...[
  ['US30','Dow Jones CFD','US30USD'],['NAS100','Nasdaq 100 CFD','NAS100USD'],
  ['SPX500','S&P 500 CFD','SPX500USD'],['GER40','Germany CFD','DE30EUR'],
  ['UK100','FTSE 100 CFD','UK100GBP'],['JP225','Japan 225 CFD','JP225USD'],
  ['AU200','Australia 200 CFD','AU200AUD'],['HK33','Hong Kong CFD','HK33HKD']
 ].map(([symbol,name,ticker])=>({symbol,name,group:'indices',tv:'OANDA:'+ticker}))
];
export const MARKET_GROUPS={metals:['ทอง / เงิน','Gold / Silver'],majors:['Forex คู่หลัก','Forex majors'],crosses:['Forex คู่รอง','Forex crosses'],indices:['ดัชนี CFD','Index CFDs']};
export function widgetConfig(market,{theme='dark',locale='th',interval='15'}={}){
 if(!GLOBAL_MARKETS.includes(market))throw new Error('Unknown global market');
 if(!['1','5','15','60','240','D'].includes(interval))throw new Error('Unsupported widget interval');
 return {autosize:true,symbol:market.tv,interval,timezone:'Asia/Bangkok',theme:theme==='light'?'light':'dark',style:'1',locale:locale==='th'?'th':'en',allow_symbol_change:false,hide_side_toolbar:false,hide_top_toolbar:false,save_image:true,withdateranges:true,calendar:false,details:false,hotlist:false,watchlist:[],support_host:'https://www.tradingview.com'};
}
export function mountGlobalChart(container,market,options={}){
 const config=widgetConfig(market,options),doc=container.ownerDocument;
 container.replaceChildren();
 const wrap=doc.createElement('div');wrap.className='tradingview-widget-container';
 const chart=doc.createElement('div');chart.className='tradingview-widget-container__widget';wrap.append(chart);
 const attribution=doc.createElement('div');attribution.className='tradingview-widget-copyright';
 const link=doc.createElement('a');link.href='https://www.tradingview.com/symbols/'+market.tv.replace(':','-')+'/';link.target='_blank';link.rel='noopener nofollow';link.textContent=market.tv+' chart by TradingView';attribution.append(link);wrap.append(attribution);
 const script=doc.createElement('script');script.type='text/javascript';script.src='https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';script.async=true;script.textContent=JSON.stringify(config);script.onerror=()=>{container.dataset.loadError='true';};wrap.append(script);container.append(wrap);delete container.dataset.loadError;
 return config;
}
