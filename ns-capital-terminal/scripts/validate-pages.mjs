import {readFile,stat} from 'node:fs/promises';
import {resolve} from 'node:path';
import {JSDOM} from 'jsdom';
export async function validatePagesArtifact(directory,basePath){
 let links=0;const origin='https://pages-artifact.test';
 for(const file of ['index.html','login.html','manual.html','track-record.html','privacy.html','404.html']){
  const html=await readFile(resolve(directory,file),'utf8');
  if(/signin-with-chatgpt|signout-with-chatgpt/.test(html))throw new Error('Sites-only authentication cannot be deployed to GitHub Pages');
  const dom=new JSDOM(html,{url:origin+basePath+file});
  try{for(const element of dom.window.document.querySelectorAll('[href],[src]')){
   const value=element.getAttribute('href')??element.getAttribute('src');if(!value||value.startsWith('#')||value.startsWith('data:'))continue;
   const url=new URL(value,origin+basePath+file);if(url.origin!==origin)continue;
   if(!url.pathname.startsWith(basePath))throw new Error(file+' escapes Pages base path: '+value);
   const local=url.pathname.slice(basePath.length)||'index.html';
   if(!(await stat(resolve(directory,decodeURIComponent(local)))).isFile())throw new Error('Missing Pages asset: '+local);links++;
  }}finally{dom.window.close();}
 }
 const manifest=JSON.parse(await readFile(resolve(directory,'manifest.webmanifest'),'utf8'));
 if(manifest.scope!=='./'||manifest.start_url!=='./?app=1')throw new Error('PWA manifest must be relative to the project');
 console.log('Validated '+links+' local links/assets across root and project Pages output');
}
