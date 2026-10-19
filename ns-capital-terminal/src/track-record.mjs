import {curvePath,reportLink} from './dashboard.mjs';
const $=id=>document.getElementById(id),cash=v=>Number.isFinite(v)?v.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}):'—',at=v=>new Date(v).toLocaleString('th-TH',{timeZone:'Asia/Bangkok',hour12:false});
try{
 const params=new URLSearchParams(location.hash.slice(1)),gateway=params.get('gateway'),token=params.get('key');
 if(!gateway||!token||!/^[A-Za-z0-9_-]{43}$/.test(token))throw new Error('ลิงก์รายงานไม่ครบ กรุณาใช้ลิงก์ที่ผู้สร้างคัดลอกไว้');
 reportLink(location.origin,gateway,token);
 const response=await fetch(gateway.replace(/\/$/,'')+'/v1/track-record/view',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token}),credentials:'omit',redirect:'error',cache:'no-store',referrerPolicy:'no-referrer',signal:AbortSignal.timeout(20000)}),data=await response.json();
 if(!response.ok||!data.report)throw new Error('รายงานถูกยกเลิก หมดอายุ หรือ Gateway ไม่พร้อม');
 const r=data.report;if(r.independentlyVerified!==false||r.live!==false)throw new Error('รูปแบบรายงานไม่ถูกต้อง');
 $('record-status').textContent='สร้าง '+at(data.createdAt)+' · หมดอายุ '+at(data.expiresAt)+' (เวลาไทย)';
 for(const[label,value,note]of[['เทรดปิดครบ',r.closedTrades,r.platform],['Win Rate',cash(r.winRate)+'%',r.wins+' W / '+r.losses+' L'],['Profit Factor',r.profitFactor===null?(r.noLosses?'∞':'—'):cash(r.profitFactor),'เฉพาะต้นทุนที่ผูกกับเทรด'],['Booked Net P&L',cash(r.bookedNet),r.currency]]){const item=document.createElement('div');for(const[tag,value]of[['small',label],['strong',value],['small',note]]){const e=document.createElement(tag);e.textContent=String(value);item.append(e);}$('report-metrics').append(item);}
 const p=curvePath(r.curve||[]);if(p){const path=document.createElementNS('http://www.w3.org/2000/svg','path');path.setAttribute('d',p.path);path.setAttribute('fill','none');path.setAttribute('stroke','#7b9eff');path.setAttribute('stroke-width','2.5');$('report-curve').append(path);}
 $('report-from').textContent=at(r.from);$('report-through').textContent=at(r.through);
 for(const[label,value]of[['แหล่งข้อมูล',r.source],['วิธีนับเทรด',r.basis],['กำไรสุทธิเทรดปิด',cash(r.closedNet)+' '+r.currency],['ต้นทุนแยกบัญชี',cash(r.unattributedCosts)+' '+r.currency],['Booked drawdown สูงสุด',cash(r.maxBookedDrawdown)+' '+r.currency]]){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=value;$('report-details').append(dt,dd);}
 $('record-data').hidden=false;
}catch(error){$('record-status').textContent='เปิดรายงานไม่ได้';$('record-error').textContent=error.name==='TimeoutError'?'Gateway ไม่ตอบกลับ กรุณาให้ผู้สร้างตรวจ Bridge และ HTTPS':error.message;}
