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
    assert.equal(Boolean(find('pick-0')),false);assert.match(d.body.textContent,/Synthetic Book via The Odds API/);
    await click('confirm');assert.match(find('pick-0').textContent,/-110/);
    await click('calculate');assert.match(find('results').textContent,/\$19\.09/);
    assert.match(find('results').textContent,/Chance under your assumptionsUnknown/);
    assert.deepEqual(errors,[]);
  }finally{dom.window.close();}
});

// Exercise the real exported app with controllable provider responses and time.
async function setupOddsApp(){
  const root=path.resolve(__dirname,'../dist');
  const state={hasGame:true};const updated=Date.now();const issued=[];
  state.expireQuotes=()=>{for(const q of issued)q.updatedAt=new Date(Date.now()-901000).toISOString();};
  const makeQuote=market=>({id:`game-a:book:${market}:Home`,eventId:'game-a',event:'Synthetic Away at Home',
    startAt:new Date(updated+3600000).toISOString(),sport:'basketball_nba',market,
    label:market==='spreads'?'Synthetic Home -3.5':'Synthetic Home',americanOdds:'-110',bookmaker:'Synthetic Book',
    updatedAt:new Date(updated).toISOString(),fetchedAt:new Date(updated).toISOString()});
  class Assets extends ResourceLoader{fetch(url){const u=new URL(url);assert.equal(u.origin,'http://slipsavvy.test');
    const file=path.resolve(root,'.'+decodeURIComponent(u.pathname));assert.ok(file.startsWith(root+path.sep));return fs.readFile(file);}}
  const errors=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
  const dom=new JSDOM(await fs.readFile(path.join(root,'index.html'),'utf8'),{
    url:'http://slipsavvy.test/',runScripts:'dangerously',resources:new Assets(),pretendToBeVisual:true,virtualConsole:vc,
    beforeParse(w){w.AbortController=AbortController;
      w.matchMedia=()=>({matches:false,addListener(){},removeListener(){},addEventListener(){},removeEventListener(){}});w.scrollTo=()=>{};
      w.fetch=async url=>({ok:true,json:async()=>{
        if(String(url).endsWith('/api/sports'))return {sports:[{key:'basketball_nba',title:'NBA'}]};
        const q=makeQuote(new URL(url).searchParams.get('market'));issued.push(q);
        return {quotes:state.hasGame?[q]:[]};
      }});
    }});
  const d=dom.window.document,find=id=>d.querySelector(`[data-testid="${id}"]`);
  const tick=()=>new Promise(r=>setTimeout(r,30));
  const wait=async id=>{const end=Date.now()+10000;while(!find(id)&&Date.now()<end)await tick();assert.ok(find(id),id);return find(id);};
  const click=async id=>{(await wait(id)).click();await tick();};
  const fill=async(id,value)=>{const input=await wait(id);
    Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype,'value').set.call(input,value);
    input.dispatchEvent(new dom.window.Event('input',{bubbles:true}));await tick();};
  const choose=async()=>{await click('sport-basketball_nba');await click('game-game-a');await click('quote-'+makeQuote('h2h').id);};
  return {state,d,find,wait,click,fill,choose,makeQuote,close(){dom.window.close();assert.deepEqual(errors,[]);}};
}

test('an edited feed price survives re-editing, and choosing the original feed does not overwrite it',async()=>{
  const a=await setupOddsApp();try{
    await a.choose();await a.click('confirm');await a.click('edit-0');
    await a.fill('odds','+150');await a.click('review');await a.click('confirm');
    assert.match(a.find('pick-0').textContent,/\+150/);
    await a.click('edit-0');await a.click('review');await a.click('confirm');
    assert.match(a.find('pick-0').textContent,/\+150/);
    assert.match(a.find('pick-0').textContent,/Edited entry \(unverified\)/);
    await a.choose();await a.click('confirm');
    assert.match(a.find('pick-0').textContent,/\+150/);
    assert.match(a.find('pick-1').textContent,/-110/);
  }finally{a.close();}
});

test('editing only the user assumption preserves feed provenance and freshness checks',async()=>{
  const a=await setupOddsApp();try{
    await a.choose();await a.click('back-to-edit');await a.fill('chance','60');
    await a.click('review');await a.click('confirm');
    assert.match(a.find('pick-0').textContent,/Synthetic Book via The Odds API/);
    assert.match(a.find('pick-0').textContent,/Your win estimate: 60%/);
    await a.click('calculate');assert.match(a.find('results').textContent,/60\.00%/);
    a.state.expireQuotes();await a.click('edit-0');await a.click('review');
    assert.match(a.find('error').textContent,/no longer current/);assert.equal(Boolean(a.find('confirm')),false);
    await a.click('cancel');await a.click('calculate');
    assert.match(a.find('error').textContent,/no longer current/);assert.equal(Boolean(a.find('results')),false);
  }finally{a.close();}
});

test('market changes and refresh retain the selected game until it disappears',async()=>{
  const a=await setupOddsApp();try{
    await a.click('sport-basketball_nba');await a.click('game-game-a');
    await a.click('market-spreads');
    assert.ok(a.find('quote-'+a.makeQuote('spreads').id),'selected game survives market toggle');
    await a.click('refresh-odds');assert.ok(a.find('quote-'+a.makeQuote('spreads').id));
    a.state.hasGame=false;await a.click('refresh-odds');
    assert.equal(Boolean(a.find('game-game-a')),false);assert.equal(Boolean(a.find('quote-'+a.makeQuote('spreads').id)),false);
    a.state.hasGame=true;await a.click('refresh-odds');
    assert.ok(a.find('game-game-a'));assert.equal(Boolean(a.find('quote-'+a.makeQuote('spreads').id)),false);
  }finally{a.close();}
});

test('clicking an expired line hides quote buttons and confirmation rechecks freshness',async()=>{
  const a=await setupOddsApp();try{
    await a.click('sport-basketball_nba');await a.click('game-game-a');a.state.expireQuotes();
    await a.click('quote-'+a.makeQuote('h2h').id);
    assert.match(a.d.body.textContent,/no longer current/);
    assert.equal(Boolean(a.find('quote-'+a.makeQuote('h2h').id)),false);
  }finally{a.close();}
  const b=await setupOddsApp();try{
    await b.choose();b.state.expireQuotes();await b.click('confirm');
    assert.match(b.find('error').textContent,/no longer current/);assert.equal(Boolean(b.find('pick-0')),false);
  }finally{b.close();}
});

test('editing a feed pick at eight selections replaces its original slot',async()=>{
  const a=await setupOddsApp();try{
    await a.choose();await a.click('confirm');
    for(let i=1;i<8;i++){
      await a.click('add');await a.fill('selection','Manual '+i);await a.fill('event','Other game '+i);
      await a.fill('odds','+100');await a.click('review');await a.click('confirm');
    }
    await a.click('edit-0');await a.fill('odds','+150');await a.click('review');await a.click('confirm');
    assert.match(a.find('pick-0').textContent,/\+150/);
    assert.match(a.find('pick-7').textContent,/Manual 7/);assert.equal(Boolean(a.find('pick-8')),false);
    assert.equal(Boolean(a.find('error')),false);
  }finally{a.close();}
});
