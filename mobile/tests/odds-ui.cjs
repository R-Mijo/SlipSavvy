const {test}=require('node:test');
const assert=require('node:assert/strict');
const {setup,response}=require('./app-helper.cjs');
async function app(){
 const day=new Date(Date.now()+2*86400000).toISOString().slice(0,10),tomorrow=new Date(Date.parse(day+'T00:00:00Z')+86400000).toISOString().slice(0,10);
 const games=[...Array.from({length:9},(_,i)=>({id:'morning-'+i,at:day+'T08:00:00Z'})),{id:'afternoon',at:day+'T14:00:00Z'},{id:'night',at:day+'T20:00:00Z'},{id:'next-day',at:tomorrow+'T04:00:00Z'}];
 const state={fail:false,empty:false,quotes:[]};
 const a=await setup(async url=>{
  if(String(url).endsWith('/api/sports'))return response({sports:[{key:'americanfootball_ncaaf',title:'NCAA Football'}]});
  if(state.fail)return response({error:'Unavailable'},503);
  const market=new URL(url).searchParams.get('market');
  const quotes=games.map(g=>({id:g.id+':'+market,eventId:g.id,event:'Synthetic '+g.id,startAt:g.at,sport:'americanfootball_ncaaf',market,label:'Synthetic line',americanOdds:'-110',bookmaker:'FanDuel',bookmakerKey:'fanduel',outcome:'Synthetic Home',point:market==='h2h'?null:-3.5,homeTeam:'Synthetic Home',awayTeam:'Synthetic Away',updatedAt:new Date().toISOString(),fetchedAt:new Date().toISOString()}));
  state.quotes=quotes;return response({quotes:state.empty?[]:quotes});
 });
 await a.click('tab-check');await a.wait('browse-odds');await a.zone('UTC');await a.click('sport-americanfootball_ncaaf');
 return {...a,state,day,tomorrow};
}
test('NCAA dates, day parts and eight-game pages shorten the list',async()=>{
 const a=await app();try{
  await a.wait('date-'+a.day);await a.wait('game-morning-0');
  assert.equal(a.d.querySelectorAll('[data-testid^="game-"]').length,8);assert.equal(Boolean(a.find('game-morning-8')),false);
  await a.click('games-next');await a.wait('game-morning-8');assert.equal(a.d.querySelectorAll('[data-testid^="game-"]').length,1);
  await a.click('part-afternoon');await a.wait('game-afternoon');assert.equal(Boolean(a.find('game-morning-8')),false);
  await a.click('game-afternoon');await a.click('quote-afternoon:h2h');assert.match(a.find('parlay-count').textContent,/1\/8/);
  await a.click('market-spreads');await a.wait('quote-afternoon:spreads');
  await a.click('part-night');await a.wait('game-night');assert.equal(Boolean(a.find('quote-afternoon:spreads')),false);
  await a.click('date-'+a.tomorrow);await a.wait('game-next-day');assert.match(a.find('date-'+a.tomorrow).textContent,/20\d\d/);
 }finally{a.close();}
});
test('time-zone choice moves games into the corresponding local date and part',async()=>{
 const a=await app();try{
  await a.zone('America/Phoenix');await a.click('date-'+a.day);await a.click('part-night');await a.wait('game-next-day');
  assert.equal(Boolean(a.find('date-'+a.tomorrow)),false,'next UTC day is still the previous evening in Phoenix');
  assert.match(a.find('game-next-day').textContent,/9:00/);
  await a.zone('Asia/Tokyo');await a.wait('date-'+a.tomorrow);await a.click('date-'+a.tomorrow);await a.click('part-afternoon');await a.wait('game-next-day');
  assert.match(a.find('game-next-day').textContent,/1:00/);
  assert.match(a.find('timezone-toggle').textContent,/Asia\/Tokyo/);
 }finally{a.close();}
});
test('stale quotes, provider failures and missing games never leave selectable old lines',async()=>{
 const a=await app();try{
  await a.click('game-morning-0');await a.wait('quote-morning-0:h2h');
  a.state.quotes[0].updatedAt=new Date(Date.now()-901000).toISOString();await a.click('quote-morning-0:h2h');
  assert.equal(Boolean(a.find('quote-morning-0:h2h')),false);assert.equal(Boolean(a.find('pick-0')),false);
  a.state.fail=true;await a.click('refresh-odds');assert.equal(Boolean(a.find('game-morning-0')),false);
  a.state.fail=false;a.state.empty=true;await a.click('refresh-odds');assert.match(a.d.body.textContent,/No current pregame lines/);
 }finally{a.close();}
});
