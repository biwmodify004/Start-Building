import {bridgeURL} from './broker.mjs';
export function accountKey(account){if(!account||!String(account.id||'').trim()||!String(account.server||'').trim())throw new Error('Update Broker Bridge to read the actual account ID and server');return String(account.server).trim()+'|'+String(account.id).trim();}
export function maskedAccount(account){const id=String(account?.id||'');return id?'•••• '+id.slice(-4):'—';}
const KEY='ns-capital-trading-accounts-v1';
export class TradingAccounts{
 #tokens=new Map();
 #tradeTokens=new Map();
 constructor({storage=globalThis.localStorage}={}){this.storage=storage;this.profiles=[];this.activeId=null;try{const data=JSON.parse(storage.getItem(KEY));if(Array.isArray(data))for(const p of data){try{if(!/^[a-z0-9]{8,40}$/.test(p.id))continue;this.profiles.push({id:p.id,label:String(p.label||p.broker).slice(0,80),url:bridgeURL(p.url),broker:String(p.broker||'').slice(0,160),platform:String(p.platform||''),account:{id:String(p.account.id),server:String(p.account.server),currency:String(p.account.currency||'')},kind:['cfd','futures','all'].includes(p.kind)?p.kind:'all',accountKey:accountKey(p.account)});}catch{}}}catch{}}
 save(){this.storage.setItem(KEY,JSON.stringify(this.profiles));}
 get(id){return this.profiles.find(p=>p.id===id);}
 token(id){return this.#tokens.get(id)||'';}
 tradeToken(id){return this.#tradeTokens.get(id)||'';}
 add({label,url,kind='all',status,token,tradeToken=''}){
  const key=accountKey(status.account),endpoint=bridgeURL(url);if(!status.connected||typeof status.readOnly!=='boolean')throw new Error('Connect and verify the trading terminal first');
  let profile=this.profiles.find(p=>p.url===endpoint&&p.accountKey===key);
  if(!profile){profile={id:crypto.randomUUID().replaceAll('-','')};this.profiles.push(profile);}
  Object.assign(profile,{label:String(label||status.broker).trim().slice(0,80),url:endpoint,kind:['cfd','futures','all'].includes(kind)?kind:'all',broker:String(status.broker).slice(0,160),platform:String(status.platform),account:{id:String(status.account.id),server:String(status.account.server),currency:String(status.account.currency||'')},accountKey:key});
  this.#tokens.set(profile.id,token);this.#tradeTokens.set(profile.id,tradeToken);this.activeId=profile.id;this.save();return profile;
 }
 signOut(){this.#tokens.clear();this.#tradeTokens.clear();this.activeId=null;}
 disconnect(){this.activeId=null;}
 remove(id){this.profiles=this.profiles.filter(p=>p.id!==id);this.#tokens.delete(id);this.#tradeTokens.delete(id);if(this.activeId===id)this.activeId=null;this.save();}
}
