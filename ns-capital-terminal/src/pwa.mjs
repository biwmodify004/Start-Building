export function setupPWA({doc=document,win=window,language=()=>doc.documentElement.lang||'th',onNetwork=()=>{}}={}){
 const $=id=>doc.getElementById(id),nav=win.navigator,listeners=[];let promptEvent=null,installed=false,destroyed=false;
 const standalone=()=>installed||nav.standalone===true||win.matchMedia?.('(display-mode: standalone)').matches===true;
 const text=(th,en)=>language()==='th'?th:en;
 function listen(target,name,fn){target?.addEventListener(name,fn);listeners.push(()=>target?.removeEventListener(name,fn));}
 function render(){const offline=nav.onLine===false;doc.documentElement.dataset.network=offline?'offline':'online';$('pwa-offline-banner').hidden=!offline;$('network-state').textContent=offline?'OFFLINE':'ONLINE';$('network-state').classList.toggle('offline',offline);
  $('install-confirm').hidden=!promptEvent||standalone();$('install-status').textContent=standalone()?text('กำลังใช้งานเป็นแอปแล้ว','Running as an installed app'):promptEvent?text('เบราว์เซอร์พร้อมให้ติดตั้งแอป','The browser is ready to install this app'):text('เปิดใน Chrome หรือ Safari แล้วติดตั้งจากเมนูเบราว์เซอร์','Open in Chrome or Safari and use the browser installation menu');
  if(offline)$('install-status').textContent=text('ออฟไลน์ · เชื่อมต่ออินเทอร์เน็ตก่อนติดตั้งครั้งแรก','Offline · Connect before the first installation');$('install-confirm').disabled=offline;
 }
 function open(){if($('compact-menu').open)$('compact-menu').close();render();$('install-dialog').showModal();}
 listen($('app-install-btn'),'click',open);
 listen(win,'beforeinstallprompt',event=>{event.preventDefault();promptEvent=event;render();});
 listen(win,'appinstalled',()=>{installed=true;promptEvent=null;render();});
 listen($('install-confirm'),'click',async()=>{if(!promptEvent||nav.onLine===false)return;const event=promptEvent;promptEvent=null;$('install-confirm').disabled=true;try{await event.prompt();await event.userChoice;}catch{$('install-status').textContent=text('ใช้เมนูติดตั้งของเบราว์เซอร์ได้เช่นกัน','Use the browser installation menu');}finally{render();}});
 for(const event of ['online','offline'])listen(win,event,()=>{render();onNetwork(nav.onLine!==false);});
 render();
 if('serviceWorker'in nav&&win.isSecureContext!==false){nav.serviceWorker.register('sw.js',{scope:'/',updateViaCache:'none'}).then(()=>{if(!destroyed)$('install-cache-status').textContent=text('แอปจะพร้อมเปิดออฟไลน์เมื่อบันทึกหน้าแอปครบแล้ว','Offline shell becomes available after its files are saved');}).catch(()=>{if(!destroyed)$('install-cache-status').textContent=text('ยังเปิดออฟไลน์ไม่ได้ ใช้งานออนไลน์และติดตั้งจากเบราว์เซอร์ได้','Offline shell unavailable; use online mode and the browser installation menu');});}
 else $('install-cache-status').textContent=text('เบราว์เซอร์นี้ไม่รองรับการบันทึกหน้าแอปออฟไลน์','This browser does not support the offline app shell');
 return{open,render,destroy(){destroyed=true;for(const off of listeners)off();}};
}
