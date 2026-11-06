const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const {JSDOM,ResourceLoader,VirtualConsole}=require('jsdom');
test('browse sport, game and quote, review, confirm and calculate without typed odds',async()=>{
  const root=path.resolve(__dirname,'../dist');
  class Assets extends ResourceLoader{fetch(url){const u=new URL(url);assert.equal(u.origin,'http://slipsavvy.test');
    const file=path.resolve(root,'.'+decodeURIComponent(u.pathname));assert.ok(file.startsWith(root+path.sep));return fs.readFile(file);}}
  const errors=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
  const q={id:'synthetic-game:book:h2h:Home',eventId:'synthetic-game',event:'Synthetic Away at Home',
    startAt:new Date(Date.now()+3600000).toISOString(),sport:'basketball_nba',market:'h2h',label:'Synthetic Home',americanOdds:'-110',
    bookmaker:'Synthetic Book',updatedAt:new Date().toISOString(),fetchedAt:new Date().toISOString()};
  const dom=new JSDOM(await fs.readFile(path.join(root,'index.html'),'utf8'),{
    url:'http://slipsavvy.test/',runScripts:'dangerously',resources:new Assets(),pretendToBeVisual:true,virtualConsole:vc,
    beforeParse(w){w.AbortController=AbortController;
      w.matchMedia=()=>({matches:false,addListener(){},removeListener(){},addEventListener(){},removeEventListener(){}});w.scrollTo=()=>{};
      w.fetch=async url=>({ok:true,json:async()=>String(url).endsWith('/api/sports')?
        {sports:[{key:'basketball_nba',title:'NBA'}]}:{quotes:[q]}});
    }});
  const d=dom.window.document;
  const find=id=>d.querySelector(`[data-testid="${id}"]`);
  const wait=async id=>{const end=Date.now()+10000;while(!find(id)&&Date.now()<end)await new Promise(r=>setTimeout(r,30));assert.ok(find(id),id);return find(id);};
  const click=async id=>{(await wait(id)).click();await new Promise(r=>setTimeout(r,40));};
  try{
    await click('sport-basketball_nba');await click('game-synthetic-game');await click('quote-'+q.id);
    assert.equal(find('pick-0'),null);assert.match(d.body.textContent,/Synthetic Book via The Odds API/);
    await click('confirm');assert.match(find('pick-0').textContent,/-110/);
    await click('calculate');assert.match(find('results').textContent,/\$19\.09/);
    assert.match(find('results').textContent,/Chance under your assumptionsUnknown/);
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});
