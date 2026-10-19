// Small dependency-free ZIP writer (stored entries, UTF-8 filenames).
import {readFile,writeFile,readdir} from 'node:fs/promises';
import {join} from 'node:path';
const crcTable=Array.from({length:256},(_,n)=>{let c=n;for(let j=0;j<8;j++)c=c&1?0xedb88320^(c>>>1):c>>>1;return c>>>0;});
const crc32=bytes=>{let c=0xffffffff;for(const b of bytes)c=crcTable[(c^b)&255]^(c>>>8);return(c^0xffffffff)>>>0;};
export async function zipFolder(directory,target,extraFiles=[]){
 const local=[],central=[];let offset=0,count=0,centralSize=0;
 const files=(await readdir(directory,{withFileTypes:true})).filter(e=>e.isFile()&&/\.(?:py|mq4|md|json)$/.test(e.name)&&!e.name.startsWith('.')).map(e=>({name:e.name,path:join(directory,e.name)})).concat(extraFiles).sort((a,b)=>a.name.localeCompare(b.name));
 for(const file of files){
  if(!/^[A-Za-z0-9_.-]+$/.test(file.name)||file.name.startsWith('.'))throw new Error('Unsafe download filename');
  const data=await readFile(file.path),name=Buffer.from(file.name),crc=crc32(data);
  const header=Buffer.alloc(30);header.writeUInt32LE(0x04034b50);header.writeUInt16LE(20,4);header.writeUInt16LE(0x800,6);header.writeUInt32LE(crc,14);header.writeUInt32LE(data.length,18);header.writeUInt32LE(data.length,22);header.writeUInt16LE(name.length,26);
  local.push(header,name,data);
  const record=Buffer.alloc(46);record.writeUInt32LE(0x02014b50);record.writeUInt16LE(20,4);record.writeUInt16LE(20,6);record.writeUInt16LE(0x800,8);record.writeUInt32LE(crc,16);record.writeUInt32LE(data.length,20);record.writeUInt32LE(data.length,24);record.writeUInt16LE(name.length,28);record.writeUInt32LE(offset,42);central.push(record,name);centralSize+=record.length+name.length;offset+=header.length+name.length+data.length;count++;
 }
 const end=Buffer.alloc(22);end.writeUInt32LE(0x06054b50);end.writeUInt16LE(count,8);end.writeUInt16LE(count,10);end.writeUInt32LE(centralSize,12);end.writeUInt32LE(offset,16);
 await writeFile(target,Buffer.concat([...local,...central,end]));
}
