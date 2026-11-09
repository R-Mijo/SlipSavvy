const {test}=require('node:test');
const assert=require('node:assert/strict');
const {setup,response,fixture,tick}=require('./app-helper.cjs');
async function app(){
 const data=await fixture(),state={odds:[],reports:[],hold:false,release:[],fail:false,failFirst:false,holdReport:false};
 const a=await setup(async(url,options={})=>{
  const u=new URL(url);
  if(u.pathname==='/api/sports')return response({sports:[{key:'basketball_nba',title:'NBA'}]});
  if(u.pathname==='/api/odds'){
   state.odds.push(url);if(state.hold)await new Promise(r=>state.release.push(r));
   if(state.fail)return response({error:'Synthetic unavailable'},503);
   return response({quotes:data.legs.map(l=>l.quote).filter(q=>q.market===u.searchParams.get('market'))});
  }
  assert.equal(u.pathname,'/api/game-reports');
  const input=JSON.parse(options.body);state.reports.push(input);
  if(state.holdReport)await new Promise(r=>state.release.push(r));
  const result=structuredClone(data);result.assessment.comparisonContext={totalStake:input.totalStake,minimumTotalReturn:input.minimumTotalReturn??null,stakeBasis:'fixed_total_capital'};
  result.legs=input.legs.map(l=>({...result.legs.find(v=>v.selection.eventId===l.eventId&&v.selection.market===l.market),id:l.id,selection:l}));
  if(state.failFirst&&state.reports.length===1){const leg=result.legs[0];leg.matchStatus='quote_unavailable';leg.eventRef=null;leg.quote=null;leg.price=null;leg.quoteSource=null;}
  return response(result);
 });
 return {...a,state};
}
test('builder proposes a below-target ticket, researches it automatically and compares fixed-budget splits',async()=>{
 const a=await app();try{
  await a.wait('savvy-builder');await a.wait('builder-legs-6');assert.equal(a.find('ticket-toggle').getAttribute('aria-expanded'),'false');await a.click('sports-handle');assert.equal(a.find('sports-handle').getAttribute('aria-expanded'),'false');await a.click('sports-handle');assert.equal(a.d.querySelectorAll('[role=tab]').length,2);
  await a.click('sport-basketball_nba');assert.equal(a.state.odds.length,0,'sport selection alone spends no odds requests');
  await a.click('builder-legs-2');await a.click('stake-20');await a.fill('builder-target','100');await a.click('build-savvy');
  await a.wait('builder-results');await a.wait('game-reports');
  assert.equal(a.state.odds.length,3);assert.equal(a.state.reports.length,3,'three candidates researched; chosen report reused');
  assert.equal(a.state.reports[0].totalStake,'20.00');assert.equal(a.state.reports[0].minimumTotalReturn,'100.00');
  assert.equal(new Set(a.state.reports[0].legs.map(l=>l.eventId)).size,2);
  assert.match(a.find('builder-results').textContent,/below target/);assert.match(a.find('confidence-meter').textContent,/27.4\/100/);
  assert.equal(a.find('parlay-info').getAttribute('aria-expanded'),'false');await a.click('parlay-info');
  assert.match(a.d.body.textContent,/Same \$20.00 budget/);assert.match(a.d.body.textContent,/Neither wins: \$0.00/);
  assert.equal(a.find('analytic-info').getAttribute('aria-expanded'),'false');
  assert.ok(a.find('builder-results').compareDocumentPosition(a.find('analyze-parlay'))&4);
  await a.click('tab-check');assert.match(a.find('parlay-count').textContent,/2\/8/);
 }finally{a.close();}
});
test('a failed current-line check changes the automatic suggestion and disables that candidate',async()=>{
 const a=await app();try{
  a.state.failFirst=true;await a.click('sport-basketball_nba');await a.click('builder-legs-2');await a.click('build-savvy');
  await a.wait('game-reports');assert.equal(a.state.reports.length,3);
  await a.click('candidate-comparisons');assert.equal(a.find('use-candidate-2').getAttribute('aria-disabled'),'true');
  assert.match(a.find('builder-results').textContent,/current price or game could not be matched/);
  await a.click('analytic-info');assert.doesNotMatch(a.find('game-reports').textContent,/This exact line is unavailable/);
 }finally{a.close();}
});
test('cancelling during candidate research never installs a late report or ticket',async()=>{
 const a=await app();try{
  a.state.holdReport=true;await a.click('sport-basketball_nba');await a.click('builder-legs-2');await a.click('build-savvy');
  const end=Date.now()+5000;while(!a.state.reports.length&&Date.now()<end)await tick();assert.equal(a.state.reports.length,1);
  await a.click('cancel-builder');a.state.release.forEach(r=>r());await tick();
  assert.equal(Boolean(a.find('builder-results')),false);assert.equal(Boolean(a.find('pick-0')),false);assert.equal(Boolean(a.find('game-reports')),false);
  assert.equal(a.state.reports.length,1);
 }finally{a.state.release.forEach(r=>r());a.close();}
});
test('invalid targets use no odds quota and changed filters suppress in-flight candidates',async()=>{
 const a=await app();try{
  await a.click('sport-basketball_nba');await a.fill('builder-target','0');await a.click('build-savvy');
  await a.wait('builder-error');assert.equal(a.state.odds.length,0);
  await a.fill('builder-target','100');await a.click('builder-legs-2');a.state.hold=true;
  await a.click('build-savvy');await a.wait('cancel-builder');await a.click('stake-5');
  a.state.release.forEach(r=>r());await tick();
  assert.equal(Boolean(a.find('builder-results')),false);assert.equal(Boolean(a.find('pick-0')),false);assert.equal(a.state.reports.length,0);
  a.state.hold=false;a.state.fail=true;await a.click('build-savvy');await a.wait('builder-error');
  assert.equal(Boolean(a.find('builder-results')),false);
 }finally{a.state.release.forEach(r=>r());a.close();}
});
