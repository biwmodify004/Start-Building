/* Static shell only. No quotes, account data, tokens or execution requests. */
const REVISION='__NS_SHELL_REVISION__';
const BASE=new URL('./',self.location.href||self.location.origin+'/sw.js').pathname;
const PREFIX='ns-capital-shell-'+encodeURIComponent(BASE)+'-';
const CACHE=PREFIX+REVISION;
const SHELL=['index.html','app.mjs','style.css','responsive.css','terminal.css','icons.svg','manifest.webmanifest','app-icons/icon-192.png','app-icons/icon-512.png','app-icons/maskable-512.png','app-icons/apple-touch-icon.png'].map(path=>BASE+path);
const STATIC=new Set(SHELL);
async function validShell(path,response){
 if(!response||!response.ok||response.redirected||new URL(response.url||self.location.origin+path).origin!==self.location.origin)return false;
 const type=response.headers.get('content-type')||'';
 if(path===BASE+'index.html')return type.includes('text/html')&&(await response.clone().text()).includes('name="ns-app-shell" content="'+REVISION+'"');
 if(path.endsWith('.mjs'))return /javascript|ecmascript/.test(type);
 if(path.endsWith('.css'))return type.includes('text/css');
 if(path.endsWith('.png'))return type.includes('image/png');
 if(path.endsWith('.svg'))return type.includes('image/svg+xml');
 return path.endsWith('.webmanifest')&&/application\/(?:manifest\+)?json/.test(type);
}
self.addEventListener('install',event=>event.waitUntil((async()=>{
 const cache=await caches.open(CACHE);
 try{await Promise.all(SHELL.map(async path=>{const response=await fetch(new Request(path,{cache:'no-store',credentials:'same-origin'}));if(!await validShell(path,response))throw new Error('Static shell unavailable');await cache.put(path,response);}));}
 catch(error){await caches.delete(CACHE);throw error;}
 // Let an existing app session finish; never force an update during a trade.
})()));
self.addEventListener('activate',event=>event.waitUntil((async()=>{for(const name of await caches.keys())if(name.startsWith(PREFIX)&&name!==CACHE)await caches.delete(name);await self.clients.claim();})()));
self.addEventListener('fetch',event=>{
 const request=event.request,url=new URL(request.url);
 if(request.method!=='GET'||url.origin!==self.location.origin)return;
 if(request.mode==='navigate'&&(url.pathname===BASE||url.pathname===BASE+'index.html')){
  event.respondWith((async()=>{try{const response=await fetch(request);if(!await validShell(BASE+'index.html',response)){if(response.ok&&!response.redirected&&(response.headers.get('content-type')||'').includes('text/html')&&(await response.clone().text()).includes('name="ns-app-shell"'))return(await caches.match(BASE+'index.html',{cacheName:CACHE}))||response;return response;}const cache=await caches.open(CACHE);await cache.put(BASE+'index.html',response.clone());return response;}catch{const cached=await caches.match(BASE+'index.html',{cacheName:CACHE});return cached||new Response('Connect to the internet to open NS Capital.',{status:503,headers:{'Content-Type':'text/plain; charset=utf-8'}});}})());return;
 }
 if(!STATIC.has(url.pathname)||url.search)return;
 event.respondWith((async()=>{const cache=await caches.open(CACHE),cached=await cache.match(url.pathname);if(cached)return cached;const response=await fetch(request);if(await validShell(url.pathname,response))await cache.put(url.pathname,response.clone());return response;})());
});
