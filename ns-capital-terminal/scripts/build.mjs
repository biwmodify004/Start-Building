import {mkdir,cp,copyFile,rm,readFile,readdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {build} from 'esbuild';
import {createHash} from 'node:crypto';
import {zipFolder} from './zip.mjs';
import {buildManual} from './manual.mjs';
const root=process.cwd();
const pkg=JSON.parse(await readFile(resolve(root,'node_modules/@luxalgo/vela/package.json'),'utf8'));
if(pkg.version!=='0.8.4')throw new Error('Unexpected Vela version');
await rm(resolve(root,'dist'),{recursive:true,force:true});
await mkdir(resolve(root,'dist/vendor'),{recursive:true});
await mkdir(resolve(root,'dist/downloads'),{recursive:true});
await zipFolder(resolve(root,'broker-bridge'),resolve(root,'dist/downloads/NS-Capital-Broker-Bridge.zip'),[{name:'USER-MANUAL-TH.md',path:resolve(root,'docs/USER-MANUAL-TH.md')}]);
await copyFile(resolve(root,'broker-bridge/README-TH.md'),resolve(root,'dist/downloads/README-TH.md'));
await copyFile(resolve(root,'broker-bridge/JOURNAL-RISK-TH.md'),resolve(root,'dist/downloads/Journal-Risk-TH.md'));
await copyFile(resolve(root,'AI-BACKEND-TH.md'),resolve(root,'dist/downloads/AI-Backend-TH.md'));
await cp(resolve(root,'src'),resolve(root,'dist'),{recursive:true});
await buildManual(root,resolve(root,'dist'));
await build({entryPoints:[resolve(root,'src/app.mjs')],outfile:resolve(root,'dist/app.mjs'),bundle:true,format:'esm',platform:'browser',target:'es2022',minify:true,legalComments:'linked'});
await copyFile(resolve(root,'node_modules/@luxalgo/vela/LICENSE'),resolve(root,'dist/vendor/VELA-LICENSE.txt'));
await copyFile(resolve(root,'node_modules/@luxalgo/vela/NOTICE'),resolve(root,'dist/vendor/VELA-NOTICE.txt'));
let notices='NS Capital Terminal — bundled third-party dependency licenses\n\n';
for(const entry of await readdir(resolve(root,'node_modules/@zag-js'))){const dir=resolve(root,'node_modules/@zag-js',entry);try{const license=await readFile(resolve(dir,'LICENSE'),'utf8');notices+='\n@zag-js/'+entry+'\n'+license+'\n';}catch{}}
await writeFile(resolve(root,'dist/vendor/DEPENDENCY-LICENSES.txt'),notices);
// Match each service-worker shell to the exact built HTML and bundled assets.
const shellHash=createHash('sha256');
for(const file of ['index.html','app.mjs','style.css','responsive.css','terminal.css','icons.svg','manifest.webmanifest','app-icons/icon-192.png','app-icons/icon-512.png','app-icons/maskable-512.png','app-icons/apple-touch-icon.png'])shellHash.update(await readFile(resolve(root,'dist',file)));
const revision=shellHash.digest('hex').slice(0,16);
for(const file of ['index.html','sw.js']){const path=resolve(root,'dist',file);await writeFile(path,(await readFile(path,'utf8')).replaceAll('__NS_SHELL_REVISION__',revision));}
console.log('Built NS Capital Terminal with Vela '+pkg.version+' and bundled attribution notices.');
