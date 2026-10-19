// Server-side configuration only. Never included in the browser bundle.
export function localAIConfig(env=process.env){
 const provider=(env.AI_PROVIDER||'openai-compatible').trim().toLowerCase();
 const defaults={'ollama':'http://127.0.0.1:11434/v1','lm-studio':'http://127.0.0.1:1234/v1','openai-compatible':''};
 if(!Object.hasOwn(defaults,provider))throw new Error('AI_PROVIDER must be ollama, lm-studio or openai-compatible');
 const base=(env.AI_BASE_URL||defaults[provider]).replace(/\/+$/,'');
 if(base){const url=new URL(base);if(url.username||url.password||url.search||url.hash||!(url.protocol==='https:'||url.protocol==='http:'&&['127.0.0.1','localhost','[::1]'].includes(url.hostname)))throw new Error('AI base URL requires HTTPS or localhost HTTP without embedded credentials');}
 return{provider,base,model:env.AI_MODEL||'',key:env.AI_API_KEY||''};
}
export function completionPayload(config,messages){
 return{model:config.model,temperature:.1,max_tokens:900,stream:false,...(config.provider==='ollama'?{response_format:{type:'json_object'}}:{}),messages};
}
