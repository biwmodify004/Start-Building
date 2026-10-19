import {GLOBAL_MARKETS,MARKET_GROUPS,mountGlobalChart} from './global-markets.mjs';

export function setupConnections({broker,tr,theme,language,onConnect,onDisconnect,onSelect}){
 const $=id=>document.getElementById(id);
 let selected='XAUUSD';
 function renderGlobalList(){
  const markets=GLOBAL_MARKETS.filter(m=>!$('global-category').value||m.group===$('global-category').value);
  const select=$('global-symbol');select.replaceChildren();
  for(const group of Object.keys(MARKET_GROUPS)){const items=markets.filter(m=>m.group===group);if(!items.length)continue;const opt=document.createElement('optgroup');opt.label=MARKET_GROUPS[group][language()==='th'?0:1];for(const m of items){const option=document.createElement('option');option.value=m.symbol;option.textContent=m.symbol+' · '+m.name;opt.append(option);}select.append(opt);}
  if(markets.some(m=>m.symbol===selected))select.value=selected;else selected=markets[0]?.symbol;
 }
 function renderGlobal(){
  const market=GLOBAL_MARKETS.find(m=>m.symbol===$('global-symbol').value);if(!market)return;selected=market.symbol;
  mountGlobalChart($('global-chart'),market,{theme:theme(),locale:language(),interval:$('global-timeframe').value});
  $('global-open').href='https://www.tradingview.com/chart/?symbol='+encodeURIComponent(market.tv);
  $('global-note').textContent=market.tv+' · '+tr('ราคาอ้างอิงจาก OANDA ผ่าน TradingView · ตรวจสถานะข้อมูลที่กราฟแสดง','OANDA reference prices via TradingView · Check the data status displayed on the chart');
 }
 function openGlobal(){renderGlobalList();$('global-dialog').showModal();renderGlobal();}
 function openBroker(){$('broker-dialog').showModal();renderBroker();}
 function renderBroker(){
  const connection=broker.connection,markets=broker.catalog,query=$('broker-search').value.toUpperCase().trim();
  $('broker-catalog').hidden=!connection;$('broker-remote').hidden=!connection;$('broker-mcp-url').value=connection?broker.url+'/mcp':'';
  $('broker-status').textContent=connection?connection.broker+' · '+connection.platform+' · '+markets.length+' '+tr('สินทรัพย์ · เชื่อมต่อ gateway แล้ว','symbols · gateway connected'):tr('ยังไม่ได้เชื่อมต่อ','Not connected');
  $('broker-disconnect').disabled=!connection;
  const select=$('broker-pair'),chosen=select.value;select.replaceChildren();
  for(const market of markets){const option=document.createElement('option');option.value=market.ticker;option.textContent=market.ticker+' · '+market.description;select.append(option);}if(markets.some(m=>m.ticker===chosen))select.value=chosen;
  $('broker-feed-name').textContent=connection?connection.broker+' · '+connection.platform:'';
  const filtered=markets.filter(m=>(m.ticker+' '+m.description+' '+m.type).toUpperCase().includes(query));
  const list=$('broker-market-list');list.replaceChildren();
  const summary=document.createElement('p');summary.className='tiny muted';summary.textContent=filtered.length+' / '+markets.length+' · '+tr('ค้นหาเพื่อเลือกชื่อและ suffix ให้ตรงกับบัญชี','Search for the exact name and suffix in your account');list.append(summary);
  for(const market of filtered.slice(0,200)){const button=document.createElement('button');button.className='broker-market';button.type='button';const name=document.createElement('strong');name.textContent=market.ticker;const detail=document.createElement('span');detail.textContent=market.description+' · '+market.currency;button.append(name,detail);button.addEventListener('click',async()=>{await onSelect(market.ticker);$('broker-dialog').close();});list.append(button);}
  if(filtered.length>200){const help=document.createElement('p');help.className='tiny muted';help.textContent=tr('แสดง 200 รายการแรก ใช้ช่องค้นหาด้านบน หรือเลือกได้ทุกสินทรัพย์จากรายการ BROKER เหนือกราฟ','Showing the first 200. Search to narrow the list, or use the complete BROKER selector above the chart.');list.append(help);}
 }
 $('global-markets-btn').addEventListener('click',openGlobal);
 $('global-category').addEventListener('change',()=>{renderGlobalList();renderGlobal();});
 for(const id of ['global-symbol','global-timeframe'])$(id).addEventListener('change',renderGlobal);
 $('global-dialog').addEventListener('close',()=>$('global-chart').replaceChildren());
 $('global-to-broker').addEventListener('click',()=>{$('global-dialog').close();$('broker-search').value=selected;openBroker();});
 $('broker-btn').addEventListener('click',openBroker);$('broker-manage').addEventListener('click',openBroker);
 $('broker-search').addEventListener('input',renderBroker);
 $('broker-form').addEventListener('submit',async event=>{
  event.preventDefault();$('broker-connect').disabled=true;$('broker-error').textContent='';$('broker-status').textContent=tr('กำลังตรวจ terminal และโหลดสินทรัพย์…','Checking terminal and loading symbols…');
  try{await broker.connect({url:$('broker-url').value,token:$('broker-token').value});$('broker-token').value='';await onConnect();renderBroker();}
  catch(error){renderBroker();$('broker-error').textContent=error.message+tr(' · ตรวจว่า gateway เปิดอยู่ Token ถูกต้อง และ browser เข้าถึง URL ได้',' · Check that the gateway is running, the token is correct, and the URL is reachable from this browser');}
  finally{$('broker-connect').disabled=false;}
 });
 $('broker-refresh').addEventListener('click',async()=>{try{await broker.listSymbols();renderBroker();}catch(error){$('broker-error').textContent=error.message;}});
 $('broker-disconnect').addEventListener('click',async()=>{await onDisconnect();$('broker-token').value='';renderBroker();});
 $('broker-pair').addEventListener('change',()=>onSelect($('broker-pair').value));
 renderGlobalList();renderBroker();
 return {openGlobal,openBroker,renderBroker,refreshLanguage(){renderGlobalList();if($('global-dialog').open)renderGlobal();renderBroker();},refreshTheme(){if($('global-dialog').open)renderGlobal();}};
}
