import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
const esc=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function inline(value){
 const pattern=/`([^`]+)`|\*\*([^*]+)\*\*|\[([^\]]+)\]\(([^)]+)\)/g;let html='',from=0;
 for(const match of value.matchAll(pattern)){html+=esc(value.slice(from,match.index));if(match[1])html+='<code>'+esc(match[1])+'</code>';else if(match[2])html+='<strong>'+esc(match[2])+'</strong>';else{const url=match[4],safe=/^(?:https?:\/\/|\.{0,2}\/|#)/.test(url);html+=safe?'<a href="'+esc(url)+'"'+(url.startsWith('http')?' target="_blank" rel="noopener"':'')+'>'+esc(match[3])+'</a>':esc(match[3]);}from=match.index+match[0].length;}
 return html+esc(value.slice(from));
}
export function renderManual(markdown){
 const lines=markdown.replaceAll('\r\n','\n').split('\n');let html='',toc='',list=null,section=false;const slugs=new Map();
 const closeList=()=>{if(list){html+='</'+list+'>';list=null;}};
 for(let i=0;i<lines.length;i++){
  const line=lines[i];if(!line.trim()){closeList();continue;}
  if(line.startsWith('```')){closeList();const code=[];while(++i<lines.length&&!lines[i].startsWith('```'))code.push(lines[i]);html+='<pre><code>'+esc(code.join('\n'))+'</code></pre>';continue;}
  const heading=line.match(/^(#{1,3}) (.+)$/);if(heading){closeList();const level=heading[1].length,title=heading[2];if(level===1)continue;if(level===2){if(section)html+='</section>';const base=title.toLowerCase().replace(/[^\p{L}\p{N}]+/gu,'-').replace(/^-|-$/g,''),n=slugs.get(base)||0;slugs.set(base,n+1);const id=base+(n?'-'+n:'');html+='<section id="'+esc(id)+'"><h2>'+inline(title)+'</h2>';toc+='<a href="#'+esc(id)+'">'+esc(title)+'</a>';section=true;}else html+='<h3>'+inline(title)+'</h3>';continue;}
  if(line.startsWith('|')&&lines[i+1]?.match(/^\|[\s:|\-]+\|$/)){closeList();const cells=v=>v.trim().replace(/^\||\|$/g,'').split('|').map(v=>v.trim());html+='<div class="manual-table"><table><thead><tr>'+cells(line).map(v=>'<th>'+inline(v)+'</th>').join('')+'</tr></thead><tbody>';i++;while(lines[i+1]?.startsWith('|'))html+='<tr>'+cells(lines[++i]).map(v=>'<td>'+inline(v)+'</td>').join('')+'</tr>';html+='</tbody></table></div>';continue;}
  const item=line.match(/^(?:\d+\. |(-) )(.+)$/);if(item){const type=item[1]?'ul':'ol';if(list!==type){closeList();html+='<'+type+'>';list=type;}html+='<li>'+inline(item[2])+'</li>';continue;}
  closeList();html+='<p>'+inline(line)+'</p>';
 }
 closeList();if(section)html+='</section>';return{html,toc,sections:slugs.size};
}
export async function buildManual(root,out){
 const md=await readFile(resolve(root,'docs/USER-MANUAL-TH.md'),'utf8'),{html,toc,sections}=renderManual(md);
 if(sections<20)throw new Error('The Thai manual is incomplete');
 const page=`<!doctype html><html lang="th"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#101521"><title>คู่มือภาษาไทย · NS Capital Terminal</title><link rel="stylesheet" href="manual.css"></head><body><header class="manual-header"><a href="/" class="manual-brand"><span>N</span>NS CAPITAL <small>คู่มือภาษาไทย</small></a><div><a href="downloads/NS-Capital-Manual-TH.md" download>ดาวน์โหลด Markdown</a><button id="manual-print">พิมพ์ / บันทึก PDF</button><a href="/">เปิด Terminal ↗</a></div></header><div class="manual-layout"><aside><label for="manual-search">ค้นหาในคู่มือ</label><input id="manual-search" type="search" placeholder="เช่น MT4, Risk, Backup" autocomplete="off"><p id="manual-search-status" role="status"></p><nav aria-label="สารบัญคู่มือ">${toc}</nav></aside><main><div class="manual-intro"><span>NS CAPITAL TERMINAL / 1.8</span><h1>คู่มือใช้งานภาษาไทย</h1><p>ตั้งค่าครั้งแรก อ่านข้อมูลจริง และดูแลแพลตฟอร์มของคุณอย่างเป็นขั้นตอน</p></div>${html}<p id="manual-no-results" hidden>ไม่พบหัวข้อที่ตรงกับคำค้น ลองใช้คำสั้นลงหรือค้นชื่อเมนูภาษาอังกฤษ</p></main></div><script type="module" src="manual-ui.mjs"></script></body></html>`;
 await mkdir(resolve(out,'downloads'),{recursive:true});await writeFile(resolve(out,'manual.html'),page);await writeFile(resolve(out,'downloads/NS-Capital-Manual-TH.md'),md);
 return sections;
}
