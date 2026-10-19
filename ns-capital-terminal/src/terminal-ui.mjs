const FONT='Inter, "Noto Sans Thai", "Segoe UI", Tahoma, sans-serif';
export function terminalTheme(mode='dark'){
 const light=mode==='light';
 return {background:light?'#ffffff':'#131722',textColor:light?'#434651':'#b2b5be',gridColor:light?'#f0f3fa':'#1e222d',borderColor:light?'#e0e3eb':'#2a2e39',upColor:'#089981',downColor:'#f23645',fontFamily:FONT};
}
export function styleTerminalChart(chart,mode){
 const palette=terminalTheme(mode);
 chart.setTheme(palette);
 chart.renderer.applyConfig({version:1,layout:{background:palette.background,textColor:palette.textColor,fontFamily:FONT,fontSize:12},grid:{vertLines:{visible:true,color:palette.gridColor},horzLines:{visible:true,color:palette.gridColor}},crosshair:{color:mode==='light'?'#9598a1':'#787b86',labelBackground:mode==='light'?'#787b86':'#363a45'},candles:{upColor:palette.upColor,downColor:palette.downColor,borderUpColor:palette.upColor,borderDownColor:palette.downColor,wickUpColor:palette.upColor,wickDownColor:palette.downColor},bars:{upColor:palette.upColor,downColor:palette.downColor},line:{color:'#2962ff'},area:{lineColor:'#2962ff',topColor:'#2962ff35',bottomColor:'#2962ff00'}});
}
export function styleTerminalWorkspace(workspace,mode){
 workspace.setTheme(terminalTheme(mode));
 for(const cell of workspace.cells())styleTerminalChart(cell.chart,mode);
}
export function setupMarketTabs({doc=document}={}){
 const buttons=[...doc.querySelectorAll('[data-market-tab]')],names=['watchlist','paper','risk'];
 function select(name){if(!names.includes(name))return;doc.getElementById('market-panel').dataset.section=name;
  for(const button of buttons){const active=button.dataset.marketTab===name;button.classList.toggle('active',active);button.setAttribute('aria-selected',String(active));button.tabIndex=active?0:-1;doc.getElementById(button.getAttribute('aria-controls')).hidden=!active;}
 }
 for(const button of buttons){button.addEventListener('click',()=>select(button.dataset.marketTab));button.addEventListener('keydown',event=>{
  const index=buttons.indexOf(button),target=event.key==='ArrowRight'?(index+1)%buttons.length:event.key==='ArrowLeft'?(index+buttons.length-1)%buttons.length:event.key==='Home'?0:event.key==='End'?buttons.length-1:null;
  if(target===null)return;event.preventDefault();select(buttons[target].dataset.marketTab);buttons[target].focus();
 });}
 select('watchlist');return{select};
}
