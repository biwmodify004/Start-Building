import http from 'node:http';
import {readFile,stat} from 'node:fs/promises';
import {resolve,extname,sep} from 'node:path';
import {validateConfig} from '../src/engine.mjs';

// Optional local runtime. Static hosting runs the local rules helper only.
const root=resolve('dist'),port=Number(process.env.PORT||8080),host=process.env.NS_HOST||'127.0.0.1';
const aiBase=process.env.AI_BASE_URL?.replace(/\/$/,''),aiModel=process.env.AI_MODEL,aiKey=process.env.AI_API_KEY;
const mime={'.html':'text/html; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json','.txt':'text/plain; charset=utf-8'};
const json=(res,status,body)=>{res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(body));};
const server=http.createServer(async(req,res)=>{
 try {
  res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Referrer-Policy','strict-origin-when-cross-origin');
  const url=new URL(req.url,'http://localhost');
  if(url.pathname==='/api/status')return json(res,200,{ai:!!(aiBase&&aiModel),model:aiBase&&aiModel?aiModel:null});
  if(url.pathname==='/api/research') {
   if(req.method!=='POST')return json(res,405,{error:'POST required'});
   if(req.headers.origin&&new URL(req.headers.origin).host!==req.headers.host)return json(res,403,{error:'Origin rejected'});
   if(!aiBase||!aiModel)return json(res,503,{error:'AI_BASE_URL and AI_MODEL are not configured. Use local rules.'});
   if(!req.headers['content-type']?.startsWith('application/json'))return json(res,415,{error:'JSON required'});
   let text='';for await(const part of req){text+=part;if(text.length>12000)return json(res,413,{error:'Request too large'});}
   const input=JSON.parse(text),config=validateConfig(input.config);
   if(typeof input.message!=='string'||input.message.length>4000)return json(res,400,{error:'Message must be at most 4,000 characters'});
   const response=await fetch(aiBase+'/chat/completions',{method:'POST',headers:{'Content-Type':'application/json',...(aiKey?{Authorization:'Bearer '+aiKey}:{})},body:JSON.stringify({model:aiModel,temperature:.1,messages:[{role:'system',content:'You are a strategy configuration assistant. Return only a JSON object with keys "config" and "explanation". Config must keep the supplied numeric fields and choose kind from trend, mean, breakout only. Explain unsupported features honestly. Never claim to execute or backtest, and never promise profits. No code, markup or tools. Current configuration: '+JSON.stringify(config)},{role:'user',content:input.message}]}),signal:AbortSignal.timeout(60000)});
   if(!response.ok)return json(res,502,{error:'AI provider request failed ('+response.status+').'});
   const body=await response.json(),content=body.choices?.[0]?.message?.content||'';
   const proposal=JSON.parse(content.replace(/^\s*```(?:json)?\s*/,'').replace(/\s*```\s*$/,''));
   return json(res,200,{config:validateConfig(proposal.config),explanation:String(proposal.explanation||'Review the proposed settings before running a backtest.').slice(0,3000),model:aiModel});
  }
  if(!['GET','HEAD'].includes(req.method)){res.writeHead(405);return res.end();}
  const path=resolve(root,'.'+decodeURIComponent(url.pathname==='/'?'/index.html':url.pathname));
  if(!path.startsWith(root+sep)){res.writeHead(403);return res.end('Forbidden');}
  const file=await stat(path);if(!file.isFile())throw new Error('Not a file');
  res.writeHead(200,{'Content-Type':mime[extname(path)]||'application/octet-stream','Cache-Control':'no-cache'});
  if(req.method==='HEAD')return res.end();res.end(await readFile(path));
 }catch(error){if(req.url?.startsWith('/api/'))json(res,400,{error:error.name==='TimeoutError'?'AI request timed out':error.message});else{res.writeHead(404,{'Content-Type':'text/plain'});res.end('Not found');}}
});
server.listen(port,host,()=>console.log(`NS Capital Terminal: http://${host}:${port}${aiBase&&aiModel?'/?ai=1':''} · ${aiBase&&aiModel?'AI adapter configured':'Local rules mode'}`));
