const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const {setup,response,shifted}=require('./app-helper.cjs');

async function app(){
 const raw=JSON.parse(await fs.readFile(path.join(__dirname,'fixtures/player-props-v1.json'),'utf8'));
 const data=shifted(raw,Date.now()-Date.parse(raw.generatedAt));
 const state={calls:[],fail:false,empty:false,deferred:null,requests:[]};
 const a=await setup(async(url,options)=>{
  const u=new URL(url);state.calls.push(u.pathname);
  if(u.pathname==='/api/sports')return response({sports:[{key:'americanfootball_nfl',title:'NFL'}]});
  if(u.pathname==='/api/game-reports'){
   const req=JSON.parse(options.body);state.requests.push(req);
   const r=structuredClone(data);r.assessment.comparisonContext={totalStake:req.totalStake,minimumTotalReturn:null,stakeBasis:'fixed_total_capital'};
   r.legs=req.legs.map(l=>{const original=data.legs.find(x=>x.selection.market===l.market);return {...original,id:l.id,selection:l,quoteSource:{...original.quoteSource,id:'quote:'+l.id}};});
   return response(r);
  }
  if(u.pathname==='/api/odds/props'){
   if(state.deferred)return state.deferred;
   if(state.fail)return response({error:'Synthetic props unavailable'},503);
   const markets=u.searchParams.getAll('market'),alt=markets.some(m=>m.endsWith('_alternate'));
   const quotes=data.legs.filter(l=>l.quote.playerName).map(l=>({...l.quote,market:l.quote.market+(alt?'_alternate':''),id:l.quote.id+(alt?':alt':'')}));
   return response({quotes:state.empty?[]:quotes});
  }
  const market=u.searchParams.get('market');
  const quote=data.legs.find(l=>l.selection.market===market)?.quote??data.legs[0].quote;
  return response({quotes:[quote,{...quote,id:quote.id+':b',eventId:'game-b',event:'Another synthetic game'}]});
 });
 await a.wait('browse-odds');await a.click('sport-americanfootball_nfl');await a.click('game-game-a');
 return {...a,state,data};
}

test('props load on demand, mix with team lines and reach the Sevenfold report with exact player identity',async()=>{
 const a=await app();try{
  assert.equal(a.state.calls.filter(p=>p==='/api/odds/props').length,0);
  await a.click('quote-'+a.data.legs[0].quote.id);
  await a.click('load-props');await a.wait('prop-player-0');
  await a.click('prop-quote-'+a.data.legs[2].quote.id);
  await a.click('props-rush');await a.click('prop-quote-'+a.data.legs[3].quote.id);
  assert.match(a.find('parlay-count').textContent,/3\/8/);
  assert.equal(a.state.calls.filter(p=>p==='/api/odds/props').length,1);
  await a.click('analyze-parlay');await a.wait('game-reports');
  assert.equal(a.state.requests[0].legs[1].playerName,'Synthetic Player A');
  assert.match(a.d.body.textContent,/Whole-parlay win chance: research needed/);
  await a.click('report-toggle-1');await a.click('seven-toggle-1');
  assert.match(a.find('seven-responses-1').textContent,/Gus/);
  await a.click('props-alternate');assert.equal(Boolean(a.d.querySelector('[data-testid^="prop-quote-"]')),false);
  await a.click('load-props');await a.wait('prop-quote-'+a.data.legs[3].quote.id+':alt');
 }finally{a.close();}
});

test('empty or failed prop coverage removes old offers and does not substitute team lines',async()=>{
 const a=await app();try{
  await a.click('load-props');await a.wait('prop-player-0');
  a.state.fail=true;await a.click('load-props');assert.equal(Boolean(a.d.querySelector('[data-testid^="prop-quote-"]')),false);
  assert.match(a.d.body.textContent,/Synthetic props unavailable/);
  a.state.fail=false;a.state.empty=true;await a.click('load-props');
  assert.match(a.d.body.textContent,/No current passing yards/);assert.equal(Boolean(a.find('pick-0')),false);
 }finally{a.close();}
});

test('an old game response cannot populate the next selected game',async()=>{
 const a=await app();let resolve;try{
  a.state.deferred=new Promise(r=>resolve=r);
  await a.click('load-props');await a.click('game-game-b');
  resolve(response({quotes:a.data.legs.filter(l=>l.quote.playerName).map(l=>l.quote)}));
  await new Promise(r=>setTimeout(r,80));
  assert.equal(Boolean(a.d.querySelector('[data-testid^="prop-quote-"]')),false);
  assert.equal(Boolean(a.find('pick-0')),false);
 }finally{if(resolve)resolve(response({quotes:[]}));a.close();}
});
