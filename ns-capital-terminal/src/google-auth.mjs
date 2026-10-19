import {bridgeURL} from './broker.mjs';

export function loadGoogleIdentity(doc=document,win=window){
 if(win.google?.accounts?.id)return Promise.resolve(win.google.accounts.id);
 return new Promise((resolve,reject)=>{
  doc.getElementById('google-identity-sdk')?.remove();
  const script=doc.createElement('script');script.id='google-identity-sdk';script.src='https://accounts.google.com/gsi/client';script.async=true;
  const timer=win.setTimeout(()=>finish(new Error('Google Identity Services ไม่ตอบกลับ กรุณาลองใหม่')),15000);
  function finish(error){win.clearTimeout(timer);script.onload=script.onerror=null;if(error){script.remove();reject(error);}else if(win.google?.accounts?.id)resolve(win.google.accounts.id);else reject(new Error('Google Identity Services ไม่พร้อม'));}
  script.onload=()=>finish();script.onerror=()=>finish(new Error('โหลด Google Login ไม่ได้ ตรวจการเชื่อมต่อหรือส่วนขยายที่บล็อก Google'));doc.head.append(script);
 });
}

export function setupGoogleLogin({broker,connections,onLocalLogout=()=>{},doc=document,win=window,fetchImpl=globalThis.fetch?.bind(globalThis),loadSDK=()=>loadGoogleIdentity(doc,win),now=()=>Date.now()}={}){
 const $=id=>doc.getElementById(id),sessions=new Map();let epoch=0,loaded=null,closed=false,busy=false;
 async function request(url,path,body,token){
  if(win.navigator.onLine===false)throw new Error('ออฟไลน์ ไม่สามารถเข้าสู่ระบบได้');
  let response;try{response=await fetchImpl(url+path,{method:body?'POST':'GET',headers:{...(body?{'Content-Type':'application/json'}:{}),...(token?{Authorization:'Bearer '+token}:{})},...(body?{body:JSON.stringify(body)}:{}),credentials:'omit',redirect:'error',cache:'no-store',signal:AbortSignal.timeout(20000)});}catch{throw new Error('เชื่อม Backend ไม่ได้ ตรวจว่า Bridge เปิดอยู่, URL/Port, HTTPS, NS_ALLOWED_ORIGINS และสิทธิ์ Local network ของเบราว์เซอร์');}
  let data;try{data=await response.json();}catch{throw new Error('Backend ไม่ใช่ NS Broker Bridge หรือส่งข้อมูลไม่ถูกต้อง');}
  if(!response.ok){if(path==='/v1/auth/config'&&response.status===401)throw new Error('Bridge รุ่นนี้ยังไม่มี Google Login ให้อัปเดตชุด Broker Bridge รุ่น 1.9 แล้วเริ่มใหม่');throw new Error(data.error||'Google Login HTTP '+response.status);}return data;
 }
 function render(){
  const session=sessions.get(broker.token),valid=session&&session.expiresAt>now()&&broker.connection;
  $('member-google-user').textContent=valid?session.user.name+' · '+session.user.email:broker.connection?'เชื่อมด้วย Token โดยตรง · ยังไม่ได้เข้าสู่ระบบ Google':'ยังไม่ได้เข้าสู่ระบบ Google';
  const mark=$('member-btn').querySelector('span');if(mark)mark.textContent=valid?(session.user.name||'G').slice(0,1).toUpperCase():'N';
  $('google-auth-prepare').disabled=busy||win.navigator.onLine===false;
 }
 function open(){epoch++;busy=false;loaded=null;$('google-auth-url').value=broker.url||$('broker-url')?.value||'http://127.0.0.1:8787';$('google-auth-trade-token').value='';$('google-auth-error').textContent='';$('google-auth-button').replaceChildren();if(!$('google-auth-dialog').open)$('google-auth-dialog').showModal();render();}
 async function revoke(session){try{await request(session.url,'/v1/auth/logout',{},session.token);}catch{/* Local sign-out still clears credentials when the server is unavailable. */}}
 async function receive(result,c){
  if(c.epoch!==epoch||closed||!$('google-auth-dialog').open)return;
  busy=true;render();let session;
  try{
   if(typeof result?.credential!=='string')throw new Error('Google ไม่ได้ส่ง ID token ที่ตรวจสอบได้');
   const data=await request(c.url,'/v1/auth/google',{credential:result.credential,challengeId:c.challenge.challengeId});
   if(typeof data.token!=='string'||data.token.length<32||!Number.isFinite(data.expiresAt)||data.expiresAt<=now()||data.user?.provider!=='google'||typeof data.accountKey!=='string')throw new Error('เซสชัน Google จาก Backend ไม่ถูกต้อง');
   session={url:c.url,...data};
   if(c.epoch!==epoch||c.generation!==broker.generation||closed){await revoke(session);return;}
   const tradeToken=$('google-auth-trade-token').value;await connections.connectWithGoogle({url:c.url,token:session.token,tradeToken,accountKey:session.accountKey,user:session.user});
   if(c.epoch!==epoch||closed){if(broker.token===session.token)await onLocalLogout();await revoke(session);return;}
   sessions.set(session.token,session);$('google-auth-trade-token').value='';$('google-auth-dialog').close();$('member-dialog').open&&$('member-dialog').close();render();
  }catch(error){if(session)await revoke(session);if(c.epoch===epoch)$('google-auth-error').textContent=error.message;}
  finally{if(c.epoch===epoch){busy=false;render();}}
 }
 $('google-auth-prepare').addEventListener('click',async()=>{
  if(busy)return;const seq=++epoch;busy=true;loaded=null;$('google-auth-button').replaceChildren();$('google-auth-error').textContent='';render();
  try{
   const url=bridgeURL($('google-auth-url').value),generation=broker.generation,config=await request(url,'/v1/auth/config');
   if(!config.enabled||!config.clientId)throw new Error(config.error||'Backend ยังไม่ได้ตั้ง Google OAuth Client ID และรายชื่อผู้มีสิทธิ์');
   const challenge=await request(url,'/v1/auth/challenge',{});
   if(typeof challenge.challengeId!=='string'||typeof challenge.nonce!=='string')throw new Error('Backend ไม่ส่ง challenge สำหรับ Google Login');
   const sdk=await loadSDK();if(seq!==epoch||closed)return;
   loaded={epoch:seq,url,generation,challenge};const c=loaded;
   sdk.initialize({client_id:config.clientId,nonce:challenge.nonce,auto_select:false,ux_mode:'popup',callback:response=>void receive(response,c)});
   sdk.renderButton($('google-auth-button'),{theme:'outline',size:'large',text:'signin_with',shape:'rectangular',width:Math.min(340,win.innerWidth-80)});
   $('google-auth-error').textContent='เลือกบัญชี Google ที่เจ้าของ Bridge อนุญาต ปุ่มนี้ไม่เปิดสิทธิ์ส่งคำสั่งเอง';
  }catch(error){if(seq===epoch)$('google-auth-error').textContent=error.message;}
  finally{if(seq===epoch){busy=false;render();}}
 });
 for(const id of ['google-auth-url','google-auth-trade-token'])$(id).addEventListener('input',()=>{if(id==='google-auth-url'){epoch++;busy=false;loaded=null;$('google-auth-button').replaceChildren();render();}});
 $('google-auth-dialog').addEventListener('close',()=>{epoch++;busy=false;loaded=null;$('google-auth-trade-token').value='';$('google-auth-button').replaceChildren();});
 async function signOut(){epoch++;const previous=[...sessions.values()];sessions.clear();win.google?.accounts?.id?.disableAutoSelect?.();const local=onLocalLogout();render();await Promise.allSettled([local,...previous.map(revoke)]);render();}
 const timer=win.setInterval(()=>{const active=sessions.get(broker.token);if(active&&active.expiresAt<=now())void signOut();else render();},1000);
 render();return{open,render,signOut,destroy(){closed=true;epoch++;win.clearInterval(timer);sessions.clear();}};
}
