import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {JSDOM} from 'jsdom';
import {setupResponsive} from '../src/responsive.mjs';
import {setupMarketTabs} from '../src/terminal-ui.mjs';

// DOM behavior only: no browser layout, device pixels or canvas rendering are simulated.
const html=await readFile(new URL('../src/index.html',import.meta.url),'utf8');
function fixture(width=390,height=844){
 const dom=new JSDOM(html,{url:'https://terminal.test/'}),win=dom.window,doc=win.document,$=id=>doc.getElementById(id);
 Object.defineProperties(win,{innerWidth:{value:width,writable:true,configurable:true},innerHeight:{value:height,writable:true,configurable:true}});
 const viewport=new win.EventTarget();Object.assign(viewport,{height,width,scale:1});Object.defineProperty(win,'visualViewport',{value:viewport,configurable:true});
 win.HTMLDialogElement.prototype.showModal=function(){this.open=true;};win.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new win.Event('close'));};
 setupMarketTabs({doc});let openedMarkets=0;const controller=setupResponsive({doc,win,onMarkets:()=>{openedMarkets++;}});
 return{dom,win,doc,$,viewport,controller,markets:()=>openedMarkets,button:view=>doc.querySelector('[data-compact-view="'+view+'"]'),resize(w,h){win.innerWidth=w;win.innerHeight=h;viewport.height=h;win.dispatchEvent(new win.Event('resize'));},destroy(){controller.destroy();dom.window.close();}};
}
test('phone drawers are exclusive, block background focus, and restore their opener',()=>{
 const f=fixture();try{
  assert.equal(f.doc.documentElement.dataset.viewport,'phone');assert.ok(f.$('analysis-panel').classList.contains('collapsed'));assert.equal(f.$('analysis-toggle').getAttribute('aria-expanded'),'false');
  assert.equal(f.$('research-panel').inert,true);f.button('research').focus();f.button('research').click();
  assert.equal(f.$('research-panel').getAttribute('aria-modal'),'true');assert.equal(f.$('drawer-backdrop').hidden,false);assert.equal(f.doc.querySelector('.workspace-main').inert,true);assert.equal(f.doc.activeElement,f.$('research-close'));
  f.controller.togglePanel('watchlist',f.button('watchlist'));assert.equal(f.$('research-panel').inert,true);assert.equal(f.$('market-panel').inert,false);assert.ok(!f.doc.body.classList.contains('mobile-research'));
  f.$('drawer-backdrop').click();assert.equal(f.$('drawer-backdrop').hidden,true);assert.equal(f.doc.querySelector('.workspace-main').inert,false);assert.equal(f.doc.activeElement,f.button('watchlist'));
  f.button('research').click();f.doc.dispatchEvent(new f.win.KeyboardEvent('keydown',{key:'Escape',bubbles:true}));assert.equal(f.$('research-panel').inert,true);assert.equal(f.doc.activeElement,f.button('research'));
 }finally{f.destroy();}
});
test('drawer keyboard navigation remains inside the panel and watchlist selection closes it',()=>{
 const f=fixture();try{
  f.button('watchlist').click();f.$('market-tab-risk').click();const input=f.$('risk-lot-step');input.focus();f.doc.dispatchEvent(new f.win.KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true}));assert.equal(f.doc.activeElement,f.$('watch-add'));
  f.$('watch-add').focus();f.doc.dispatchEvent(new f.win.KeyboardEvent('keydown',{key:'Tab',shiftKey:true,bubbles:true,cancelable:true}));assert.equal(f.doc.activeElement,input);
  const row=f.doc.createElement('button');row.dataset.symbol='binance:BTCUSDT';f.$('watchlist').append(row);row.click();assert.equal(f.$('market-panel').inert,true);assert.equal(f.$('drawer-backdrop').hidden,true);
 }finally{f.destroy();}
});
test('compact menu forwards each action to the existing control and closes before opening a dialog',()=>{
 const f=fixture(820,1180);try{
  const targets=[...f.doc.querySelectorAll('[data-menu-target]')];assert.equal(targets.length,9);assert.ok(targets.every(button=>f.$(button.dataset.menuTarget)));
  let calls=0;f.$('broker-btn').addEventListener('click',()=>{assert.equal(f.$('compact-menu').open,false);calls++;f.$('broker-dialog').showModal();});
  f.button('more').click();assert.equal(f.$('compact-menu').open,true);f.doc.querySelector('[data-menu-target="broker-btn"]').click();assert.equal(calls,1);assert.equal(f.$('broker-dialog').open,true);
  f.$('broker-dialog').close();f.button('markets').click();assert.equal(f.markets(),1);assert.equal(f.$('drawer-backdrop').hidden,true);
 }finally{f.destroy();}
});
test('rotation and desktop resizing clear modal state while retaining input and desktop panel preference',()=>{
 const f=fixture();try{
  f.$('journal-input').value='Preserve my research';f.button('research').click();f.resize(820,1180);
  assert.equal(f.controller.mode(),'tablet');assert.equal(f.$('drawer-backdrop').hidden,true);assert.equal(f.$('research-panel').inert,true);assert.equal(f.$('journal-input').value,'Preserve my research');
  f.resize(1180,820);assert.equal(f.controller.mode(),'tablet');f.resize(1366,1024);assert.equal(f.controller.mode(),'desktop');assert.equal(f.$('research-panel').inert,false);assert.equal(f.$('market-panel').inert,false);
  f.$('left-toggle').click();assert.ok(f.doc.body.classList.contains('no-left'));f.resize(390,844);f.button('research').click();assert.equal(f.$('research-panel').inert,false);f.resize(1366,1024);assert.equal(f.$('research-panel').inert,true);assert.equal(f.$('drawer-backdrop').hidden,true);
 }finally{f.destroy();}
});
test('keyboard and visual viewport changes preserve the active journal instead of collapsing it',()=>{
 const f=fixture();try{
  f.$('analysis-panel').classList.remove('collapsed');f.$('journal-input').value='Typing with the keyboard open';f.$('journal-input').focus();
  f.viewport.height=380;f.viewport.dispatchEvent(new f.win.Event('resize'));assert.equal(f.doc.documentElement.style.getPropertyValue('--app-height'),'380px');assert.ok(!f.$('analysis-panel').classList.contains('collapsed'));
  f.win.innerHeight=380;f.win.dispatchEvent(new f.win.Event('resize'));assert.ok(!f.$('analysis-panel').classList.contains('collapsed'));assert.equal(f.$('journal-input').value,'Typing with the keyboard open');
  f.viewport.scale=2;f.viewport.height=190;f.viewport.dispatchEvent(new f.win.Event('resize'));assert.equal(f.doc.documentElement.style.getPropertyValue('--app-height'),'380px');
  f.$('journal-input').blur();f.resize(390,844);f.resize(844,390);assert.ok(f.doc.body.classList.contains('short-viewport'));assert.ok(f.$('analysis-panel').classList.contains('collapsed'));
 }finally{f.destroy();}
});
