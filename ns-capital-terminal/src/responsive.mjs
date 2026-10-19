// Host layout only. Vela keeps its chart/data instances and handles its own
// touch chrome and canvas resizing through its supported automatic layout mode.
export function viewportMode(width){return width<=767?'phone':width<=1180?'tablet':'desktop';}

export function setupResponsive({doc=document,win=window,onMarkets=()=>{},onChart=()=>{}}={}){
 const $=id=>doc.getElementById(id),body=doc.body,root=doc.documentElement;
 let mode=null,panel=null,returnFocus=null,wasShort=false;
 const listeners=[];
 function listen(target,name,fn){target?.addEventListener(name,fn);listeners.push(()=>target?.removeEventListener(name,fn));}
 function syncAnalysis(){const expanded=!$('analysis-panel').classList.contains('collapsed');$('analysis-toggle').setAttribute('aria-expanded',String(expanded));$('analysis-toggle').textContent=expanded?'⌄':'⌃';}
 function sync(){
  const compact=mode!=='desktop',research=compact?panel==='research':!body.classList.contains('no-left'),market=compact?panel==='watchlist':!body.classList.contains('no-right');
  body.classList.toggle('mobile-research',compact&&panel==='research');body.classList.toggle('show-market',compact&&panel==='watchlist');
  $('drawer-backdrop').hidden=!compact||!panel;
  for(const [id,visible]of [['research-panel',research],['market-panel',market]]){const el=$(id);el.inert=!visible;el.setAttribute('aria-hidden',String(!visible));if(compact&&visible){el.setAttribute('role','dialog');el.setAttribute('aria-modal','true');}else{el.removeAttribute('role');el.removeAttribute('aria-modal');}}
  for(const el of doc.querySelectorAll('.workspace-main,.app-header,#compact-nav,.app-footer'))el.inert=compact&&!!panel;
  $('left-toggle').setAttribute('aria-expanded',String(research));$('right-toggle').setAttribute('aria-expanded',String(market));
  for(const button of doc.querySelectorAll('[data-compact-view]')){
   const active=button.dataset.compactView===(panel||'chart');button.classList.toggle('active',active);
   if(active)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');
   if(['research','watchlist'].includes(button.dataset.compactView))button.setAttribute('aria-expanded',String(button.dataset.compactView===panel));
  }
 }
 function closePanel(restoreFocus=false){panel=null;sync();if(restoreFocus&&returnFocus?.isConnected)returnFocus.focus();returnFocus=null;}
 function togglePanel(name,opener){
  if(!['research','watchlist'].includes(name))return;
  if(mode==='desktop'){body.classList.toggle(name==='research'?'no-left':'no-right');sync();return;}
  if(panel===name){closePanel(true);return;}
  returnFocus=opener||doc.activeElement;panel=name;body.classList.remove('focus');sync();$(name==='research'?'research-close':'market-close').focus();
 }
 function refresh(){
  const width=win.innerWidth||root.clientWidth||1280,height=win.innerHeight||800;
  const visual=win.visualViewport,effectiveHeight=visual&&(!visual.scale||Math.abs(visual.scale-1)<.01)&&visual.height>0?Math.min(height,visual.height):height;
  root.style.setProperty('--app-height',Math.max(144,Math.round(effectiveHeight))+'px');
  const next=viewportMode(width),short=height<=560,editing=doc.activeElement?.matches('input,textarea,select,[contenteditable="true"]');
  if(next!==mode){panel=null;mode=next;root.dataset.viewport=mode;body.classList.toggle('compact-layout',mode!=='desktop');body.classList.toggle('phone-layout',mode==='phone');
   if(!editing){if(mode==='phone'||short)$('analysis-panel').classList.add('collapsed');else $('analysis-panel').classList.remove('collapsed');}
   if(mode==='desktop'&&$('compact-menu').open)$('compact-menu').close();
  }else if(short&&!wasShort&&!editing)$('analysis-panel').classList.add('collapsed');
  body.classList.toggle('short-viewport',short);wasShort=short;sync();syncAnalysis();
 }
 function openMenu(){closePanel();$('compact-menu').showModal();}
 listen($('left-toggle'),'click',event=>togglePanel('research',event.currentTarget));
 listen($('right-toggle'),'click',event=>togglePanel('watchlist',event.currentTarget));
 listen($('research-close'),'click',()=>closePanel(true));listen($('market-close'),'click',()=>closePanel(true));listen($('drawer-backdrop'),'click',()=>closePanel(true));
 listen($('compact-menu-btn'),'click',openMenu);
 listen($('analysis-toggle'),'click',syncAnalysis);
 listen($('compact-nav'),'click',event=>{
  const button=event.target.closest('[data-compact-view]');if(!button)return;
  const action=button.dataset.compactView;
  if(action==='research'||action==='watchlist')togglePanel(action,button);
  else if(action==='more')openMenu();
  else if(action==='markets'){closePanel();onMarkets();}
  else{closePanel();body.classList.remove('focus');if(mode==='phone'||wasShort)$('analysis-panel').classList.add('collapsed');onChart();}
 });
 listen($('compact-menu'),'click',event=>{
  const button=event.target.closest('[data-menu-target]');if(!button)return;
  const target=$(button.dataset.menuTarget);$('compact-menu').close();closePanel();target?.click();
 });
 listen($('watchlist'),'click',event=>{if(event.target.closest('[data-symbol]')&&mode!=='desktop')closePanel();});
 listen(doc,'keydown',event=>{
  if(event.key==='Escape'){body.classList.remove('focus');closePanel(true);}
  if(event.key==='Tab'&&panel&&mode!=='desktop'){
   const drawer=$(panel==='research'?'research-panel':'market-panel'),items=[...drawer.querySelectorAll('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href]')].filter(el=>!el.closest('[hidden]'));
   const first=items[0],last=items.at(-1);if(!first)return;
   if(!drawer.contains(doc.activeElement)){event.preventDefault();first.focus();}
   else if(event.shiftKey&&doc.activeElement===first){event.preventDefault();last.focus();}
   else if(!event.shiftKey&&doc.activeElement===last){event.preventDefault();first.focus();}
  }
 });
 listen(win,'resize',refresh);listen(win,'orientationchange',refresh);listen(win.visualViewport,'resize',refresh);
 refresh();
 return{refresh,closePanel,togglePanel,syncAnalysis,mode:()=>mode,destroy(){closePanel();for(const off of listeners)off();}};
}
