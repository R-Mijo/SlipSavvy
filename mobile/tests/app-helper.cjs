const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const {JSDOM,ResourceLoader,VirtualConsole}=require('jsdom');
const tick=()=>new Promise(r=>setTimeout(r,40));
function shifted(value,delta){
 if(typeof value==='string'&&/^\d{4}-\d\d-\d\dT\d\d:\d\d/.test(value))return new Date(Date.parse(value)+delta).toISOString();
 if(Array.isArray(value))return value.map(v=>shifted(v,delta));
 if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,shifted(v,delta)]));
 return value;
}
async function setup(fetcher){
 const root=path.resolve(__dirname,'../dist');
 class Assets extends ResourceLoader {fetch(url){const u=new URL(url);assert.equal(u.origin,'http://slipsavvy.test');const file=path.resolve(root,'.'+decodeURIComponent(u.pathname));assert.ok(file.startsWith(root+path.sep));return fs.readFile(file);}}
 const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
 const dom=new JSDOM(await fs.readFile(path.join(root,'index.html'),'utf8'),{url:'http://slipsavvy.test/',runScripts:'dangerously',resources:new Assets(),pretendToBeVisual:true,virtualConsole:vc,
 beforeParse(w){w.AbortController=AbortController;w.matchMedia=()=>({matches:false,addListener(){},removeListener(){},addEventListener(){},removeEventListener(){}});w.scrollTo=()=>{};w.fetch=fetcher;}});
 const d=dom.window.document,find=id=>d.querySelector(`[data-testid="${id}"]`);
 const wait=async id=>{const end=Date.now()+10000;while(!find(id)&&Date.now()<end)await tick();assert.ok(Boolean(find(id)),id);return find(id);};
 const click=async id=>{(await wait(id)).click();await tick();};
 const fill=async(id,value)=>{const input=await wait(id);Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype,'value').set.call(input,value);input.dispatchEvent(new dom.window.Event('input',{bubbles:true}));await tick();};
 const zone=async value=>{await click('timezone-toggle');await fill('timezone-search',value);await click('timezone-'+value);};
 return {d,find,wait,click,fill,zone,close(){dom.window.close();assert.deepEqual(errors,[]);}};
}
const response=(data,status=200)=>({ok:status>=200&&status<300,status,json:async()=>data,text:async()=>JSON.stringify(data)});
async function fixture(){const raw=JSON.parse(await fs.readFile(path.join(__dirname,'fixtures/game-reports-v1.json'),'utf8'));return shifted(raw,Date.now()-Date.parse(raw.generatedAt));}
module.exports={setup,response,fixture,tick};
