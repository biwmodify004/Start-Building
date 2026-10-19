import {TradingAccounts,maskedAccount} from './accounts.mjs';
import {GLOBAL_MARKETS,MARKET_GROUPS,mountGlobalChart} from './global-markets.mjs';

export function setupConnections({broker,tr,theme,language,onConnect,onDisconnect,onSelect}){
 const $=id=>document.getElementById(id);
 const accounts=new TradingAccounts();let editingId=null,busy=false;
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
 function renderAccounts(){
  const list=$('account-list');list.replaceChildren();$('account-new').disabled=busy;
  if(!accounts.profiles.length){const empty=document.createElement('div');empty.className='account-empty';empty.textContent=tr('ยังไม่มีบัญชี · เพิ่ม MT4/MT5 ของคุณด้านล่าง','No accounts yet · Add your MT4/MT5 terminal below');list.append(empty);}
  for(const profile of accounts.profiles){
   const active=accounts.activeId===profile.id&&!!broker.connection,row=document.createElement('div');row.className='account-row'+(active?' active':'');
   const icon=document.createElement('span');icon.className='account-icon';icon.textContent=profile.platform;
   const info=document.createElement('div');info.className='account-info';const title=document.createElement('strong'),detail=document.createElement('small');title.textContent=profile.label;detail.textContent=profile.broker+' · '+maskedAccount(profile.account)+' · '+profile.account.server+' · '+(active?tr('เลือกอยู่','Selected'):tr('รอเชื่อมต่อ','Not connected'));info.append(title,detail);
   const connect=document.createElement('button');connect.type='button';connect.className='quiet account-activate';connect.textContent=active?tr('เลือกอยู่','Selected'):tr('เชื่อมต่อ','Connect');connect.disabled=busy||active;connect.dataset.accountId=profile.id;
   connect.addEventListener('click',()=>{editingId=profile.id;$('broker-search').value='';$('account-label').value=profile.label;$('account-kind').value=profile.kind;$('broker-url').value=profile.url;$('broker-token').value=accounts.token(profile.id);$('broker-error').textContent='';if(accounts.token(profile.id))$('broker-form').requestSubmit();else $('broker-token').focus();});
   const remove=document.createElement('button');remove.type='button';remove.className='square account-remove';remove.setAttribute('aria-label',tr('ลบบัญชี ','Remove account ')+profile.label);remove.textContent='×';remove.disabled=busy;remove.addEventListener('click',async()=>{if(active){await onDisconnect();accounts.disconnect();}accounts.remove(profile.id);if(editingId===profile.id)newAccount();renderBroker();});
   row.append(icon,info,connect,remove);list.append(row);
  }
 }
 function newAccount(){editingId=null;$('broker-search').value='';$('account-label').value='';$('account-kind').value='all';$('broker-url').value='http://127.0.0.1:8787';$('broker-token').value='';$('broker-error').textContent='';$('account-label').focus();}
 function renderSummary(){
  const account=broker.connection?.account,summary=$('account-summary');summary.replaceChildren();summary.hidden=!account;
  if(!account)return;for(const [label,value]of [[tr('บัญชี','Account'),maskedAccount(account)+' · '+(account.mode||'')],[tr('ยอดเงิน','Balance'),account.balance],[tr('อิควิตี้','Equity'),account.equity]]){const item=document.createElement('div'),caption=document.createElement('small'),amount=document.createElement('strong');caption.textContent=label;amount.textContent=typeof value==='number'?value.toLocaleString('en-US',{maximumFractionDigits:2})+' '+(account.currency||''):String(value??'—');item.append(caption,amount);summary.append(item);}
 }
 function renderBroker(){
  const connection=broker.connection,markets=broker.catalog,query=$('broker-search').value.toUpperCase().trim();renderAccounts();renderSummary();
  $('broker-catalog').hidden=!connection;$('broker-remote').hidden=!connection;$('broker-mcp-url').value=connection?broker.url+'/mcp':'';
  $('broker-status').textContent=connection?connection.broker+' · '+connection.platform+' · '+maskedAccount(connection.account)+' · '+markets.length+' '+tr('สินทรัพย์ · เชื่อมต่อ gateway แล้ว','symbols · gateway connected'):tr('ยังไม่ได้เชื่อมต่อ','Not connected');
  $('broker-disconnect').disabled=busy||!connection;
  const select=$('broker-pair'),chosen=select.value;select.replaceChildren();
  for(const market of markets){const option=document.createElement('option');option.value=market.ticker;option.textContent=market.ticker+' · '+market.description;select.append(option);}if(markets.some(m=>m.ticker===chosen))select.value=chosen;
  $('broker-feed-name').textContent=connection?connection.broker+' · '+connection.platform:'';
  const filtered=markets.filter(m=>($('broker-asset-class').value==='all'||(m.assetClass||'other')===$('broker-asset-class').value)&&(m.ticker+' '+m.description+' '+m.type).toUpperCase().includes(query));
  const list=$('broker-market-list');list.replaceChildren();
  const summary=document.createElement('p');summary.className='tiny muted';summary.textContent=filtered.length+' / '+markets.length+' · '+tr('ค้นหาเพื่อเลือกชื่อและ suffix ให้ตรงกับบัญชี','Search for the exact name and suffix in your account');list.append(summary);
  for(const market of filtered.slice(0,200)){const button=document.createElement('button');button.className='broker-market';button.type='button';const name=document.createElement('strong');name.textContent=market.ticker;const detail=document.createElement('span');detail.textContent=market.description+' · '+market.currency+' · '+(market.assetClass==='futures'?'Futures':market.assetClass==='cfd'?'CFD / Forex':'Other')+(market.expiry?' · '+new Date(market.expiry).toISOString().slice(0,10):'');button.append(name,detail);button.addEventListener('click',async()=>{await onSelect(market.ticker);$('broker-dialog').close();});list.append(button);}
  if(!filtered.length){const empty=document.createElement('div');empty.className='empty';empty.textContent=tr('บัญชีนี้ไม่มีสัญญาที่ตรงตัวกรอง · ตรวจรายการใน Terminal','No matching contracts in this account · Check the terminal catalog');list.append(empty);}
  if(filtered.length>200){const help=document.createElement('p');help.className='tiny muted';help.textContent=tr('แสดง 200 รายการแรก ใช้ช่องค้นหาด้านบน หรือเลือกได้ทุกสินทรัพย์จากรายการ BROKER เหนือกราฟ','Showing the first 200. Search to narrow the list, or use the complete BROKER selector above the chart.');list.append(help);}
 }
 $('global-markets-btn').addEventListener('click',openGlobal);
 $('global-category').addEventListener('change',()=>{renderGlobalList();renderGlobal();});
 for(const id of ['global-symbol','global-timeframe'])$(id).addEventListener('change',renderGlobal);
 $('global-dialog').addEventListener('close',()=>$('global-chart').replaceChildren());
 $('global-to-broker').addEventListener('click',()=>{$('global-dialog').close();$('broker-search').value=selected;openBroker();});
 $('broker-btn').addEventListener('click',openBroker);$('broker-manage').addEventListener('click',openBroker);
 $('account-new').addEventListener('click',newAccount);$('broker-asset-class').addEventListener('change',renderBroker);
 $('broker-search').addEventListener('input',renderBroker);
 $('broker-form').addEventListener('submit',async event=>{
  event.preventDefault();if(busy)return;busy=true;$('broker-connect').disabled=true;$('broker-disconnect').disabled=true;renderAccounts();$('broker-error').textContent='';$('broker-status').textContent=tr('กำลังตรวจ terminal และโหลดสินทรัพย์…','Checking terminal and loading symbols…');
  try{const url=$('broker-url').value,token=$('broker-token').value,profile=accounts.get(editingId),label=$('account-label').value,kind=$('account-kind').value;await onDisconnect();accounts.disconnect();const status=await broker.connect({url,token,expectedAccount:profile?.accountKey});const added=accounts.add({label,url,kind,status,token});editingId=added.id;$('broker-token').value='';$('broker-asset-class').value=kind;await onConnect(added);renderBroker();}
  catch(error){await onDisconnect();accounts.disconnect();renderBroker();$('broker-error').textContent=error.message+tr(' · ตรวจว่า gateway เปิดอยู่ Token ถูกต้อง และ browser เข้าถึง URL ได้',' · Check that the gateway is running, the token is correct, and the URL is reachable from this browser');}
  finally{busy=false;$('broker-connect').disabled=false;$('broker-disconnect').disabled=!broker.connection;renderAccounts();}
 });
 $('broker-refresh').addEventListener('click',async()=>{try{const status=await broker.request('/v1/status');if(!status.connected||broker.connectionKey(status)!==broker.accountIdentity)throw new Error('Trading account changed. Reconnect the account');broker.connection=status;await broker.listSymbols();renderBroker();}catch(error){$('broker-error').textContent=error.message;}});
 $('broker-disconnect').addEventListener('click',async()=>{await onDisconnect();accounts.disconnect();$('broker-token').value='';renderBroker();});
 $('broker-pair').addEventListener('change',()=>onSelect($('broker-pair').value));
 renderGlobalList();renderBroker();
 return {openGlobal,openBroker,renderBroker,refreshLanguage(){renderGlobalList();if($('global-dialog').open)renderGlobal();renderBroker();},refreshTheme(){if($('global-dialog').open)renderGlobal();}};
}
